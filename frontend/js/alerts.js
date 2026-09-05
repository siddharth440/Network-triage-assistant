/**
 * Alerts View Controller
 */

document.addEventListener("DOMContentLoaded", () => {
  loadAlertsPage();

  document.getElementById("filter-alert-status")?.addEventListener("change", loadAlertsPage);
  document.getElementById("btn-clear-alerts-page")?.addEventListener("click", async () => {
    if (confirm("Clear all alerts?")) {
      await API.clearAlerts();
      await loadAlertsPage();
    }
  });
});

async function loadAlertsPage() {
  const tbody = document.getElementById("alerts-page-table-body");
  const noiseContainer = document.getElementById("uncorrelated-noise-list");
  if (!tbody) return;

  try {
    const statusFilter = document.getElementById("filter-alert-status")?.value || "all";
    const alerts = await API.getAlerts(statusFilter);

    if (alerts.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color: var(--text-muted); padding: 2rem;">No alerts recorded in database.</td></tr>';
    } else {
      tbody.innerHTML = alerts.map(a => {
        const dateStr = new Date(a.timestamp).toLocaleTimeString();
        const sevBadge = getSeverityBadgeClass(a.severity);
        const statusBadge = getStatusBadgeClass(a.status);
        const occBadge = a.occurrence_count > 1 
          ? `<span class="badge badge-high">×${a.occurrence_count} Duplicate</span>` 
          : '<span class="badge badge-low">1</span>';

        return `
          <tr>
            <td style="font-family: var(--font-mono); color: var(--text-muted);">${dateStr}</td>
            <td><strong>${a.device}</strong></td>
            <td><span class="badge ${sevBadge}">${a.severity}</span></td>
            <td><code style="color: var(--accent-cyan);">${a.alert_type}</code></td>
            <td>${a.message}</td>
            <td>${occBadge}</td>
            <td><span class="badge ${statusBadge}">${a.status}</span></td>
            <td>${a.incident_id ? `<strong style="color: var(--accent-blue);">${a.incident_id}</strong>` : '<span style="color: var(--text-muted);">None</span>'}</td>
          </tr>
        `;
      }).join("");
    }

    // Load Uncorrelated Noise Section
    if (noiseContainer) {
      const noiseAlerts = alerts.filter(a => a.status === "noise");
      if (noiseAlerts.length === 0) {
        noiseContainer.innerHTML = '<div style="color: var(--text-muted); padding: 1rem;">No noise alerts present.</div>';
      } else {
        noiseContainer.innerHTML = noiseAlerts.map(n => `
          <div style="background-color: #0b1120; border: 1px solid var(--border-color); border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem;">
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom: 0.4rem;">
              <strong style="color: var(--accent-cyan);">${n.device}</strong>
              <span class="badge badge-noise">NOISE</span>
            </div>
            <div style="font-weight:600; margin-bottom: 0.4rem;">${n.message}</div>
            <div style="font-size: 0.8rem; color: var(--color-high);">
              <strong>Reason:</strong> ${n.noise_reason || 'Not grouped because no related network event was detected within correlation window.'}
            </div>
          </div>
        `).join("");
      }
    }

  } catch (err) {
    console.error("Alerts page error:", err);
    tbody.innerHTML = '<tr><td colspan="8" style="color: var(--color-critical); text-align:center; padding: 2rem;">Error fetching alert stream from backend API.</td></tr>';
  }
}
