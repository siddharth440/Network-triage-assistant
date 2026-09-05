/**
 * Dashboard Controller Logic
 */

let streamInterval = null;
let isStreaming = false;

document.addEventListener("DOMContentLoaded", () => {
  loadDashboardData();
  setupEventListeners();
  // Refresh stats every 5 seconds
  setInterval(loadDashboardStats, 5000);
});

async function loadDashboardData() {
  await Promise.all([loadDashboardStats(), loadIncidentsTable()]);
}

async function loadDashboardStats() {
  try {
    const stats = await API.getStats();
    document.getElementById("stat-total-alerts").innerText = stats.total_alerts;
    document.getElementById("stat-active-incidents").innerText = stats.active_incidents;
    document.getElementById("stat-critical-incidents").innerText = stats.critical_incidents;
    document.getElementById("stat-high-incidents").innerText = stats.high_priority_incidents;
    document.getElementById("stat-noise-alerts").innerText = stats.noise_alerts;
    document.getElementById("stat-escalated-incidents").innerText = stats.escalated_incidents;

    renderActivityStream(stats.recent_activity);
  } catch (err) {
    console.error("Dashboard stats error:", err);
  }
}

function renderActivityStream(activities) {
  const container = document.getElementById("stream-list-container");
  if (!container) return;

  if (!activities || activities.length === 0) {
    container.innerHTML = '<div style="color: var(--text-muted); padding: 1rem;">No recent alert stream activity.</div>';
    return;
  }

  container.innerHTML = activities.map(act => {
    const badgeClass = getSeverityBadgeClass(act.severity);
    const occBadge = act.occurrence_count > 1 ? `<span class="badge badge-medium">×${act.occurrence_count}</span>` : '';
    return `
      <div class="stream-item">
        <div class="stream-meta">
          <span class="stream-time">${act.timestamp}</span>
          <span class="stream-device">${act.device}</span>
          <span class="badge ${badgeClass}">${act.severity}</span>
          ${occBadge}
        </div>
        <span class="stream-msg" title="${act.message}">${act.message}</span>
        <span class="badge ${getStatusBadgeClass(act.status)}">${act.status}</span>
      </div>
    `;
  }).join("");
}

