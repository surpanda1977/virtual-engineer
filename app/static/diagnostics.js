// Incident Diagnostics UI logic
function $(id) { return document.getElementById(id); }

// Per-session identity (for isolated uploaded datasets) + active dataset.
const SID = (() => {
  let s = localStorage.getItem("ve-sid");
  if (!s) {
    s = (window.crypto && crypto.randomUUID) ? crypto.randomUUID()
        : "s" + Date.now() + Math.random().toString(16).slice(2);
    localStorage.setItem("ve-sid", s);
  }
  return s;
})();
let activeDataset = "base"; // "base" | "mine"

// Append the active dataset (and session id when using "my data") to any API URL.
function withDS(url) {
  const sep = url.includes("?") ? "&" : "?";
  let q = `dataset=${activeDataset}`;
  if (activeDataset === "mine") q += `&sid=${encodeURIComponent(SID)}`;
  return url + sep + q;
}

function escapeHtml(s) {
  return (s == null ? "" : String(s))
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

// Minimal markdown: **bold**, *em*, `code`, paragraphs.
function md(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, "<code>$1</code>")
    .split(/\n{2,}/).map((p) => `<p>${p.replaceAll("\n", "<br/>")}</p>`).join("");
}

function spinner(el, msg) {
  el.innerHTML = `<p class="muted">⏳ ${escapeHtml(msg || "Working…")}</p>`;
}

function sourceTag(src) {
  return src === "claude"
    ? `<span class="src-tag claude">✨ Claude analysis</span>`
    : `<span class="src-tag">offline heuristic</span>`;
}

