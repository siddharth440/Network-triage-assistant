import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine, Base, SessionLocal
from seed_data import seed_database

from api.alerts import router as alerts_router
from api.incidents import router as incidents_router
from api.runbooks import router as runbooks_router
from api.escalations import router as escalations_router
from api.dashboard import router as dashboard_router
from api.demo import router as demo_router

app = FastAPI(
    title="AI Network Incident Triage Assistant API",
    description="Automated Network Operations Center (NOC) alert deduplication, multi-signal correlation, priority assessment, runbook matching, and escalation engine.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for local development and frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # Initialize DB tables
    Base.metadata.create_all(bind=engine)
    # Seed initial data if empty
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

# Include API routers
app.include_router(alerts_router)
app.include_router(incidents_router)
app.include_router(runbooks_router)
app.include_router(escalations_router)
app.include_router(dashboard_router)
app.include_router(demo_router)

# Serve the dashboard from the same Render web service as the API.
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")

@app.get("/")
def root():
    return {
        "status": "online",
        "system": "AI Network Incident Triage Assistant",
        "version": "1.0.0",
        "documentation": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
