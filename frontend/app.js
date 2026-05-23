/* ------------------------------------------------------------------ *
 * Agentic Review — dashboard SPA (vanilla, no build step)
 * Hash router · reusable components · real data (your review runs +
 * /api/metrics + /api/config). No fabricated repos/history/confidence.
 * ------------------------------------------------------------------ */

"use strict";

// ----------------------------- constants -----------------------------
const SEV_ORDER = ["high", "medium", "low"];
const SEV_RANK = { high: 3, medium: 2, low: 1 };
const KINDS = ["bug", "style", "refactor"];

const PIPELINE = [
  { t: "Resolving pull request", d: "Validate URL · confirm public repo" },
  { t: "Fetching diff", d: "Pull unified diff from GitHub" },
  { t: "Parsing changed files", d: "Split hunks · map line ranges" },
  { t: "Bug detection", d: "Chain-of-Thought · correctness defects" },
  { t: "Style & consistency review", d: "Chain-of-Thought · naming, dead code" },
  { t: "Refactor analysis", d: "Chain-of-Thought · simplifications" },
  { t: "Aggregating findings", d: "Merge · de-duplicate by file·line·kind" },
];

const NAV = [
  { name: "dashboard", label: "Dashboard", icon: "grid" },
  { name: "repositories", label: "Repositories", icon: "branch" },
  { name: "reviews", label: "Reviews", icon: "pr" },
  { name: "findings", label: "Findings", icon: "shield" },
  { name: "agents", label: "Agents", icon: "cpu" },
  { name: "settings", label: "Settings", icon: "gear" },
];

const ICONS = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
  branch: '<line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/>',
  pr: '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><line x1="6" y1="9" x2="6" y2="21"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>',
  cpu: '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 0 1-4 0v-.1A1.6 1.6 0 0 0 7 19.7l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0-1.1-2.7H3a2 2 0 0 1 0-4h.1A1.6 1.6 0 0 0 4.3 7l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H9a1.6 1.6 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.6 1.6 0 0 0 2.7 1.1l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V9a1.6 1.6 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z"/>',
  search: '<circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
  plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  check: '<polyline points="20 6 9 17 4 12"/>',
  x: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  chevron: '<polyline points="9 18 15 12 9 6"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
  alert: '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  clock: '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/>',
  external: '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>',
  inbox: '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
  checkCircle: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
};

