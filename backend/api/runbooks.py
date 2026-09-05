import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import RunbookDB
from schemas import RunbookResponse
from services.runbook_engine import sync_runbooks_to_db

router = APIRouter(prefix="/api/runbooks", tags=["runbooks"])

@router.get("", response_model=List[RunbookResponse])
def get_runbooks(db: Session = Depends(get_db)):
    sync_runbooks_to_db(db)
    rbs = db.query(RunbookDB).all()
    res = []
    for rb in rbs:
        res.append(
            RunbookResponse(
                id=rb.id,
                title=rb.title,
                description=rb.description or "",
                conditions=json.loads(rb.conditions or "{}"),
                steps=json.loads(rb.steps or "[]"),
                category=rb.category or "General"
            )
        )
    return res

@router.get("/{runbook_id}", response_model=RunbookResponse)
def get_runbook(runbook_id: str, db: Session = Depends(get_db)):
    sync_runbooks_to_db(db)
    rb = db.query(RunbookDB).filter(RunbookDB.id == runbook_id).first()
    if not rb:
        raise HTTPException(status_code=404, detail="Runbook not found")
    return RunbookResponse(
        id=rb.id,
        title=rb.title,
        description=rb.description or "",
        conditions=json.loads(rb.conditions or "{}"),
        steps=json.loads(rb.steps or "[]"),
        category=rb.category or "General"
    )
