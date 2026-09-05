/**
 * Incidents View Controller
 */

document.addEventListener("DOMContentLoaded", () => {
  loadIncidentsPage();

  document.getElementById("filter-priority")?.addEventListener("change", loadIncidentsPage);
  document.getElementById("filter-status")?.addEventListener("change", loadIncidentsPage);
  document.getElementById("btn-process-now")?.addEventListener("click", async () => {
    await API.processIncidents();
    await loadIncidentsPage();
  });
});

async function loadIncidentsPage() {
  const tbody = document.getElementById("incidents-page-table-body");
  if (!tbody) return;

  try {
    const incidents = await API.getIncidents();
    const prioFilter = document.getElementById("filter-priority")?.value || "ALL";
    const statusFilter = document.getElementById("filter-status")?.value || "ALL";

    const filtered = incidents.filter(inc => {
      const matchPrio = prioFilter === "ALL" || inc.priority.toUpperCase() === prioFilter.toUpperCase();
      const matchStatus = statusFilter === "ALL" || inc.status.toUpperCase() === statusFilter.toUpperCase();
      return matchPrio && matchStatus;
    });

    if (filtered.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color: var(--text-muted); padding: 2rem;">No incidents match the selected filter parameters.</td></tr>';
      return;
    }

    tbody.innerHTML = filtered.map(inc => {
      const prioBadge = getPriorityBadgeClass(inc.priority);
      const statusBadge = getStatusBadgeClass(inc.status);
      const alertCount = inc.alerts ? inc.alerts.length : 0;
      const dupCount = inc.duplicate_count ? ` (+${inc.duplicate_count} duplicates)` : '';

      return `
        <tr onclick="openIncidentModal('${inc.id}')">
          <td><strong style="color: var(--accent-cyan); font-family: var(--font-mono);">${inc.id}</strong></td>
          <td><strong>${inc.root_device}</strong></td>
          <td><span class="badge ${prioBadge}">${inc.priority}</span></td>
          <td>${inc.impact}</td>
          <td><span class="badge ${statusBadge}">${inc.status}</span></td>
          <td><strong style="color: var(--accent-blue);">${inc.confidence}%</strong></td>
          <td>${alertCount} alerts ${dupCount}</td>
          <td>
            <div style="font-weight:600;">${inc.recommendation || 'Evaluating...'}</div>
            ${inc.runbook_id ? `<span class="runbook-citation" onclick="event.stopPropagation(); openRunbookModal('${inc.runbook_id}')">Runbook: ${inc.explainable_recommendation ? inc.explainable_recommendation.runbook_title : inc.runbook_id}</span>` : ''}
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    console.error("Incidents page error:", err);
    tbody.innerHTML = '<tr><td colspan="8" style="color: var(--color-critical); text-align:center; padding: 2rem;">Error fetching incident records from API backend.</td></tr>';
  }
}
