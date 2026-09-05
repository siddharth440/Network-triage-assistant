/**
 * Escalations View Controller
 */

document.addEventListener("DOMContentLoaded", () => {
  loadEscalationsPage();
});

async function loadEscalationsPage() {
  const container = document.getElementById("escalations-container");
  if (!container) return;

  try {
    const escalations = await API.getEscalations();
    if (escalations.length === 0) {
      container.innerHTML = '<div style="color: var(--text-muted); padding: 2rem;">No incidents currently escalated.</div>';
      return;
    }

    container.innerHTML = escalations.map(esc => {
      const createdDate = new Date(esc.created_at).toLocaleString();
      const prioBadge = getPriorityBadgeClass(esc.priority);
      const ev = esc.evidence || {};
      const alerts = esc.grouped_alerts || [];

      return `
        <div class="noc-panel" style="margin-bottom: 1.5rem; border-left: 4px solid var(--color-escalated);">
          <div class="panel-header">
            <div>
              <span class="badge badge-escalated" style="margin-bottom: 0.4rem;">${esc.id}</span>
              <h3 style="font-size: 1.25rem; font-weight: 700; color: #fff;">
                Escalated Incident: <span style="color: var(--accent-cyan);">${esc.incident_id}</span>
              </h3>
              <small style="color: var(--text-muted);">Timestamp: ${createdDate}</small>
            </div>
            <div style="text-align: right;">
              <span class="badge ${prioBadge}">${esc.priority}</span>
              <div style="margin-top: 0.4rem; font-weight: 700; color: var(--accent-purple);">Assigned: ${esc.assigned_team}</div>
            </div>
          </div>

          <p style="font-size: 0.95rem; color: var(--text-primary); margin-bottom: 1rem; background: rgba(168,85,247,0.1); padding: 0.8rem; border-radius: 6px; border: 1px solid rgba(168,85,247,0.3);">
            <strong>Summary:</strong> ${esc.summary}
          </p>

          <!-- Collected Context & Evidence Panel -->
          <div style="background-color: #0b1120; border: 1px solid var(--border-color); border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem;">
            <h4 style="color: var(--accent-cyan); font-size: 0.85rem; font-weight: 700; text-transform: uppercase; margin-bottom: 0.75rem;">Preserved Evidence Context</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; font-size: 0.85rem;">
              <div><strong>Root Device:</strong> ${ev.root_device || 'N/A'}</div>
              <div><strong>Correlation Score:</strong> ${ev.correlation_score || 0}%</div>
              <div><strong>Grouped Events:</strong> ${ev.total_grouped_alerts || alerts.length}</div>
              <div><strong>Evaluated Runbooks:</strong> ${ev.evaluated_runbooks_count || 4}</div>
              <div><strong>Runbook Match Result:</strong> <span style="color: var(--color-critical);">0% (No Match)</span></div>
              <div><strong>Previous Action:</strong> ${esc.previous_recommendation || 'None'}</div>
            </div>
          </div>

          <!-- Grouped Evidence Alerts Table -->
          <h4 style="color: var(--text-secondary); font-size: 0.8rem; font-weight: 700; text-transform: uppercase; margin-bottom: 0.5rem;">Preserved Alert Evidence Stream:</h4>
          <div class="table-responsive">
            <table class="noc-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Device</th>
                  <th>Severity</th>
                  <th>Alert Type</th>
                  <th>Message</th>
                </tr>
              </thead>
              <tbody>
                ${alerts.map(a => `
                  <tr>
                    <td style="font-family: var(--font-mono);">${a.timestamp}</td>
                    <td>${a.device}</td>
                    <td><span class="badge ${getSeverityBadgeClass(a.severity)}">${a.severity}</span></td>
                    <td><code>${a.alert_type}</code></td>
                    <td>${a.message}</td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>
      `;
    }).join("");

  } catch (err) {
    console.error("Escalations page error:", err);
    container.innerHTML = '<div style="color: var(--color-critical); padding: 2rem;">Error fetching escalations record.</div>';
  }
}
