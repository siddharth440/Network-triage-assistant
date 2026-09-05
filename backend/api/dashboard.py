from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import AlertDB, IncidentDB, EscalationDB
from schemas import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_alerts = db.query(AlertDB).count()
    active_incidents = db.query(IncidentDB).filter(IncidentDB.status.in_(["OPEN", "IN_PROGRESS"])).count()
    critical_incidents = db.query(IncidentDB).filter(IncidentDB.priority == "CRITICAL", IncidentDB.status != "RESOLVED").count()
    high_priority_incidents = db.query(IncidentDB).filter(IncidentDB.priority == "HIGH", IncidentDB.status != "RESOLVED").count()
    noise_alerts = db.query(AlertDB).filter(AlertDB.status == "noise").count()
    escalated_incidents = db.query(EscalationDB).count()

    # Recent activity stream
    recent_alerts = db.query(AlertDB).order_by(AlertDB.timestamp.desc()).limit(10).all()
    recent_activity = [
        {
            "id": a.id,
            "timestamp": a.timestamp.strftime("%H:%M:%S"),
            "device": a.device,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "message": a.message,
            "status": a.status,
            "incident_id": a.incident_id,
            "occurrence_count": a.occurrence_count
        }
        for a in recent_alerts
    ]

    return DashboardStats(
        total_alerts=total_alerts,
        active_incidents=active_incidents,
        critical_incidents=critical_incidents,
        high_priority_incidents=high_priority_incidents,
        noise_alerts=noise_alerts,
        escalated_incidents=escalated_incidents,
        recent_activity=recent_activity
    )
