/* FM27 Profiles Explorer — frontend */
const $ = (s) => document.querySelector(s);
const PER = 36;

const state = {
  q: "", gender: "", nat: "", club: "", div: "", pos: "",
  min_age: "", max_age: "", min_ca: "", max_ca: "", min_pa: "",
  sort: "ca", order: "desc", page: 1, per: PER,
};

const ATTR_GROUPS = {
  Technical: ["Crossing", "Dribbling", "Finishing", "Heading", "LongShots", "Marking",
    "Passing", "PenaltyTaking", "Tackling", "FirstTouch", "Technique", "Flair",
    "Corners", "FreeKicks", "LongThrows"],
  Mental: ["Anticipation", "Decisions", "Composure", "Concentration", "Determination",
    "Teamwork", "WorkRate", "Leadership", "Positioning", "OffTheBall", "Vision",
    "Aggression", "Bravery", "Consistency", "ImportantMatches", "Dirtiness",
    "InjuryProneness", "Versatility"],
  Physical: ["Acceleration", "Pace", "Strength", "Stamina", "Agility", "Balance",
    "JumpingReach", "NaturalFitness"],
  Goalkeeping: ["Handling", "AerialReach", "CommandOfArea", "Communication", "Kicking",
    "Throwing", "OneOnOnes", "Reflexes", "RushingOut", "Punching", "Eccentricity"],
};
const PERSONALITY = ["adaptability", "ambition", "loyalty", "pressure", "professionalism",
  "sportsmanship", "temperament", "controversy"];

const ATTR_LABELS = {
  OffTheBall: "Off The Ball", JumpingReach: "Jumping Reach", LongShots: "Long Shots",
  FirstTouch: "First Touch", WorkRate: "Work Rate", NaturalFitness: "Natural Fitness",
  ImportantMatches: "Important Matches", InjuryProneness: "Injury Proneness",
  OneOnOnes: "One On Ones", CommandOfArea: "Command Of Area", AerialReach: "Aerial Reach",
  LongThrows: "Long Throws", FreeKicks: "Free Kicks", PenaltyTaking: "Penalty Taking",
};
const GK_KEYS = new Set(ATTR_GROUPS.Goalkeeping);
const ALL_ATTRS = Object.values(ATTR_GROUPS).flat();
const RADAR_AXES = [
  ["Technique", ["Crossing", "Dribbling", "Finishing", "FirstTouch", "Technique", "Passing", "LongShots", "FreeKicks", "PenaltyTaking", "Corners"]],
  ["Mental", ["Anticipation", "Decisions", "Composure", "Concentration", "Determination", "Teamwork", "WorkRate", "Leadership", "Positioning", "OffTheBall", "Vision", "Consistency", "ImportantMatches"]],
  ["Physical", ["Acceleration", "Pace", "Strength", "Stamina", "Agility", "Balance", "JumpingReach", "NaturalFitness"]],
  ["Defending", ["Marking", "Tackling", "Positioning", "Concentration", "Bravery", "Aggression", "WorkRate", "Strength"]],
  ["Attacking", ["Finishing", "LongShots", "OffTheBall", "Composure", "Dribbling", "FirstTouch", "Technique", "Flair", "Acceleration", "Pace"]],
  ["Speed", ["Acceleration", "Pace"]],
  ["Aerial", ["Heading", "JumpingReach", "Strength", "Bravery"]],
  ["Goalkeeping", ATTR_GROUPS.Goalkeeping],
];
const POS_COORDS = {
  GK: [100, 232], DL: [28, 205], DC: [100, 205], DR: [172, 205],
  WBL: [14, 165], WBR: [186, 165], DM: [100, 168],
  ML: [28, 128], MC: [100, 128], MR: [172, 128],
  AML: [28, 88], AMC: [100, 88], AMR: [172, 88], ST: [100, 38],
};