async function loadIncidentsTable() {
  const tbody = document.getElementById("incidents-table-body");
  if (!tbody) return;

  try {
    const incidents = await API.getIncidents();
    if (incidents.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color: var(--text-muted); padding: 2rem;">No incidents found. Stream or generate alerts to triage.</td></tr>';
      return;
    }

    tbody.innerHTML = incidents.map(inc => {
      const prioBadge = getPriorityBadgeClass(inc.priority);
      const recText = inc.recommendation ? inc.recommendation : 'Under evaluation';
      const runbookLink = inc.runbook_id 
        ? `<br/><span class="runbook-citation" onclick="event.stopPropagation(); openRunbookModal('${inc.runbook_id}')">Source: ${inc.explainable_recommendation ? inc.explainable_recommendation.runbook_title : inc.runbook_id}</span>`
        : (inc.escalated ? `<br/><span style="color: var(--color-escalated); font-size:0.75rem; font-weight:700;">[ESCALATED - No Runbook Match]</span>` : '');

      return `
        <tr onclick="openIncidentModal('${inc.id}')">
          <td><strong style="color: var(--accent-cyan);">${inc.id}</strong></td>
          <td><strong>${inc.root_device}</strong></td>
          <td style="text-align: right; font-family: var(--font-mono);">${inc.alerts ? inc.alerts.length : 0}</td>
          <td><span class="badge ${prioBadge}">${inc.priority}</span></td>
          <td>${inc.impact}</td>
          <td><span class="badge ${getStatusBadgeClass(inc.status)}">${inc.status}</span></td>
          <td style="max-width: 380px;">
            <div>${recText}</div>
            ${runbookLink}
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Incidents table error:", err);
    tbody.innerHTML = '<tr><td colspan="7" style="color: var(--color-critical); text-align:center; padding: 2rem;">Error connecting to Python backend REST API.</td></tr>';
  }
}

function setupEventListeners() {
  const btnStreamToggle = document.getElementById("btn-stream-toggle");
  if (btnStreamToggle) {
    btnStreamToggle.addEventListener("click", toggleAlertStream);
  }

  const btnClear = document.getElementById("btn-clear-all");
  if (btnClear) {
    btnClear.addEventListener("click", async () => {
      if (confirm("Reset all alerts and incidents database?")) {
        await API.clearDemo();
        await loadDashboardData();
      }
    });
  }

  const btnDemo = document.getElementById("btn-run-demo");
  if (btnDemo) {
    btnDemo.addEventListener("click", runFullDemo);
  }

  // Simulation controls
  document.getElementById("btn-sim-router")?.addEventListener("click", () => triggerSim("router_failure"));
  document.getElementById("btn-sim-auth")?.addEventListener("click", () => triggerSim("auth_problem"));
  document.getElementById("btn-sim-noise")?.addEventListener("click", () => triggerSim("noise"));
  document.getElementById("btn-sim-unknown")?.addEventListener("click", () => triggerSim("unknown_incident"));
}

function toggleAlertStream() {
  const btn = document.getElementById("btn-stream-toggle");
  if (isStreaming) {
    clearInterval(streamInterval);
    isStreaming = false;
    btn.innerHTML = '▶ Start Stream';
    btn.classList.remove("btn-danger");
    btn.classList.add("btn-primary");
  } else {
    isStreaming = true;
    btn.innerHTML = '⏸ Pause Stream';
    btn.classList.remove("btn-primary");
    btn.classList.add("btn-danger");

    streamInterval = setInterval(async () => {
      const scenarios = ["router_failure", "auth_problem", "noise"];
      const randomScen = scenarios[Math.floor(Math.random() * scenarios.length)];
      await API.simulateStream(randomScen);
      await loadDashboardData();
    }, 4000);
  }
}

async function triggerSim(scenarioType) {
  await API.simulateStream(scenarioType);
  await loadDashboardData();
}

async function runFullDemo() {
  const demoCard = document.getElementById("demo-pipeline-card");
  if (demoCard) demoCard.style.display = "block";

  try {
    const result = await API.startDemo();
    document.getElementById("flow-val-incoming").innerText = result.total_incoming;
    document.getElementById("flow-val-duplicates").innerText = result.duplicate_count;
    document.getElementById("flow-val-incidents").innerText = result.correlated_incidents;
    document.getElementById("flow-val-noise").innerText = result.noise_count;
    document.getElementById("flow-val-prio").innerText = result.priority;
    document.getElementById("flow-val-match").innerText = `${result.runbook_match_score}%`;
    document.getElementById("flow-val-rec").innerText = result.recommendation;

    await loadDashboardData();
  } catch (err) {
    alert("Error executing demo scenario: " + err.message);
  }
}

/* Modal View Handlers */
async function openIncidentModal(incidentId) {
  try {
    const inc = await API.getIncidentDetail(incidentId);
    const modal = document.getElementById("incident-modal");
    if (!modal) return;

    document.getElementById("modal-inc-id").innerText = inc.id;
    document.getElementById("modal-inc-device").innerText = inc.root_device;
    document.getElementById("modal-inc-priority").innerHTML = `<span class="badge ${getPriorityBadgeClass(inc.priority)}">${inc.priority}</span>`;
    document.getElementById("modal-inc-impact").innerText = inc.impact;
    document.getElementById("modal-inc-status").innerHTML = `<span class="badge ${getStatusBadgeClass(inc.status)}">${inc.status}</span>`;
    document.getElementById("modal-inc-confidence").innerText = `${inc.confidence}%`;

    // Root Cause
    document.getElementById("modal-inc-rootcause").innerText = inc.root_cause || "Analyzing topology...";

    // Correlation Explanation
    const corrReasonsList = document.getElementById("modal-corr-reasons");
    corrReasonsList.innerHTML = inc.correlation_reasons.map(r => `<li>${r}</li>`).join("");

    // Explainable Recommendation
    if (inc.explainable_recommendation) {
      document.getElementById("modal-rec-action").innerText = inc.explainable_recommendation.recommended_action;
      document.getElementById("modal-rec-why").innerHTML = inc.explainable_recommendation.why.map(w => `<li>${w}</li>`).join("");
      document.getElementById("modal-rec-runbook").innerText = inc.explainable_recommendation.runbook_title || "None";
      document.getElementById("modal-rec-confidence").innerText = `${inc.explainable_recommendation.match_confidence}%`;
    }

    // Timeline
    const timelineContainer = document.getElementById("modal-timeline");
    timelineContainer.innerHTML = inc.timeline.map(t => `
      <div class="timeline-item">
        <div class="timeline-dot"></div>
        <div class="timeline-time">${t.timestamp}</div>
        <div class="timeline-content">${t.event} <span class="badge ${getSeverityBadgeClass(t.severity)}">${t.severity}</span></div>
      </div>
    `).join("");

    // Correlated Alerts Table
    const alertsBody = document.getElementById("modal-alerts-body");
    alertsBody.innerHTML = inc.alerts.map(a => `
      <tr>
        <td>${a.device}</td>
        <td><span class="badge ${getSeverityBadgeClass(a.severity)}">${a.severity}</span></td>
        <td>${a.alert_type}</td>
        <td>${a.message}</td>
        <td>${a.occurrence_count > 1 ? `×${a.occurrence_count}` : '1'}</td>
      </tr>
    `).join("");

    // Escalation Section
    const escPanel = document.getElementById("modal-escalation-panel");
    if (inc.escalated) {
      escPanel.style.display = "block";
      document.getElementById("modal-esc-team").innerText = "Network Engineering (L3)";
      document.getElementById("modal-esc-status").innerText = inc.escalation_status;
    } else {
      escPanel.style.display = "none";
    }

    modal.classList.add("active");
  } catch (err) {
    alert("Error opening incident detail: " + err.message);
  }
}

function closeIncidentModal() {
  document.getElementById("incident-modal")?.classList.remove("active");
}

async function openRunbookModal(runbookId) {
  try {
    const rb = await API.getRunbookDetail(runbookId);
    alert(`📖 RUNBOOK CITATION:\n\nTitle: ${rb.title}\nCategory: ${rb.category}\n\nTroubleshooting Actions:\n` + rb.steps.map((s, i) => `${i+1}. ${s}`).join("\n"));
  } catch (err) {
    alert("Runbook detail unavailable: " + err.message);
  }
}

/* Badge helpers */
function getSeverityBadgeClass(sev) {
  switch ((sev || "").toLowerCase()) {
    case "critical": return "badge-critical";
    case "high": return "badge-high";
    case "medium": return "badge-medium";
    case "low": return "badge-low";
    default: return "badge-noise";
  }
}

function getPriorityBadgeClass(prio) {
  switch ((prio || "").toUpperCase()) {
    case "CRITICAL": return "badge-critical";
    case "HIGH": return "badge-high";
    case "MEDIUM": return "badge-medium";
    case "LOW": return "badge-low";
    default: return "badge-noise";
  }
}

function getStatusBadgeClass(st) {
  switch ((st || "").toUpperCase()) {
    case "OPEN": return "badge-critical";
    case "IN_PROGRESS": return "badge-high";
    case "ESCALATED": return "badge-escalated";
    case "RESOLVED": return "badge-low";
    case "CORRELATED": return "badge-medium";
    case "NOISE": return "badge-noise";
    default: return "badge-noise";
  }
}
