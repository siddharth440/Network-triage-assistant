import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import EscalationDB
from schemas import EscalationResponse

router = APIRouter(prefix="/api/escalations", tags=["escalations"])

def build_escalation_response(esc: EscalationDB) -> EscalationResponse:
    return EscalationResponse(
        id=esc.id,
        incident_id=esc.incident_id,
        created_at=esc.created_at,
        priority=esc.priority,
        summary=esc.summary,
        evidence=json.loads(esc.evidence or "{}"),
        grouped_alerts=json.loads(esc.grouped_alerts or "[]"),
        previous_recommendation=esc.previous_recommendation,
        assigned_team=esc.assigned_team,
        status=esc.status
    )

@router.get("", response_model=List[EscalationResponse])
def get_escalations(db: Session = Depends(get_db)):
    escalations = db.query(EscalationDB).order_by(EscalationDB.created_at.desc()).all()
    return [build_escalation_response(esc) for esc in escalations]

@router.get("/{escalation_id}", response_model=EscalationResponse)
def get_escalation(escalation_id: str, db: Session = Depends(get_db)):
    esc = db.query(EscalationDB).filter(EscalationDB.id == escalation_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return build_escalation_response(esc)
