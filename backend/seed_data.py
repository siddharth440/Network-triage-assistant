from datetime import datetime, timedelta
import json
from sqlalchemy.orm import Session
from database import engine, Base, SessionLocal
from models import AlertDB, IncidentDB, RunbookDB, EscalationDB
from services.runbook_engine import sync_runbooks_to_db
from services.priority_engine import calculate_incident_priority
from services.runbook_engine import match_runbook_for_incident
from services.escalation_engine import create_incident_escalation

def seed_database(db: Session):
    """
    Seeds the SQLite database with realistic NOC alerts, incidents, runbooks, and escalations.
    """
    # Create tables if not exist
    Base.metadata.create_all(bind=engine)

    # Check if already seeded
    if db.query(AlertDB).count() > 0:
        return

    # Sync Runbooks first
    sync_runbooks_to_db(db)

    now = datetime.utcnow()

    # --- INCIDENT 1: Core Connectivity Failure (INC-1001) - CRITICAL ---
    inc1 = IncidentDB(
        id="INC-1001",
        created_at=now - timedelta(minutes=25),
        updated_at=now - timedelta(minutes=20),
        root_device="RTR-01",
        priority="CRITICAL",
        impact="High",
        status="OPEN",
        root_cause="Network link failure on primary edge router uplink",
        correlation_score=95.0,
        confidence=94.0,
        recommendation="Check the interface status on RTR-01 and verify physical connectivity to the neighboring switch.",
        runbook_id="RB-CONNECTIVITY-01",
        escalated=False,
        escalation_status="NONE"
    )
    db.add(inc1)

    alerts_inc1 = [
        AlertDB(
            timestamp=now - timedelta(minutes=25),
            alert_type="link_down",
            severity="critical",
            device="RTR-01",
            source_ip="10.0.0.1",
            destination_ip="10.0.0.2",
            location="DC-East Rack 4",
            message="Interface GigabitEthernet0/0/1 down",
            packet_loss=100.0,
            status="correlated",
            incident_id="INC-1001",
            first_seen=now - timedelta(minutes=25),
            last_seen=now - timedelta(minutes=25),
            occurrence_count=1
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=24),
            alert_type="device_unreachable",
            severity="critical",
            device="RTR-01",
            source_ip="10.0.0.1",
            location="DC-East Rack 4",
            message="Router RTR-01 unreachable via ICMP echo",
            packet_loss=100.0,
            status="correlated",
            incident_id="INC-1001",
            first_seen=now - timedelta(minutes=24),
            last_seen=now - timedelta(minutes=22),
            occurrence_count=3
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=23),
            alert_type="packet_loss",
            severity="high",
            device="RTR-01",
            source_ip="10.0.0.1",
            location="DC-East Rack 4",
            message="Packet loss spike 85% on WAN trunk",
            packet_loss=85.0,
            status="correlated",
            incident_id="INC-1001",
            first_seen=now - timedelta(minutes=23),
            last_seen=now - timedelta(minutes=23),
            occurrence_count=1
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=22),
            alert_type="high_latency",
            severity="high",
            device="RTR-01",
            source_ip="10.0.0.1",
            location="DC-East Rack 4",
            message="Latency elevated to 240ms across uplink",
            latency=240.0,
            status="correlated",
            incident_id="INC-1001",
            first_seen=now - timedelta(minutes=22),
            last_seen=now - timedelta(minutes=22),
            occurrence_count=1
        )
    ]
    db.add_all(alerts_inc1)

    # --- INCIDENT 2: Latency & Degradation (INC-1002) - HIGH ---
    inc2 = IncidentDB(
        id="INC-1002",
        created_at=now - timedelta(minutes=45),
        updated_at=now - timedelta(minutes=35),
        root_device="SW-CORE-01",
        priority="HIGH",
        impact="Medium",
        status="IN_PROGRESS",
        root_cause="Core switch backplane queue congestion and packet degradation",
        correlation_score=88.0,
        confidence=91.0,
        recommendation="Check interface bandwidth utilization on SW-CORE-01 and inspect NetFlow top talkers.",
        runbook_id="RB-LATENCY-01",
        escalated=False,
        escalation_status="NONE"
    )
    db.add(inc2)

    alerts_inc2 = [
        AlertDB(
            timestamp=now - timedelta(minutes=45),
            alert_type="high_latency",
            severity="high",
            device="SW-CORE-01",
            source_ip="10.1.0.10",
            location="DC-East Core",
            message="Latency threshold exceeded 180ms on VLAN 100",
            latency=180.0,
            status="correlated",
            incident_id="INC-1002",
            first_seen=now - timedelta(minutes=45),
            last_seen=now - timedelta(minutes=45),
            occurrence_count=2
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=44),
            alert_type="packet_loss",
            severity="medium",
            device="SW-CORE-01",
            source_ip="10.1.0.10",
            location="DC-East Core",
            message="Packet loss 35% detected on aggregation port",
            packet_loss=35.0,
            status="correlated",
            incident_id="INC-1002",
            first_seen=now - timedelta(minutes=44),
            last_seen=now - timedelta(minutes=44),
            occurrence_count=1
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=42),
            alert_type="cpu_high",
            severity="high",
            device="SW-CORE-01",
            location="DC-East Core",
            message="Switch CPU utilization 92%",
            status="correlated",
            incident_id="INC-1002",
            first_seen=now - timedelta(minutes=42),
            last_seen=now - timedelta(minutes=40),
            occurrence_count=4
        )
    ]
    db.add_all(alerts_inc2)

    # --- INCIDENT 3: TACACS/RADIUS Auth Storm (INC-1003) - HIGH ---
    inc3 = IncidentDB(
        id="INC-1003",
        created_at=now - timedelta(hours=2),
        updated_at=now - timedelta(hours=1, minutes=45),
        root_device="SRV-AUTH-01",
        priority="HIGH",
        impact="High",
        status="OPEN",
        root_cause="Repeated authentication failures / brute force attack signature on authentication gateway",
        correlation_score=82.0,
        confidence=89.0,
        recommendation="Verify RADIUS server health on SRV-AUTH-01 and analyze failed login IP logs.",
        runbook_id="RB-AUTH-01",
        escalated=False,
        escalation_status="NONE"
    )
    db.add(inc3)

    alerts_inc3 = [
        AlertDB(
            timestamp=now - timedelta(hours=2),
            alert_type="authentication_failure",
            severity="high",
            device="SRV-AUTH-01",
            source_ip="192.168.50.44",
            location="HQ Security Zone",
            message="RADIUS TACACS+ multiple bad password attempts",
            authentication_failures=12,
            status="correlated",
            incident_id="INC-1003",
            first_seen=now - timedelta(hours=2),
            last_seen=now - timedelta(hours=1, minutes=50),
            occurrence_count=5
        ),
        AlertDB(
            timestamp=now - timedelta(hours=1, minutes=58),
            alert_type="authentication_failure",
            severity="high",
            device="SRV-AUTH-01",
            source_ip="192.168.50.45",
            location="HQ Security Zone",
            message="Admin lockout triggered on TACACS server",
            authentication_failures=8,
            status="correlated",
            incident_id="INC-1003",
            first_seen=now - timedelta(hours=1, minutes=58),
            last_seen=now - timedelta(hours=1, minutes=58),
            occurrence_count=2
        )
    ]
    db.add_all(alerts_inc3)

    # --- INCIDENT 4: Hardware / Power Outage (INC-1004) - MEDIUM ---
    inc4 = IncidentDB(
        id="INC-1004",
        created_at=now - timedelta(hours=3),
        updated_at=now - timedelta(hours=2, minutes=30),
        root_device="FW-01",
        priority="MEDIUM",
        impact="Medium",
        status="IN_PROGRESS",
        root_cause="Primary firewall gateway power supply failure and service disruption",
        correlation_score=85.0,
        confidence=87.0,
        recommendation="Ping device FW-01 and check out-of-band IPMI power status.",
        runbook_id="RB-DEVICE-01",
        escalated=False,
        escalation_status="NONE"
    )
    db.add(inc4)

    alerts_inc4 = [
        AlertDB(
            timestamp=now - timedelta(hours=3),
            alert_type="device_unreachable",
            severity="high",
            device="FW-01",
            source_ip="10.254.0.1",
            location="DMZ Rack 1",
            message="Firewall FW-01 management interface unresponsive",
            status="correlated",
            incident_id="INC-1004",
            first_seen=now - timedelta(hours=3),
            last_seen=now - timedelta(hours=3),
            occurrence_count=2
        ),
        AlertDB(
            timestamp=now - timedelta(hours=2, minutes=55),
            alert_type="service_unavailable",
            severity="medium",
            device="FW-01",
            location="DMZ Rack 1",
            message="VPN Concentrator service daemon dead",
            status="correlated",
            incident_id="INC-1004",
            first_seen=now - timedelta(hours=2, minutes=55),
            last_seen=now - timedelta(hours=2, minutes=55),
            occurrence_count=1
        )
    ]
    db.add_all(alerts_inc4)

    # --- INCIDENT 5: UNKNOWN / UNMATCHED INCIDENT (INC-1005) -> ESCALATED ---
    inc5 = IncidentDB(
        id="INC-1005",
        created_at=now - timedelta(minutes=15),
        updated_at=now - timedelta(minutes=10),
        root_device="SW-24",
        priority="HIGH",
        impact="High",
        status="ESCALATED",
        root_cause="Anomalous route flapping combined with interface bit errors and gateway unreachability",
        correlation_score=87.0,
        confidence=82.0,
        recommendation="No automated runbook matched this complex multi-failure signature. Escalated to Network Engineering.",
        runbook_id=None,
        escalated=True,
        escalation_status="ESCALATED"
    )
    db.add(inc5)

    alerts_inc5 = [
        AlertDB(
            timestamp=now - timedelta(minutes=15),
            alert_type="interface_error",
            severity="high",
            device="SW-24",
            location="Branch Office 12",
            message="CRC bit error rate exceeding 10^-3 threshold on port 12",
            status="correlated",
            incident_id="INC-1005",
            first_seen=now - timedelta(minutes=15),
            last_seen=now - timedelta(minutes=15),
            occurrence_count=1
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=14),
            alert_type="route_failure",
            severity="critical",
            device="SW-24",
            location="Branch Office 12",
            message="BGP Route flap detected to upstream ASN 65001",
            status="correlated",
            incident_id="INC-1005",
            first_seen=now - timedelta(minutes=14),
            last_seen=now - timedelta(minutes=12),
            occurrence_count=3
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=12),
            alert_type="device_unreachable",
            severity="high",
            device="SW-25",
            location="Branch Office 12",
            message="Cascading switch SW-25 unreachable following route drop",
            status="correlated",
            incident_id="INC-1005",
            first_seen=now - timedelta(minutes=12),
            last_seen=now - timedelta(minutes=12),
            occurrence_count=1
        )
    ]
    db.add_all(alerts_inc5)

    # --- NOISE ALERTS (Uncorrelated / Isolated Events) ---
    noise_alerts = [
        AlertDB(
            timestamp=now - timedelta(minutes=50),
            alert_type="cpu_high",
            severity="low",
            device="PRINTER-02",
            location="Floor 3 Print Room",
            message="Printer-02 toner low and temporary CPU spike during print spool",
            status="noise",
            noise_reason="Not grouped because no related network event was detected within the correlation window.",
            first_seen=now - timedelta(minutes=50),
            last_seen=now - timedelta(minutes=50),
            occurrence_count=1
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=40),
            alert_type="memory_high",
            severity="low",
            device="DESKTOP-901",
            location="Finance Dept",
            message="Minor memory warning on endpoint workstation",
            status="noise",
            noise_reason="Isolated endpoint alert below threshold; non-critical network impact.",
            first_seen=now - timedelta(minutes=40),
            last_seen=now - timedelta(minutes=40),
            occurrence_count=1
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=30),
            alert_type="interface_error",
            severity="info",
            device="AP-OUTDOOR-01",
            location="Courtyard",
            message="Transient wireless client disassociation warning",
            status="noise",
            noise_reason="Transient RF noise event without downstream network impact.",
            first_seen=now - timedelta(minutes=30),
            last_seen=now - timedelta(minutes=30),
            occurrence_count=1
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=18),
            alert_type="service_unavailable",
            severity="low",
            device="TEST-VM-09",
            location="Dev Sandbox",
            message="Dev sandbox environment container stop event",
            status="noise",
            noise_reason="Isolated test environment alert excluded from production NOC incident triage.",
            first_seen=now - timedelta(minutes=18),
            last_seen=now - timedelta(minutes=18),
            occurrence_count=1
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=8),
            alert_type="high_latency",
            severity="low",
            device="GUEST-WIFI-GW",
            location="Guest Lounge",
            message="Guest WiFi ping response latency 95ms",
            status="noise",
            noise_reason="Guest network degradation within expected SLA bounds; no core incident matched.",
            first_seen=now - timedelta(minutes=8),
            last_seen=now - timedelta(minutes=8),
            occurrence_count=1
        )
    ]
    db.add_all(noise_alerts)

    # Add extra raw/duplicate alerts to reach >= 30 total alerts
    extra_alerts = [
        AlertDB(
            timestamp=now - timedelta(minutes=10),
            alert_type="link_down",
            severity="medium",
            device="RTR-02",
            location="DC-West",
            message="Backup link G0/0/2 state change down",
            status="new",
            first_seen=now - timedelta(minutes=10),
            last_seen=now - timedelta(minutes=10),
            occurrence_count=1
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=7),
            alert_type="cpu_high",
            severity="medium",
            device="RTR-02",
            location="DC-West",
            message="Router CPU high during bgp re-convergence",
            status="new",
            first_seen=now - timedelta(minutes=7),
            last_seen=now - timedelta(minutes=7),
            occurrence_count=1
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=5),
            alert_type="packet_loss",
            severity="medium",
            device="RTR-02",
            location="DC-West",
            message="Packet loss 15% on backup WAN path",
            packet_loss=15.0,
            status="new",
            first_seen=now - timedelta(minutes=5),
            last_seen=now - timedelta(minutes=5),
            occurrence_count=1
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=3),
            alert_type="authentication_failure",
            severity="low",
            device="FW-02",
            location="DC-West",
            message="Failed SSH attempt from unauthorized subnet",
            authentication_failures=1,
            status="new",
            first_seen=now - timedelta(minutes=3),
            last_seen=now - timedelta(minutes=3),
            occurrence_count=1
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=1),
            alert_type="interface_error",
            severity="low",
            device="SW-CORE-02",
            location="DC-East Core",
            message="Optical transceiver rx power warning on port TenGig0/1",
            status="new",
            first_seen=now - timedelta(minutes=1),
            last_seen=now - timedelta(minutes=1),
            occurrence_count=1
        ),
        # Extra 6 alerts to ensure distinct alert DB count >= 30
        AlertDB(
            timestamp=now - timedelta(minutes=60),
            alert_type="high_latency",
            severity="low",
            device="VOIP-GW-01",
            location="HQ Telecom",
            message="SIP Trunk latency jitter warning 45ms",
            status="new",
            first_seen=now - timedelta(minutes=60),
            last_seen=now - timedelta(minutes=60),
            occurrence_count=1
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=55),
            alert_type="memory_high",
            severity="medium",
            device="PROXY-01",
            location="DMZ Rack 2",
            message="Squid proxy cache memory buffer utilization 88%",
            status="new",
            first_seen=now - timedelta(minutes=55),
            last_seen=now - timedelta(minutes=55),
            occurrence_count=1
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=48),
            alert_type="service_unavailable",
            severity="low",
            device="DNS-SEC-02",
            location="DC-West",
            message="Secondary DNS daemon zone transfer delay",
            status="new",
            first_seen=now - timedelta(minutes=48),
            last_seen=now - timedelta(minutes=48),
            occurrence_count=1
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=35),
            alert_type="interface_error",
            severity="low",
            device="VPN-CON-01",
            location="DMZ Rack 3",
            message="IPsec Tunnel #4 re-keying timeout warning",
            status="new",
            first_seen=now - timedelta(minutes=35),
            last_seen=now - timedelta(minutes=35),
            occurrence_count=1
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=28),
            alert_type="cpu_high",
            severity="medium",
            device="LOADBAL-01",
            location="DC-East Core",
            message="SSL offloading engine CPU utilization 79%",
            status="new",
            first_seen=now - timedelta(minutes=28),
            last_seen=now - timedelta(minutes=28),
            occurrence_count=1
        ),
        AlertDB(
            timestamp=now - timedelta(minutes=16),
            alert_type="route_failure",
            severity="medium",
            device="RTR-EDGE-03",
            location="Branch Office 5",
            message="OSPF external route cost metric adjustment",
            status="new",
            first_seen=now - timedelta(minutes=16),
            last_seen=now - timedelta(minutes=16),
            occurrence_count=1
        )
    ]

    db.add_all(extra_alerts)
    db.commit()

    # Create Escalation Record for INC-1005
    create_incident_escalation(
        db, 
        inc5, 
        reason="Complex multi-failure event (route_failure + interface_error + device_unreachable) matched 0 out of 4 knowledge base runbooks."
    )
    print("Database successfully seeded with realistic NOC alerts, incidents, runbooks, and escalation.")

if __name__ == "__main__":
    db = SessionLocal()
    seed_database(db)
    db.close()
