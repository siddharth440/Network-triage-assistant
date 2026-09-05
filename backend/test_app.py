import sys
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal, Base, engine
from seed_data import seed_database

client = TestClient(app)

def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_database(db)
    db.close()

def test_api():
    print("--- 0. Resetting Database ---")
    reset_db()

    print("\n--- 1. Testing Root Endpoint ---")
    res = client.get("/")
    assert res.status_code == 200
    print("Root API response:", res.json())

    print("\n--- 2. Testing Dashboard Stats Endpoint ---")
    res = client.get("/api/dashboard/stats")
    assert res.status_code == 200
    stats = res.json()
    print("Dashboard Stats:", stats)
    assert stats["total_alerts"] >= 30
    assert stats["active_incidents"] >= 3

    print("\n--- 3. Testing Incidents Endpoint ---")
    res = client.get("/api/incidents")
    assert res.status_code == 200
    incidents = res.json()
    print(f"Retrieved {len(incidents)} incidents")
    assert len(incidents) >= 4

    print("\n--- 4. Testing Incident Detail View ---")
    inc_id = incidents[0]["id"]
    res = client.get(f"/api/incidents/{inc_id}")
    assert res.status_code == 200
    detail = res.json()
    print(f"Incident {inc_id} detail:")
    print("  Root Device:", detail["root_device"])
    print("  Priority:", detail["priority"])
    print("  Confidence:", detail["confidence"])
    print("  Explainable Recommendation:", detail["explainable_recommendation"]["recommended_action"])

    print("\n--- 5. Testing Runbooks Endpoint ---")
    res = client.get("/api/runbooks")
    assert res.status_code == 200
    runbooks = res.json()
    print(f"Retrieved {len(runbooks)} runbooks")
    assert len(runbooks) >= 4

    print("\n--- 6. Testing Escalations Endpoint ---")
    res = client.get("/api/escalations")
    assert res.status_code == 200
    escalations = res.json()
    print(f"Retrieved {len(escalations)} escalations")
    assert len(escalations) >= 1
    print("Escalated incident ID:", escalations[0]["incident_id"])

    print("\n--- 7. Testing Demo Scenario Workflow ---")
    res = client.post("/api/demo/start")
    assert res.status_code == 200
    demo_res = res.json()
    print("Demo Result Summary:", demo_res["summary_message"])
    assert demo_res["total_incoming"] == 10
    assert demo_res["duplicate_count"] == 3
    assert demo_res["correlated_incidents"] >= 1

    print("\n[SUCCESS] ALL BACKEND ENDPOINTS AND CORE ENGINES VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    test_api()
