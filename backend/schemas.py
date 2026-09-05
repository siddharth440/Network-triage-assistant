from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field

class AlertCreate(BaseModel):
    alert_type: str
    severity: str
    device: str
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    location: Optional[str] = None
    message: str
    latency: Optional[float] = 0.0
    packet_loss: Optional[float] = 0.0
    authentication_failures: Optional[int] = 0
    timestamp: Optional[datetime] = None

class AlertResponse(BaseModel):
    id: int
    timestamp: datetime
    alert_type: str
    severity: str
    device: str
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    location: Optional[str] = None
    message: str
    latency: float
    packet_loss: float
    authentication_failures: int
    status: str
    incident_id: Optional[str] = None
    first_seen: datetime
    last_seen: datetime
    occurrence_count: int
    noise_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ExplainableRecommendation(BaseModel):
    recommended_action: str
    why: List[str]
    runbook_title: Optional[str] = None
    runbook_id: Optional[str] = None
    match_confidence: float

class TimelineEvent(BaseModel):
    timestamp: str
    event: str
    alert_type: str
    severity: str

class IncidentResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    root_device: str
    priority: str
    impact: str
    status: str
    root_cause: Optional[str] = None
    correlation_score: float
    confidence: float
    recommendation: Optional[str] = None
    runbook_id: Optional[str] = None
    escalated: bool
    escalation_status: str
    alerts: List[AlertResponse] = []
    duplicate_count: int = 0
    explainable_recommendation: Optional[ExplainableRecommendation] = None
    timeline: List[TimelineEvent] = []
    correlation_reasons: List[str] = []

    model_config = ConfigDict(from_attributes=True)

class RunbookResponse(BaseModel):
    id: str
    title: str
    description: str
    conditions: Dict[str, Any]
    steps: List[str]
    category: str

    model_config = ConfigDict(from_attributes=True)

class EscalationResponse(BaseModel):
    id: str
    incident_id: str
    created_at: datetime
    priority: str
    summary: str
    evidence: Dict[str, Any]
    grouped_alerts: List[Dict[str, Any]]
    previous_recommendation: Optional[str] = None
    assigned_team: str
    status: str

    model_config = ConfigDict(from_attributes=True)

class DashboardStats(BaseModel):
    total_alerts: int
    active_incidents: int
    critical_incidents: int
    high_priority_incidents: int
    noise_alerts: int
    escalated_incidents: int
    recent_activity: List[Dict[str, Any]]

class DemoResult(BaseModel):
    total_incoming: int
    duplicate_count: int
    correlated_incidents: int
    noise_count: int
    priority: str
    runbook_match_score: float
    matched_runbook: str
    recommendation: str
    summary_message: str
    incidents: List[IncidentResponse]