function icon(name, size = 16) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[name] || ""}</svg>`;
}

// ----------------------------- state ---------------------------------
const App = {
  health: null,
  config: null,
  metrics: null,
  repoFilter: "",
  findingsFilter: { severity: "", kind: "", status: "", q: "" },
};

// ----------------------------- store ---------------------------------
const RKEY = "acr.reviews.v1";
const SKEY = "acr.status.v1";

function loadReviews() {
  try { return JSON.parse(localStorage.getItem(RKEY) || "[]"); } catch { return []; }
}
function saveReviews(list) { localStorage.setItem(RKEY, JSON.stringify(list)); }
function loadStatuses() {
  try { return JSON.parse(localStorage.getItem(SKEY) || "{}"); } catch { return {}; }
}
function saveStatuses(map) { localStorage.setItem(SKEY, JSON.stringify(map)); }

function addReview(res, prUrl) {
  const list = loadReviews();
  const rec = {
    id: "rv_" + Math.random().toString(36).slice(2, 9),
    repo: res.repo || parsePr(prUrl)?.repo || "unknown",
    pr_number: res.pr_number || parsePr(prUrl)?.number || 0,
    pr_url: res.pr_url || prUrl,
    createdAt: Date.now(),
    summary: res.summary || "",
    findings: res.findings || [],
    diff: res.diff || "",
  };
  list.unshift(rec);
  saveReviews(list.slice(0, 50));
  return rec;
}
function getReview(id) { return loadReviews().find((r) => r.id === id); }

function fingerprint(repo, f) { return `${repo}|${f.file}|${f.line}|${f.kind}`; }
function statusOf(repo, f) { return loadStatuses()[fingerprint(repo, f)] || "open"; }
function setStatus(repo, f, status) {
  const map = loadStatuses();
  map[fingerprint(repo, f)] = status;
  saveStatuses(map);
}

function allFindings() {
  const out = [];
  for (const r of loadReviews()) {
    for (const f of r.findings) {
      out.push({ ...f, repo: r.repo, reviewId: r.id, pr_number: r.pr_number, createdAt: r.createdAt });
    }
  }
  return out;
}
function reposFromReviews() {
  const map = new Map();
  for (const r of loadReviews()) {
    const m = map.get(r.repo) || { repo: r.repo, reviews: 0, findings: 0, open: 0, last: 0, topSev: null };
    m.reviews += 1;
    m.findings += r.findings.length;
    m.last = Math.max(m.last, r.createdAt);
    for (const f of r.findings) {
      if (statusOf(r.repo, f) === "open") m.open += 1;
      if (!m.topSev || SEV_RANK[f.severity] > SEV_RANK[m.topSev]) m.topSev = f.severity;
    }
    map.set(r.repo, m);
  }
  return [...map.values()].sort((a, b) => b.last - a.last);
}

// ----------------------------- utils ---------------------------------
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function parsePr(url) {
  const m = /github\.com\/([^/\s]+)\/([^/\s]+)\/pull\/(\d+)/.exec(url || "");
  return m ? { owner: m[1], repo: `${m[1]}/${m[2]}`, name: m[2], number: +m[3] } : null;
}
function timeAgo(ts) {
  const s = Math.floor((Date.now() - ts) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  if (s < 7 * 86400) return `${Math.floor(s / 86400)}d ago`;
  return new Date(ts).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
function sevCounts(findings) {
  const c = { high: 0, medium: 0, low: 0 };
  for (const f of findings) if (c[f.severity] != null) c[f.severity]++;
  return c;
}

// ----------------------------- components ----------------------------
function sevBadge(sev) {
  return `<span class="badge sev-${sev}"><span class="bdot"></span>${esc(sev)}</span>`;
}
function kindBadge(kind) {
  return `<span class="badge badge-kind"><span class="bdot ${esc(kind)}"></span>${esc(kind)}</span>`;
}
function statusBadge(st) {
  return `<span class="badge badge-status ${esc(st)}">${esc(st)}</span>`;
}
function sevChips(c) {
  const parts = [];
  if (c.high) parts.push(`<span class="badge sev-high"><span class="bdot"></span>${c.high} high</span>`);
  if (c.medium) parts.push(`<span class="badge sev-medium"><span class="bdot"></span>${c.medium} medium</span>`);
  if (c.low) parts.push(`<span class="badge sev-low"><span class="bdot"></span>${c.low} low</span>`);
  return parts.join(" ") || `<span class="badge sev-low"><span class="bdot"></span>clean</span>`;
}
function emptyState({ ico = "inbox", title, body, action = "" }) {
  return `<div class="state"><div class="ico">${icon(ico, 20)}</div><h4>${esc(title)}</h4><p>${esc(body)}</p>${action}</div>`;
}

// ----------------------------- diff parser ---------------------------
function parseDiff(text) {
  const files = [];
  let cur = null;
  let oldNo = 0, newNo = 0;
  const push = () => { if (cur) files.push(cur); };
  for (const line of (text || "").split("\n")) {
    if (line.startsWith("diff --git")) {
      push();
      cur = { path: "", hunks: [], additions: 0, deletions: 0 };
    } else if (line.startsWith("--- ")) {
      if (!cur) cur = { path: "", hunks: [], additions: 0, deletions: 0 };
      cur._old = line.slice(4).replace(/^a\//, "");
    } else if (line.startsWith("+++ ")) {
      if (!cur) cur = { path: "", hunks: [], additions: 0, deletions: 0 };
      const p = line.slice(4).replace(/^b\//, "");
      cur.path = p !== "/dev/null" ? p : (cur._old && cur._old !== "/dev/null" ? cur._old : p);
    } else if (line.startsWith("@@")) {
      const m = /@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)/.exec(line);
      if (m && cur) {
        oldNo = +m[1]; newNo = +m[2];
        cur.hunks.push({ header: line.slice(0, line.indexOf("@@", 2) + 2), context: m[3].trim(), lines: [] });
      }
    } else if (cur && cur.hunks.length) {
      const h = cur.hunks[cur.hunks.length - 1];
      if (line.startsWith("+")) { h.lines.push({ type: "add", newNo, text: line.slice(1) }); cur.additions++; newNo++; }
      else if (line.startsWith("-")) { h.lines.push({ type: "del", oldNo, text: line.slice(1) }); cur.deletions++; oldNo++; }
      else if (line.startsWith("\\")) { /* no newline marker */ }
      else { h.lines.push({ type: "ctx", oldNo, newNo, text: line.slice(1) }); oldNo++; newNo++; }
    }
  }
  push();
  return files.filter((f) => f.path);
}
function snippetFor(files, path, line, ctx = 2) {
  const f = files.find((x) => x.path === path);
  if (!f || line == null) return null;
  const rows = [];
  for (const h of f.hunks) for (const l of h.lines) if (l.type !== "del") rows.push(l);
  const idx = rows.findIndex((l) => l.newNo === line);
  if (idx < 0) return null;
  return rows.slice(Math.max(0, idx - ctx), idx + ctx + 1).map((l) => ({ no: l.newNo, text: l.text, target: l.newNo === line }));
}

// ----------------------------- pages ---------------------------------
function pageDashboard() {
  const reviews = loadReviews();
  const findings = allFindings();
  const open = findings.filter((f) => statusOf(f.repo, f) === "open");
  const c = sevCounts(open);
  const m = App.metrics && App.metrics.summary ? App.metrics.summary : null;
  const f1 = m ? m.overall.f1.toFixed(2) : "—";

  const stat = (k, v, ico, extra = "") =>
    `<div class="card stat"><div class="k">${icon(ico, 14)} ${k}</div><div class="v">${v}</div>${extra}</div>`;

  const recent = reviews.slice(0, 6);
  const recentCard = `
    <div class="card">
      <div class="card-head"><h3>Recent reviews</h3><div class="actions"><a class="btn btn-sm" href="#/reviews">View all ${icon("chevron", 14)}</a></div></div>
      <div class="card-body flush">
        ${recent.length ? `<div class="table-wrap"><table class="tbl">
          <thead><tr><th>Pull request</th><th>Findings</th><th>Severity</th><th>When</th></tr></thead>
          <tbody>${recent.map((r) => {
            const cc = sevCounts(r.findings);
            return `<tr class="clickable" data-go="#/reviews/${r.id}">
              <td><span class="path">${esc(r.repo)}#${r.pr_number}</span></td>
              <td class="num">${r.findings.length}</td>
              <td>${sevChips(cc)}</td>
              <td class="muted">${timeAgo(r.createdAt)}</td></tr>`;
          }).join("")}</tbody></table></div>`
          : emptyState({ ico: "pr", title: "No reviews yet", body: "Review a public pull request to populate your dashboard.", action: `<button class="btn btn-primary btn-sm" data-new>${icon("plus", 14)} New review</button>` })}
      </div>
    </div>`;

  const riskCard = `
    <div class="card">
      <div class="card-head"><h3>Open findings by severity</h3></div>
      <div class="card-body">
        ${open.length ? SEV_ORDER.map((s) => {
          const n = c[s]; const pct = open.length ? Math.round((n / open.length) * 100) : 0;
          return `<div class="between" style="margin-bottom:10px"><div class="row" style="min-width:90px">${sevBadge(s)}</div>
            <div style="flex:1;height:8px;border-radius:999px;background:var(--surface-2);overflow:hidden"><div style="height:100%;width:${pct}%;background:var(--sev-${s})"></div></div>
            <div class="muted" style="width:36px;text-align:right;font-variant-numeric:tabular-nums">${n}</div></div>`;
        }).join("")
          : emptyState({ ico: "checkCircle", title: "Nothing open", body: "Findings you triage will appear here grouped by severity." })}
      </div>
    </div>`;

  return {
    crumbs: [{ cur: "Dashboard" }],
    actions: `<button class="btn btn-primary" data-new>${icon("plus", 15)} New review</button>`,
    body: `
      <div class="grid" style="grid-template-columns:repeat(4,1fr);margin-bottom:16px">
        ${stat("Open findings", open.length, "shield")}
        ${stat("High severity", c.high, "alert")}
        ${stat("Reviews run", reviews.length, "pr")}
        ${stat("Benchmark F1", f1, "checkCircle", m ? `<div class="delta">precision ${m.overall.precision.toFixed(2)} · recall ${m.overall.recall.toFixed(2)}</div>` : "")}
      </div>
      <div class="grid grid-2" style="margin-bottom:16px">${recentCard}${riskCard}</div>
      ${benchmarkCard()}
    `,
    wire: wireRowNav,
  };
}

function benchmarkCard() {
  const data = App.metrics;
  if (!data || data.available === false || !data.summary) {
    return `<div class="card"><div class="card-head"><h3>Benchmark</h3></div><div class="card-body">${emptyState({ ico: "checkCircle", title: "No benchmark results", body: "Run python -m eval.run to generate eval/results.json." })}</div></div>`;
  }
  const s = data.summary;
  const sample = data.sample ? `<span class="mono-tag" title="Illustrative placeholder">sample data</span>` : "";
  const rows = [["overall", s.overall], ...KINDS.filter((k) => s.by_kind && s.by_kind[k]).map((k) => [k, s.by_kind[k]])];
  let delta = `<p class="muted" style="margin:12px 0 0;font-size:12.5px">Single-shot baseline not measured for this run.</p>`;
  if (data.baseline && data.baseline.overall) {
    const cot = s.overall.precision, base = data.baseline.overall.precision, d = cot - base;
    delta = `<div class="chip" style="margin-top:12px">CoT precision <b style="color:var(--ink)">${cot.toFixed(2)}</b> vs ${esc(data.baseline.label || "single-shot")} <b style="color:var(--ink)">${base.toFixed(2)}</b> · Δ <b style="color:var(--ok)">${d >= 0 ? "+" : ""}${d.toFixed(2)}</b></div>`;
  }
  return `
    <div class="card">
      <div class="card-head"><h3>Benchmark results</h3><div class="actions">${sample}</div></div>
      <div class="card-body flush">
        <div class="table-wrap"><table class="tbl">
          <thead><tr><th>Scope</th><th>Precision</th><th>Recall</th><th>F1</th><th>Labels found</th></tr></thead>
          <tbody>${rows.map(([name, mm]) => `<tr><td style="text-transform:capitalize">${esc(name)}</td>
            <td class="num">${mm.precision.toFixed(2)}</td><td class="num">${mm.recall.toFixed(2)}</td>
            <td class="num">${mm.f1.toFixed(2)}</td><td class="num">${mm.labels_found}/${mm.labels}</td></tr>`).join("")}</tbody>
        </table></div>
        <div style="padding:0 16px 16px">${delta}</div>
      </div>
    </div>`;
}

function pageRepositories() {
  const repos = reposFromReviews().filter((r) => !App.repoFilter || r.repo === App.repoFilter);
  return {
    crumbs: [{ cur: "Repositories" }],
    actions: `<button class="btn btn-primary" data-new>${icon("plus", 15)} New review</button>`,
    body: `<div class="card"><div class="card-head"><h3>Repositories</h3><div class="sub">Derived from pull requests you've reviewed</div></div>
      <div class="card-body flush">${repos.length ? `<div class="table-wrap"><table class="tbl">
        <thead><tr><th>Repository</th><th>Reviews</th><th>Open findings</th><th>Top severity</th><th>Last reviewed</th></tr></thead>
        <tbody>${repos.map((r) => `<tr class="clickable" data-go="#/reviews">
          <td><span class="path">${esc(r.repo)}</span></td>
          <td class="num">${r.reviews}</td><td class="num">${r.open}</td>
          <td>${r.topSev ? sevBadge(r.topSev) : '<span class="muted">—</span>'}</td>
          <td class="muted">${timeAgo(r.last)}</td></tr>`).join("")}</tbody></table></div>`
        : emptyState({ ico: "branch", title: "No repositories yet", body: "Review a public PR and the repository will show up here with its findings.", action: `<button class="btn btn-primary btn-sm" data-new>${icon("plus", 14)} New review</button>` })}
      </div></div>`,
    wire: wireRowNav,
  };
}

function pageReviews() {
  let reviews = loadReviews();
  if (App.repoFilter) reviews = reviews.filter((r) => r.repo === App.repoFilter);
  return {
    crumbs: [{ cur: "Reviews" }],
    actions: `<button class="btn btn-primary" data-new>${icon("plus", 15)} New review</button>`,
    body: `<div class="card"><div class="card-head"><h3>Reviews</h3><div class="sub">${reviews.length} total</div></div>
      <div class="card-body flush">${reviews.length ? `<div class="table-wrap"><table class="tbl">
        <thead><tr><th>Pull request</th><th>Findings</th><th>Severity</th><th>Status</th><th>Reviewed</th></tr></thead>
        <tbody>${reviews.map((r) => `<tr class="clickable" data-go="#/reviews/${r.id}">
          <td><span class="path">${esc(r.repo)}#${r.pr_number}</span></td>
          <td class="num">${r.findings.length}</td>
          <td>${sevChips(sevCounts(r.findings))}</td>
          <td><span class="badge badge-status resolved">completed</span></td>
          <td class="muted">${timeAgo(r.createdAt)}</td></tr>`).join("")}</tbody></table></div>`
        : emptyState({ ico: "pr", title: "No reviews yet", body: "Paste a public pull request URL to run your first review.", action: `<button class="btn btn-primary btn-sm" data-new>${icon("plus", 14)} New review</button>` })}
      </div></div>`,
    wire: wireRowNav,
  };
}

function pageReviewDetail(id) {
  const r = getReview(id);
  if (!r) {
    return { crumbs: [{ link: "#/reviews", label: "Reviews" }, { cur: "Not found" }],
      body: emptyState({ ico: "alert", title: "Review not found", body: "This review isn't in your local history. It may have been cleared." }) };
  }
  const files = parseDiff(r.diff);
  const c = sevCounts(r.findings);
  const findingsByFile = {};
  for (const f of r.findings) (findingsByFile[f.file] = findingsByFile[f.file] || []).push(f);

  // --- Findings tab (severity-grouped) ---
  const grouped = SEV_ORDER.map((sev) => {
    const items = r.findings.filter((f) => f.severity === sev);
    if (!items.length) return "";
    return `<div class="sev-group"><div class="sev-group-head">${sevBadge(sev)}<span class="n">${items.length} finding${items.length > 1 ? "s" : ""}</span></div>
      ${items.map((f) => findingCard(r, f, files)).join("")}</div>`;
  }).join("");
  const findingsTab = r.findings.length ? grouped
    : emptyState({ ico: "checkCircle", title: "No issues found", body: "The agent reviewed every changed hunk and flagged nothing." });

  // --- Files changed tab (diff) ---
  const filesTab = files.length ? files.map((f) => diffFile(f, findingsByFile[f.path] || [])).join("")
    : `<div class="card"><div class="card-body">${emptyState({ ico: "file", title: "No diff available", body: "The diff for this pull request wasn't captured." })}</div></div>`;

  // --- left rail ---
  const fileList = files.length ? `<div class="filelist">${files.map((f) => {
    const fc = (findingsByFile[f.path] || []).length;
    return `<div class="fl" data-file="${esc(f.path)}"><span>${icon("file", 15)}</span><span class="fp">${esc(f.path)}</span>
      <span class="fc"><span class="mono" style="color:var(--ok);font-size:11px">+${f.additions}</span><span class="mono" style="color:var(--err);font-size:11px">−${f.deletions}</span>${fc ? `<span class="badge sev-low" style="height:18px">${fc}</span>` : ""}</span></div>`;
  }).join("")}</div>` : `<div class="muted" style="padding:8px">No changed files parsed.</div>`;

  return {
    crumbs: [{ link: "#/reviews", label: "Reviews" }, { cur: `${r.repo}#${r.pr_number}`, mono: true }],
    actions: `<a class="btn" href="${esc(r.pr_url)}" target="_blank" rel="noopener">${icon("external", 14)} Open on GitHub</a><button class="btn btn-primary" data-new>${icon("plus", 15)} New review</button>`,
    body: `
      <div class="card" style="margin-bottom:20px"><div class="card-body">
        <div class="between" style="align-items:flex-start">
          <div>
            <div class="row" style="gap:10px"><span class="path mono" style="font-size:15px;font-weight:600">${esc(r.repo)}</span><span class="mono-tag">#${r.pr_number}</span><span class="badge badge-status resolved">${icon("check", 12)} completed</span></div>
            <div class="muted" style="margin-top:6px;font-size:13px">${esc(r.summary || "Review completed.")}</div>
          </div>
          <div class="wrap-gap" style="justify-content:flex-end;max-width:340px">${sevChips(c)}</div>
        </div>
      </div></div>
      <div class="cols">
        <div class="grid" style="gap:16px">
          <div class="card"><div class="card-head"><h3>Changed files</h3><div class="sub">${files.length}</div></div><div class="card-body" style="padding:8px">${fileList}</div></div>
          <div class="card"><div class="card-head"><h3>Agent pipeline</h3></div><div class="card-body">${timelineHtml(PIPELINE.length, true)}</div></div>
        </div>
        <div>
          <div class="tabs"><div class="tab active" data-tab="findings">Findings <span class="n">${r.findings.length}</span></div><div class="tab" data-tab="diff">Files changed <span class="n">${files.length}</span></div></div>
          <div data-pane="findings">${findingsTab}</div>
          <div data-pane="diff" style="display:none">${filesTab}</div>
        </div>
      </div>`,
    wire(root) {
      root.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => {
        root.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x === t));
        const which = t.dataset.tab;
        root.querySelector('[data-pane="findings"]').style.display = which === "findings" ? "" : "none";
        root.querySelector('[data-pane="diff"]').style.display = which === "diff" ? "" : "none";
      }));
      root.querySelectorAll(".fl").forEach((fl) => fl.addEventListener("click", () => {
        root.querySelector('.tab[data-tab="diff"]').click();
        const target = root.querySelector(`.difffile[data-file="${CSS.escape(fl.dataset.file)}"]`);
        if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      }));
    },
  };
}

