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

const photoMemo = new Map();
const photoQueue = [];
let photoActive = 0;
const PHOTO_CONCURRENCY = 4;

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
    fillDatalist("#clubs", f.clubs.map((x) => x.club));
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
  observePhotos();
  renderPager(data);
}

function card(p) {
  const el = document.createElement("article");
  el.className = "card";
  el.dataset.id = p.id;
  const chips = String(p.pos || "").split(",").map((s) => s.trim()).filter(Boolean)
    .slice(0, 5).map((s) => `<span class="chip">${esc(s)}</span>`).join("");
  el.innerHTML = `
    <div class="photo" data-id="${p.id}">
      <div class="fallback">${esc(initials(p.name))}</div>
    </div>
    <div class="card-body">
      <div class="card-top"><h3>${esc(p.name)}</h3><span class="age">${p.age ?? "—"}</span></div>
      <div class="meta">${esc(p.nat || "—")}</div>
      <div class="club">${esc(p.club || "Free agent")}${p.div ? ` <span class="div">· ${esc(p.div)}</span>` : ""}</div>
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

/* ---------------- photos (live Wikipedia, no server cache) ---------------- */
const io = new IntersectionObserver((entries) => {
  for (const e of entries) {
    if (!e.isIntersecting) continue;
    io.unobserve(e.target);
    enqueuePhoto(e.target);
  }
}, { rootMargin: "300px" });

function observePhotos() {
  document.querySelectorAll(".photo[data-id]").forEach((el) => {
    if (!el.dataset.done) io.observe(el);
  });
}

function enqueuePhoto(el) {
  if (el.dataset.done) return;
  el.dataset.done = "1";
  photoQueue.push(el);
  pumpPhotos();
}

function pumpPhotos() {
  while (photoActive < PHOTO_CONCURRENCY && photoQueue.length) {
    const el = photoQueue.shift();
    const id = String(el.dataset.id || "");
    if (!id) continue;
    if (photoMemo.has(id)) { applyPhoto(el, photoMemo.get(id)); continue; }
    photoActive++;
    fetch(`/api/photo/${encodeURIComponent(id)}`)
      .then((r) => r.json())
      .then((p) => { photoMemo.set(id, p); applyPhoto(el, p); })
      .catch(() => {})
      .finally(() => { photoActive--; pumpPhotos(); });
  }
}

function applyPhoto(el, p) {
  if (!p || !p.found || !p.thumb) return;
  const img = new Image();
  img.referrerPolicy = "no-referrer";
  img.alt = "";
  img.onload = () => { el.innerHTML = ""; el.appendChild(img); };
  img.onerror = () => {};
  img.src = p.thumb;
}

/* ---------------- profile drawer ---------------- */
async function openPlayer(id) {
  const drawer = $("#drawer");
  const profile = $("#profile");
  drawer.classList.remove("hidden");
  drawer.setAttribute("aria-hidden", "false");
  document.body.classList.add("locked");
  profile.innerHTML = '<div class="loading">Loading profile…</div>';
  profile.scrollTop = 0;
  try {
    const [p, h] = await Promise.all([
      api(`/api/player/${encodeURIComponent(id)}`),
      api(`/api/history/${encodeURIComponent(id)}`),
    ]);
    const memo = photoMemo.get(String(id)) || null;
    profile.innerHTML = renderProfile(p, h, memo);
    if (!memo) {
      api(`/api/photo/${encodeURIComponent(id)}`).then((ph) => {
        photoMemo.set(String(id), ph);
        updateProfilePhoto(ph);
      }).catch(() => {});
    }
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

function renderProfile(p, h, photo) {
  const found = photo && photo.found && photo.thumb;
  const photoHtml = found
    ? `<img src="${esc(photo.thumb)}" alt="" referrerpolicy="no-referrer">`
    : esc(initials(p.name));
  const credit = found
    ? `<div class="credit">Photo: <a href="${esc(photo.page)}" target="_blank" rel="noopener">${esc(photo.title)} · Wikipedia</a></div>`
    : `<div class="credit">No Wikipedia photo found.</div>`;
  const chips = String(p.pos || "").split(",").map((s) => s.trim()).filter(Boolean)
    .map((s) => `<span class="chip">${esc(s)}</span>`).join("");
  return `
    <div class="profile-head">
      <div class="profile-photo" id="profile-photo">${photoHtml}</div>
      <div class="profile-title">
        <h2>${esc(p.name)}</h2>
        <div class="sub">${esc(p.nat || "—")} · ${p.age ?? "—"} years</div>
        <div class="club-line">${esc(p.club || "Free agent")}${p.div ? ` · ${esc(p.div)}` : ""}</div>
        <div class="big-badges">
          <span class="badge ca">CA ${p.ca ?? "—"}</span>
          <span class="badge pa">PA ${p.pa ?? "—"}</span>
          ${chips}
        </div>
        <div class="credit" id="profile-credit">${credit}</div>
      </div>
    </div>

    <div class="section"><h3>Profile</h3>
      <div class="bio-grid">
        <div>${bio("Date of birth", p.dob || "—")}${bio("Age", p.age ?? "—")}${bio("Nationality", p.nat || "—")}${bio("Gender", p.gender || "—")}${bio("Club", p.club || "Free agent")}${bio("Division", p.div || "—")}${bio("Position", p.pos || "—")}${bio("Natural positions", p.posNat || "—")}</div>
        <div>${bio("Preferred foot", p.foot || "—")}${bio("Height", p.height ? p.height + " cm" : "—")}${bio("Market value", fmtMoney(p.value))}${bio("Asking price", fmtMoney(p.askingPrice))}${bio("Wage", fmtWage(p.wage))}${bio("Contract expires", p.expires || "—")}${bio("World reputation", fmtInt(p.worldRep))}${bio("Club reputation", fmtInt(p.clubRep))}</div>
      </div>
    </div>

    <div class="section history" id="history-section">${renderHistory(h)}</div>

    <div class="section"><h3>Personality</h3>${bars(PERSONALITY, p)}</div>

    <div class="section"><h3>Attributes</h3>
      <div class="attr-groups">
        ${Object.entries(ATTR_GROUPS).map(([g, keys]) => `<div class="attr-group"><h4>${g}</h4>${bars(keys, p)}</div>`).join("")}
      </div>
    </div>`;
}

function updateProfilePhoto(photo) {
  const el = $("#profile-photo");
  if (!el) return;
  if (photo && photo.found && photo.thumb) {
    const img = new Image();
    img.referrerPolicy = "no-referrer";
    img.onload = () => { el.innerHTML = ""; el.appendChild(img); };
    img.src = photo.thumb;
  }
  const credit = $("#profile-credit");
  if (credit && photo && photo.found) {
    credit.innerHTML = `Photo: <a href="${esc(photo.page)}" target="_blank" rel="noopener">${esc(photo.title)} · Wikipedia</a>`;
  }
}

function renderHistory(h) {
  const recs = (h && h.records) || [];
  if (!recs.length) {
    return `<h3>Career history</h3><div class="empty-history">No career history in the shipped database. Regens and newly created players usually have none.</div>`;
  }
  const t = h.totals || {};
  const rows = recs.map((r) => {
    const youth = r.record_type !== "Senior" ? `<span class="tag youth">${esc(r.record_type)}</span>` : "";
    const loan = r.parent_club ? `<span class="loan"> · on loan from ${esc(r.parent_club)}</span>` : "";
    return `<tr class="${r.record_type !== "Senior" ? "youth-row" : ""}">
      <td class="season">${esc(seasonLabel(r))}</td>
      <td>${esc(r.club || "—")}${loan}${youth}</td>
      <td>${esc(r.competition || "—")}</td>
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
