/**
 * Centralized API Communication Module for AI Network Incident Triage Assistant
 */
const API_BASE_URL = "http://localhost:8000/api";

const API = {
  // Stats & Dashboard
  getStats: async () => {
    const res = await fetch(`${API_BASE_URL}/dashboard/stats`);
    if (!res.ok) throw new Error("Failed to fetch dashboard stats");
    return await res.json();
  },

  // Alerts
  getAlerts: async (status = "all") => {
    const url = status && status !== "all" ? `${API_BASE_URL}/alerts?status=${status}` : `${API_BASE_URL}/alerts`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch alerts");
    return await res.json();
  },

  postAlert: async (alertData) => {
    const res = await fetch(`${API_BASE_URL}/alerts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(alertData)
    });
    if (!res.ok) throw new Error("Failed to ingest alert");
    return await res.json();
  },

  clearAlerts: async () => {
    const res = await fetch(`${API_BASE_URL}/alerts`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to clear alerts");
    return await res.json();
  },

  // Incidents
  getIncidents: async () => {
    const res = await fetch(`${API_BASE_URL}/incidents`);
    if (!res.ok) throw new Error("Failed to fetch incidents");
    return await res.json();
  },

  getIncidentDetail: async (incidentId) => {
    const res = await fetch(`${API_BASE_URL}/incidents/${incidentId}`);
    if (!res.ok) throw new Error(`Failed to fetch incident ${incidentId}`);
    return await res.json();
  },

  processIncidents: async () => {
    const res = await fetch(`${API_BASE_URL}/incidents/process`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to process incidents");
    return await res.json();
  },

  // Runbooks
  getRunbooks: async () => {
    const res = await fetch(`${API_BASE_URL}/runbooks`);
    if (!res.ok) throw new Error("Failed to fetch runbooks");
    return await res.json();
  },

  getRunbookDetail: async (runbookId) => {
    const res = await fetch(`${API_BASE_URL}/runbooks/${runbookId}`);
    if (!res.ok) throw new Error(`Failed to fetch runbook ${runbookId}`);
    return await res.json();
  },

  // Escalations
  getEscalations: async () => {
    const res = await fetch(`${API_BASE_URL}/escalations`);
    if (!res.ok) throw new Error("Failed to fetch escalations");
    return await res.json();
  },

  getEscalationDetail: async (id) => {
    const res = await fetch(`${API_BASE_URL}/escalations/${id}`);
    if (!res.ok) throw new Error(`Failed to fetch escalation ${id}`);
    return await res.json();
  },

  // Demo Controls
  startDemo: async () => {
    const res = await fetch(`${API_BASE_URL}/demo/start`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to execute demo scenario");
    return await res.json();
  },

  clearDemo: async () => {
    const res = await fetch(`${API_BASE_URL}/demo/clear`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to reset demo data");
    return await res.json();
  },

  simulateStream: async (scenarioType) => {
    const res = await fetch(`${API_BASE_URL}/demo/simulate-stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario: scenarioType })
    });
    if (!res.ok) throw new Error(`Failed to simulate stream scenario: ${scenarioType}`);
    return await res.json();
  }
};
