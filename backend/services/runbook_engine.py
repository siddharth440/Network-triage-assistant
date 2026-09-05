import os
import json
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from models import IncidentDB, AlertDB, RunbookDB

def load_runbooks_from_disk() -> List[Dict[str, Any]]:
    """Loads all runbook JSON files from backend/runbooks/ directory."""
    runbook_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "runbooks")
    runbooks = []
    if os.path.exists(runbook_dir):
        for fname in os.listdir(runbook_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(runbook_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        runbooks.append(json.load(f))
                except Exception as e:
                    print(f"Error loading runbook {fname}: {e}")
    return runbooks

def sync_runbooks_to_db(db: Session):
    """Ensures database runbooks table has up-to-date JSON definitions."""
    disk_runbooks = load_runbooks_from_disk()
    for rb in disk_runbooks:
        existing = db.query(RunbookDB).filter(RunbookDB.id == rb["id"]).first()
        if not existing:
            db_rb = RunbookDB(
                id=rb["id"],
                title=rb["title"],
                description=rb.get("description", ""),
                conditions=json.dumps(rb.get("conditions", {})),
                steps=json.dumps(rb.get("steps", [])),
                category=rb.get("category", "General")
            )
            db.add(db_rb)
    db.commit()

def calculate_runbook_match(incident_alerts: List[AlertDB], runbook_data: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    Calculates match score (0-100%) between incident alerts and runbook conditions.
    Returns (score, list of matching symptom explanations).
    """
    conditions = runbook_data.get("conditions", {})
    required_types = set(conditions.get("alert_types", []))
    min_symptoms = conditions.get("required_symptoms_count", 1)
    
    incident_types = {a.alert_type for a in incident_alerts}
    matched_types = required_types.intersection(incident_types)
    
    if not matched_types:
        return 0.0, []

    symptom_reasons = []
    score_points = 0.0

    # 1. Alert Type Match Ratio
    type_ratio = len(matched_types) / len(required_types) if required_types else 0.0
    score_points += type_ratio * 60.0

    for atype in matched_types:
        matching_alert = next((a for a in incident_alerts if a.alert_type == atype), None)
        if matching_alert:
            symptom_reasons.append(f"{matching_alert.device} reported '{atype}' alert ({matching_alert.message})")

    # 2. Metric Threshold Checks
    if "min_packet_loss" in conditions:
        max_loss = max((a.packet_loss for a in incident_alerts), default=0.0)
        if max_loss >= conditions["min_packet_loss"]:
            score_points += 20.0
            symptom_reasons.append(f"Packet loss reached {max_loss}% (exceeds {conditions['min_packet_loss']}% threshold)")

    if "min_latency_ms" in conditions:
        max_lat = max((a.latency for a in incident_alerts), default=0.0)
        if max_lat >= conditions["min_latency_ms"]:
            score_points += 20.0
            symptom_reasons.append(f"Latency reached {max_lat}ms (exceeds {conditions['min_latency_ms']}ms threshold)")

    if "min_auth_failures" in conditions:
        total_auth = sum(a.authentication_failures for a in incident_alerts)
        if total_auth >= conditions["min_auth_failures"]:
            score_points += 20.0
            symptom_reasons.append(f"Authentication failures reached {total_auth} attempts")

    # 3. Frequency / Time window signal
    if len(incident_alerts) >= 3:
        score_points += 10.0
        symptom_reasons.append(f"{len(incident_alerts)} alerts detected in close temporal correlation")

    final_score = min(99.0, max(0.0, score_points))
    
    # Require minimum symptoms count
    if len(matched_types) < min_symptoms and len(incident_types) > 1:
        final_score = final_score * 0.5

    return round(final_score, 1), symptom_reasons

def match_runbook_for_incident(db: Session, incident: IncidentDB) -> Optional[Dict[str, Any]]:
    """
    Finds best matching runbook for an incident.
    Returns dictionary with match details or None if no runbook meets threshold.
    """
    sync_runbooks_to_db(db)
    db_runbooks = db.query(RunbookDB).all()
    
    alerts = incident.alerts
    if not alerts:
        return None

    best_rb = None
    best_score = 0.0
    best_reasons = []
    best_steps = []

    for rb in db_runbooks:
        rb_data = {
            "id": rb.id,
            "title": rb.title,
            "conditions": json.loads(rb.conditions or "{}"),
            "steps": json.loads(rb.steps or "[]"),
            "category": rb.category
        }
        
        score, reasons = calculate_runbook_match(alerts, rb_data)
        if score > best_score:
            best_score = score
            best_rb = rb_data
            best_reasons = reasons
            best_steps = rb_data["steps"]

    # Minimum threshold to claim a match
    if best_rb and best_score >= 45.0:
        root_dev = incident.root_device or "target device"
        first_step = best_steps[0] if best_steps else "Inspect interface and device logs."
        
        recommended_action = f"Check {root_dev}: {first_step}"
        
        return {
            "runbook_id": best_rb["id"],
            "runbook_title": best_rb["title"],
            "match_confidence": best_score,
            "recommended_action": recommended_action,
            "why": best_reasons,
            "steps": best_steps
        }

    return None