function findingCard(review, f, files) {
  const snip = snippetFor(files, f.file, f.line);
  return `<div class="finding">
    <div class="finding-top">${kindBadge(f.kind)}<span class="ftitle">${esc(f.summary)}</span>
      <span class="floc">${esc(f.file)}${f.line != null ? `:${f.line}` : ""}</span></div>
    <div class="finding-body">
      <div class="fsection"><div class="lbl">Why this matters</div><p>${esc(f.detail)}</p></div>
      ${snip ? `<div class="snippet"><pre>${snip.map((l) => `${String(l.no).padStart(4)}  ${l.target ? "▸ " : "  "}${esc(l.text)}`).join("\n")}</pre></div>` : ""}
      ${f.suggested_fix ? `<div class="fix"><b>Suggested fix</b> — ${esc(f.suggested_fix)}</div>` : ""}
    </div></div>`;
}

function diffFile(f, findings) {
  const byLine = {};
  for (const fd of findings) if (fd.line != null) (byLine[fd.line] = byLine[fd.line] || []).push(fd);
  const rows = [];
  for (const h of f.hunks) {
    rows.push(`<tr class="hunk"><td class="gut"></td><td class="gut"></td><td>@@ ${esc(h.context || "")}</td></tr>`);
    for (const l of h.lines) {
      const sign = l.type === "add" ? "+" : l.type === "del" ? "−" : " ";
      rows.push(`<tr class="${l.type}"><td class="gut">${l.oldNo || ""}</td><td class="gut">${l.newNo || ""}</td><td>${esc(sign + l.text)}</td></tr>`);
      if (l.type !== "del" && byLine[l.newNo]) {
        for (const fd of byLine[l.newNo]) {
          rows.push(`<tr class="diff-inline"><td colspan="3"><div class="row" style="gap:8px;margin-bottom:6px">${sevBadge(fd.severity)}${kindBadge(fd.kind)}<b style="font-family:var(--sans)">${esc(fd.summary)}</b></div>
            <div style="font-family:var(--sans);color:var(--ink-2);font-size:13px">${esc(fd.detail)}</div>
            ${fd.suggested_fix ? `<div class="fix" style="font-family:var(--sans);margin-top:8px"><b>Suggested fix</b> — ${esc(fd.suggested_fix)}</div>` : ""}</td></tr>`);
        }
      }
    }
  }
  return `<div class="difffile" data-file="${esc(f.path)}">
    <div class="difffile-head"><span>${icon("file", 14)}</span><span class="fp">${esc(f.path)}</span>
      <span class="counts"><span class="add">+${f.additions}</span> <span class="del">−${f.deletions}</span></span></div>
    <table class="difftable"><tbody>${rows.join("")}</tbody></table></div>`;
}

