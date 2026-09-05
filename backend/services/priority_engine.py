from typing import Dict, Any, Tuple, List
from models import IncidentDB, AlertDB

CRITICAL_INFRA_KEYWORDS = ["RTR", "GW", "CORE", "FW", "BACKBONE", "DC"]

def calculate_incident_priority(incident: IncidentDB, alerts: List[AlertDB]) -> Tuple[str, str, float, str]:
    """
    Calculates incident priority, impact, confidence score, and clear justification statement.
    Returns: (priority, impact, confidence, explanation)
    """
    if not alerts:
        return "LOW", "Low", 50.0, "Minor informational incident."

    score = 0.0
    reasons = []

    # 1. Alert Severities
    severities = [a.severity.lower() for a in alerts]
    if "critical" in severities:
        score += 40.0
        reasons.append("contains critical severity alerts")
    elif "high" in severities:
        score += 25.0
        reasons.append("contains high severity alerts")
    elif "medium" in severities:
        score += 15.0

    # 2. Count of correlated alerts
    alert_count = len(alerts)
    if alert_count >= 5:
        score += 20.0
        reasons.append(f"high alert volume ({alert_count} correlated events)")
    elif alert_count >= 3:
        score += 10.0
        reasons.append(f"multiple correlated alerts ({alert_count} events)")

    # 3. Affected Devices Count & Critical Infrastructure Check
    devices = {a.device for a in alerts}
    device_count = len(devices)
    if device_count > 1:
        score += 15.0
        reasons.append(f"spans multiple devices ({device_count} devices: {', '.join(devices)})")

    is_critical_infra = any(
        any(kw in d.upper() for kw in CRITICAL_INFRA_KEYWORDS)
        for d in devices
    )
    if is_critical_infra:
        score += 20.0
        reasons.append("involves core infrastructure nodes")

    # 4. Metrics (Packet loss, Latency, Auth failures)
    max_packet_loss = max((a.packet_loss for a in alerts), default=0.0)
    max_latency = max((a.latency for a in alerts), default=0.0)
    total_auth_failures = sum(a.authentication_failures for a in alerts)

    if max_packet_loss >= 50.0:
        score += 20.0
        reasons.append(f"severe packet loss ({max_packet_loss}%)")
    elif max_packet_loss >= 20.0:
        score += 10.0

    if max_latency >= 150.0:
        score += 15.0
        reasons.append(f"extreme latency ({max_latency}ms)")

    if total_auth_failures >= 5:
        score += 20.0
        reasons.append(f"elevated authentication failure rate ({total_auth_failures} failures)")

    # Normalize score
    normalized_score = min(100.0, score)

    # Priority & Impact classification
    if normalized_score >= 70.0:
        priority = "CRITICAL"
        impact = "High"
        confidence = min(98.0, 85.0 + (normalized_score - 70.0) * 0.4)
    elif normalized_score >= 45.0:
        priority = "HIGH"
        impact = "High" if device_count > 1 else "Medium"
        confidence = min(95.0, 75.0 + (normalized_score - 45.0) * 0.4)
    elif normalized_score >= 25.0:
        priority = "MEDIUM"
        impact = "Medium"
        confidence = round(70.0 + (normalized_score - 25.0) * 0.3, 1)
    else:
        priority = "LOW"
        impact = "Low"
        confidence = 65.0

    # Build readable natural language justification
    if reasons:
        explanation = f"{priority} priority because " + ", ".join(reasons) + "."
    else:
        explanation = f"{priority} priority based on standard operational rules."

    return priority, impact, round(confidence, 1), explanation
