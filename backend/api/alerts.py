from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import AlertDB, IncidentDB
from schemas import AlertCreate, AlertResponse
from services.correlation_engine import check_duplicate_alert, correlate_alert
from services.priority_engine import calculate_incident_priority
from services.runbook_engine import match_runbook_for_incident
from services.escalation_engine import create_incident_escalation

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

@router.post("", response_model=AlertResponse)
def create_alert(payload: AlertCreate, db: Session = Depends(get_db)):
    alert_dict = payload.model_dump()
    if not alert_dict.get("timestamp"):
        alert_dict["timestamp"] = datetime.utcnow()

    # 1. Duplicate Detection
    existing_duplicate = check_duplicate_alert(db, alert_dict)
    if existing_duplicate:
        # Re-evaluate parent incident if correlated
        if existing_duplicate.incident_id:
            parent_inc = db.query(IncidentDB).filter(IncidentDB.id == existing_duplicate.incident_id).first()
            if parent_inc:
                prio, imp, conf, expl = calculate_incident_priority(parent_inc, parent_inc.alerts)
                parent_inc.priority = prio
                parent_inc.impact = imp
                parent_inc.confidence = conf
                db.commit()
        return existing_duplicate

    # 2. Store new alert
    new_alert = AlertDB(
        timestamp=alert_dict["timestamp"],
        alert_type=alert_dict["alert_type"],
        severity=alert_dict["severity"],
        device=alert_dict["device"],
        source_ip=alert_dict.get("source_ip"),
        destination_ip=alert_dict.get("destination_ip"),
        location=alert_dict.get("location"),
        message=alert_dict["message"],
        latency=alert_dict.get("latency", 0.0) or 0.0,
        packet_loss=alert_dict.get("packet_loss", 0.0) or 0.0,
        authentication_failures=alert_dict.get("authentication_failures", 0) or 0,
        status="new",
        first_seen=alert_dict["timestamp"],
        last_seen=alert_dict["timestamp"],
        occurrence_count=1
    )
    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)

    # 3. Correlation Engine
    incident, corr_score, reasons = correlate_alert(db, new_alert)

    # 4. If correlated to an incident, update Priority, Runbook Matching, Escalation
    if incident:
        inc_alerts = incident.alerts
        prio, imp, conf, expl = calculate_incident_priority(incident, inc_alerts)
        incident.priority = prio
        incident.impact = imp
        incident.confidence = conf
        incident.correlation_score = max(incident.correlation_score, corr_score)
        
        # Runbook Match
        match_res = match_runbook_for_incident(db, incident)
        if match_res:
            incident.runbook_id = match_res["runbook_id"]
            incident.recommendation = match_res["recommended_action"]
            incident.root_cause = f"Matched {match_res['runbook_title']} pattern"
        else:
            # Escalation when no runbook matches
            create_incident_escalation(
                db, 
                incident, 
                reason="Alert signature did not match any standard operational runbook."
            )

        db.commit()

    db.refresh(new_alert)
    return new_alert

@router.get("", response_model=List[AlertResponse])
def get_alerts(
    status: Optional[str] = Query(None, description="Filter by status: new, correlated, noise"),
    db: Session = Depends(get_db)
):
    query = db.query(AlertDB)
    if status and status != "all":
        query = query.filter(AlertDB.status == status)
    return query.order_by(AlertDB.timestamp.desc()).all()

@router.delete("")
def clear_alerts(db: Session = Depends(get_db)):
    db.query(AlertDB).delete()
    db.query(IncidentDB).delete()
    db.commit()
    return {"message": "All alerts and incidents cleared successfully"}