function pageFindings() {
  const flt = App.findingsFilter;
  let items = allFindings();
  items = items.filter((f) => {
    if (App.repoFilter && f.repo !== App.repoFilter) return false;
    if (flt.severity && f.severity !== flt.severity) return false;
    if (flt.kind && f.kind !== flt.kind) return false;
    if (flt.status && statusOf(f.repo, f) !== flt.status) return false;
    if (flt.q) {
      const q = flt.q.toLowerCase();
      if (!(`${f.file} ${f.summary} ${f.repo}`.toLowerCase().includes(q))) return false;
    }
    return true;
  });
  items.sort((a, b) => SEV_RANK[b.severity] - SEV_RANK[a.severity] || b.createdAt - a.createdAt);

  const sel = (name, opts) => `<select class="select" data-f="${name}"><option value="">${opts.label}</option>${opts.values.map((v) => `<option value="${v}" ${flt[name] === v ? "selected" : ""} style="text-transform:capitalize">${v}</option>`).join("")}</select>`;

  const body = `
    <div class="filters" style="margin-bottom:14px">
      <div class="search" style="min-width:240px">${icon("search", 14)}<input data-f="q" placeholder="Search file, rule, repo…" value="${esc(flt.q)}"/></div>
      ${sel("severity", { label: "All severities", values: SEV_ORDER })}
      ${sel("kind", { label: "All categories", values: KINDS })}
      ${sel("status", { label: "All statuses", values: ["open", "resolved", "ignored"] })}
      <span class="muted" style="margin-left:auto;font-size:12.5px">${items.length} finding${items.length === 1 ? "" : "s"}</span>
    </div>
    <div class="card"><div class="card-body flush">${items.length ? `<div class="table-wrap"><table class="tbl">
      <thead><tr><th>Severity</th><th>Finding</th><th>Category</th><th>Source</th><th>Detected</th><th>Status</th><th></th></tr></thead>
      <tbody>${items.map((f) => {
        const st = statusOf(f.repo, f);
        return `<tr class="clickable" data-go="#/reviews/${f.reviewId}">
          <td>${sevBadge(f.severity)}</td>
          <td><div style="font-weight:500">${esc(f.summary)}</div><div class="path">${esc(f.file)}${f.line != null ? `:${f.line}` : ""}</div></td>
          <td>${kindBadge(f.kind)}</td>
          <td><span class="path">${esc(f.repo)}#${f.pr_number}</span></td>
          <td class="muted">${timeAgo(f.createdAt)}</td>
          <td>${statusBadge(st)}</td>
          <td onclick="event.stopPropagation()"><div class="row">
            <button class="btn btn-ghost btn-sm" data-status="resolved" data-fp="${esc(fingerprint(f.repo, f))}" title="Mark resolved">${icon("check", 14)}</button>
            <button class="btn btn-ghost btn-sm" data-status="ignored" data-fp="${esc(fingerprint(f.repo, f))}" title="Ignore">${icon("x", 14)}</button>
          </div></td></tr>`;
      }).join("")}</tbody></table></div>`
      : emptyState({ ico: "shield", title: hasFindings() ? "No findings match your filters" : "No findings yet", body: hasFindings() ? "Try clearing a filter to see more results." : "Run a review and any issues the agent flags will collect here." })}
    </div></div>`;

  return {
    crumbs: [{ cur: "Findings" }],
    actions: `<button class="btn btn-primary" data-new>${icon("plus", 15)} New review</button>`,
    body,
    wire(root) {
      wireRowNav(root);
      root.querySelectorAll("[data-f]").forEach((el) => {
        const ev = el.tagName === "INPUT" ? "input" : "change";
        el.addEventListener(ev, () => {
          flt[el.dataset.f] = el.value;
          if (ev === "input") return; // don't full re-render per keystroke
          render();
        });
        if (el.tagName === "INPUT") el.addEventListener("keydown", (e) => { if (e.key === "Enter") render(); });
      });
      root.querySelectorAll("[data-status]").forEach((b) => b.addEventListener("click", () => {
        const map = loadStatuses();
        const cur = map[b.dataset.fp];
        map[b.dataset.fp] = cur === b.dataset.status ? "open" : b.dataset.status; // toggle
        saveStatuses(map); render();
      }));
    },
  };
}
function hasFindings() { return allFindings().length > 0; }

