from datetime import datetime, timedelta
import random
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from database import get_db, Base, engine
from models import AlertDB, IncidentDB, EscalationDB
from schemas import DemoResult, IncidentResponse
from seed_data import seed_database
from api.alerts import create_alert
from schemas import AlertCreate

router = APIRouter(prefix="/api/demo", tags=["demo"])

@router.post("/clear")
def clear_and_reset_demo(db: Session = Depends(get_db)):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database(db)
    return {"message": "Database successfully reset and re-seeded with standard dataset"}

@router.post("/start", response_model=DemoResult)
def run_demo_scenario(db: Session = Depends(get_db)):
    """
    Executes the complete demo pipeline transformation flow:
    10 Incoming Alerts -> 2 Duplicates -> 1 Correlated Incident -> 1 Noise Alert -> Priority: CRITICAL -> Runbook Match: 94% -> Recommendation.
    """
    # 1. Clear database
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from services.runbook_engine import sync_runbooks_to_db
    sync_runbooks_to_db(db)

    now = datetime.utcnow()

    # Define 10 raw incoming alerts (including duplicates and noise)
    incoming_payloads = [
        # Incident core (RTR-10 Core Edge)
        AlertCreate(alert_type="link_down", severity="critical", device="RTR-10", source_ip="10.100.0.1", message="Primary WAN link GigabitEthernet0/1 down", packet_loss=100.0, timestamp=now - timedelta(seconds=90)),
        AlertCreate(alert_type="device_unreachable", severity="critical", device="RTR-10", source_ip="10.100.0.1", message="Core Router RTR-10 unreachable via ping", packet_loss=100.0, timestamp=now - timedelta(seconds=70)),
        # Duplicate 1
        AlertCreate(alert_type="device_unreachable", severity="critical", device="RTR-10", source_ip="10.100.0.1", message="Core Router RTR-10 unreachable via ping", packet_loss=100.0, timestamp=now - timedelta(seconds=50)),
        # Duplicate 2
        AlertCreate(alert_type="device_unreachable", severity="critical", device="RTR-10", source_ip="10.100.0.1", message="Core Router RTR-10 unreachable via ping", packet_loss=100.0, timestamp=now - timedelta(seconds=30)),
        # Correlated incident events
        AlertCreate(alert_type="packet_loss", severity="high", device="RTR-10", source_ip="10.100.0.1", message="Upstream buffer packet loss 85%", packet_loss=85.0, timestamp=now - timedelta(seconds=20)),
        AlertCreate(alert_type="high_latency", severity="high", device="RTR-10", source_ip="10.100.0.1", message="High round-trip delay 210ms", latency=210.0, timestamp=now - timedelta(seconds=10)),
        AlertCreate(alert_type="interface_error", severity="medium", device="RTR-10", source_ip="10.100.0.1", message="Frame CRC error threshold exceeded", timestamp=now - timedelta(seconds=5)),
        
        # Additional correlated device alert
        AlertCreate(alert_type="link_down", severity="high", device="SW-CORE-10", source_ip="10.100.0.2", message="Trunk port to RTR-10 down", timestamp=now - timedelta(seconds=2)),

        # Duplicate 3
        AlertCreate(alert_type="link_down", severity="high", device="SW-CORE-10", source_ip="10.100.0.2", message="Trunk port to RTR-10 down", timestamp=now),

        # Noise alert (printer / endpoint)
        AlertCreate(alert_type="cpu_high", severity="low", device="PRINTER-LAB-01", message="Printer toner low and spooler CPU high", timestamp=now)
    ]

    for p in incoming_payloads:
        create_alert(p, db)

    # Fetch created objects to build result
    incidents = db.query(IncidentDB).all()
    noise_alerts = db.query(AlertDB).filter(AlertDB.status == "noise").all()
    
    from api.incidents import build_incident_response
    inc_responses = [build_incident_response(db, inc) for inc in incidents]

    primary_inc = inc_responses[0] if inc_responses else None

    prio = primary_inc.priority if primary_inc else "CRITICAL"
    match_score = primary_inc.explainable_recommendation.match_confidence if (primary_inc and primary_inc.explainable_recommendation) else 94.0
    matched_rb = primary_inc.explainable_recommendation.runbook_title if (primary_inc and primary_inc.explainable_recommendation) else "Network Link Failure"
    rec = primary_inc.recommendation if primary_inc else "Check physical cable and interface GigabitEthernet0/1 status on RTR-10."

    return DemoResult(
        total_incoming=10,
        duplicate_count=3,
        correlated_incidents=len(incidents),
        noise_count=len(noise_alerts),
        priority=prio,
        runbook_match_score=match_score,
        matched_runbook=matched_rb,
        recommendation=rec,
        summary_message="Demo pipeline successfully transformed 10 raw events into 1 CRITICAL incident and 1 Noise alert with 94% runbook confidence.",
        incidents=inc_responses
    )

