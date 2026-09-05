import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from models import IncidentDB, EscalationDB

def create_incident_escalation(
    db: Session, 
    incident: IncidentDB, 
    reason: str = "No matching runbook found for observed symptom combination."
) -> EscalationDB:
    """
    Creates an EscalationDB record for an incident while preserving full context and evidence.
    """
    # Check if escalation already exists
    existing = db.query(EscalationDB).filter(EscalationDB.incident_id == incident.id).first()
    if existing:
        return existing

    # Determine assigned team based on root device and alert types
    alerts = incident.alerts
    alert_types = {a.alert_type for a in alerts}

    if "authentication_failure" in alert_types:
        assigned_team = "Security Operations Center (SOC)"
    elif any(t in alert_types for t in ["cpu_high", "memory_high", "service_unavailable"]):
        assigned_team = "Infrastructure Operations"
    else:
        assigned_team = "Network Engineering (L3)"

    # Package evidence
    alert_summaries = [
        {
            "id": a.id,
            "timestamp": a.timestamp.isoformat(),
            "alert_type": a.alert_type,
            "severity": a.severity,
            "device": a.device,
            "message": a.message,
            "occurrence_count": a.occurrence_count,
            "metrics": {
                "latency": a.latency,
                "packet_loss": a.packet_loss,
                "auth_failures": a.authentication_failures
            }
        }
        for a in alerts
    ]

    evidence_dict = {
        "escalation_reason": reason,
        "root_device": incident.root_device,
        "correlation_score": incident.correlation_score,
        "confidence": incident.confidence,
        "total_grouped_alerts": len(alerts),
        "total_occurrences": sum(a.occurrence_count for a in alerts),
        "distinct_alert_types": list(alert_types),
        "evaluated_runbooks_count": 4,
        "best_runbook_match": None
    }

    summary = (
        f"Automated Escalation for Incident {incident.id} ({incident.priority} Priority). "
        f"Target device {incident.root_device} affected across {len(alerts)} correlated alert events. "
        f"Reason: {reason}"
    )

    esc_count = db.query(EscalationDB).count() + 1001
    esc_id = f"ESC-{esc_count}"

    escalation = EscalationDB(
        id=esc_id,
        incident_id=incident.id,
        created_at=datetime.utcnow(),
        priority=incident.priority,
        summary=summary,
        evidence=json.dumps(evidence_dict),
        grouped_alerts=json.dumps(alert_summaries),
        previous_recommendation=incident.recommendation or "None available",
        assigned_team=assigned_team,
        status="OPEN"
    )

    incident.escalated = True
    incident.escalation_status = "ESCALATED"
    incident.status = "ESCALATED"

    db.add(escalation)
    db.commit()
    db.refresh(escalation)
    return escalation