function pageAgents() {
  const last = loadReviews()[0];
  const model = App.config ? App.config.model : "—";
  const chains = [
    { name: "Bug detection", d: "Correctness defects — logic errors, None handling, off-by-one, race conditions, resource leaks. Tuned for high precision." },
    { name: "Style & consistency", d: "Naming, dead code, duplication, missing types/docstrings; judged against codebase conventions." },
    { name: "Refactor analysis", d: "Concrete simplifications and extractions, each paired with a suggested fix." },
  ];
  return {
    crumbs: [{ cur: "Agents" }],
    body: `
      <div class="cols">
        <div class="grid" style="gap:16px">
          <div class="card"><div class="card-head"><h3>Review pipeline</h3></div><div class="card-body">${timelineHtml(PIPELINE.length, !!last)}</div></div>
          <div class="card"><div class="card-head"><h3>Runtime</h3></div><div class="card-body"><dl class="meta-grid">
            <dt>Model</dt><dd><span class="mono-tag">${esc(model)}</span></dd>
            <dt>Mode</dt><dd>Read-only · public repos</dd>
            <dt>RAG context</dt><dd>${App.config && App.config.rag_enabled ? "enabled" : "off (hosted demo)"}</dd>
          </dl></div></div>
        </div>
        <div>
          <div class="card" style="margin-bottom:16px"><div class="card-head"><h3>Reviewer agents</h3><div class="sub">Three Chain-of-Thought chains run per changed hunk</div></div>
            <div class="card-body list-rows" style="padding:0">${chains.map((c) => `<div style="padding:14px 16px"><div class="row" style="gap:8px;margin-bottom:4px">${icon("cpu", 15)}<b>${esc(c.name)}</b></div><div class="muted" style="font-size:13px">${esc(c.d)}</div></div>`).join("")}</div>
          </div>
          <div class="card"><div class="card-head"><h3>Last run</h3></div><div class="card-body">${last
            ? `<div class="between"><div><div class="path">${esc(last.repo)}#${last.pr_number}</div><div class="muted" style="font-size:12.5px;margin-top:2px">${timeAgo(last.createdAt)} · ${last.findings.length} findings</div></div><a class="btn btn-sm" href="#/reviews/${last.id}">Open ${icon("chevron", 14)}</a></div>`
            : `<p class="muted" style="margin:0;font-size:13px">No runs yet.</p>`}</div></div>
        </div>
      </div>`,
  };
}

function pageSettings() {
  const cfg = App.config || {};
  const field = (label, value, desc) => `<div style="padding:14px 16px"><div class="between"><div><div style="font-weight:500">${esc(label)}</div><div class="muted" style="font-size:12.5px;margin-top:2px">${esc(desc)}</div></div><div>${value}</div></div></div>`;
  return {
    crumbs: [{ cur: "Settings" }],
    body: `<div class="card" style="max-width:720px"><div class="card-head"><h3>Configuration</h3><div class="sub">Read-only runtime settings</div></div>
      <div class="card-body list-rows" style="padding:0">
        ${field("Model", `<span class="mono-tag">${esc(cfg.model || "—")}</span>`, "Anthropic model backing the review chains")}
        ${field("Demo mode", `<span class="badge badge-status resolved">read-only</span>`, "Findings are returned to the dashboard; nothing is posted back to GitHub")}
        ${field("Repository access", `<span class="badge badge-status open">public only</span>`, "Private repositories are rejected")}
        ${field("RAG context", `<span class="badge badge-status ignored">${cfg.rag_enabled ? "enabled" : "off"}</span>`, "The hosted demo reviews diffs without indexing the repo")}
        ${field("Rate limit", `<span class="mono-tag">${cfg.rate_limit_per_min ?? "—"}/min</span>`, "Per client IP")}
      </div></div>
      <div class="card" style="max-width:720px;margin-top:16px"><div class="card-head"><h3>Resources</h3></div>
        <div class="card-body list-rows" style="padding:0">
          ${field("API health", `<span class="badge badge-status ${App.health === "ok" ? "resolved" : "open"}">${App.health || "checking…"}</span>`, "GET /api/health")}
          ${field("Benchmark metrics", `<a class="btn btn-sm" href="/api/metrics" target="_blank">View JSON ${icon("external", 13)}</a>`, "GET /api/metrics")}
        </div></div>`,
  };
}

// ----------------------------- timeline ------------------------------
function timelineHtml(activeUpTo, done = false) {
  return `<div class="timeline">${PIPELINE.map((s, i) => {
    let cls = "pending", node = "pending", inner = "";
    if (done || i < activeUpTo) { cls = "done"; node = "done"; inner = icon("check", 11); }
    else if (i === activeUpTo) { cls = "run"; node = "run"; inner = `<div class="spinner" style="width:10px;height:10px;border-width:2px"></div>`; }
    return `<div class="tl-step ${cls}"><div class="tl-rail"><div class="tl-node ${node}">${inner}</div><div class="tl-line"></div></div>
      <div class="tl-body"><div class="t">${esc(s.t)}</div><div class="d">${esc(s.d)}</div></div></div>`;
  }).join("")}</div>`;
}

// ----------------------------- composer ------------------------------
let composerTimer = null;
function openComposer() {
  closeComposer();
  const ov = document.createElement("div");
  ov.className = "overlay";
  ov.id = "composer";
  ov.innerHTML = `<div class="modal" role="dialog" aria-modal="true">
    <div class="modal-head"><h3>New review</h3><button class="btn btn-ghost btn-sm x" data-close>${icon("x", 16)}</button></div>
    <div class="modal-body">
      <div class="field"><label>Pull request URL</label>
        <input class="input mono" id="pr-input" placeholder="https://github.com/owner/repo/pull/123" autocomplete="off"/>
        <div class="hint">Public repositories only. The diff is reviewed read-only — nothing is posted back.</div></div>
      <div id="composer-err"></div>
      <div id="composer-tl" style="display:none"></div>
    </div>
    <div class="modal-foot"><button class="btn" data-close>Cancel</button><button class="btn btn-primary" id="run-btn">${icon("check", 15)} Run review</button></div>
  </div>`;
  document.body.appendChild(ov);
  const input = ov.querySelector("#pr-input");
  input.focus();
  ov.addEventListener("mousedown", (e) => { if (e.target === ov) closeComposer(); });
  ov.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", closeComposer));
  ov.querySelector("#run-btn").addEventListener("click", () => runReview(input.value.trim()));
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") runReview(input.value.trim()); });
}
function closeComposer() {
  if (composerTimer) { clearInterval(composerTimer); composerTimer = null; }
  const ov = document.getElementById("composer");
  if (ov) ov.remove();
}
function setComposerError(msg) {
  const e = document.getElementById("composer-err");
  if (e) e.innerHTML = msg ? `<div class="errbox">${esc(msg)}</div>` : "";
}

async function runReview(prUrl) {
  if (!prUrl) return setComposerError("Enter a pull request URL.");
  if (!parsePr(prUrl)) return setComposerError("Expected https://github.com/owner/repo/pull/123");
  setComposerError("");
  const tl = document.getElementById("composer-tl");
  const runBtn = document.getElementById("run-btn");
  const input = document.getElementById("pr-input");
  if (input) input.disabled = true;
  runBtn.disabled = true;
  runBtn.innerHTML = `<div class="spinner" style="border-top-color:#fff;border-color:rgba(255,255,255,.4);border-top-color:#fff"></div> Reviewing…`;

  let step = 0;
  tl.style.display = "";
  tl.innerHTML = timelineHtml(step);
  composerTimer = setInterval(() => {
    if (step < PIPELINE.length - 1) { step++; tl.innerHTML = timelineHtml(step); }
  }, 850);

  try {
    const res = await fetch("/api/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pr_url: prUrl }),
    });
    const data = await res.json().catch(() => ({}));
    clearInterval(composerTimer); composerTimer = null;
    if (!res.ok) {
      tl.innerHTML = timelineHtml(step);
      setComposerError(data.detail || `Request failed (${res.status})`);
      if (input) input.disabled = false;
      runBtn.disabled = false;
      runBtn.innerHTML = `${icon("check", 15)} Run review`;
      return;
    }
    tl.innerHTML = timelineHtml(PIPELINE.length, true);
    const rec = addReview(data, prUrl);
    setTimeout(() => { closeComposer(); location.hash = `#/reviews/${rec.id}`; render(); }, 400);
  } catch (e) {
    clearInterval(composerTimer); composerTimer = null;
    setComposerError("Network error: " + e.message);
    if (input) input.disabled = false;
    runBtn.disabled = false;
    runBtn.innerHTML = `${icon("check", 15)} Run review`;
  }
}

