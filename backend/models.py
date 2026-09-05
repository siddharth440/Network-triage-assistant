from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base

class AlertDB(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    alert_type = Column(String, index=True)  # link_down, device_unreachable, etc.
    severity = Column(String, index=True)    # critical, high, medium, low
    device = Column(String, index=True)
    source_ip = Column(String, nullable=True)
    destination_ip = Column(String, nullable=True)
    location = Column(String, nullable=True)
    message = Column(Text)
    latency = Column(Float, default=0.0)
    packet_loss = Column(Float, default=0.0)
    authentication_failures = Column(Integer, default=0)
    status = Column(String, default="new", index=True)  # new, correlated, noise
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=True)

    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    occurrence_count = Column(Integer, default=1)
    noise_reason = Column(Text, nullable=True)

    incident = relationship("IncidentDB", back_populates="alerts")


class IncidentDB(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True, index=True) # e.g. INC-1001
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    root_device = Column(String, index=True)
    priority = Column(String, index=True)     # CRITICAL, HIGH, MEDIUM, LOW
    impact = Column(String)                   # High, Medium, Low
    status = Column(String, default="OPEN")    # OPEN, IN_PROGRESS, ESCALATED, RESOLVED
    root_cause = Column(Text, nullable=True)
    correlation_score = Column(Float, default=0.0)
    confidence = Column(Float, default=0.0)
    recommendation = Column(Text, nullable=True)
    runbook_id = Column(String, nullable=True)
    escalated = Column(Boolean, default=False)
    escalation_status = Column(String, default="NONE")  # NONE, ESCALATED

    alerts = relationship("AlertDB", back_populates="incident", cascade="all, delete-orphan")
    escalation = relationship("EscalationDB", back_populates="incident", uselist=False)


class RunbookDB(Base):
    __tablename__ = "runbooks"

    id = Column(String, primary_key=True, index=True) # e.g. RB-LINK-01
    title = Column(String)
    description = Column(Text)
    conditions = Column(Text)  # JSON string of required symptoms/conditions
    steps = Column(Text)       # JSON string list of actions
    category = Column(String)


class EscalationDB(Base):
    __tablename__ = "escalations"

    id = Column(String, primary_key=True, index=True) # e.g. ESC-1001
    incident_id = Column(String, ForeignKey("incidents.id"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    priority = Column(String)
    summary = Column(Text)
    evidence = Column(Text)               # JSON string of detailed evidence
    grouped_alerts = Column(Text)         # JSON string of alert summaries
    previous_recommendation = Column(Text, nullable=True)
    assigned_team = Column(String)       # e.g. Network Engineering
    status = Column(String, default="OPEN")

    incident = relationship("IncidentDB", back_populates="escalation")
