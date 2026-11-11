/* Save banner for save-backed games (server.py --game fm24): which save the data came
   from, the Cmd+S reminder while the game runs, "New save detected -> Load it", and
   "?" markers on values the game does not show as numbers. Loaded before app.js only
   for save-backed games; the server injects window.FM_GAME just before it. */
(() => {
  let unverified = new Set();
  let loadedAt = null;          // saved_at of the data on screen; a change means a reload finished
  const POLL_MS = 5000;

  const esc = (v) => String(v == null ? "" : v).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
  const time = (iso) => (iso ? new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "");
  function ago(iso) {
    const min = Math.max(0, Math.round((Date.now() - new Date(iso)) / 60000));
    if (min < 1) return "just now";
    if (min < 60) return `${min} min ago`;
    const h = Math.round(min / 60);
    return h < 48 ? `${h} h ago` : `${Math.round(h / 24)} days ago`;
  }
  const gameDate = (d) => (d ? new Date(d + "T00:00:00").toLocaleDateString("en-GB",
    { day: "numeric", month: "short", year: "numeric" }) : "");

  async function meta() {
    const r = await fetch("/api/meta");
    if (!r.ok) throw new Error(r.statusText);
    return r.json();
  }

  function applyLabel(m) {
    document.title = `${m.label} Profiles Explorer`;
    const logo = document.querySelector(".logo");
    if (logo) logo.textContent = m.label;
    const foot = document.querySelector(".foot");
    if (foot) {
      const n = Number(m.players || 0).toLocaleString("en-GB");
      const save = m.save && m.save.save ? ` · from save "${m.save.save}"` : "";
      foot.textContent = `${m.label} career · ${n} players${save}`;
    }
  }

  // Mark values FM does not show numerically (CA/PA, hidden attributes) as unverified.
  function markUnverified(root) {
    if (!unverified.size) return;
    root.querySelectorAll(".badge.ca, .badge.pa").forEach((b) => {
      const key = b.classList.contains("ca") ? "ca" : "pa";
      if (unverified.has(key) && !b.dataset.unverified) {
        b.dataset.unverified = "1";
        b.title = "Unverified: decoded from the save, not shown as a number in FM";
        b.insertAdjacentHTML("beforeend", '<sup class="unverified">?</sup>');
      }
    });
    // Attribute rows and facts carry their key in data-k; bar rows (personality) in their
    // title; search cards show the market value in .value.
    root.querySelectorAll(".attr-row .an[data-k], .fact[data-k] > span, .bar-row .lbl[title], .card .value").forEach((l) => {
      const key = l.dataset.k || (l.parentElement && l.parentElement.dataset.k) || l.getAttribute("title")
        || (l.classList.contains("value") ? "value" : "");
      if (unverified.has(key) && !l.dataset.unverified) {
        l.dataset.unverified = "1";
        l.insertAdjacentHTML("beforeend", ' <sup class="unverified" title="Unverified">?</sup>');
      }
    });
  }

  function banner() {
    let el = document.querySelector("#save-banner");
    if (!el) {
      el = document.createElement("div");
      el.id = "save-banner";
      el.setAttribute("role", "status");
      el.style.cssText = "margin:8px 16px;padding:8px 12px;border-radius:8px;background:rgba(139,92,246,.12);" +
        "border:1px solid rgba(139,92,246,.35);font-size:13px;display:flex;gap:12px;flex-wrap:wrap;align-items:center";
      document.querySelector("header.top").insertAdjacentElement("afterend", el);
    }
    return el;
  }

  function renderBanner(m) {
    const s = m.save || {};
    const parts = [];
    if (s.save) {
      const inGame = s.in_game_date ? ` · in-game ${esc(gameDate(s.in_game_date))}` : "";
      parts.push(`<span>Data from "${esc(s.save)}", saved ${esc(time(s.saved_at))} (${esc(ago(s.saved_at))})${inGame}</span>`);
    }
    const r = m.reload || {};
    if (r.state === "running") {
      parts.push(`<b>Loading "${esc(r.save)}"…</b>`);
    } else if (m.newer_save) {
      parts.push(`<b>New save detected: "${esc(m.newer_save.save)}" (${esc(time(m.newer_save.saved_at))})</b>` +
        '<button id="load-save" class="linkbtn" type="button">Load it</button>');
    } else if (m.fm_running) {
      parts.push("<span>FM is running: press ⌘S in FM for fresh data.</span>");
    }
    if (r.state === "error") parts.push(`<span style="color:#f87171">Reload failed: ${esc(r.error)}. Showing the previous data.</span>`);
    const el = banner();
    el.innerHTML = parts.join("");
    const btn = el.querySelector("#load-save");
    if (btn) btn.onclick = async () => {
      btn.disabled = true;
      try { renderBanner({ ...m, reload: await (await fetch("/api/reload", { method: "POST" })).json() }); } catch (e) { /* next poll shows the state */ }
    };
  }

  async function poll() {
    try {
      const m = await meta();
      const savedAt = m.save && m.save.saved_at;
      if (loadedAt && savedAt && savedAt !== loadedAt && (m.reload || {}).state !== "running") {
        location.reload();      // a reload finished: show the new data
        return;
      }
      loadedAt = loadedAt || savedAt;
      unverified = new Set(m.unverified || []);
      renderBanner(m);
    } catch (e) {
      /* server restarting: try again on the next tick */
    }
    setTimeout(poll, POLL_MS);
  }

  document.addEventListener("DOMContentLoaded", async () => {
    const style = document.createElement("style");
    style.textContent = "sup.unverified{color:#f5b942;font-weight:700;margin-left:2px;cursor:help}";
    document.head.appendChild(style);
    try {
      const m = await meta();
      unverified = new Set(m.unverified || []);
      loadedAt = m.save && m.save.saved_at;
      applyLabel(m);
      renderBanner(m);
      markUnverified(document);      // content rendered before the list of unverified fields arrived
    } catch (e) {
      /* the page still works without the label */
    }
    setTimeout(poll, POLL_MS);
    const profile = document.querySelector("#profile");
    if (profile) new MutationObserver(() => markUnverified(profile)).observe(profile, { childList: true, subtree: true });
    const grid = document.querySelector("#grid");
    if (grid) new MutationObserver(() => markUnverified(grid)).observe(grid, { childList: true });
  });
})();