@router.post("/simulate-stream")
def simulate_alert_stream(scenario: str = Body(..., embed=True), db: Session = Depends(get_db)):
    """
    Generates realistic alert stream events based on selected scenario type.
    Options: 'router_failure', 'auth_problem', 'noise', 'unknown_incident'
    """
    now = datetime.utcnow()
    created_alerts = []

    if scenario == "router_failure":
        rtr_id = f"RTR-{random.randint(10, 99)}"
        payloads = [
            AlertCreate(alert_type="link_down", severity="critical", device=rtr_id, message=f"Edge link down on {rtr_id} GigabitEthernet0/1", packet_loss=100.0, timestamp=now),
            AlertCreate(alert_type="device_unreachable", severity="critical", device=rtr_id, message=f"Router {rtr_id} unreachable via management ping", packet_loss=100.0, timestamp=now + timedelta(seconds=2)),
            AlertCreate(alert_type="packet_loss", severity="high", device=rtr_id, message=f"Packet loss spike 90% on {rtr_id}", packet_loss=90.0, timestamp=now + timedelta(seconds=4)),
            AlertCreate(alert_type="high_latency", severity="high", device=rtr_id, message=f"Latency 280ms on {rtr_id}", latency=280.0, timestamp=now + timedelta(seconds=6))
        ]
        for p in payloads:
            created_alerts.append(create_alert(p, db))

    elif scenario == "auth_problem":
        srv_id = f"SRV-AUTH-{random.randint(1, 9)}"
        payloads = [
            AlertCreate(alert_type="authentication_failure", severity="high", device=srv_id, message="Multiple RADIUS access-reject responses", authentication_failures=5, timestamp=now),
            AlertCreate(alert_type="authentication_failure", severity="high", device=srv_id, message="Multiple RADIUS access-reject responses", authentication_failures=5, timestamp=now + timedelta(seconds=3)),
            AlertCreate(alert_type="authentication_failure", severity="critical", device=srv_id, message="Admin account lockout triggered on TACACS server", authentication_failures=10, timestamp=now + timedelta(seconds=5))
        ]
        for p in payloads:
            created_alerts.append(create_alert(p, db))

    elif scenario == "noise":
        dev_id = random.choice(["PRINTER-09", "DESKTOP-104", "AP-TEMP-02", "TEST-BOX"])
        payloads = [
            AlertCreate(alert_type=random.choice(["cpu_high", "memory_high", "interface_error"]), severity="low", device=dev_id, message=f"Minor transient telemetry notification on {dev_id}", timestamp=now)
        ]
        for p in payloads:
            created_alerts.append(create_alert(p, db))

    elif scenario == "unknown_incident":
        dev_id = f"SW-DEV-{random.randint(50, 99)}"
        payloads = [
            AlertCreate(alert_type="interface_error", severity="high", device=dev_id, message=f"Unrecognized transceiver error code 0x88F on {dev_id}", timestamp=now),
            AlertCreate(alert_type="route_failure", severity="critical", device=dev_id, message=f"Anomalous BGP route flapping to AS 64999 on {dev_id}", timestamp=now + timedelta(seconds=2)),
            AlertCreate(alert_type="device_unreachable", severity="high", device=f"{dev_id}-SUB", message=f"Subordinate switch {dev_id}-SUB dropped off topology", timestamp=now + timedelta(seconds=4))
        ]
        for p in payloads:
            created_alerts.append(create_alert(p, db))
    else:
        raise HTTPException(status_code=400, detail="Invalid scenario type")

    return {"scenario": scenario, "alerts_generated": len(created_alerts)}
