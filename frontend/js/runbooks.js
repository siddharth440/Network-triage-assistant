/**
 * Runbooks View Controller
 */

document.addEventListener("DOMContentLoaded", () => {
  loadRunbooksPage();
});

async function loadRunbooksPage() {
  const container = document.getElementById("runbooks-container");
  if (!container) return;

  try {
    const runbooks = await API.getRunbooks();
    if (runbooks.length === 0) {
      container.innerHTML = '<div style="color: var(--text-muted); padding: 2rem;">No runbooks found in knowledge base.</div>';
      return;
    }

    container.innerHTML = runbooks.map(rb => {
      const symptoms = rb.conditions.alert_types ? rb.conditions.alert_types.map(t => `<code style="background: rgba(59,130,246,0.15); color: #93c5fd; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.78rem;">${t}</code>`).join(" ") : 'None';
      const steps = rb.steps.map((s, i) => `
        <li style="margin-bottom: 0.5rem; color: var(--text-primary);">
          <strong style="color: var(--accent-cyan);">${i + 1}.</strong> ${s}
        </li>
      `).join("");

      return `
        <div class="noc-panel" style="margin-bottom: 1.5rem;">
          <div class="panel-header">
            <div>
              <span class="badge badge-medium" style="margin-bottom: 0.4rem;">${rb.category}</span>
              <h3 style="font-size: 1.2rem; font-weight: 700; color: #fff;">${rb.title}</h3>
              <small style="color: var(--text-muted); font-family: var(--font-mono);">${rb.id}</small>
            </div>
          </div>
          <p style="color: var(--text-secondary); margin-bottom: 1rem;">${rb.description}</p>

          <div style="background-color: #0b1120; border: 1px solid var(--border-color); border-radius: 8px; padding: 1rem; margin-bottom: 1rem;">
            <div style="font-size: 0.8rem; font-weight: 700; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 0.5rem;">Matching Symptoms / Conditions:</div>
            <div>${symptoms}</div>
          </div>

          <div style="font-size: 0.85rem; font-weight: 700; text-transform: uppercase; color: var(--accent-cyan); margin-bottom: 0.5rem;">Prescribed Troubleshooting Actions:</div>
          <ol style="padding-left: 1.25rem; list-style-type: none;">
            ${steps}
          </ol>
        </div>
      `;
    }).join("");

  } catch (err) {
    console.error("Runbooks page error:", err);
    container.innerHTML = '<div style="color: var(--color-critical); padding: 2rem;">Error loading runbook knowledge base.</div>';
  }
}