// ----------------------------- shell + router ------------------------
function parseRoute() {
  const h = (location.hash || "#/dashboard").replace(/^#\//, "");
  const [name, param] = h.split("/");
  return { name: name || "dashboard", param };
}

function wireRowNav(root) {
  root.querySelectorAll("[data-go]").forEach((el) =>
    el.addEventListener("click", () => { location.hash = el.dataset.go; }));
}

function pageFor(route) {
  switch (route.name) {
    case "dashboard": return pageDashboard();
    case "repositories": return pageRepositories();
    case "reviews": return route.param ? pageReviewDetail(route.param) : pageReviews();
    case "findings": return pageFindings();
    case "agents": return pageAgents();
    case "settings": return pageSettings();
    default: return pageDashboard();
  }
}

function render() {
  const route = parseRoute();
  const page = pageFor(route);
  const findingsOpen = allFindings().filter((f) => statusOf(f.repo, f) === "open").length;
  const counts = { reviews: loadReviews().length, findings: findingsOpen, repositories: reposFromReviews().length };
  const repos = reposFromReviews();

  const crumbHtml = (page.crumbs || [{ cur: "Dashboard" }]).map((c, i, arr) => {
    const sep = i < arr.length - 1 ? `<span class="sep">${icon("chevron", 13)}</span>` : "";
    if (c.cur) return `<span class="cur ${c.mono ? "mono" : ""}">${esc(c.cur)}</span>${sep}`;
    return `<a href="${c.link}">${esc(c.label)}</a>${sep}`;
  }).join("");

  const repoSel = `<select class="select" id="repo-sel" title="Filter by repository">
    <option value="">All repositories</option>
    ${repos.map((r) => `<option value="${esc(r.repo)}" ${App.repoFilter === r.repo ? "selected" : ""}>${esc(r.repo)}</option>`).join("")}
  </select>`;

  document.getElementById("app").innerHTML = `
    <div class="app">
      <aside class="sidebar">
        <div class="brand"><div class="mark">${icon("check", 16)}</div><div class="name">Agentic Review<small>code review platform</small></div></div>
        <nav class="nav">
          <div class="nav-label">Workspace</div>
          ${NAV.map((n) => `<a class="nav-item ${route.name === n.name ? "active" : ""}" href="#/${n.name}">${icon(n.icon)} <span>${n.label}</span>${counts[n.name] != null && counts[n.name] > 0 ? `<span class="count">${counts[n.name]}</span>` : ""}</a>`).join("")}
        </nav>
        <div class="sidebar-foot">
          <div class="statusline"><span class="dot ${App.health === "ok" ? "ok" : App.health ? "err" : ""}"></span> ${App.health === "ok" ? "All systems operational" : App.health ? "API unreachable" : "Checking status…"}</div>
          ${App.config ? `<div class="foot-meta">${esc(App.config.model)}</div>` : ""}
        </div>
      </aside>
      <div class="main">
        <header class="topbar">
          <div class="crumbs">${crumbHtml}</div>
          <div class="spacer"></div>
          <div class="search" id="topsearch">${icon("search", 14)}<input id="search-input" placeholder="Search findings…"/><span class="kbd">/</span></div>
          ${repos.length ? repoSel : ""}
          <button class="btn btn-primary" data-new>${icon("plus", 15)} New review</button>
        </header>
        <main class="content" id="view"></main>
      </div>
    </div>`;

  const view = document.getElementById("view");
  view.innerHTML = `<div class="page-head"><div><div class="title">${esc((page.crumbs && page.crumbs[page.crumbs.length - 1].cur) || NAV.find((n) => n.name === route.name)?.label || "")}</div>${page.subtitle ? `<div class="sub">${esc(page.subtitle)}</div>` : ""}</div>${page.actions ? `<div class="actions">${page.actions}</div>` : ""}</div>${page.body}`;

  // wire chrome
  document.querySelectorAll("[data-new]").forEach((b) => b.addEventListener("click", openComposer));
  const sel = document.getElementById("repo-sel");
  if (sel) sel.addEventListener("change", () => { App.repoFilter = sel.value; render(); });
  const si = document.getElementById("search-input");
  if (si) {
    si.value = route.name === "findings" ? App.findingsFilter.q : "";
    si.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { App.findingsFilter.q = si.value.trim(); location.hash = "#/findings"; render(); }
    });
  }
  if (page.wire) page.wire(view);
}

function bindGlobalKeys() {
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeComposer();
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") return;
    if (e.key === "/") { e.preventDefault(); document.getElementById("search-input")?.focus(); }
    if (e.key === "n") { e.preventDefault(); openComposer(); }
  });
}

async function init() {
  bindGlobalKeys();
  window.addEventListener("hashchange", render);
  render();
  try { App.health = (await (await fetch("/api/health")).json()).status; } catch { App.health = "down"; }
  try { App.config = await (await fetch("/api/config")).json(); } catch { /* noop */ }
  try { App.metrics = await (await fetch("/api/metrics")).json(); } catch { /* noop */ }
  render();
}

init();