function table(rows, cols) {
  if (!rows || !rows.length) return "<p class='muted'>None.</p>";
  const head = cols.map((c) => `<th>${escapeHtml(c.label)}</th>`).join("");
  const body = rows.map((r) =>
    "<tr>" + cols.map((c) => `<td>${escapeHtml(r[c.key])}</td>`).join("") + "</tr>"
  ).join("");
  return `<table class="dx-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

// Deloitte brand chart sequence (green first), used to give each category a distinct color.
const PALETTE = ["#86BC25", "#00A3E0", "#282728", "#63C631", "#A0DCFF", "#005587",
                 "#B7E320", "#0076A8", "#46B870", "#9DD4CF"];

function bars(rows, labelKey, valKey, colored = false) {
  if (!rows || !rows.length) return "<p class='muted'>No data.</p>";
  const max = Math.max(1, ...rows.map((r) => r[valKey]));
  return rows.map((r, i) => {
    const color = colored ? PALETTE[i % PALETTE.length] : "var(--dl-green)";
    return `
    <div class="bar-row">
      <span class="bar-label" title="${escapeHtml(r[labelKey])}">${escapeHtml(r[labelKey])}</span>
      <span class="bar-track"><span class="bar-fill" style="width:${(r[valKey] / max) * 100}%;background:${color}"></span></span>
      <span class="bar-val">${r[valKey]}</span>
    </div>`;
  }).join("");
}

// --- Tabs ---
document.querySelectorAll(".tab").forEach((t) => {
  t.onclick = () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    $("panel-" + t.dataset.tab).classList.add("active");
  };
});

// --- Stats bar ---
async function loadStats() {
  try {
    const d = await (await fetch(withDS("/api/itsm/stats"))).json();
    const s = d.stats || {};
    const cards = [
      ["incidents", "Incidents"], ["changes", "Changes"],
      ["problems", "Problems"], ["tasks", "Tasks"],
    ];
    $("stat-cards").innerHTML = cards.map(([k, label]) =>
      `<div class="stat"><b>${(s[k] || 0).toLocaleString()}</b><span>${label}</span></div>`
    ).join("");
  } catch (e) {
    $("stat-cards").innerHTML = `<div class="stat"><b>!</b><span>data not loaded</span></div>`;
  }
}

// --- Populate the Configuration Item dropdown ---
async function loadCIs() {
  const sel = $("rca-ci");
  try {
    const d = await (await fetch(withDS("/api/itsm/cis?limit=1000"))).json();
    sel.innerHTML = '<option value="">Select a configuration item…</option>' +
      (d.cis || []).map((c) =>
        `<option value="${escapeHtml(c.ci)}">${escapeHtml(c.ci)} (${c.incidents})</option>`).join("");
  } catch (e) {
    sel.innerHTML = '<option value="">Could not load configuration items</option>';
  }
}

// --- RCA (shared by the incident box and the CI dropdown) ---
async function runRca(id) {
  if (!id) return;
  const out = $("rca-out");
  spinner(out, `Correlating ITSM records for "${id}" and generating RCA…`);
  try {
    const d = await (await fetch(withDS("/api/itsm/rca?id=" + encodeURIComponent(id)))).json();
    if (!d.ok) { out.innerHTML = `<p class="err">⚠️ ${escapeHtml(d.error)}</p>`; return; }
    const c = d.correlation;
    out.innerHTML = `
      ${sourceTag(d.source)}
      <div class="rca-narrative">${md(d.rca)}</div>
      <div class="evidence">
        <h4>📋 Correlated evidence — CI: <code>${escapeHtml(d.cmdb_ci)}</code>
          <span class="muted">(${c.incident_count} incidents, ${c.change_count} changes on this CI)</span></h4>
        <details open><summary>Recent incidents (${c.incidents.length})</summary>
          ${table(c.incidents, [{key:"number",label:"INC"},{key:"opened_iso",label:"Opened"},{key:"priority",label:"Priority"},{key:"short_description",label:"Summary"},{key:"close_code",label:"Close code"}])}</details>
        <details><summary>Problems (${c.problems.length})</summary>
          ${table(c.problems, [{key:"number",label:"PRB"},{key:"short_description",label:"Summary"},{key:"state",label:"State"},{key:"related_incidents",label:"Rel. INC"}])}</details>
        <details><summary>Changes (${c.changes.length})</summary>
          ${table(c.changes, [{key:"number",label:"CHG"},{key:"type",label:"Type"},{key:"approval",label:"Approval"},{key:"created_iso",label:"Created"}])}</details>
        <details><summary>Similar past incidents (${d.similar.length})</summary>
          ${table(d.similar, [{key:"number",label:"INC"},{key:"short_description",label:"Summary"},{key:"close_code",label:"Resolution"}])}</details>
      </div>`;
  } catch (e) { out.innerHTML = `<p class="err">⚠️ ${escapeHtml(e.message)}</p>`; }
}
$("rca-go").onclick = () => runRca($("rca-input").value.trim());
$("rca-input").addEventListener("keydown", (e) => { if (e.key === "Enter") runRca($("rca-input").value.trim()); });
$("rca-ci-go").onclick = () => runRca($("rca-ci").value);
$("rca-ci").addEventListener("change", () => runRca($("rca-ci").value));

// --- Change impact ---
$("change-go").onclick = async () => {
  const w = $("change-window").value || 72;
  const out = $("change-out");
  spinner(out, "Correlating changes with subsequent incidents…");
  try {
    const d = await (await fetch(withDS(`/api/itsm/change-impact?window_hours=${w}`))).json();
    out.innerHTML = `
      ${sourceTag(d.source)}
      <div class="rca-narrative">${md(d.summary)}</div>
      <h4>Changes followed by incidents on the same CI (within ${escapeHtml(d.window_hours)}h)</h4>
      ${table(d.correlations, [{key:"change",label:"Change"},{key:"type",label:"Type"},{key:"ci",label:"CI"},{key:"change_time",label:"Change time"},{key:"incidents_after",label:"Incidents after"}])}`;
  } catch (e) { out.innerHTML = `<p class="err">⚠️ ${escapeHtml(e.message)}</p>`; }
};

// --- Similar ---
$("similar-go").onclick = async () => {
  const text = $("similar-input").value.trim();
  if (!text) return;
  const out = $("similar-out");
  spinner(out, "Retrieving similar incidents and synthesising guidance…");
  try {
    const d = await (await fetch(withDS("/api/itsm/similar"), {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    })).json();
    out.innerHTML = `
      ${sourceTag(d.source)}
      <div class="rca-narrative">${md(d.guidance)}</div>
      <h4>Most similar past incidents (${d.matches.length})</h4>
      ${table(d.matches, [{key:"number",label:"INC"},{key:"short_description",label:"Summary"},{key:"close_code",label:"Resolution"},{key:"assignment_group",label:"Team"}])}`;
  } catch (e) { out.innerHTML = `<p class="err">⚠️ ${escapeHtml(e.message)}</p>`; }
};

// --- Hotspots: interactive breakdown (responds to the dropdowns) ---
async function renderBreakdown() {
  const by = $("hot-dim").value, top = $("hot-top").value;
  const out = $("hot-breakdown");
  out.innerHTML = `<p class="muted">Loading breakdown…</p>`;
  try {
    const d = await (await fetch(withDS(`/api/itsm/breakdown?by=${by}&top=${top}`))).json();
    out.innerHTML = `<h4>📊 Incidents by ${escapeHtml(d.label)}</h4>${bars(d.rows, "label", "count", true)}`;
  } catch (e) { out.innerHTML = `<p class="err">⚠️ ${escapeHtml(e.message)}</p>`; }
}
$("hot-dim").onchange = renderBreakdown;
$("hot-top").onchange = renderBreakdown;

// --- Hotspots: portfolio summary + executive narrative ---
$("hotspots-go").onclick = async () => {
  renderBreakdown();
  const out = $("hotspots-out");
  spinner(out, "Aggregating portfolio and writing executive summary…");
  try {
    const d = await (await fetch(withDS("/api/itsm/hotspots?top=10"))).json();
    const sla = d.sla || {};
    out.innerHTML = `
      ${sourceTag(d.source)}
      <div class="rca-narrative">${md(d.summary)}</div>
      <div class="stat-cards">
        <div class="stat"><b>${(sla.breach_pct ?? 0)}%</b><span>SLA breach</span></div>
        <div class="stat"><b>${(d.reopened || 0).toLocaleString()}</b><span>reopened</span></div>
        <div class="stat"><b>${(d.major_incidents || 0).toLocaleString()}</b><span>major incidents</span></div>
      </div>
      <h4>🖥️ Top CIs by incidents</h4>${bars(d.top_cis, "ci", "incidents", true)}
      <h4>👥 Top assignment groups</h4>${bars(d.top_groups, "team", "incidents", true)}
      <h4>🗂️ Top categories</h4>${bars(d.top_categories, "category", "incidents", true)}
      <h4>📈 Monthly volume</h4>${bars(d.by_month, "month", "incidents")}`;
  } catch (e) { out.innerHTML = `<p class="err">⚠️ ${escapeHtml(e.message)}</p>`; }
};

// --- Data source toggle (Base ⇄ My data) ---
function clearOutputs() {
  ["rca-out", "change-out", "similar-out", "hot-breakdown", "hotspots-out"].forEach((id) => {
    const e = $(id); if (e) e.innerHTML = "";
  });
}
document.querySelectorAll(".seg-btn").forEach((b) => {
  b.onclick = () => {
    if (b.disabled || b.classList.contains("active")) return;
    document.querySelectorAll(".seg-btn").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    activeDataset = b.dataset.ds;
    clearOutputs();
    loadStats();
    loadCIs();
  };
});

// --- Upload your own data ---
$("upload-toggle").onclick = () => { const a = $("upload-area"); a.hidden = !a.hidden; };

$("upload-go").onclick = async () => {
  const input = $("ve-files");
  const status = $("upload-status");
  if (!input.files.length) { status.innerHTML = `<p class="muted">Choose your files first.</p>`; return; }
  status.innerHTML = `<p class="muted">⏳ Uploading and building your isolated dataset…</p>`;
  try {
    const fd = new FormData();
    [...input.files].forEach((f) => fd.append("files", f));
    const res = await fetch(`/api/itsm/upload?sid=${encodeURIComponent(SID)}`, { method: "POST", body: fd });
    const d = await res.json();
    if (!d.ok) { status.innerHTML = `<p class="err">⚠️ ${escapeHtml(d.error)}</p>`; return; }
    const det = Object.entries(d.detected)
      .map(([f, t]) => `<li>${escapeHtml(f)} → <strong>${escapeHtml(t)}</strong></li>`).join("");
    const counts = Object.entries(d.counts).filter(([k]) => k !== "fts")
      .map(([k, v]) => `${k}: ${Number(v).toLocaleString()}`).join(" · ");
    status.innerHTML = `<p>✅ Detected file types:</p><ul class="examples">${det}</ul>
      <p class="muted">Loaded — ${escapeHtml(counts)}. Now analyzing <strong>your</strong> data.</p>`;
    const segMine = $("seg-mine");
    segMine.disabled = false;
    segMine.title = "Your uploaded data";
    segMine.click(); // switch to My data + reload
  } catch (e) { status.innerHTML = `<p class="err">⚠️ ${escapeHtml(e.message)}</p>`; }
};

loadStats();
loadCIs();