/* ---------------- helpers ---------------- */
function esc(v) {
  return String(v == null ? "" : v).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
function fmtInt(v) {
  if (v == null || v === "" || Number.isNaN(Number(v))) return "—";
  return Number(v).toLocaleString("en-GB");
}
function fmtMoney(v) {
  const n = Number(v);
  if (!n) return "—";
  if (n >= 1e9) return `£${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `£${(n / 1e6).toFixed(2)}M`;
  if (n >= 1e3) return `£${(n / 1e3).toFixed(0)}K`;
  return `£${n}`;
}
function fmtWage(v) {
  const n = Number(v);
  if (!n) return "—";
  if (n >= 1e3) return `£${(n / 1e3).toFixed(1)}K/w`;
  return `£${n}/w`;
}
function initials(name) {
  const parts = String(name || "?").trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
function attrClass(v) {
  if (v >= 16) return "v-elite";
  if (v >= 12) return "v-good";
  if (v >= 8) return "v-mid";
  return "v-low";
}
function seasonLabel(r) { return r.season || (r.season_start === r.season_end ? String(r.season_start) : `${r.season_start}-${String(r.season_end).slice(-2)}`); }
function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }

async function api(url) {
  const r = await fetch(url);
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).error || msg; } catch (e) { /* ignore */ }
    throw new Error(msg);
  }
  return r.json();
}

/* ---------------- filters ---------------- */
function fillDatalist(sel, values) {
  const dl = $(sel);
  dl.innerHTML = values.map((v) => `<option value="${esc(v)}">`).join("");
}

async function loadFilters() {
  try {
    const f = await api("/api/filters");
    const s = f.stats;
    $("#stats-line").textContent =
      `${fmtInt(s.players)} players · ${fmtInt(s.clubs)} clubs · ${fmtInt(s.divisions)} divisions · ${fmtInt(s.nations)} nations`;
    fillDatalist("#nations", f.nations);
    fillDatalist("#clubs", f.clubs.map((x) => x.display));
    fillDatalist("#divisions", f.divisions.map((x) => x.div));
    const pos = $("#pos");
    for (const p of f.positions) {
      const o = document.createElement("option");
      o.value = p.pos;
      o.textContent = `${p.pos} (${fmtInt(p.count)})`;
      pos.appendChild(o);
    }
  } catch (e) {
    $("#stats-line").textContent = "Could not load filters: " + e.message;
  }
}

/* ---------------- search ---------------- */
function params() {
  const p = new URLSearchParams();
  for (const k of ["q", "gender", "nat", "club", "div", "pos", "min_age", "max_age",
    "min_ca", "max_ca", "min_pa", "sort", "order"]) {
    if (state[k] !== "" && state[k] != null) p.set(k, state[k]);
  }
  p.set("page", state.page);
  p.set("per", state.per);
  return p;
}

let searchSeq = 0;
async function search(resetPage = false) {
  if (resetPage) state.page = 1;
  const seq = ++searchSeq;
  const grid = $("#grid");
  grid.classList.add("loading");
  try {
    const data = await api("/api/players?" + params());
    if (seq !== searchSeq) return;
    renderResults(data);
  } catch (e) {
    if (seq !== searchSeq) return;
    grid.innerHTML = `<div class="empty">Search failed: ${esc(e.message)}</div>`;
    $("#summary").textContent = "Error";
  } finally {
    grid.classList.remove("loading");
  }
}

function renderResults(data) {
  const grid = $("#grid");
  const empty = $("#empty");
  $("#summary").innerHTML =
    `<b>${fmtInt(data.total)}</b> players · page ${data.page} of ${data.pages}`;
  grid.innerHTML = "";
  empty.classList.toggle("hidden", data.players.length !== 0);
  if (!data.players.length) { renderPager(data); return; }
  const frag = document.createDocumentFragment();
  for (const p of data.players) frag.appendChild(card(p));
  grid.appendChild(frag);
  renderPager(data);
}

function card(p) {
  const el = document.createElement("article");
  el.className = "card";
  el.dataset.id = p.id;
  const chips = String(p.pos || "").split(",").map((s) => s.trim()).filter(Boolean)
    .slice(0, 5).map((s) => `<span class="chip">${esc(s)}</span>`).join("");
  const flag = p.natId ? `<img class="flag" src="/api/nation-logo/${p.natId}" alt="" loading="lazy" onerror="this.remove()">` : "";
  el.innerHTML = `
    <div class="photo">
      <div class="fallback">${esc(initials(p.name))}</div>
      <img class="face" src="/api/face/${p.id}" alt="" loading="lazy" decoding="async" onerror="this.remove()">
    </div>
    <div class="card-body">
      <div class="card-top"><h3>${esc(p.name)}</h3><span class="age">${p.age ?? "—"}</span></div>
      <div class="meta">${flag}${esc(p.nat || "—")}</div>
      <div class="club">
        <img class="club-logo" src="/api/player-club-logo/${p.id}" alt="" loading="lazy" onerror="this.remove()">
        <span class="club-name">${esc(p.club_display || p.club || "Free agent")}</span>
        ${p.div ? `<span class="div">· ${esc(p.div)}</span>` : ""}
      </div>
      <div class="chips">${chips}</div>
      <div class="stats">
        <span class="badge ca">CA ${p.ca ?? "—"}</span>
        <span class="badge pa">PA ${p.pa ?? "—"}</span>
        <span class="value">${fmtMoney(p.value)}</span>
      </div>
    </div>`;
  el.addEventListener("click", () => openPlayer(p.id));
  return el;
}

function renderPager(data) {
  const html = `
    <button ${data.page <= 1 ? "disabled" : ""} data-page="${data.page - 1}">‹ Prev</button>
    <span>${fmtInt(data.total)} · page ${data.page}/${data.pages}</span>
    <button ${data.page >= data.pages ? "disabled" : ""} data-page="${data.page + 1}">Next ›</button>`;
  for (const sel of ["#pager-top", "#pager-bottom"]) {
    const el = $(sel);
    el.innerHTML = html;
    el.querySelectorAll("button").forEach((b) => {
      b.onclick = () => {
        state.page = Number(b.dataset.page);
        search();
        window.scrollTo({ top: 0, behavior: "smooth" });
      };
    });
  }
}

/* ---------------- profile drawer ---------------- */
async function openPlayer(id) {
  const drawer = $("#drawer");
  const profile = $("#profile");
  drawer.classList.remove("hidden");
  drawer.setAttribute("aria-hidden", "false");
  document.body.classList.add("locked");
  profile.innerHTML = '<div class="loading">Loading profile…</div>';
  drawer.querySelector(".panel").scrollTop = 0;
  try {
    const [p, h] = await Promise.all([
      api(`/api/player/${encodeURIComponent(id)}`),
      api(`/api/history/${encodeURIComponent(id)}`),
    ]);
    profile.innerHTML = renderProfile(p, h);
  } catch (e) {
    profile.innerHTML = `<div class="loading">Could not load player: ${esc(e.message)}</div>`;
  }
}

function closeDrawer() {
  const drawer = $("#drawer");
  drawer.classList.add("hidden");
  drawer.setAttribute("aria-hidden", "true");
  document.body.classList.remove("locked");
}

function bio(k, v) {
  return `<div class="bio-row"><span class="k">${esc(k)}</span><span class="v">${esc(v ?? "—")}</span></div>`;
}

function bars(keys, obj) {
  return `<div class="bars">` + keys.map((k) => {
    const raw = obj ? obj[k] : null;
    const v = Number(raw);
    const has = raw !== null && raw !== "" && Number.isFinite(v);
    return `<div class="bar-row">
      <span class="lbl" title="${esc(k)}">${esc(k)}</span>
      <span class="abar"><span class="${attrClass(has ? v : 0)}" style="width:${has ? Math.max(0, Math.min(100, v * 5)) : 0}%"></span></span>
      <span class="num">${has ? v : "—"}</span>
    </div>`;
  }).join("") + `</div>`;
}

function label(k) { return ATTR_LABELS[k] || k; }
function avg(obj, keys) {
  const v = keys.map((k) => Number(obj[k])).filter((x) => Number.isFinite(x));
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : 0;
}
function positionsOf(p) {
  const raw = (p.posNat || p.posArr || p.pos || "").replace(/,/g, ";");
  return [...new Set(raw.split(";").map((s) => s.trim().toUpperCase()).filter(Boolean))];
}
function clubColors(name) {
  let h = 0;
  for (const ch of String(name || "")) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  const hue = h % 360;
  return { c1: `hsl(${hue} 52% 30%)`, c2: `hsl(${(hue + 50) % 360} 55% 12%)` };
}
function fact(k, v) { return `<div class="fact"><span>${esc(k)}</span><b>${esc(v ?? "—")}</b></div>`; }
function attrRow(k, p) {
  const raw = p[k]; const v = Number(raw);
  const has = raw !== null && raw !== "" && Number.isFinite(v);
  return `<div class="attr-row"><span class="an" title="${esc(label(k))}">${esc(label(k))}</span><span class="av">${has ? v : "—"}</span><span class="ab"><i class="${attrClass(has ? v : 0)}" style="width:${has ? Math.min(100, v * 5) : 0}%"></i></span></div>`;
}
function attrColumn(title, keys, p) {
  return `<div class="attr-col"><h4>${esc(title)}</h4>${keys.map((k) => attrRow(k, p)).join("")}</div>`;
}
function radarSvg(p) {
  const cx = 160, cy = 160, R = 104, n = RADAR_AXES.length;
  const pt = (i, r) => { const a = -Math.PI / 2 + i * 2 * Math.PI / n; return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; };
  const vals = RADAR_AXES.map(([, keys]) => avg(p, keys));
  let grid = "";
  for (const f of [0.25, 0.5, 0.75, 1]) {
    const pts = RADAR_AXES.map((_, i) => pt(i, R * f).map((x) => x.toFixed(1)).join(",")).join(" ");
    grid += `<polygon points="${pts}" fill="none" stroke="rgba(139,92,246,.16)" stroke-width="1"/>`;
  }
  const data = RADAR_AXES.map((_, i) => pt(i, R * Math.max(0, Math.min(1, vals[i] / 20))).map((x) => x.toFixed(1)).join(",")).join(" ");
  const labels = RADAR_AXES.map(([name], i) => {
    const [x, y] = pt(i, R + 20);
    return `<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" text-anchor="middle" dominant-baseline="middle" font-size="9" fill="#8e99ba">${esc(name)}</text>`;
  }).join("");
  const dots = RADAR_AXES.map((_, i) => { const [x, y] = pt(i, R); return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="2.2" fill="#34d399"/>`; }).join("");
  return `<svg viewBox="0 0 320 320" class="radarsvg">${grid}<polygon points="${data}" fill="rgba(52,211,153,.16)" stroke="#34d399" stroke-width="2"/>${dots}${labels}</svg>`;
}
function pitchSvg(active) {
  const on = new Set(active);
  const dots = Object.entries(POS_COORDS).map(([k, [x, y]]) => {
    const a = on.has(k);
    return `<g class="${a ? "pos-on" : "pos-off"}"><circle cx="${x}" cy="${y}" r="${a ? 7 : 5}"/><text x="${x}" y="${y + 2.6}" text-anchor="middle">${k}</text></g>`;
  }).join("");
  return `<svg viewBox="0 0 200 260" class="pitchsvg">
    <rect x="6" y="6" width="188" height="248" rx="2" class="pitch-bg"/>
    <rect x="6" y="6" width="188" height="248" class="pitch-line"/>
    <line x1="6" y1="130" x2="194" y2="130" class="pitch-line"/>
    <circle cx="100" cy="130" r="24" class="pitch-line"/>
    <rect x="60" y="6" width="80" height="30" class="pitch-line"/>
    <rect x="60" y="224" width="80" height="30" class="pitch-line"/>
    <rect x="76" y="6" width="48" height="12" class="pitch-line"/>
    <rect x="76" y="242" width="48" height="12" class="pitch-line"/>
    ${dots}
  </svg>`;
}
function renderProfile(p, h) {
  const pos = positionsOf(p);
  const colors = clubColors(p.club_display || p.club);
  const flag = p.natId ? `<img class="flag" src="/api/nation-logo/${p.natId}" alt="" onerror="this.remove()">` : "";
  const face = `<div class="pfallback">${esc(initials(p.name))}</div><img class="pfaceimg" src="/api/face/${p.id}" alt="" decoding="async" onerror="this.remove()">`;
  const clubLogo = `<img class="club-logo" src="/api/player-club-logo/${p.id}" alt="" onerror="this.remove()">`;
  const chips = pos.map((x) => `<span class="chip">${esc(x)}</span>`).join("");
  return `
  <div class="ppage">
    <div class="phero">
      <div class="pcard" style="--c1:${colors.c1};--c2:${colors.c2}">
        <div class="ppos">${esc(pos[0] || "")}</div>
        <div class="pface">${face}</div>
        <div class="pname"><h1>${esc(p.name)}</h1><div class="psub">${flag} ${esc(p.nat || "—")} · ${p.age ?? "—"} years</div></div>
        <div class="pclub">${clubLogo}<span>${esc(p.club_display || p.club || "Free agent")}</span>${p.div ? `<em>${esc(p.div)}</em>` : ""}</div>
      </div>
      <div class="pinfo">
        <div class="pbadges"><span class="badge ca">CA ${p.ca ?? "—"}</span><span class="badge pa">PA ${p.pa ?? "—"}</span>${chips}</div>
        <div class="pfacts">
          ${fact("Nationality", p.nat || "—")}${fact("Club", p.club_display || p.club || "Free agent")}
          ${fact("Age", p.age ?? "—")}${fact("Date of birth", p.dob || "—")}
          ${fact("Height", p.height ? p.height + " cm" : "—")}${fact("Preferred foot", p.foot || "—")}
          ${fact("Contract expires", p.expires || "—")}${fact("Wage", fmtWage(p.wage))}
          ${fact("Market value", fmtMoney(p.value))}${fact("Asking price", fmtMoney(p.askingPrice))}
          ${fact("World reputation", fmtInt(p.worldRep))}${fact("Club reputation", fmtInt(p.clubRep))}
        </div>
        <div class="pblock ppersonality"><h3>Personality</h3>${bars(PERSONALITY, p)}</div>
      </div>
      <div class="pblock pradar"><h3>Attribute profile</h3>${radarSvg(p)}</div>
    </div>

    <div class="pgrid">
      <div class="pblock attrs"><h3>Attributes</h3><div class="attr-cols">
        ${attrColumn("Technical", ATTR_GROUPS.Technical, p)}
        ${attrColumn("Mental", ATTR_GROUPS.Mental, p)}
        ${attrColumn("Physical", ATTR_GROUPS.Physical, p)}
        ${pos.includes("GK") ? attrColumn("Goalkeeping", ATTR_GROUPS.Goalkeeping, p) : ""}
      </div></div>
      <div class="pblock pitch"><h3>Positions</h3>${pitchSvg(pos)}<div class="pos-lists"><div><b>Natural</b> ${esc(p.posNat || p.posArr || p.pos || "—")}</div><div><b>Accomplished</b> ${esc(p.posArr || p.pos || "—")}</div></div></div>
    </div>

    <div class="pblock phistory">${renderHistory(h)}</div>
  </div>`;
}

function renderHistory(h) {
  const recs = (h && h.records) || [];
  if (!recs.length) {
    return `<h3>Career history</h3><div class="empty-history">No career history in the shipped database. Regens and newly created players usually have none.</div>`;
  }
  const t = h.totals || {};
  const rows = recs.map((r) => {
    const youth = r.record_type !== "Senior" ? `<span class="tag youth">${esc(r.record_type)}</span>` : "";
    const loan = r.parent_club ? `<span class="loan"> · on loan from ${esc(r.parent_club_display || r.parent_club)}</span>` : "";
    const clubLogo = r.club_id ? `<img class="club-logo small" src="/api/club-logo/${r.club_id}" alt="" loading="lazy" onerror="this.remove()">` : "";
    const compLogo = r.competition_id ? `<img class="comp-logo" src="/api/comp-logo/${r.competition_id}" alt="" loading="lazy" onerror="this.remove()">` : "";
    return `<tr class="${r.record_type !== "Senior" ? "youth-row" : ""}">
      <td class="season">${esc(seasonLabel(r))}</td>
      <td>${clubLogo}${esc(r.club_display || r.club || "—")}${loan}${youth}</td>
      <td>${compLogo}${esc(r.competition || "—")}</td>
      <td class="num">${r.apps ?? "—"}</td>
      <td class="num">${r.goals ?? "—"}</td>
    </tr>`;
  }).join("");
  return `<div class="history-head">
      <h3>Career history</h3>
      <span class="totals">${fmtInt(t.apps)} apps · ${fmtInt(t.goals)} goals · ${fmtInt(t.clubs)} clubs · ${fmtInt(t.seasons)} seasons</span>
      <a class="csv" href="/api/history/${encodeURIComponent(h.person_id)}.csv">Download CSV</a>
    </div>
    <div class="table-wrap"><table class="history">
      <thead><tr><th>Season</th><th>Club</th><th>Competition</th><th class="num">Apps</th><th class="num">Goals</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
}

/* ---------------- events ---------------- */
function bindField(id, key) {
  const el = $(id);
  if (!el) return;
  const ev = el.tagName === "SELECT" || el.type === "number" ? "change" : "input";
  el.addEventListener(ev, ev === "input" ? debounce(() => {
    state[key] = el.value.trim();
    search(true);
  }, 260) : () => {
    state[key] = el.value.trim();
    search(true);
  });
}

function init() {
  loadFilters();
  search();
  bindField("#q", "q");
  bindField("#gender", "gender");
  bindField("#nat", "nat");
  bindField("#club", "club");
  bindField("#div", "div");
  bindField("#pos", "pos");
  bindField("#min_age", "min_age");
  bindField("#max_age", "max_age");
  bindField("#min_ca", "min_ca");
  bindField("#max_ca", "max_ca");
  bindField("#min_pa", "min_pa");
  bindField("#sort", "sort");
  bindField("#order", "order");
  $("#reset").addEventListener("click", () => {
    for (const k of Object.keys(state)) {
      if (k === "per" || k === "page") continue;
      state[k] = k === "sort" ? "ca" : (k === "order" ? "desc" : "");
    }
    for (const id of ["#q", "#gender", "#nat", "#club", "#div", "#pos", "#min_age", "#max_age",
      "#min_ca", "#max_ca", "#min_pa"]) {
      const el = $(id); if (el) el.value = "";
    }
    $("#sort").value = "ca";
    $("#order").value = "desc";
    search(true);
  });
  document.querySelectorAll("[data-close]").forEach((el) => el.addEventListener("click", closeDrawer));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeDrawer();
    if (e.key === "/" && document.activeElement !== $("#q")) {
      e.preventDefault();
      $("#q").focus();
    }
  });
}

document.addEventListener("DOMContentLoaded", init);
