from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import IncidentDB, AlertDB
from schemas import IncidentResponse, ExplainableRecommendation, TimelineEvent
from services.priority_engine import calculate_incident_priority
from services.runbook_engine import match_runbook_for_incident
from services.escalation_engine import create_incident_escalation
from services.correlation_engine import compute_correlation_score

router = APIRouter(prefix="/api/incidents", tags=["incidents"])

def build_incident_response(db: Session, inc: IncidentDB) -> IncidentResponse:
    alerts = inc.alerts
    total_duplicates = sum(a.occurrence_count - 1 for a in alerts)

    # Re-calculate priority & match details for fresh response
    prio, imp, conf, expl = calculate_incident_priority(inc, alerts)
    rb_match = match_runbook_for_incident(db, inc)

    explainable_rec = None
    if rb_match:
        explainable_rec = ExplainableRecommendation(
            recommended_action=rb_match["recommended_action"],
            why=rb_match["why"],
            runbook_title=rb_match["runbook_title"],
            runbook_id=rb_match["runbook_id"],
            match_confidence=rb_match["match_confidence"]
        )
    else:
        why_bullets = [
            f"Target device {inc.root_device} experiencing critical unhandled alerts",
            f"{len(alerts)} correlated events detected",
            "Evaluated against 4 standard runbooks with 0% match confidence"
        ]
        explainable_rec = ExplainableRecommendation(
            recommended_action=f"Escalate incident {inc.id} to Network Engineering for manual investigation.",
            why=why_bullets,
            runbook_title="None (Escalated)",
            runbook_id=None,
            match_confidence=0.0
        )

    # Build chronological timeline
    sorted_alerts = sorted(alerts, key=lambda x: x.timestamp)
    timeline = [
        TimelineEvent(
            timestamp=a.timestamp.strftime("%H:%M:%S"),
            event=f"{a.device} — {a.message} (Occurrences: {a.occurrence_count})",
            alert_type=a.alert_type,
            severity=a.severity
        )
        for a in sorted_alerts
    ]

    # Build correlation explanation reasons
    correlation_reasons = []
    if len(alerts) > 1:
        first = sorted_alerts[0]
        for other in sorted_alerts[1:]:
            _, reasons = compute_correlation_score(other, [first])
            correlation_reasons.extend(reasons)
        correlation_reasons = list(set(correlation_reasons))
    else:
        correlation_reasons = ["Primary device incident trigger event"]

    return IncidentResponse(
        id=inc.id,
        created_at=inc.created_at,
        updated_at=inc.updated_at,
        root_device=inc.root_device,
        priority=prio,
        impact=imp,
        status=inc.status,
        root_cause=inc.root_cause or f"Potential issue on {inc.root_device}",
        correlation_score=inc.correlation_score,
        confidence=conf,
        recommendation=inc.recommendation or explainable_rec.recommended_action,
        runbook_id=inc.runbook_id,
        escalated=inc.escalated,
        escalation_status=inc.escalation_status,
        alerts=alerts,
        duplicate_count=total_duplicates,
        explainable_recommendation=explainable_rec,
        timeline=timeline,
        correlation_reasons=correlation_reasons
    )

@router.get("", response_model=List[IncidentResponse])
def get_incidents(db: Session = Depends(get_db)):
    incidents = db.query(IncidentDB).order_by(IncidentDB.created_at.desc()).all()
    return [build_incident_response(db, inc) for inc in incidents]

@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident_detail(incident_id: str, db: Session = Depends(get_db)):
    inc = db.query(IncidentDB).filter(IncidentDB.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return build_incident_response(db, inc)

@router.post("/process")
def process_unassigned_alerts(db: Session = Depends(get_db)):
    """Manually re-run correlation and prioritization over any unprocessed alerts."""
    unprocessed = db.query(AlertDB).filter(AlertDB.status == "new").all()
    correlated_count = 0
    noise_count = 0

    from services.correlation_engine import correlate_alert

    for alert in unprocessed:
        inc, score, reasons = correlate_alert(db, alert)
        if inc:
            correlated_count += 1
            inc_alerts = inc.alerts
            prio, imp, conf, expl = calculate_incident_priority(inc, inc_alerts)
            inc.priority = prio
            inc.impact = imp
            inc.confidence = conf
            
            rb_match = match_runbook_for_incident(db, inc)
            if rb_match:
                inc.runbook_id = rb_match["runbook_id"]
                inc.recommendation = rb_match["recommended_action"]
            else:
                create_incident_escalation(db, inc, reason="No matching runbook found.")
            db.commit()
        else:
            noise_count += 1

    return {
        "processed": len(unprocessed),
        "correlated": correlated_count,
        "noise": noise_count
    }
