from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from models import AlertDB, IncidentDB

CORRELATION_THRESHOLD = 55.0

ALERT_RELATIONSHIPS = [
    {"types": {"device_unreachable", "link_down", "packet_loss"}, "score": 35.0},
    {"types": {"high_latency", "packet_loss"}, "score": 25.0},
    {"types": {"device_unreachable", "service_unavailable"}, "score": 30.0},
    {"types": {"authentication_failure"}, "score": 20.0},
    {"types": {"interface_error", "route_failure"}, "score": 25.0},
    {"types": {"cpu_high", "memory_high"}, "score": 25.0}
]

def check_duplicate_alert(db: Session, alert_data: dict) -> Optional[AlertDB]:
    """
    Checks if a matching alert arrived recently (same device, alert_type, message pattern).
    If found within 10 minutes, updates existing alert's occurrence_count and return it.
    """
    ten_mins_ago = datetime.utcnow() - timedelta(minutes=10)
    
    existing = db.query(AlertDB).filter(
        AlertDB.device == alert_data["device"],
        AlertDB.alert_type == alert_data["alert_type"],
        AlertDB.message == alert_data["message"],
        AlertDB.last_seen >= ten_mins_ago
    ).first()

    if existing:
        existing.occurrence_count += 1
        existing.last_seen = datetime.utcnow()
        if alert_data.get("latency"):
            existing.latency = alert_data["latency"]
        if alert_data.get("packet_loss"):
            existing.packet_loss = alert_data["packet_loss"]
        if alert_data.get("authentication_failures"):
            existing.authentication_failures += alert_data.get("authentication_failures", 0)
        db.commit()
        db.refresh(existing)
        return existing
    
    return None

def compute_correlation_score(alert: AlertDB, incident_alerts: List[AlertDB]) -> Tuple[float, List[str]]:
    """
    Computes multi-signal correlation score between a new alert and an existing list of incident alerts.
    Signals:
    1. Device match / topology
    2. Time proximity
    3. Network relationship (IP subnets / source-dest)
    4. Alert relationship patterns
    5. Message similarity
    """
    reasons = []
    if not incident_alerts:
        return 0.0, reasons

    device_score = 0.0
    time_score = 0.0
    network_score = 0.0
    relationship_score = 0.0
    message_score = 0.0

    # 1. Device match
    devices = {a.device for a in incident_alerts}
    if alert.device in devices:
        device_score = 35.0
        reasons.append(f"Same device ({alert.device}) affected")
    else:
        # Check device naming convention or topology (e.g. RTR-01 and RTR-02 or same prefix)
        alert_prefix = alert.device.split("-")[0] if "-" in alert.device else alert.device
        if any(a.device.startswith(alert_prefix) for a in incident_alerts):
            device_score = 20.0
            reasons.append(f"Adjacent device in same topology group ({alert_prefix})")

    # 2. Time correlation
    latest_time = max(a.timestamp for a in incident_alerts)
    time_diff = abs((alert.timestamp - latest_time).total_seconds()) / 60.0  # in minutes

    if time_diff <= 2.0:
        time_score = 35.0
        reasons.append(f"Occurred within 2-minute window ({time_diff:.1f}m)")
    elif time_diff <= 5.0:
        time_score = 25.0
        reasons.append(f"Occurred within 5-minute window ({time_diff:.1f}m)")
    elif time_diff <= 10.0:
        time_score = 15.0
        reasons.append(f"Occurred within 10-minute window ({time_diff:.1f}m)")
    else:
        time_score = 5.0

    # 3. Network relationship
    ips = set()
    for a in incident_alerts:
        if a.source_ip: ips.add(a.source_ip)
        if a.destination_ip: ips.add(a.destination_ip)
    
    if (alert.source_ip and alert.source_ip in ips) or (alert.destination_ip and alert.destination_ip in ips):
        network_score = 20.0
        reasons.append("Shared IP source/destination relationship detected")

    # 4. Alert relationship
    combined_types = {a.alert_type for a in incident_alerts} | {alert.alert_type}
    for rel in ALERT_RELATIONSHIPS:
        if rel["types"].issubset(combined_types):
            relationship_score = max(relationship_score, rel["score"])
            rel_str = " + ".join(sorted(list(rel["types"])))
            reasons.append(f"Matching alert combination pattern ({rel_str})")

    # 5. Message similarity
    alert_tokens = set(alert.message.lower().split())
    for a in incident_alerts:
        other_tokens = set(a.message.lower().split())
        overlap = alert_tokens.intersection(other_tokens)
        if len(overlap) >= 2:
            message_score = 15.0
            reasons.append("Similar alert message signature")
            break

    total_score = min(100.0, device_score + time_score + network_score + relationship_score + message_score)
    return total_score, list(set(reasons))

def correlate_alert(db: Session, alert: AlertDB) -> Tuple[Optional[IncidentDB], float, List[str]]:
    """
    Correlates an alert with active incidents.
    Returns (IncidentDB, score, reasons) if correlated, or (None, score, reasons) if classified as noise.
    """
    active_incidents = db.query(IncidentDB).filter(IncidentDB.status != "RESOLVED").all()

    best_incident = None
    best_score = 0.0
    best_reasons = []

    for inc in active_incidents:
        inc_alerts = inc.alerts
        score, reasons = compute_correlation_score(alert, inc_alerts)
        if score > best_score:
            best_score = score
            best_incident = inc
            best_reasons = reasons

    if best_incident and best_score >= CORRELATION_THRESHOLD:
        alert.status = "correlated"
        alert.incident_id = best_incident.id
        db.commit()
        return best_incident, best_score, best_reasons

    # Check if there are other unassigned recent alerts that can form a new incident with this alert
    ten_mins_ago = datetime.utcnow() - timedelta(minutes=10)
    recent_unassigned = db.query(AlertDB).filter(
        AlertDB.incident_id.is_(None),
        AlertDB.id != alert.id,
        AlertDB.timestamp >= ten_mins_ago
    ).all()

    group_candidate = []
    group_reasons = []
    group_score = 0.0

    for candidate in recent_unassigned:
        score, reasons = compute_correlation_score(alert, [candidate])
        if score >= CORRELATION_THRESHOLD:
            group_candidate.append(candidate)
            group_score = max(group_score, score)
            group_reasons.extend(reasons)

    if group_candidate:
        # Create a new incident for this group
        inc_count = db.query(IncidentDB).count() + 1001
        new_inc_id = f"INC-{inc_count}"
        
        new_inc = IncidentDB(
            id=new_inc_id,
            root_device=alert.device,
            priority="MEDIUM",
            impact="Medium",
            status="OPEN",
            correlation_score=group_score,
            confidence=round(group_score * 0.95, 1)
        )
        db.add(new_inc)
        db.commit()

        # Link alert & candidate alerts
        alert.status = "correlated"
        alert.incident_id = new_inc_id
        alert.noise_reason = None

        for cand in group_candidate:
            cand.status = "correlated"
            cand.incident_id = new_inc_id
            cand.noise_reason = None

        db.commit()
        db.refresh(new_inc)
        return new_inc, group_score, list(set(group_reasons))

    # Below threshold -> classify as Noise
    alert.status = "noise"
    alert.noise_reason = "Not grouped because no related network event was detected within the correlation window."
    db.commit()
    return None, best_score, ["Below correlation threshold; classified as noise."]
