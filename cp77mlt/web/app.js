/* Cyberpunk 2077 Mod List Tool — frontend. Talks to Python via window.pywebview.api. */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
/* Python bridge. pywebview fills window.pywebview.api in a background thread after each page
   load, so a call can land while a function isn't there yet. Wait for it, and fall back to the
   single rpc() dispatcher if it still isn't exposed. */
const bridgeReady = () => new Promise((res) => {
  if (window.pywebview?.api?.rpc) return res();
  const t = setTimeout(res, 4000);
  window.addEventListener("pywebviewready", () => { clearTimeout(t); res(); }, { once: true });
});
const call = async (name, ...args) => {
  try {
    let api = window.pywebview?.api;
    if (!api || typeof api[name] !== "function") {
      await bridgeReady();
      for (let i = 0; i < 20 && typeof window.pywebview?.api?.[name] !== "function" && typeof window.pywebview?.api?.rpc !== "function"; i++)
        await new Promise((r) => setTimeout(r, 100));
      api = window.pywebview?.api;
    }
    if (api && typeof api[name] === "function") return await api[name](...args);
    if (api && typeof api.rpc === "function") return await api.rpc(name, args);
    return { ok: false, error: "The app's connection to Python isn't ready. Try again in a moment." };
  } catch (e) { return { ok: false, error: String(e && e.message || e) }; }
};
const fmtSize = (b) => !b ? "" : b < 1e6 ? `${Math.max(1, Math.round(b / 1e3))} KB` : b < 1e9 ? `${(b / 1e6).toFixed(1)} MB` : `${(b / 1e9).toFixed(2)} GB`;
const fmtDate = (ts) => ts ? new Date(ts * 1000).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) : "";
const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
const LOC_PATH = { archive: "archive/pc/mod", redmod: "mods", cet: "bin/x64/plugins/cyber_engine_tweaks/mods", redscript: "r6/scripts",
  tweak: "r6/tweaks", red4ext: "red4ext/plugins", input: "r6/input", asi: "bin/x64/plugins" };
const norm = (n) => String(n || "").toLowerCase().replace(/[^a-z0-9]/g, "");
const groupTitle = (m) => "Grouped as one mod: " + m.components.map((c) => `${LOC[c.location] || c.location}: ${c.name}`).join(", ");
const LOC = { archive: "Archive", redmod: "REDmod", cet: "CET", redscript: "Redscript", tweak: "TweakXL", red4ext: "RED4ext", input: "Input", asi: "ASI" };
const SRC = { loose: "Manual", vortex: "Vortex", mo2: "MO2", github: "GitHub" };

const S = {
  boot: null, page: "overview", status: {}, mods: [], summary: {}, sel: new Set(),
  filter: { q: "", state: "enabled", source: "all", locs: new Set() }, sort: { key: "name", dir: 1 },
  logSel: null, errorsOnly: false, drawerKey: null, lastReport: null, tasks: {},
};

/* ------------------------------------------------------------------ toasts & tasks */
function toast(html, kind = "", ms = 5000) {
  const t = document.createElement("div");
  t.className = `toast ${kind}`;
  t.innerHTML = html;
  $("#toasts").append(t);
  if (ms) setTimeout(() => t.remove(), ms);
  return t;
}
function result(r, okMsg) {
  if (!r) return false;
  if (r.ok === false && r.error) { toast(esc(r.error), "bad", 8000); return false; }
  const issues = [...(r.errors || [])];
  if (issues.length) toast(`<b>Finished with problems</b><ul>${issues.slice(0, 6).map((e) => `<li>${esc(e)}</li>`).join("")}</ul>`, "bad", 12000);
  (r.notes || []).forEach((n) => toast(esc(n), "", 9000));
  if (r.note) toast(esc(r.note), "", 9000);
  if (okMsg && !issues.length && r.ok !== false) toast(esc(okMsg), "ok", 3500);
  return r.ok !== false;
}
const TASK_LABEL = { export: "Exporting preset", install: "Installing archive", backup: "Backing up mods", restore: "Restoring backup", identify: "Identifying mods on Nexus",
  updates: "Checking for updates", update: "Updating mod", "track-all": "Tracking mods on Nexus", "nexus-sso": "Logging in to Nexus" };
const taskDone = {};
const activeTasks = new Set(), finishedTasks = new Set();
let taskPoller = null;
const silentTasks = new Set();  // progress shown in-page instead of a toast
function startTask(r, onDone, silent = false) {
  if (silent && r && r.task) silentTasks.add(r.task);
  if (!r || r.ok === false) { result(r); return; }
  if (!r.task) return;
  taskDone[r.task] = onDone;
  activeTasks.add(r.task);
  window.cp.onTask({ id: r.task, name: r.name || "", progress: 0, message: "", done: false });
  if (!taskPoller) taskPoller = setInterval(pollTasks, 400);
}
async function pollTasks() {
  for (const id of [...activeTasks]) {
    const t = await call("get_task", id);
    if (t && t.ok === false) { activeTasks.delete(id); continue; }
    if (t) window.cp.onTask(t);
  }
  if (!activeTasks.size) { clearInterval(taskPoller); taskPoller = null; }
}
const taskListeners = new Set();
window.cp = {
  onTask(t) {
    if (finishedTasks.has(t.id)) return;  // a late push after the poller already finished it
    taskListeners.forEach((fn) => fn(t));
    if (silentTasks.has(t.id)) {
      if (t.done) {
        finishedTasks.add(t.id); activeTasks.delete(t.id); silentTasks.delete(t.id);
        if (t.error) toast(esc(t.error), "bad", 9000);
        const cb = taskDone[t.id]; delete taskDone[t.id];
        if (cb && !t.error) cb(t.result || {});
      }
      return;
    }
    let el = S.tasks[t.id];
    if (!el) {
      el = S.tasks[t.id] = toast(`<b>${esc(TASK_LABEL[t.name] || "Working")}</b><div class="tmsg"></div><div class="prog"><i></i></div>
        <button class="btn small">Cancel</button>`, "", 0);
      $("button", el).onclick = () => call("cancel_task", t.id);
    }
    if (t.name && TASK_LABEL[t.name]) $("b", el).textContent = TASK_LABEL[t.name];
    $(".tmsg", el).textContent = t.message || "";
    $(".prog i", el).style.width = `${Math.round((t.progress || 0) * 100)}%`;
    if (t.done) {
      finishedTasks.add(t.id); activeTasks.delete(t.id);
      el.remove(); delete S.tasks[t.id];
      if (t.error) toast(esc(t.error), "bad", 9000);
      const cb = taskDone[t.id]; delete taskDone[t.id];
      if (cb && !t.error) cb(t.result || {});
    }
  },
};

/* ------------------------------------------------------------------ modal */
function modal(html, wire, cls = "") {
  const back = $("#modal");
  back.innerHTML = `<div class="modal ${cls}" role="dialog" aria-modal="true">${html}</div>`;
  back.hidden = false;
  const close = () => { back.hidden = true; back.innerHTML = ""; };
  back.onclick = (e) => { if (e.target === back) close(); };
  $$("[data-close]", back).forEach((b) => (b.onclick = close));
  wire && wire(back, close);
  const f = $("input, .btn.primary", back); f && f.focus();
}
function confirmBox(title, text, okLabel, danger = false) {
  return new Promise((res) => modal(`<h3>${esc(title)}</h3><p>${text}</p><div class="btn-row">
      <button class="btn" data-close>Cancel</button><button class="btn ${danger ? "danger" : "primary"}" id="mOk">${esc(okLabel)}</button></div>`,
    (m, close) => { $("#mOk", m).onclick = () => { close(); res(true); }; m.addEventListener("click", (e) => { if (e.target.hasAttribute("data-close")) res(false); }); }));
}

/* Ask what to do with files that already exist. Resolves true (overwrite), false (keep a copy) or null (cancelled). */
function conflictChoice(title, intro, okLabel) {
  return new Promise((res) => modal(`<h3>${esc(title)}</h3><p>${intro}</p>
    <p class="muted">If a file is already in your game folder:</p>
    <div class="choice-list">
      <label class="choice"><input type="radio" name="cmode" value="keep" checked><span><b>Keep a copy of the old file</b>
        <em>It's moved to Temporarily Disabled Mods\\_Backups (replaced files), so you can roll back.</em></span></label>
      <label class="choice"><input type="radio" name="cmode" value="overwrite"><span><b>Overwrite it</b>
        <em>The old file is replaced and can't be recovered. Uses no extra disk space.</em></span></label>
    </div>
    <div class="btn-row"><button class="btn" data-close>Cancel</button><button class="btn primary" id="cOk">${esc(okLabel)}</button></div>`,
  (m, close) => {
    let done = false;
    $("#cOk", m).onclick = () => { done = true; const v = $("input[name=cmode]:checked", m).value; close(); res(v === "overwrite"); };
    m.addEventListener("click", (e) => { if (!done && (e.target === m || e.target.hasAttribute("data-close"))) res(null); });
  }));
}

/* ------------------------------------------------------------------ mod backups */
async function save(vals) { const r = await call("save_settings", vals); if (r && r.ok) S.boot.settings = r.settings; return r; }
const fmtWhen = (ts) => ts ? `${fmtDate(ts)}, ${new Date(ts * 1000).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}` : "";
function backupReadout() {
  const b = S.backup;
  if (!b) return "Checking…";
  if (b.running) return "Backing up now…";
  return b.last ? `${fmtDate(b.last)} (${ago(b.last)})` : "Never";
}
function renderBackupReadout() { const d = $("#ovBackup"); if (d) d.textContent = backupReadout(); }
function backupsView(d) {
  const rows = d.backups.map((b) => `<tr>
      <td>${esc(fmtWhen(b.created))}</td><td><span class="src ${b.kind === "scheduled" ? "vortex" : "loose"}">${b.kind === "scheduled" ? "Scheduled" : "Manual"}</span></td>
      <td>${b.mods ? plural(b.mods, "mod") : "—"}</td><td class="num">${fmtSize(b.size)}</td>
      <td class="num"><button class="btn small" data-restore="${esc(b.path)}">Restore</button> <button class="btn small danger" data-del="${esc(b.path)}" title="Delete this backup">Delete</button></td></tr>`).join("");
  return `<div class="field"><label for="bkSched">Automatic backups</label><div class="bk-sched">
      <select id="bkSched"><option value="off">Off</option><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option></select>
      <span>keep the newest</span><select id="bkKeep">${[1, 3, 5, 10, 20].map((n) => `<option value="${n}" ${n === d.keep ? "selected" : ""}>${n}</option>`).join("")}</select>
      <span class="muted small bk-help">Runs while this tool is open and the game isn't running. If a backup is due when you open the tool, it runs then. Older scheduled backups are deleted past the limit; manual backups are always kept.</span></div></div>
    <div class="field"><label>Saved in</label><div class="bk-folder"><code title="${esc(d.folder)}">${esc(d.folder)}</code>
      <button class="btn small" id="bkOpenDir">Open folder</button><button class="btn small" id="bkDir">Change</button>${d.custom_folder ? `<button class="btn small" id="bkDefault">Use default</button>` : ""}</div></div>
    ${d.backups.length ? `<div class="bk-list"><table class="table"><thead><tr><th>Created</th><th>Type</th><th>Contents</th><th class="num">Size</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>`
      : `<p class="note">No backups yet. Back up now before your next big update or preset install.</p>`}`;
}
/* Wire a rendered backupsView. `leave` runs before an action that opens another dialog; `again` re-renders the view. */
function wireBackups(root, d, again, leave = () => {}) {
  $("#bkSched", root).value = d.schedule;
  $("#bkSched", root).onchange = async (e) => { await save({ backup_schedule: e.target.value }); toast(e.target.value === "off" ? "Automatic backups are off." : `Mods will be backed up ${e.target.value}.`, "ok", 2500); poll(); };
  $("#bkKeep", root).onchange = (e) => save({ backup_keep: +e.target.value });
  $("#bkOpenDir", root).onclick = async () => result(await call("open_mod_backups"));
  $("#bkDir", root).onclick = async () => { const r = await call("mod_backup_browse_dir"); if (r.ok) again(); };
  const def = $("#bkDefault", root); if (def) def.onclick = async () => { await call("mod_backup_reset_dir"); again(); };
  const now = $("#bkNow", root);
  if (now) now.onclick = async () => { leave(); startTask(await call("mod_backup_create", "manual"), async (res) => { await backupDone(res); if (S.page === "settings") again(); }); };
  $$("[data-restore]", root).forEach((b) => (b.onclick = async () => {
    const path = b.dataset.restore; leave();
    const ow = await conflictChoice("Restore this backup?", "Every file in the backup goes back where it was. Mods you installed after the backup stay installed.", "Restore");
    if (ow === null) return again();
    startTask(await call("mod_backup_restore", path, ow), async (res) => {
      toast(`Restored ${plural(res.restored, "file")}.${res.replaced ? ` ${plural(res.replaced, "existing file")} ${res.overwrite ? "overwritten" : "kept in _Backups (replaced files)"}.` : ""}`, "ok", 7000);
      await refreshMods(true); go(S.page);
    });
  }));
  $$("[data-del]", root).forEach((b) => (b.onclick = async () => {
    const path = b.dataset.del; leave();
    if (await confirmBox("Delete this backup?", "The backup file is deleted permanently. Your installed mods aren't affected.", "Delete backup", true)) {
      result(await call("mod_backup_delete", path), "Backup deleted."); poll();
    }
    again();
  }));
}
async function openBackups() {
  const d = await call("mod_backups_list");
  if (!result(d)) return;
  S.backup = d.state; renderBackupReadout();
  modal(`<h3>Mod backups</h3>
    <p class="muted">A backup is one zip of every manually installed mod, enabled or disabled, plus the core frameworks.
      Vortex and MO2 keep their own copies of their mods, so those aren't included.</p>
    ${backupsView(d)}
    <div class="btn-row"><button class="btn" data-close>Close</button><button class="btn primary" id="bkNow" ${d.state.running ? "disabled" : ""}>${d.state.running ? "Backing up…" : "Back up now"}</button></div>`,
  (m, close) => wireBackups(m, d, openBackups, close), "wide-bk");
}
async function renderSettingsBackups() {
  const host = $("#setBackups");
  if (!host) return;
  const d = await call("mod_backups_list");
  if (!result(d)) return;
  S.backup = d.state;
  const last = d.state.last ? `Last backup ${fmtWhen(d.state.last)} (${ago(d.state.last)}).` : "No backups yet.";
  host.innerHTML = `<div class="upd-strip"><p>${esc(last)}</p><button class="btn small primary" id="bkNow" ${d.state.running ? "disabled" : ""}>${d.state.running ? "Backing up…" : "Back up now"}</button></div>${backupsView(d)}`;
  wireBackups(host, d, renderSettingsBackups);
}
async function backupDone(res) {
  S.backup = { ...(S.backup || {}), last: res.created, running: false }; renderBackupReadout();
  toast(`${res.kind === "scheduled" ? "Scheduled backup" : "Backup"} saved: ${plural(res.mods, "mod")}, ${fmtSize(res.size)}.${res.pruned ? ` Removed ${plural(res.pruned, "older scheduled backup")}.` : ""}`, "ok", 6000);
}

/* ------------------------------------------------------------------ chrome */
const PAGES = {
  overview: { title: "Overview", sub: "Check for updates on linked mods, detect game abnormalities, mod stats and mod/log lists for troubleshooting." },
  mods: { title: "Mods", sub: "Every installed mod detected, grouped from all mod folders. Click on a mod for file details." },
  core: { title: "Core Frameworks", sub: "Required framework if you are installing mods. Missing or outdated core mods can cause crashes." },
  logs: { title: "Logs", sub: "Framework logs from your last session. If errors are detected they will be highlighted." },
  nexus: { title: "Nexus Mods", sub: "Link your account, track and link your mods." },
  browse: { title: "Browse Nexus", sub: "Browse trending, new, and updated Cyberpunk 2077 mods, along with direct search." },
  settings: { title: "Settings", sub: "Manage all settings for Cyberpunk 2077 Mod List Tool." },
};
function setHeader() {
  const p = PAGES[S.page];
  $("#pageTitle").textContent = p.title;
  $("#pageSub").textContent = p.sub;
  const g = S.boot?.game || {};
  const sm = S.summary || {};
  $("#slabMeta").innerHTML = g.valid ? `<div><b>${esc(g.version || "—")}</b>Game version</div>
    <div><b>${g.phantom_liberty ? "Yes" : "No"}</b>Phantom Liberty</div>
    <div><b>${sm.enabled ?? "—"}</b>Mods enabled</div>` : "";
}
async function go(page) {
  S.page = page;
  $$(".nav").forEach((b) => b.classList.toggle("active", b.dataset.page === page));
  closeDrawer();
  setHeader();
  const el = $("#page");
  el.className = "page";
  el.scrollTop = 0;
  if (!S.boot.game.valid && !["settings", "nexus", "browse"].includes(page)) return renderNoGame(el);
  await RENDER[page](el);
}
function renderNoGame(el) {
  el.innerHTML = `<div class="panel hatch"><div class="empty"><b>Point the tool at your game folder</b>
    It's the folder that contains <code>bin\\x64\\Cyberpunk2077.exe</code>.<br><br>
    <button class="btn primary" id="ngPick">Choose game folder</button> <button class="btn" id="ngSet">Open settings</button></div></div>`;
  $("#ngPick").onclick = pickGameDir;
  $("#ngSet").onclick = () => go("settings");
}
async function pickGameDir() {
  const r = await call("browse_game_dir");
  if (r.ok) { S.boot.game = r.game; loadGameIcon(); toast("Game folder set.", "ok"); await refreshMods(true); go(S.page === "settings" ? "settings" : "overview"); }
  else result(r);
}

/* ------------------------------------------------------------------ status polling */
/* ------------------------------------------------------------------ Nexus service health */
// The backend tells problems on Nexus's end apart from problems on the user's PC/network:
//   down     = Nexus isn't responding (seen by the app) or a major outage on the status page
//   degraded = the status page reports degraded performance / an incident
//   local    = the user's connection or a DNS filter is blocking Nexus
const NXH_LABEL = { down: "Nexus: service issue", degraded: "Nexus Mods Status: Degraded", local: "Nexus: can't connect" };
function nexusHealthBanner(h) {
  h = h || S.nexusHealth;
  if (!h || h.level === "ok") return "";
  const ob = h.observed, of = h.official;
  const title = ob ? ob.title : "Nexus Mods is reporting problems";
  const lead = ob ? esc(ob.message)
    : `Nexus's status page reports: <b>${esc(of.summary)}</b>. Downloads, update checks and linking may be slow or fail. This is on Nexus's end, not your PC.`;
  const inc = (of?.incidents || []).map((i) => `<li><a href="#" data-nxurl="${esc(i.url)}">${esc(i.name)}</a> <span class="muted">(${esc(i.status)})</span></li>`).join("");
  const official = ob && of ? `<p class="small" style="margin:6px 0 0">Nexus status page: ${esc(of.summary)}</p>` : "";
  return `<div class="note nxh-banner ${h.level}" role="status"><b>${esc(title)}</b><div>${lead}</div>${official}
    ${inc ? `<ul class="small" style="margin:6px 0 0">${inc}</ul>` : ""}
    <p class="small" style="margin:6px 0 0"><a href="#" data-nxurl="${esc(h.status_page)}">Nexus status page</a>${h.level !== "local" ? " · <a href=\"#\" data-nxurl=\"https://discord.gg/nexusmods\">Nexus Discord</a>" : ""}</p></div>`;
}
function wireNexusLinks(root) { $$("[data-nxurl]", root).forEach((a) => (a.onclick = (e) => { e.preventDefault(); call("open_url", a.dataset.nxurl); })); }
function renderNexusHealth(h) {
  const prev = S.nexusHealth;
  S.nexusHealth = h || null;
  const sb = $("#sbNexus");
  if (sb) {
    const bad = h && h.level !== "ok";
    sb.hidden = !bad;
    sb.className = `nxh ${bad ? h.level : ""}`;
    sb.textContent = bad ? NXH_LABEL[h.level] : "";
    sb.title = bad ? (h.observed?.message || h.official?.summary || "") + " Click for the Nexus status page." : "";
    sb.onclick = (e) => { e.preventDefault(); call("open_url", h?.status_page || "https://nexusmods.statuspage.io"); };
  }
  // refresh in-page banners only when something changed
  if (JSON.stringify(prev) === JSON.stringify(h)) return;
  $$(".nxh-slot").forEach((slot) => { slot.innerHTML = nexusHealthBanner(h); wireNexusLinks(slot); });
}

async function poll() {
  const st = await call("get_status");
  S.status = st || {};
  if ("nexus_health" in S.status) renderNexusHealth(S.status.nexus_health);
  applyRunning(st.running || {}, st.valid);
  renderFooterRun();
  const nx = st.nxm_tasks || {};
  (nx.errors || []).forEach((e) => toast(esc(e), "bad", 9000));
  (nx.tasks || []).forEach((id) => startTask({ ok: true, task: id, name: "update" }, async (res) => {
    toast(`Installed <b>${esc(res.name)}</b>${res.version ? ` ${esc(res.version)}` : ""}.`, "ok", 7000);
    await refreshMods(true); if (S.page === "overview") renderUpdatesPanel(); else if (S.page === "mods") renderModsTable();
  }));
  if (st.backup) { S.backup = st.backup; renderBackupReadout(); }
  if (st.backup_task) startTask({ ok: true, task: st.backup_task, name: "backup" }, backupDone);
  const sm = st.summary;
  if (sm) {
    S.summary = sm;
    $("#navModCount").textContent = sm.enabled;
    $("#navModCount").className = "info";
  }
  const cf = $("#navCoreFlag");
  cf.textContent = st.core_ok === false ? st.core_missing.length : "";
  cf.className = st.core_ok === false ? "bad" : "";
  const lf = $("#navLogFlag");
  lf.textContent = st.log_errors ? st.log_errors : "";
  lf.className = st.log_errors ? "bad" : "";
  const nf = $("#navNexusFlag");
  nf.textContent = sm && sm.updates ? sm.updates : "";
  nf.className = sm && sm.updates ? "info" : "";
  const g = S.boot.game;
  $("#sbGame").textContent = g.valid ? `${g.store || ""} · ${g.dir}`.replace(/^ · /, "") : "No game folder set";
  const mgr = [];
  if (sm?.vortex) mgr.push(`Vortex: ${sm.vortex} mods`);
  if (sm?.mo2) mgr.push(`MO2: ${sm.mo2} mods`);
  $("#sbManager").textContent = mgr.join("   ");
  setHeader();
  if (st.changed && S.page === "mods") { await refreshMods(); renderModsTable(); }
  if (st.changed && S.page === "overview") RENDER.overview($("#page"));
}

/* ------------------------------------------------------------------ OVERVIEW */
async function refreshMods(force = false) {
  const r = await call("get_mods", force);
  if (r.ok) { S.mods = r.mods; S.summary = r.summary; }
  return r;
}
const RENDER = {};
function renderFooterRun() {
  const run = S.running || {}, st = S.status || {};
  const parts = [];
  if (run.game) parts.push(`<span class="live">Cyberpunk 2077 is running. Mod changes are locked.</span>`);
  if (st.log_errors) {
    const fresh = st.log_errors_fresh;
    const where = (st.logs_with_errors || []).slice(0, 3).join(", ");
    parts.push(`<button class="sb-alert" id="sbErr" title="${esc(where)}">◆ ${fresh || run.game ? "Game error detected" : "Errors in last session's logs"} (${plural(st.log_errors, "error")}${where ? ` in ${esc(where)}` : ""}). Review logs</button>`);
  }
  $("#sbRun").innerHTML = parts.join("");
  const b = $("#sbErr");
  if (b) b.onclick = () => showLogs((st.logs_with_errors || [])[0] || S.logSel, true);
}
function applyRunning(run, valid = true) {
  S.running = run;
  const lb = $("#launchBtn");
  lb.disabled = !!run.game || !!run.launching || !valid;
  lb.classList.toggle("running", !!run.game);
  lb.classList.toggle("launching", !!run.launching && !run.game);
  $("#launchLabel").textContent = run.game ? "Game Running" : run.launching ? "Starting…" : "Launch Game";
  $("#launchSub").textContent = run.game ? "Mods are locked" : run.launching ? "Waiting for game" : launchVia();
  renderFooterRun();
  if (S.page === "mods" && S._lastGame !== !!run.game) { S._lastGame = !!run.game; renderModsTable(); }
}
async function pollRunning() { const r = await call("get_running"); if (r && r.ok !== false) applyRunning(r, S.boot.game.valid); }
function launchVia() {
  const v = S.boot?.settings?.launch_via, mo2 = S.boot?.managers?.mo2 && S.mods.some((m) => m.source === "mo2");
  if (v === "store") return "through Steam";
  if (v === "mo2" || (v === "auto" && mo2)) return "through MO2";
  return "Cyberpunk 2077";
}
/* Header logo: the PNG is light artwork on a dark card. Measure it instead of assuming a layout:
   trim to the bright artwork, split it into horizontal bands, and if the bottom band is a short
   subtitle line (the small "MOD LIST TOOL"), crop it off and show our larger live text instead.
   Brightness becomes alpha, and the result is used as a CSS mask so it prints black on yellow. */
function applyLogo(cached) {
  for (const box of [$("#slabLogo"), $("#splashLogo")]) {
    if (!box) continue;
    box.style.setProperty("--logo", `url(${cached.mask})`);
    box.style.setProperty("--logo-ratio", cached.ratio);
    box.classList.remove("text-only");
    box.classList.toggle("no-sub", !!cached.noSub);
  }
}
async function loadLogo() {
  const box = $("#slabLogo");
  const r = await call("app_logo");
  if (!r.ok || !r.uri) { box.classList.add("text-only"); return; }
  const cacheKey = "cp77mlt.logo." + r.uri.length + "." + r.uri.slice(-40);
  try {   // processed logo from last launch: show it instantly
    const hit = JSON.parse(localStorage.getItem(cacheKey) || "null");
    if (hit && hit.mask) { applyLogo(hit); return; }
  } catch (e) { /* storage unavailable */ }
  await new Promise((done) => {
  const img = new Image();
  img.onload = () => {
    const W = img.naturalWidth, H = img.naturalHeight;
    const src = document.createElement("canvas");
    src.width = W; src.height = H;
    const sctx = src.getContext("2d");
    sctx.drawImage(img, 0, 0);
    const all = sctx.getImageData(0, 0, W, H).data;
    // background = median corner brightness; artwork = clearly brighter than that
    const lumAt = (x, y) => { const i = (y * W + x) * 4; return Math.max(all[i], all[i + 1], all[i + 2]) * (all[i + 3] / 255); };
    const corners = [lumAt(0, 0), lumAt(W - 1, 0), lumAt(0, H - 1), lumAt(W - 1, H - 1)].sort((a, b) => a - b);
    const bg = (corners[1] + corners[2]) / 2, thr = bg + 50;
    const rows = new Array(H).fill(0);
    let x0 = W, x1 = -1;
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (lumAt(x, y) > thr) { rows[y]++; if (x < x0) x0 = x; if (x > x1) x1 = x; }
    const bands = [];
    for (let y = 0, start = -1, gap = 0; y <= H; y++) {
      const on = y < H && rows[y] > 0;
      if (on) { if (start < 0) start = y; gap = 0; }
      else if (start >= 0 && (++gap >= 2 || y === H)) { bands.push([start, y - gap]); start = -1; gap = 0; }
    }
    if (!bands.length || x1 < 0) { box.classList.add("text-only"); done(); return; }
    const top = bands[0][0], total = bands[bands.length - 1][1] - top + 1;
    let bottom = bands[bands.length - 1][1], hasSub = false;
    const last = bands[bands.length - 1];
    if (bands.length >= 2 && (last[1] - last[0] + 1) < total * 0.22) { bottom = bands[bands.length - 2][1]; hasSub = true; }
    // recompute horizontal extent for the kept rows only
    x0 = W; x1 = -1;
    for (let y = top; y <= bottom; y++) for (let x = 0; x < W; x++) if (lumAt(x, y) > thr) { if (x < x0) x0 = x; if (x > x1) x1 = x; }
    const pad = 2, cx = Math.max(0, x0 - pad), cy = Math.max(0, top - pad);
    const cw = Math.min(W, x1 + pad + 1) - cx, ch = Math.min(H, bottom + pad + 1) - cy;
    const c = document.createElement("canvas");
    c.width = cw; c.height = ch;
    const ctx = c.getContext("2d");
    const out = ctx.createImageData(cw, ch), o = out.data;
    for (let y = 0; y < ch; y++) for (let x = 0; x < cw; x++) {
      const l = lumAt(cx + x, cy + y), i = (y * cw + x) * 4;
      o[i] = o[i + 1] = o[i + 2] = 0;
      o[i + 3] = Math.max(0, Math.min(255, (l - bg - 20) * 255 / 150));
    }
    ctx.putImageData(out, 0, 0);
    const result = { mask: c.toDataURL("image/png"), ratio: `${cw} / ${ch}`, noSub: !hasSub && cw / ch < 3.8 };
    applyLogo(result);
    try { localStorage.setItem(cacheKey, JSON.stringify(result)); } catch (e) { /* storage full/unavailable */ }
    done();
    // If a subtitle band was cropped off, print ours. If not, the artwork either has no subtitle (a wide
    // wordmark, ~4:1) or one touching the "2077" line (taller than ~3.8:1): then keep the image's own.
  };
  img.onerror = () => { box.classList.add("text-only"); done(); };
  img.src = r.uri;
  });
}
function preloadImage(url, timeout = 2000) {
  return new Promise((res) => {
    if (!url) return res();
    const i = new Image(), t = setTimeout(res, timeout);
    i.onload = i.onerror = () => { clearTimeout(t); res(); };
    i.src = url;
  });
}
function renderUserChip() {
  const u = S.boot?.nexus?.user, chip = $("#userChip");
  chip.classList.toggle("off", !u);
  chip.innerHTML = u
    ? `${u.avatar ? `<img src="${esc(u.avatar)}" alt="" onerror="this.outerHTML='<i class=ph>${esc((u.name || "?")[0].toUpperCase())}</i>'">` : `<i class="ph">${esc((u.name || "?")[0].toUpperCase())}</i>`}
       <span><b>${esc(u.name)}</b><small class="${u.is_premium ? "prem" : ""}">${u.is_premium ? "Nexus Premium" : "Nexus Mods"}</small></span><i class="dot" title="Signed in"></i>`
    : `<i class="ph">?</i><span><b>Not signed in</b><small>Connect Nexus Mods</small></span><i class="dot"></i>`;
}
async function loadGameIcon() {
  const r = await call("game_icon");
  const img = $("#gameIcon");
  if (r.ok && r.uri) { img.src = r.uri; img.hidden = false; $("#gameIconFallback").style.display = "none"; }
  else { img.hidden = true; $("#gameIconFallback").style.display = ""; }
}
RENDER.overview = async (el) => {
  await refreshMods();
  const [core, lg, st] = await Promise.all([call("get_core"), call("get_logs"), call("get_status")]);
  const sm = S.summary, g = S.boot.game;
  // Setup check: green = good, orange = outdated, red = needs fixing
  const alerts = [];
  const coreList = core.core || [];
  const missing = coreList.filter((c) => !c.installed);
  const outdated = coreList.filter((c) => c.installed && c.update?.update);
  missing.forEach((c) => alerts.push({ lvl: "bad",
    t: `<b>${esc(c.name)}</b> is ${c.disabled ? "disabled" : "not installed"}. ${esc(c.desc)}`,
    a: c.disabled ? `<button class="btn small" data-go="core">Review</button>` : `<button class="btn small" data-url="https://www.nexusmods.com/cyberpunk2077/mods/${c.nexus_id}">Get it on Nexus</button>` }));
  if (!missing.length && outdated.length) alerts.push({ lvl: "warn",
    t: `All ${coreList.length} core frameworks are installed, but ${outdated.map((c) => `<b>${esc(c.name)}</b>`).join(", ")} ${outdated.length === 1 ? "has an update" : "have updates"}.`,
    a: `<button class="btn small" data-go="core">Update</button>` });
  if (!missing.length && !outdated.length) alerts.push({ lvl: "ok", t: `All ${coreList.length} core frameworks are installed and up to date.` });
  const errLogs = (lg.logs || []).filter((l) => l.errors);
  errLogs.forEach((l) => alerts.push({ lvl: "bad",
    t: `<b>${esc(l.name)}</b> logged ${plural(l.errors, "error")} in the last session.`, a: `<button class="btn small" data-log="${esc(l.name)}">View log</button>` }));
  if (!errLogs.length) alerts.push({ lvl: (lg.logs || []).length ? "ok" : "none",
    t: (lg.logs || []).length ? "The last game session logged no framework errors." : "No framework logs yet. They appear after you play once." });
  const total = Math.max(sm.total, 1);
  const logs = lg.logs || [];
  const auto = S.boot.settings.auto_select_all_logs;
  el.innerHTML = `<div class="nxh-slot">${nexusHealthBanner()}</div><div class="panel upd-panel" id="updPanel"></div><div class="grid cols-2">
    <div class="panel">
      <div class="readout">
        <div class="bignum" aria-label="${sm.enabled} mods enabled">${sm.enabled}</div>
        <dl>
          <dt>Mods enabled</dt><dd>${sm.enabled} of ${sm.total}</dd>
          <dt>Disabled</dt><dd>${sm.disabled}</dd>
          <dt>Installed manually</dt><dd>${sm.loose}</dd>
          ${sm.vortex ? `<dt>Through Vortex</dt><dd>${sm.vortex}</dd>` : ""}
          ${sm.mo2 ? `<dt>Through MO2</dt><dd>${sm.mo2}</dd>` : ""}
          <dt>Store</dt><dd>${esc(g.store)}</dd>
          <dt>Last backup</dt><dd><button class="link plain" id="ovBackup" title="Back up or restore your mods">${esc(backupReadout())}</button></dd>
        </dl>
      </div>
      <div class="bar" title="Manual / Vortex / MO2 / disabled">
        <i style="flex:${sm.loose - S.mods.filter((m) => m.source === "loose" && !m.enabled).length};background:var(--yellow)"></i>
        <i style="flex:${S.mods.filter((m) => m.source === "vortex" && m.enabled).length};background:var(--cyan)"></i>
        <i style="flex:${S.mods.filter((m) => m.source === "mo2" && m.enabled).length};background:var(--bone)"></i>
        <i style="flex:${sm.disabled};background:var(--graphite)"></i>
        <i style="flex:${total === 1 && !sm.total ? 1 : 0};background:var(--graphite)"></i>
      </div>
    </div>
    <div class="panel"><h2>Setup check</h2><ul class="alerts">${alerts.map((a) =>
      `<li class="lvl-${a.lvl}"><span class="dot" aria-label="${{ ok: "Good", warn: "Outdated", bad: "Problem", none: "" }[a.lvl]}"></span><span>${a.t}</span><span class="act">${a.a || ""}</span></li>`).join("")}</ul></div>
  </div>
  <div class="panel" style="margin-top:18px">
    <h2>Mod list for troubleshooting <span class="hint">${S.boot.settings.ask_report_path ? "You'll choose the name and folder" : `Saved to ${esc(S.boot.settings.output_dir_effective)}`}</span></h2>
    <p class="muted" style="margin-top:-4px;max-width:70ch">Creates <b>Cyberpunk 2077 Mod List.txt</b> with your game version, frameworks, every mod and the logs you pick. Attach it when you ask a mod author for help.</p>
    <div style="display:flex;flex-wrap:wrap;gap:4px 26px;margin:10px 0 14px">
      ${logs.length ? logs.map((l) => `<label class="check"><input type="checkbox" class="logpick" value="${esc(l.name)}" ${auto ? "checked" : ""}>${esc(l.name)}${l.errors ? ` <span style="color:var(--red)">(${plural(l.errors, "error")})</span>` : ""}</label>`).join("")
      : `<span class="muted">No framework logs found yet. Run the game once with mods installed.</span>`}
    </div>
    <div class="btn-row">
      <button class="btn primary" id="genBtn">Generate mod list</button>
      ${S.lastReport ? `<button class="btn" id="openRep">Open file</button><button class="btn" id="copyRep">Copy text</button><button class="btn" id="showRep">Show in folder</button>` : ""}
    </div>
  </div>`;
  wireCommon(el);
  wireNexusLinks(el);
  $("#ovBackup").onclick = openBackups;
  renderUpdatesPanel();
  $("#genBtn").onclick = async () => {
    const names = $$(".logpick:checked").map((c) => c.value);
    const r = await call("generate_report", names);
    if (r.cancelled) return;
    if (result(r)) { S.lastReport = r.path; toast(`Mod list saved to <b>${esc(r.path)}</b>`, "ok", 6000); RENDER.overview(el); }
  };
  if (S.lastReport) {
    $("#openRep").onclick = () => call("open_path", S.lastReport);
    $("#showRep").onclick = () => call("open_path", S.lastReport.replace(/[\\/][^\\/]+$/, ""));
    $("#copyRep").onclick = async () => {
      const r = await call("copy_report", S.lastReport);
      if (r.ok) { await navigator.clipboard.writeText(r.text).then(() => toast("Mod list copied to the clipboard.", "ok"), () => toast("Couldn't access the clipboard.", "bad")); }
    };
  }
};
/* Open the Logs page on a log. Already showing it: do nothing (no reload/flicker). */
function showLogs(name, errorsOnly) {
  const same = S.page === "logs" && S.logSel === name && (errorsOnly === undefined || !!S.errorsOnly === errorsOnly);
  if (same) { closeDrawer(); return; }
  S.logSel = name;
  if (errorsOnly !== undefined) S.errorsOnly = errorsOnly;
  if (S.page === "logs") { closeDrawer(); RENDER.logs($("#page")); } else go("logs");
}
function wireCommon(el) {
  $$("[data-go]", el).forEach((b) => (b.onclick = () => go(b.dataset.go)));
  $$("[data-url]", el).forEach((b) => (b.onclick = () => call("open_url", b.dataset.url)));
  $$("[data-log]", el).forEach((b) => (b.onclick = () => showLogs(b.dataset.log)));
  $$("[data-mod]", el).forEach((b) => (b.onclick = async () => { await go("mods"); openDrawer(b.dataset.mod); }));
}

/* updates panel (top of overview) */
let updTaskId = null, autoChecked = false;
const ago = (ts) => { if (!ts) return ""; const m = Math.round((Date.now() / 1000 - ts) / 60);
  return m < 1 ? "just now" : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago`; };
async function renderUpdatesPanel() {
  const host = $("#updPanel");
  if (!host) return;
  const u = await call("get_updates");
  if (!u.ok) { host.remove(); return; }
  const checking = updTaskId && activeTasks.has(updTaskId);
  if (!u.connected) {
    host.innerHTML = `<h2>Mod updates</h2><div class="upd-strip"><p>Connect your Nexus Mods account to see which of your mods have updates.</p>
      <button class="btn primary" data-go="nexus">Connect Nexus Mods</button></div>`;
    wireCommon(host); return;
  }
  const rows = u.updates;
  const head = `<h2>${rows.length ? `${plural(rows.length, "update")} available` : "Mod updates"}
    <span class="hint">${checking ? "Checking Nexus…" : u.checked ? `Checked ${ago(u.checked)}` : "Not checked yet"}
    ${checking ? "" : `<button class="link" id="updCheck">Check now</button>`}</span></h2>`;
  const body = rows.length ? `<div class="upd-rows">${rows.map((r) => `
      <div class="n"><button class="link plain" data-open="${esc(r.key)}" title="${r.core ? "Open Core Frameworks" : "Show details"}">${esc(r.name)}</button><span class="src ${r.core ? "fw" : r.source}">${r.core ? "Framework" : SRC[r.source] || r.source}</span></div>
      <div class="vv" title="${r.basis === "estimated" ? "Installed version estimated from file dates" : r.basis === "dates" ? "Nexus has a newer upload than your files; installed version unknown" : ""}">${r.basis === "dates" ? "Newer upload" : `${esc(r.installed || "?")}${r.basis === "estimated" ? "<sup>≈</sup>" : ""}`} → <b>${esc(r.latest)}</b></div>
      <div class="d">${r.updated ? fmtDate(r.updated) : ""}</div>
      <div class="btn-row" style="flex-wrap:nowrap"><button class="btn small primary" data-upd="${esc(r.key)}">${(r.source === "loose" || r.core) && u.premium ? "Update" : "Get update"}</button>
        <button class="btn small" data-uptodate="${esc(r.key)}" title="I already have this version">Dismiss</button></div>`).join("")}</div>`
    : `<p class="muted" style="margin:0">${checking ? "Comparing your installed versions with Nexus." : u.checked ? "Everything linked to Nexus is up to date." : "Run a check to compare your installed versions with Nexus."}</p>`;
  const unlinked = S.mods.filter((m) => m.source === "loose" && !m.nexus_id && !m.github && (S.boot.settings.queue_include_disabled || m.enabled)).length;
  const foot = unlinked && !checking ? `<p class="muted upd-foot">${plural(unlinked, "manually installed mod")} ${unlinked === 1 ? "isn't" : "aren't"} linked to Nexus yet, so ${unlinked === 1 ? "it can't" : "they can't"} be checked.
    <button class="link" id="updFind">Find them on Nexus</button></p>` : "";
  host.innerHTML = head + body + foot + (checking ? `<div class="upd-prog"><i id="updBar"></i></div>` : "");
  if ($("#updFind")) $("#updFind").onclick = () => runIdentify(null);
  $$("[data-open]", host).forEach((b) => (b.onclick = () => b.dataset.open.startsWith("core:") ? go("core") : openDrawer(b.dataset.open)));
  $$("[data-uptodate]", host).forEach((b) => (b.onclick = async () => { if (result(await call("mark_up_to_date", b.dataset.uptodate))) { await refreshMods(); renderUpdatesPanel(); poll(); } }));
  if ($("#updCheck")) $("#updCheck").onclick = runUpdateCheck;
  $$("[data-upd]", host).forEach((b) => (b.onclick = async () => {
    const key = b.dataset.upd;
    await doUpdate(key, () => renderUpdatesPanel());
  }));
  // first visit this session: check automatically if results are old
  if (!checking && !autoChecked && (!u.checked || Date.now() / 1000 - u.checked > 6 * 3600)) { autoChecked = true; runUpdateCheck(); }
}
async function runUpdateCheck() {
  autoChecked = true;
  const r = await call("nexus_check_updates");
  if (!r || r.ok === false) { result(r); return; }
  updTaskId = r.task;
  startTask(r, async (res) => {
    toast(`Checked ${res.checked}: ${plural(res.updates, "update")} available.`, "ok", 5000);
    await refreshMods(true); poll();
    if (S.page === "overview") renderUpdatesPanel(); else if (S.page === "nexus") RENDER.nexus($("#page"));
  }, S.page === "overview");
  renderUpdatesPanel();
}
taskListeners.add((t) => {
  if (t.id !== updTaskId) return;
  const bar = $("#updBar"); if (bar) bar.style.width = `${Math.round(t.progress * 100)}%`;
  const hint = $("#updPanel .hint"); if (hint && !t.done) hint.textContent = `Checking Nexus… ${t.message || ""}`;
  if (t.done && t.error && S.page === "overview") renderUpdatesPanel();
});

async function doUpdate(key, after) {
  const r = await call("nexus_update", key);
  if (r.task) return startTask(r, async (res) => { toast(`Updated <b>${esc(res.name)}</b>${res.version ? ` to ${esc(res.version)}` : ""}.`, "ok", 6000); await refreshMods(true); after && after(); poll(); });
  if (r.needs_nxm) return modal(`<h3>Update from the website</h3>
    <p>Free Nexus accounts can't download through the API directly. Nexus offers a <b>Mod Manager Download</b> button for this instead.</p>
    <p class="muted">Turn this on and that button installs the file here. Links for other games still go to the app that handled them before (Vortex or MO2), and you can switch this off in Settings at any time.</p>
    <div class="btn-row"><button class="btn" data-close>Not now</button><button class="btn primary" id="nxmOn">Install Mod Manager Downloads here</button></div>`,
    (m, close) => { $("#nxmOn", m).onclick = async () => { close(); if (result(await call("nxm_set", true), "Mod Manager Downloads will install here. Click the button on the Files tab.")) poll(); }; });
  result(r);
}
async function runIdentify(keys = null) {
  const r = await call("nexus_identify", keys);
  startTask(r, async (res) => {
    const bits = [];
    if (res.by_url) bits.push(`${res.by_url} from Nexus links inside the mod's own files`);
    if (res.by_github) bits.push(`${res.by_github} to GitHub repositories mentioned in their files`);
    if (res.by_download) bits.push(`${res.by_download} from your downloaded archives`);
    if (res.verified) bits.push(`${res.verified} confirmed by comparing files with Nexus`);
    if (res.by_name) bits.push(`${res.by_name} by exact name`);
    toast(`<b>Linked ${res.identified} of ${res.checked} mods</b>${bits.length ? `<br>${bits.join(", ")}` : ""}
      ${res.suggested ? `<br>${plural(res.suggested, "possible match")} to review on the Nexus page.` : ""}
      ${res.unlinked ? `<br>${res.unlinked} left to link by hand in the link queue.` : ""}
      ${!res.logged_in ? "<br>Connect Nexus Mods to also search by name." : ""}${res.search_error ? `<br>Name search: ${esc(res.search_error)}` : ""}`, "ok", 12000);
    await refreshMods(true);
    if (S.page === "overview") renderUpdatesPanel(); else if (S.page === "mods") renderModsTable(); else if (S.page === "nexus") RENDER.nexus($("#page"));
    if (res.identified && S.boot.nexus.user) runUpdateCheck();
  });
}

/* search Nexus and link a mod (drawer + link queue) */
function mountLinkSearch(host, key, initial, onLinked) {
  host.innerHTML = `<div class="lsearch"><label class="lslabel">
      <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M13 13l5 5" stroke="currentColor" stroke-width="2"/></svg>
      <input type="search" placeholder="Search Nexus by name" aria-label="Search Nexus" value="${esc(initial || "")}"></label>
    <div class="lres-head muted small" hidden></div><div class="lresults" hidden></div><div class="lprev"></div></div>`;
  const input = $("input", host), list = $(".lresults", host), head = $(".lres-head", host), prev = $(".lprev", host);
  let timer = null, seq = 0;
  const link = async (id, name) => {
    const r2 = await call("nexus_link", key, String(id));
    if (result(r2, `Linked to ${name || "#" + id}.`)) {
      await refreshMods(); onLinked && onLinked(); poll();
      const chk = await call("nexus_check_updates", [key]);   // newly linked: see if it's out of date
      if (chk.ok) startTask(chk, async () => { await refreshMods(); if (S.page === "mods") renderModsTable(); }, true);
    }
  };
  const run = async () => {
    const q = input.value.trim(), my = ++seq;
    if (q.length < 2) { list.hidden = head.hidden = true; return; }
    list.hidden = head.hidden = false; head.textContent = "Searching…"; list.innerHTML = "";
    const r = await call("nexus_search", q);
    if (my !== seq) return;
    if (!r.ok) { head.textContent = r.error; return; }
    head.textContent = r.results.length ? `${plural(r.results.length, "result")}. Click one to preview it, or Link to link it now.` : "No matches. Try fewer words, or paste the mod's URL above.";
    list.innerHTML = r.results.map((x) => `<div class="lrow" data-id="${x.mod_id}" data-name="${esc(x.name)}" tabindex="0">
        <span class="lname">${esc(x.name)}</span><small>#${x.mod_id}${x.version ? ` · ${esc(x.version)}` : ""}</small>
        <button class="btn small primary" data-link>Link</button></div>`).join("");
    $$(".lrow", list).forEach((row) => {
      const id = +row.dataset.id, name = row.dataset.name;
      row.onclick = (e) => { if (!e.target.closest("[data-link]")) preview(id); };
      row.ondblclick = () => link(id, name);
      row.onkeydown = (e) => { if (e.key === "Enter") preview(id); };
      $("[data-link]", row).onclick = (e) => { e.stopPropagation(); link(id, name); };
    });
  };
  const preview = async (id) => {
    $$(".lrow", list).forEach((r) => r.classList.toggle("on", +r.dataset.id === id));
    prev.innerHTML = `<p class="muted small">Loading #${id}…</p>`;
    const r = await call("nexus_mod_info", id);
    if (!r.ok) { prev.innerHTML = `<p class="muted">${esc(r.error)}</p>`; return; }
    const d = r.mod;
    prev.innerHTML = `<div class="lpreview">${d.picture_url ? `<img src="${esc(d.picture_url)}" alt="">` : "<span></span>"}<div>
      <b>${esc(d.name)}</b> <span class="muted">by ${esc(d.author || "unknown")} · ${esc(d.version || "")}</span>
      <p>${esc((d.summary || "").replace(/<[^>]+>/g, "").slice(0, 180))}</p>
      <div class="btn-row"><button class="btn small primary" data-link>Link to this mod</button><button class="btn small" data-open>Open page</button></div></div></div>`;
    $("[data-open]", prev).onclick = () => call("open_url", `https://www.nexusmods.com/cyberpunk2077/mods/${id}`);
    $("[data-link]", prev).onclick = () => link(id, d.name);
  };
  input.oninput = () => { clearTimeout(timer); timer = setTimeout(run, 350); };
  input.onkeydown = (e) => { if (e.key === "Enter") { clearTimeout(timer); run(); } };
  if (initial) run();
}
const niceName = (n) => n.replace(/^[^A-Za-z0-9]+/, "").replace(/[_\-.]+/g, " ").replace(/([a-z])([A-Z])/g, "$1 $2").trim();

/* ------------------------------------------------------------------ MODS */
RENDER.mods = async (el) => {
  const r = await refreshMods();
  if (!r.ok) return result(r);
  const f = S.filter;
  el.innerHTML = `
    <div class="toolbar">
      <div class="search"><input type="search" id="q" placeholder="Search mods, files or Nexus IDs" value="${esc(f.q)}" aria-label="Search mods"></div>
      <div class="seg" id="segState"></div>
      <div class="seg" id="segSource"></div>
    </div>
    <div class="subbar"><div class="chips" id="locChips"></div><div class="btn-row">
      <div class="seg" id="segView">
        <button data-v="mods" title="Groups mods with files which are installed in multiple folders as one mod.">Grouped Mods</button>
        <button data-v="folders" title="Does not group mods with files which are installed in multiple folders as one mod. Lists every file in a row from each folder.">Ungrouped Mods</button></div>
      <button class="btn" id="btnInstall" title="Install a mod from a .zip, .7z or .rar you downloaded">Install mod</button>
      <button class="btn" id="btnMore" aria-haspopup="true">More actions</button></div></div>
    <table class="table" id="modsTable"><thead><tr>
      <th style="width:34px"><label class="check" title="Select all shown"><input type="checkbox" id="selAll"></label></th>
      <th style="width:76px" title="Switch a mod on or off">Toggle</th><th data-sort="name" id="thName" title="Click to flip the order">Mod Name A to Z</th><th data-sort="source" style="width:90px">Source</th>
      <th data-sort="version" style="width:110px">Version</th><th data-sort="nexus" style="width:150px">Nexus</th><th data-sort="size" style="width:90px;text-align:right">Size</th>
    </tr></thead><tbody></tbody></table>
    <div id="bulkHost"></div>`;
  $("#q").oninput = (e) => { f.q = e.target.value; renderModsTable(); };
  $$("#segView button", el).forEach((b) => (b.onclick = async () => {
    const r2 = await call("save_settings", { mods_view: b.dataset.v });
    if (r2.ok) S.boot.settings = r2.settings;
    renderModsTable();
  }));
  const installDone = async (res) => {
    const n = res.displaced?.length;
    toast(`Installed ${plural(res.installed.length, "file")}.${n ? res.overwritten ? ` ${plural(n, "existing file")} overwritten.` : (S.boot.settings.replaced_keep === 0 ? ` ${plural(n, "old file")} replaced.` : ` ${plural(n, "old file")} replaced (a copy is kept in Settings → Replaced files).`) : ""}`, "ok", 7000);
    await refreshMods(true); renderModsTable();
  };
  $("#btnInstall").onclick = async () => startTask(await call("install_archive", "mod"), installDone);
  $("#btnMore").onclick = () => modal(`<h3>More actions</h3>
    <p class="muted">These act on manually installed mods. Vortex and MO2 mods stay under their manager's control.</p>
    <div class="btn-row" style="justify-content:flex-start;flex-direction:column;align-items:stretch">
      <button class="btn" id="bEnableAll">Enable all manual mods</button>
      <button class="btn" id="bDisableAll">Disable all manual mods</button>
      <button class="btn" id="bBackups">Back up or restore mods</button>
      <button class="btn" id="bImport">Install a mod preset</button>
      <button class="btn" id="bExport">Export enabled mods as a preset</button>
      <button class="btn" id="bOpenDis">Open the disabled mods folder</button>
      <button class="btn" id="bRescan">Rescan game folder</button>
    </div><div class="btn-row"><button class="btn" data-close>Close</button></div>`, (m, close) => {
    $("#bEnableAll", m).onclick = async () => { close(); result(await call("set_all_enabled", true), "All manual mods enabled."); await refreshMods(); renderModsTable(); };
    $("#bDisableAll", m).onclick = async () => { close(); if (await confirmBox("Disable all manual mods?", "Their files move to <b>Temporarily Disabled Mods</b> in your game folder. You can enable them again at any time.", "Disable all")) { result(await call("set_all_enabled", false), "All manual mods disabled."); await refreshMods(); renderModsTable(); } };
    $("#bExport", m).onclick = () => { close(); exportPreset(null)(); };
    $("#bBackups", m).onclick = () => { close(); openBackups(); };
    $("#bImport", m).onclick = async () => {
      close();
      const ow = await conflictChoice("Install a mod preset", "Pick the preset archive next. Its mods are added to your game folder.", "Choose preset");
      if (ow !== null) startTask(await call("install_archive", "preset", ow), installDone);
    };
    $("#bOpenDis", m).onclick = async () => { close(); result(await call("open_game_folder", "Temporarily Disabled Mods")); };
    $("#bRescan", m).onclick = async () => { close(); await refreshMods(true); renderModsTable(); toast("Rescanned.", "ok", 2000); };
  });
  $$("th[data-sort]", el).forEach((th) => (th.onclick = () => {
    const k = th.dataset.sort; S.sort = { key: k, dir: S.sort.key === k ? -S.sort.dir : 1 }; renderModsTable();
  }));
  $("#selAll").onchange = (e) => { visibleMods().forEach((m) => e.target.checked ? S.sel.add(m.key) : S.sel.delete(m.key)); renderModsTable(); };
  renderModsTable();
};
function visibleMods() {
  const f = S.filter, q = f.q.trim().toLowerCase();
  let list = S.mods.filter((m) => {
    if (f.state === "enabled" && !m.enabled) return false;
    if (f.state === "disabled" && m.enabled) return false;
    if (f.state === "updates" && !(m.update && m.update.update && m.enabled)) return false;
    if (f.state === "unlinked" && (m.nexus_id || m.github || m.source === "mo2")) return false;
    if (f.source !== "all" && m.source !== f.source) return false;
    if (f.locs.size && !m.locations.some((l) => f.locs.has(l))) return false;
    if (q) {
      const hay = [m.name, m.nexus_id, m.link?.name, ...m.components.flatMap((c) => c.paths), ...(m.files || [])].join(" ").toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  const k = S.sort.key, d = S.sort.dir;
  const val = (m) => k === "size" ? m.size : k === "nexus" ? (m.update?.update ? 0 : m.nexus_id ? 1 : 2) : String(k === "source" ? SRC[m.source] : m[k] || "").toLowerCase();
  return list.sort((a, b) => (val(a) > val(b) ? 1 : val(a) < val(b) ? -1 : 0) * d || a.name.localeCompare(b.name));
}
function renderModsTable() {
  const tb = $("#modsTable tbody");
  if (!tb) return;
  const f = S.filter, all = S.mods;
  const cnt = (fn) => all.filter(fn).length;
  $("#segState").innerHTML = [["all", "All", all.length], ["enabled", "Enabled", cnt((m) => m.enabled)], ["disabled", "Disabled", cnt((m) => !m.enabled)],
    ["updates", "Updates", cnt((m) => m.update?.update && m.enabled)], ["unlinked", "Not linked", cnt((m) => !m.nexus_id && !m.github && m.source !== "mo2")]].filter((x) => !["updates", "unlinked"].includes(x[0]) || x[2])
    .map(([k, l, n]) => `<button data-k="${k}" class="${f.state === k ? "on" : ""}">${l}<em>${n}</em></button>`).join("");
  const srcs = ["loose", "vortex", "mo2"].filter((s) => cnt((m) => m.source === s));
  $("#segSource").innerHTML = srcs.length > 1 ? [["all", "Any source"], ...srcs.map((s) => [s, SRC[s]])]
    .map(([k, l]) => `<button data-k="${k}" class="${f.source === k ? "on" : ""}">${l}</button>`).join("") : "";
  $("#segSource").style.display = srcs.length > 1 ? "" : "none";
  $$("#segState button").forEach((b) => (b.onclick = () => { f.state = b.dataset.k; renderModsTable(); }));
  $$("#segSource button").forEach((b) => (b.onclick = () => { f.source = b.dataset.k; renderModsTable(); }));
  const locs = Object.keys(LOC).filter((l) => all.some((m) => m.locations.includes(l)));
  $("#locChips").innerHTML = locs.map((l) => `<button class="chip ${f.locs.has(l) ? "on" : ""}" data-l="${l}">${LOC[l]} · ${cnt((m) => m.locations.includes(l))}</button>`).join("");
  $$("#locChips .chip").forEach((c) => (c.onclick = () => { f.locs.has(c.dataset.l) ? f.locs.delete(c.dataset.l) : f.locs.add(c.dataset.l); renderModsTable(); }));
  $$("th[data-sort]").forEach((th) => th.classList.toggle("sorted", th.dataset.sort === S.sort.key));
  if ($("#thName")) $("#thName").textContent = S.sort.key === "name" && S.sort.dir < 0 ? "Mod Name Z to A" : "Mod Name A to Z";

  const list = visibleMods();
  const locked = S.running?.game;
  if (!list.length) {
    tb.innerHTML = `<tr><td colspan="7"><div class="empty">${all.length ? "<b>No mods match these filters</b>Clear the search or pick another filter." :
      "<b>No mods installed yet</b>Use Install mod to add one, or install mods with Vortex or MO2."}</div></td></tr>`;
  } else {
    const view = S.boot.settings.mods_view === "folders" ? "folders" : "mods";
    $$("#segView button").forEach((b) => b.classList.toggle("on", b.dataset.v === view));
    const fileRowHtml = (m, c) => {
      const lock = locked || m.source === "vortex";
      const files = c.is_dir ? [c.paths[0].split("/").pop() + "/"] : c.paths.map((p) => p.split("/").pop()).sort((a, b) => a.length - b.length || a.localeCompare(b));
      const nx = m.nexus_id ? `<span class="muted">#${m.nexus_id}</span>` : m.github ? `<span class="tag">GitHub</span>` : `<span class="muted">Not linked</span>`;
      return `<tr class="row ${c.disabled ? "off" : ""} ${S.sel.has(m.key) ? "sel" : ""}" data-key="${esc(m.key)}">
        <td><label class="check"><input type="checkbox" class="pick" ${S.sel.has(m.key) ? "checked" : ""} aria-label="Select ${esc(m.name)}"></label></td>
        <td><input type="checkbox" class="switch ${m.partial ? "partial" : ""}" ${m.enabled ? "checked" : ""} ${lock ? "disabled" : ""}
          title="${m.source === "vortex" ? "Managed by Vortex. Toggle it in Vortex." : locked ? "Close the game to change mods" : `${m.enabled ? "Disable" : "Enable"} ${m.grouped ? "the whole mod: " + m.name : "this mod"}`}" aria-label="Enable ${esc(m.name)}"></td>
        <td><div class="name">${files.map(esc).join("<br>")}</div>${m.grouped || norm(m.name) !== norm(c.name) ? `<span class="tag" title="This file belongs to ${esc(m.name)}">Part of ${esc(m.name)}</span>` : ""}</td>
        <td><span class="src ${m.source}">${SRC[m.source]}</span></td>
        <td>${esc(m.version || m.link?.version || "")}</td>
        <td>${nx}</td>
        <td class="num">${fmtSize(c.size)}</td></tr>`;
    };
    const rowHtml = (m, loc) => {
      const lock = locked || m.source === "vortex";
      const nx = m.update?.update && m.enabled ? `<span class="upd">Update ${esc(m.update.latest)}</span>` :
        m.nexus_id ? `<span class="muted">#${m.nexus_id}</span>${m.tracked ? `<span class="trk" title="Tracked on Nexus">◆</span>` : ""}${m.github ? ` <span class="tag">GitHub</span>` : ""}`
          : m.github ? `<span class="tag" title="${esc(m.github.repo)}">GitHub</span>` : `<span class="muted">Not linked</span>`;
      return `<tr class="row ${m.enabled ? "" : "off"} ${S.sel.has(m.key) ? "sel" : ""}" data-key="${esc(m.key)}">
        <td><label class="check"><input type="checkbox" class="pick" ${S.sel.has(m.key) ? "checked" : ""} aria-label="Select ${esc(m.name)}"></label></td>
        <td><input type="checkbox" class="switch ${m.partial ? "partial" : ""}" ${m.enabled ? "checked" : ""} ${lock ? "disabled" : ""}
          title="${m.source === "vortex" ? "Managed by Vortex. Toggle it in Vortex." : locked ? "Close the game to change mods" : m.enabled ? "Disable" : "Enable"}" aria-label="Enable ${esc(m.name)}"></td>
        <td><div class="name">${esc(m.name)}${m.grouped ? ` <span class="tag grp" title="${esc(groupTitle(m))}">${m.components.length} parts</span>` : ""}</div>${loc
          ? m.components.filter((c) => c.location === loc).map((c) => `<span class="tag">${esc(c.name)}</span>`).join("")
          : m.locations.map((l) => `<span class="tag">${LOC[l] || l}</span>`).join("")}</td>
        <td><span class="src ${m.source}">${SRC[m.source]}</span></td>
        <td>${esc(m.version || m.link?.version || "")}</td>
        <td>${nx}</td>
        <td class="num">${fmtSize(m.size)}</td></tr>`;
    };
    if (view === "folders") {
      const order = Object.keys(LOC).filter((l) => !f.locs.size || f.locs.has(l));
      const other = list.filter((m) => !m.locations.length);
      tb.innerHTML = order.map((l) => {
        const parts = list.flatMap((m) => m.components.filter((c) => c.location === l).map((c) => [m, c]))
          .sort((a, b) => a[1].name.localeCompare(b[1].name));
        return parts.length ? `<tr class="grouphead"><td colspan="7">${LOC[l]} <span class="muted">${esc(LOC_PATH[l] || "")} · ${plural(parts.length, "item")}</span></td></tr>` + parts.map(([m, c]) => fileRowHtml(m, c)).join("") : "";
      }).join("") + (other.length ? `<tr class="grouphead"><td colspan="7">Mod manager (virtual files) <span class="muted">· ${plural(other.length, "mod")}</span></td></tr>` + other.map((m) => rowHtml(m)).join("") : "");
    } else tb.innerHTML = list.map((m) => rowHtml(m)).join("");
  }
  $$("tr.row", tb).forEach((tr) => {
    const key = tr.dataset.key;
    tr.onclick = (e) => {
      if (e.target.closest(".switch, .check")) return;
      if (e.ctrlKey || e.metaKey) { S.sel.has(key) ? S.sel.delete(key) : S.sel.add(key); renderModsTable(); return; }
      drawerShows(key) ? closeDrawer() : openDrawer(key);   // clicking the same mod again closes its pane
    };
    $(".pick", tr).onchange = (e) => { e.target.checked ? S.sel.add(key) : S.sel.delete(key); renderModsTable(); };
    $(".switch", tr).onchange = async (e) => { await toggleMods([key], e.target.checked); };
  });
  const visKeys = list.map((m) => m.key);
  $("#selAll").checked = visKeys.length > 0 && visKeys.every((k) => S.sel.has(k));
  renderBulk();
}
async function toggleMods(keys, enable) {
  const r = await call("set_mods_enabled", keys, enable);
  result(r);
  await refreshMods();
  renderModsTable();
  if (S.drawerKey) openDrawer(S.drawerKey);
  poll();
}
function renderBulk() {
  const host = $("#bulkHost");
  if (!host) return;
  const keys = [...S.sel].filter((k) => S.mods.some((m) => m.key === k));
  if (!keys.length) { host.innerHTML = ""; return; }
  host.innerHTML = `<div class="bulk"><b>${keys.length} selected</b>
    <button class="btn" id="bkOn">Enable</button><button class="btn" id="bkOff">Disable</button>
    ${keys.length > 1 ? `<button class="btn" id="bkGrp" title="Treat the selected entries as one mod, for example a mod that isn't on Nexus">Group as one mod</button>` : ""}
    <button class="btn" id="bkExp">Export as preset</button><button class="btn" id="bkId">Find on Nexus</button>
    <button class="btn primary" id="bkClr">Clear selection</button></div>`;
  $("#bkOn").onclick = () => toggleMods(keys, true);
  $("#bkOff").onclick = () => toggleMods(keys, false);
  $("#bkExp").onclick = exportPreset(keys);
  if ($("#bkId")) $("#bkId").onclick = () => runIdentify(keys);
  if ($("#bkGrp")) $("#bkGrp").onclick = () => groupSelected(keys);
  $("#bkClr").onclick = () => { S.sel.clear(); renderModsTable(); };
}
function groupSelected(keys) {
  const picked = keys.map((k) => S.mods.find((m) => m.key === k)).filter(Boolean);
  const managed = picked.filter((m) => m.source !== "loose");
  if (managed.length) return toast(`${esc(managed[0].name)} is managed by ${SRC[managed[0].source]}. Only manually installed mods can be grouped.`, "bad", 6000);
  const guess = [...picked].sort((a, b) => b.size - a.size)[0];
  modal(`<h3>Group ${picked.length} entries as one mod</h3>
    <p class="muted">They'll be listed, counted, enabled and disabled as a single mod. Use this for mods that aren't on Nexus, or pieces that weren't grouped automatically. You can ungroup it later from its side pane.</p>
    <div class="files" style="max-height:140px;margin-bottom:12px">${esc(picked.map((m) => m.name).join("\n"))}</div>
    <label for="grpName" class="muted small">Name</label>
    <input type="text" id="grpName" style="width:100%" value="${esc(guess.name)}">
    <div class="btn-row"><button class="btn" data-close>Cancel</button><button class="btn primary" id="grpOk">Group</button></div>`, (m, close) => {
    const go2 = async () => {
      const r = await call("group_mods", keys, $("#grpName", m).value);
      if (!result(r, `Grouped as ${r.name}.`)) return;
      close(); S.sel.clear(); await refreshMods(true); renderModsTable();
    };
    $("#grpOk", m).onclick = go2;
    $("#grpName", m).onkeydown = (e) => { if (e.key === "Enter") go2(); };
    setTimeout(() => $("#grpName", m).select(), 30);
  });
}
function exportPreset(keys) {
  return async () => {
    const fmts = await call("export_formats");
    modal(`<h3>Export mod preset</h3><p class="muted">${keys ? plural(keys.length, "selected mod") : "All enabled mods"} will be packed with a list of what's inside. Install it on another PC with More actions → Install a mod preset.</p>
      <div class="seg" id="fmtSeg">${fmts.map((f, i) => `<button data-f="${f}" class="${i ? "" : "on"}">.${f}</button>`).join("")}</div>
      <div class="btn-row"><button class="btn" data-close>Cancel</button><button class="btn primary" id="expGo">Choose where to save</button></div>`, (m, close) => {
      let fmt = fmts[0];
      $$("#fmtSeg button", m).forEach((b) => (b.onclick = () => { fmt = b.dataset.f; $$("#fmtSeg button", m).forEach((x) => x.classList.toggle("on", x === b)); }));
      $("#expGo", m).onclick = async () => { close(); startTask(await call("export_preset", keys, fmt), (res) => toast(`Exported ${plural(res.mods, "mod")} (${res.files} files) to <b>${esc(res.path)}</b>.`, "ok", 8000)); };
    });
  };
}
async function identifyDone(res) {
  toast(`Matched ${res.identified} of ${res.checked} manual mods to Nexus.`, "ok", 6000);
  await refreshMods(true);
  if (S.page === "mods") renderModsTable(); else go(S.page);
}

/* drawer */
const drawerShows = (k) => S.drawerKey === k && $("#drawer").classList.contains("open");
function closeDrawer() { const d = $("#drawer"); d.classList.remove("open"); d.setAttribute("aria-hidden", "true"); S.drawerKey = null; }
function openDrawer(key) {
  const m = S.mods.find((x) => x.key === key);
  if (!m) return;
  S.drawerKey = key;
  const d = $("#drawer");
  const locked = S.running?.game;
  const signedIn = !!S.boot.nexus.user;
  const files = m.source === "mo2" ? m.files : m.components.flatMap((c) => c.paths.map((p) => `${c.disabled ? "[disabled] " : ""}${p}${c.is_dir ? "/" : ""}`));
  const filesHtml = m.source === "mo2" || m.locations.length < 2 ? `<div class="files">${esc(files.join("\n"))}</div>`
    : m.locations.map((l) => {
      const fl = m.components.filter((c) => c.location === l).flatMap((c) => c.paths.map((p) => `${c.disabled ? "[disabled] " : ""}${p}${c.is_dir ? "/" : ""}`));
      return `<div class="files-h">${LOC[l] || l} <span class="muted">(${fl.length})</span></div><div class="files">${esc(fl.join("\n"))}</div>`;
    }).join("");
  const how = { in_files: "found in the mod's own files", verified: "its files match the Nexus upload", download: "matched to " + (m.link?.archive || "a downloaded archive"),
    name: "matched by name", confirmed: "confirmed by you", manual: "linked by you", installed: "installed by this tool", md5: "matched by file hash" }[m.link?.method] || "";
  const canLink = m.source !== "vortex";
  d.innerHTML = `<button class="close" aria-label="Close">×</button>
    <header><h3>${esc(m.name)}</h3><span class="src ${m.source}">${SRC[m.source]}</span>
      <span class="muted" style="margin-left:8px">${m.enabled ? "Enabled" : m.partial ? "Partly enabled" : "Disabled"}</span></header>
    <div class="body">
      <div id="dHero"></div>
      ${m.source === "vortex" ? `<div class="note">Vortex deployed this mod. Enable, disable or update it in Vortex, otherwise Vortex reports the files as changed outside of it.</div>` : ""}
      ${m.source === "mo2" ? `<div class="note">This mod lives in Mod Organizer 2 and only loads when you start the game through MO2. Toggling it here edits your MO2 profile (MO2 must be closed).</div>` : ""}
      <div class="btn-row">
        ${m.source !== "vortex" ? `<button class="btn ${m.enabled ? "" : "primary"}" id="dToggle" ${locked ? "disabled" : ""}>${m.enabled && !m.partial ? "Disable" : "Enable"}</button>` : ""}
        <button class="btn" id="dOpen">Open folder</button>
        ${m.update?.update && m.enabled ? `<button class="btn primary" id="dUpd">Update to ${esc(m.update.latest)}</button>` : (m.nexus_id && signedIn) || m.github ? `<button class="btn" id="dChk">Check for update</button>` : ""}
      </div>
      ${(() => { const c = (S.culprits || []).find((x) => x.key === m.key && x.errors); return c ? `<div class="note warn drawer-err"><span><b>${plural(c.errors, "error")}</b> in ${esc(c.logs.join(", "))} from the last game session${c.changed_since ? " (changed since, relaunch to check)" : ""}.</span><button class="btn small primary" id="dFix">Fix</button></div>` : ""; })()}
      <h4>Details</h4>
      <dl class="kv">
        <dt>Installed version</dt><dd>${esc(m.version || m.link?.version || m.update?.installed || "Unknown")}${!m.version && !m.link?.version && m.update?.basis === "estimated" ? " <span class='muted'>(estimated from file dates)</span>" : ""}</dd>
        ${m.update ? `<dt>Latest</dt><dd>${esc(m.update.latest || "Unknown")}${m.update.updated ? ` · ${fmtDate(m.update.updated)}` : ""}${m.update.source === "github" ? " (GitHub)" : ""}</dd>` : ""}
        <dt>Installs into</dt><dd>${m.locations.map((l) => LOC[l]).join(", ") || "—"}</dd>
        <dt>Size</dt><dd>${fmtSize(m.size) || "—"}</dd>
      </dl>

      ${canLink ? `<h4>Nexus Mods page</h4>
      ${m.nexus_id ? `<div class="linkbox"><div><b>${esc(m.link?.name || m.update?.nexus_name || "Mod")}</b> <span class="muted">#${m.nexus_id}</span>
          ${how ? `<div class="muted small">Linked because ${esc(how)}</div>` : ""}</div>
          <div class="btn-row"><button class="btn small" id="dPage">Open page</button>${m.source === "loose" ? `<button class="btn small danger" id="dUnlink" title="Remove this link. Automatic matching won't pick this page again.">Not this mod</button>` : ""}</div></div>
        ${signedIn ? `<label class="check"><input type="checkbox" id="dTrack" ${m.tracked ? "checked" : ""}>Track on Nexus</label>` : ""}` : `<p class="muted small" style="margin:0 0 8px">Not linked.</p>`}
      <div class="inline-form"><input type="text" id="dLink" placeholder="Paste a Nexus mod URL or ID" aria-label="Nexus mod URL or ID"><button class="btn" id="dLinkBtn">${m.nexus_id ? "Relink" : "Link"}</button></div>
      ${signedIn ? `<details id="dSearchWrap" ${m.nexus_id ? "" : "open"}><summary class="muted small">Search Nexus</summary><div id="dSearch"></div></details>` : ""}
      ${!m.nexus_id && m.source === "loose" ? `<p class="muted small">Or <button class="link" id="dIdent">find it automatically</button>.</p>` : ""}

      <h4>GitHub</h4>
      ${m.github ? `<div class="linkbox"><div><b>${esc(m.github.repo)}</b><div class="muted small" id="dGhInfo">${m.github.method === "in_files" ? "Linked because it's mentioned in the mod's files" : "Linked by you"}</div></div>
          <div class="btn-row"><button class="btn small" data-url="https://github.com/${esc(m.github.repo)}/releases">Releases</button><button class="btn small danger" id="dGhUnlink">Unlink</button></div></div>`
        : `<div class="inline-form"><input type="text" id="dGh" placeholder="For mods released on GitHub: paste the repository URL" aria-label="GitHub repository URL"><button class="btn" id="dGhBtn">Link</button></div>`}` : ""}

      <h4>Files (${files.length})${m.grouped ? ` <span class="muted small">· ${m.components.length} parts grouped as one mod</span>` : ""}${m.manual_group ? ` <button class="link small" id="dUngroup" title="Split this back into separate entries">Ungroup</button>` : ""}</h4>
      ${filesHtml}
    </div>`;
  d.classList.add("open");
  d.setAttribute("aria-hidden", "false");
  wireCommon(d);
  const refresh = async () => { await refreshMods(); if (S.page === "mods") renderModsTable(); if (S.page === "overview") renderUpdatesPanel(); openDrawer(key); poll(); };
  $(".close", d).onclick = closeDrawer;
  $("#dOpen").onclick = async () => result(await call("open_mod_folder", key));
  if ($("#dToggle")) $("#dToggle").onclick = () => toggleMods([key], !(m.enabled && !m.partial));
  if ($("#dPage")) $("#dPage").onclick = () => call("open_url", `https://www.nexusmods.com/cyberpunk2077/mods/${m.nexus_id}`);
  if ($("#dUpd")) $("#dUpd").onclick = () => doUpdate(key, refresh);
  if ($("#dFix")) $("#dFix").onclick = () => openFix(key);
  if ($("#dUngroup")) $("#dUngroup").onclick = async () => {
    if (!result(await call("ungroup_mod", key), "Ungrouped.")) return;
    closeDrawer(); await refreshMods(true); if ($("#modsTable")) renderModsTable();
  };
  if ($("#dChk")) $("#dChk").onclick = async () => startTask(await call("nexus_check_updates", [key]), refresh);
  if ($("#dUnlink")) $("#dUnlink").onclick = async () => { if (result(await call("nexus_unlink", key), "Link removed.")) refresh(); };
  if ($("#dLinkBtn")) $("#dLinkBtn").onclick = async () => {
    const r = await call("nexus_link", key, $("#dLink").value);
    if (result(r, "Linked to Nexus.")) { refresh(); const chk = await call("nexus_check_updates", [key]); if (chk.ok) startTask(chk, refresh, true); }
  };
  if ($("#dLink")) $("#dLink").onkeydown = (e) => { if (e.key === "Enter") $("#dLinkBtn").click(); };
  if ($("#dSearch")) {
    const mount = () => mountLinkSearch($("#dSearch"), key, m.nexus_id ? "" : niceName(m.name), refresh);
    if ($("#dSearchWrap").open) mount(); else $("#dSearchWrap").addEventListener("toggle", mount, { once: true });
  }
  if ($("#dTrack")) $("#dTrack").onchange = async (e) => { if (result(await call("nexus_track", m.nexus_id, e.target.checked), e.target.checked ? "Tracking on Nexus." : "No longer tracked.")) { await refreshMods(); if (S.page === "mods") renderModsTable(); } };
  if ($("#dIdent")) $("#dIdent").onclick = () => runIdentify([key]);
  if ($("#dGhBtn")) $("#dGhBtn").onclick = async () => {
    const r = await call("github_link", key, $("#dGh").value);
    if (result(r, `Linked to ${r.repo} on GitHub.`)) { await refresh(); const chk = await call("nexus_check_updates", [key]); if (chk.ok) startTask(chk, refresh, true); }
  };
  if ($("#dGhUnlink")) $("#dGhUnlink").onclick = async () => { if (result(await call("github_unlink", key), "GitHub link removed.")) refresh(); };
  if (m.nexus_id || m.github) loadHero(key);
}
async function loadHero(key) {
  const r = await call("mod_details", key);
  if (S.drawerKey !== key || !r.ok) return;
  const host = $("#dHero"), n = r.nexus, g = r.github;
  if (n && n.name) {
    host.innerHTML = `<div class="hero">${n.picture_url ? `<img src="${esc(n.picture_url)}" alt="" class="${n.contains_adult_content ? "adult" : ""}">` : ""}
      <div class="hero-body"><button class="link plain hero-name" id="dNxName" title="Open on Nexus Mods">${esc(n.name)}</button><span class="muted small">by ${esc(n.author || "unknown")} · v${esc(n.version || "?")}${n.endorsement_count != null ? ` · ${Number(n.endorsement_count).toLocaleString()} endorsements` : ""}${n.updated_timestamp ? ` · updated ${fmtDate(n.updated_timestamp)}` : ""}</span>
      <p>${esc((n.summary || "").replace(/<[^>]+>/g, ""))}</p></div></div>`;
    $("#dNxName").onclick = () => call("open_url", `https://www.nexusmods.com/cyberpunk2077/mods/${n.mod_id}`);
  } else if (n && n.error) {
    host.innerHTML = `<p class="muted small">${esc(n.error)}</p>`;
  }
  if (g && $("#dGhInfo")) {
    $("#dGhInfo").textContent = g.error ? g.error : [g.description, g.latest ? `latest release ${g.latest}${g.latest_date ? " · " + fmtDate(g.latest_date) : ""}` : "no releases", g.stars != null ? `★ ${g.stars}` : ""].filter(Boolean).join(" · ");
  }
}

/* ------------------------------------------------------------------ CORE */
RENDER.core = async (el) => {
  const r = await call("get_core");
  if (!result(r)) return;
  const manualOk = ["EquipmentEx", "Redscript", "Cyber Engine Tweaks"];
  el.innerHTML = `<div class="core-list">${r.core.map((c) => `
    <div class="core ${c.installed ? "" : c.disabled ? "disabledc missing" : "missing"}">
      <h3><button class="link plain core-name" data-url="https://www.nexusmods.com/cyberpunk2077/mods/${c.nexus_id}" title="Open ${esc(c.name)} on Nexus Mods">${esc(c.name)}</button></h3><span class="state">${c.installed ? "Installed" : c.disabled ? "Disabled" : "Missing"}</span>
      <p>${esc(c.desc)}</p>
      <div class="ver">${esc(c.version || (c.installed ? "Version unknown" : "—"))}${c.version_source === "manual" ? "<small>entered by you</small>" : ""}
        ${c.update?.update ? `<small style="color:var(--yellow)">${esc(c.update.latest)} available</small>`
          : c.installed && c.update && c.update.update === false ? `<small class="uptodate" title="Checked against Nexus${c.update.latest ? `: latest is ${esc(c.update.latest)}` : ""}">✔ Up to date</small>` : ""}</div>
      <div></div>
      <div class="acts">
        ${c.update?.update ? `<button class="btn small primary" data-coreupd="${esc(c.name)}">Update to ${esc(c.update.latest)}</button>` : ""}
        ${c.installed ? "" : `<button class="btn small primary" data-url="https://www.nexusmods.com/cyberpunk2077/mods/${c.nexus_id}?tab=files">Download</button>`}
        ${c.installed && manualOk.includes(c.name) && c.version_source !== "file" ? `<button class="btn small" data-ver="${esc(c.name)}">Set version</button>` : ""}
      </div>
    </div>`).join("")}</div>
    <div class="panel" style="margin-top:18px"><h2>Disable frameworks for testing</h2>
      <p class="muted" style="max-width:75ch;margin-top:-4px">Moving the frameworks out runs the game close to vanilla, which helps you tell whether a crash comes from mods. Most mods stop working until you enable them again.</p>
      <div class="btn-row"><button class="btn danger" id="coreOff">Disable frameworks</button><button class="btn" id="coreOn">Enable frameworks</button></div></div>`;
  wireCommon(el);
  $$("[data-coreupd]", el).forEach((b) => (b.onclick = () => doUpdate(`core:${b.dataset.coreupd}`, () => RENDER.core(el))));
  $$("[data-ver]", el).forEach((b) => (b.onclick = () => modal(`<h3>${esc(b.dataset.ver)} version</h3>
    <p class="muted">This version can't be read from the files, so it comes from you. Find it on the mod's Nexus page or in its download name.</p>
    <input type="text" id="verIn" style="width:100%" placeholder="For example 1.2.7">
    <div class="btn-row"><button class="btn" data-close>Cancel</button><button class="btn primary" id="verOk">Save version</button></div>`, (m, close) => {
    $("#verOk", m).onclick = async () => { await call("set_manual_version", b.dataset.ver, $("#verIn", m).value); close(); RENDER.core(el); };
  })));
  $("#coreOff").onclick = async () => {
    if (await confirmBox("Disable core frameworks?", "RED4ext, Redscript, CET, ArchiveXL, TweakXL, Codeware and EquipmentEx move to <b>Temporarily Disabled Mods</b>.", "Disable frameworks", true)) {
      result(await call("set_core_enabled", false), "Frameworks disabled."); RENDER.core(el); poll();
    }
  };
  $("#coreOn").onclick = async () => { result(await call("set_core_enabled", true), "Frameworks enabled."); RENDER.core(el); poll(); };
};

/* ------------------------------------------------------------------ LOGS */
RENDER.logs = async (el) => {
  const r = await call("get_logs");
  if (!result(r)) return;
  el.classList.add("fill");
  if (!r.logs.length) { el.innerHTML = `<div class="panel"><div class="empty"><b>No logs yet</b>Logs appear after you launch the game with the frameworks installed.</div></div>`; return; }
  if (!S.logSel || !r.logs.some((l) => l.name === S.logSel)) S.logSel = (r.logs.find((l) => l.errors) || r.logs[0]).name;
  el.innerHTML = `<div id="culprits"></div><div class="logs"><div class="loglist">${r.logs.map((l) => `<button data-n="${esc(l.name)}" class="${l.name === S.logSel ? "on" : ""}">
      ${esc(l.name)}<small>${esc(l.file)} · ${new Date(l.modified * 1000).toLocaleString()}</small>
      <small>${l.errors ? `<span class="e">${plural(l.errors, "error")}</span> ` : ""}${l.warnings ? `<span class="w">${plural(l.warnings, "warning")}</span>` : ""}${!l.errors && !l.warnings ? "Clean" : ""}</small></button>`).join("")}</div>
    <div class="viewer"><div class="vt"><b id="lvName"></b><span class="grow" style="flex:1"></span>
      <label class="check"><input type="checkbox" id="errOnly" ${S.errorsOnly ? "checked" : ""}>Only errors and warnings</label>
      <button class="btn small" id="lvCopy">Copy</button><button class="btn small" id="lvOpen">Open in editor</button></div><pre id="lvText"></pre></div></div>`;
  $$(".loglist button", el).forEach((b) => (b.onclick = () => { S.logSel = b.dataset.n; RENDER.logs(el); }));
  $("#errOnly").onchange = (e) => { S.errorsOnly = e.target.checked; showLog(); };
  let current = null;
  async function showLog() {
    current = current || await call("read_log", S.logSel);
    if (!result(current)) return;
    $("#lvName").textContent = current.name;
    const lines = S.errorsOnly ? current.lines.filter((l) => l.k) : current.lines;
    const pre = $("#lvText");
    pre.innerHTML = lines.length ? lines.map((l) => `<div class="${l.k || ""}">${esc(l.t) || " "}${l.m ? `<button class="lmod" data-k="${esc(l.m)}" title="Show this mod">${esc(l.mn)}</button>` : ""}</div>`).join("") : `<div class="muted">No errors or warnings in this log.</div>`;
    $$(".lmod", pre).forEach((b) => (b.onclick = () => (drawerShows(b.dataset.k) ? closeDrawer() : openDrawer(b.dataset.k))));
    const first = $("div.error", pre); if (first && !S.errorsOnly) first.scrollIntoView({ block: "center" });
  }
  $("#lvOpen").onclick = () => current && call("open_path", current.path);
  $("#lvCopy").onclick = () => {
    if (!current) return;
    const lines = S.errorsOnly ? current.lines.filter((l) => l.k) : current.lines;
    navigator.clipboard.writeText(lines.map((l) => l.t).join("\n"))
      .then(() => toast(S.errorsOnly ? `Copied ${plural(lines.length, "error/warning line")}.` : "Log copied.", "ok", 2500));
  };
  showLog();
  renderCulprits();
};

/* mods named in log errors */
async function loadCulprits() {
  const r = await call("log_culprits");
  S.culprits = r && r.ok ? r.culprits : [];
  renderCulprits(true);
  return S.culprits;
}
async function renderCulprits(cached = false) {
  if (!$("#culprits")) return;
  if (!cached) return loadCulprits();
  const host = $("#culprits");
  const list = (S.culprits || []).filter((c) => c.errors);
  if (!list.length) { host.innerHTML = ""; return; }
  host.innerHTML = `<div class="panel culprits"><h2>Mods named in errors <span class="hint">${plural(list.length, "mod")} · from the last game session</span></h2>
    <div class="crows">${list.map((c) => `<div class="crow" data-k="${esc(c.key)}">
      <button class="link plain cname" title="Show files and details"><b>${esc(c.name)}</b></button>
      <span class="cerr">${plural(c.errors, "error")}</span>${c.warnings ? ` <span class="muted small">${plural(c.warnings, "warning")}</span>` : ""}
      <span class="muted small">in ${esc(c.logs.join(", "))}</span>
      ${!c.enabled ? `<span class="tag">Disabled</span>` : ""}${c.update?.update ? `<span class="tag upd-tag">Update ${esc(c.update.latest)}</span>` : ""}
      ${c.changed_since ? `<span class="tag" title="Its files changed after this log was written. Launch the game again to see if the error is gone.">Changed since: relaunch to check</span>` : ""}
      <button class="btn small ${c.enabled ? "primary" : ""}" data-fix="${esc(c.key)}">Fix</button></div>`).join("")}</div></div>`;
  $$(".crow", host).forEach((row) => {
    const k = row.dataset.k;
    $(".cname", row).onclick = () => (drawerShows(k) ? closeDrawer() : openDrawer(k));
    $("[data-fix]", row).onclick = () => openFix(k);
  });
}
function bugReportText(c) {
  const g = S.boot.game || {};
  return [`${c.name}${c.version ? ` v${c.version}` : ""} shows errors in ${c.logs.join(", ")}.`,
    `Game version: ${g.version || "unknown"}`, "", "Log lines:", ...c.lines.slice(0, 10), "",
    "(Found with Cyberpunk 2077 Mod List Tool)"].join("\n");
}
function openFix(key) {
  const c = (S.culprits || []).find((x) => x.key === key);
  if (!c) return;
  const signed = !!S.boot.nexus.user;
  const u = c.update;
  const again = async () => { await refreshMods(true); await loadCulprits(); if (drawerShows(key)) openDrawer(key); if ((S.culprits || []).some((x) => x.key === key)) openFix(key); };
  let upd;
  if (u?.update) upd = `<button class="btn primary" id="fxUpd">Update to ${esc(u.latest)}</button><p>A newer version is out. Updating is the most likely fix.</p>`;
  else if ((c.nexus_id && signed) || c.github) upd = u ? `<button class="btn" id="fxChk">Check again</button><p>Up to date${u.installed ? ` (${esc(u.installed)})` : ""}, so updating won't fix this.</p>`
    : `<button class="btn primary" id="fxChk">Check for update</button><p>See whether a newer version is available.</p>`;
  else if (c.nexus_id) upd = `<button class="btn" data-go="nexus">Connect Nexus</button><p>Log in to Nexus to check this mod for updates.</p>`;
  else upd = `<button class="btn" id="fxLink">Find it on Nexus</button><p>This mod isn't linked to a Nexus page yet, so updates can't be checked.</p>`;
  const dis = c.source === "vortex" ? `<button class="btn" disabled>Disable mod</button><p>Vortex manages this mod. Disable it in Vortex.</p>`
    : c.enabled ? `<button class="btn danger" id="fxOff">Disable mod</button><p>Turns it off without deleting anything. Its files move to <b>Temporarily Disabled Mods</b>. You can enable it again any time.</p>`
      : `<button class="btn" disabled>Disabled</button><p>Already off. The error is from a session when it was still on.</p>`;
  const bugUrl = c.nexus_id ? `https://www.nexusmods.com/cyberpunk2077/mods/${c.nexus_id}?tab=bugs` : c.github ? `https://github.com/${c.github}/issues` : null;
  const bug = bugUrl ? `<button class="btn" id="fxBug">Report a bug</button><p>Opens the mod's ${c.nexus_id ? "Bugs tab on Nexus" : "GitHub issues"} and copies the error lines and your game version, ready to paste.</p>`
    : `<button class="btn" disabled>Report a bug</button><p>Link the mod to Nexus or GitHub to report it to the author.</p>`;
  modal(`<h3>Fix ${esc(c.name)}</h3>
    <p class="muted">${plural(c.errors, "error")} in ${esc(c.logs.join(", "))}${c.version ? ` · installed ${esc(c.version)}` : ""}.</p>
    ${c.changed_since ? `<div class="note">This mod changed after the log was written. Launch the game again first to see if it's already fixed.</div>` : ""}
    <div class="fix-err"><div class="files" style="max-height:150px;white-space:pre-wrap;word-break:break-word">${esc(c.lines.slice(0, 6).join("\n"))}</div>
      <button class="btn small" id="fxCopy" title="Copy every error line for this mod">Copy errors</button></div>
    <div class="fix-opts"><div>${upd}</div><div>${dis}</div><div>${bug}</div></div>
    <div class="btn-row"><button class="btn" data-close>Close</button></div>`, (m, close) => {
    wireCommon(m);
    $("#fxCopy", m).onclick = () => navigator.clipboard.writeText(c.lines.join("\n"))
      .then(() => toast(`Copied ${plural(c.lines.length, "error line")}.`, "ok", 2500));
    if ($("#fxUpd", m)) $("#fxUpd", m).onclick = () => { close(); doUpdate(key, async () => { await loadCulprits(); if (drawerShows(key)) openDrawer(key); }); };
    if ($("#fxChk", m)) $("#fxChk", m).onclick = async () => { close(); startTask(await call("nexus_check_updates", [key]), again); };
    if ($("#fxLink", m)) $("#fxLink", m).onclick = () => { close(); openDrawer(key); };
    if ($("#fxOff", m)) $("#fxOff", m).onclick = async () => {
      close();
      if (result(await call("set_mods_enabled", [key], false), `${esc(c.name)} disabled. Launch the game to check the error is gone.`)) {
        await refreshMods(true); await loadCulprits(); if (drawerShows(key)) openDrawer(key);
        if ($("#modsTable")) renderModsTable();
      }
    };
    if ($("#fxBug", m)) $("#fxBug", m).onclick = () => {
      const open = () => call("open_url", bugUrl);
      navigator.clipboard.writeText(bugReportText(c)).then(() => { toast("Error details copied. Paste them into the bug report.", "ok", 6000); open(); }, open);
    };
  });
}

/* ------------------------------------------------------------------ NEXUS */
RENDER.nexus = async (el) => {
  const st = await call("nexus_status");
  const u = st.user;
  S.boot.nexus.user = u || null;
  renderUserChip();
  if (!u) {
    el.innerHTML = `<div class="nxh-slot">${nexusHealthBanner()}</div><div class="grid cols-2"><div class="panel"><h2>Connect your Nexus Mods account</h2>
      ${st.error ? `<div class="note warn">${esc(st.error)}</div>` : ""}
      ${S.boot.nexus.sso ? `<p><button class="btn primary" id="sso">Log in with Nexus Mods</button></p><p class="muted">Or use a personal API key instead:</p>` : ""}
      <p class="muted" style="max-width:62ch">Open your Nexus API keys page, copy your <b>Personal API Key</b> and paste it here. It's encrypted with your Windows account and only used to talk to Nexus.</p>
      <div class="inline-form"><input type="password" id="apikey" placeholder="Personal API key" aria-label="Nexus API key" autocomplete="off"><button class="btn primary" id="keyGo">Connect</button></div>
      <p><button class="link" id="keyPage">Open my Nexus API keys page</button></p></div>
      <div class="panel hatch"><h2>What connecting gives you</h2><ul class="alerts">
        <li><span class="dot"></span><span><b>Identify manual installs.</b> Mods you dropped into the game folder are matched to their Nexus pages by file hash.</span></li>
        <li><span class="dot"></span><span><b>Update checks.</b> See which mods and frameworks have newer versions.</span></li>
        <li><span class="dot"></span><span><b>Tracking.</b> Track everything you have installed so Nexus notifies you about updates.</span></li>
        <li><span class="dot"></span><span><b>One-click updates</b> for manual installs with Nexus Premium. Free accounts go to the Files tab.</span></li></ul></div></div>`;
    wireNexusLinks(el);
    $("#keyPage").onclick = () => call("open_url", S.boot.nexus.api_key_page);
    $("#keyGo").onclick = async () => {
      const r = await call("nexus_login_key", $("#apikey").value);
      if (result(r, `Connected as ${r.user?.name}.`)) { S.boot.nexus.user = r.user; renderUserChip(); RENDER.nexus(el); }
    };
    $("#apikey").onkeydown = (e) => { if (e.key === "Enter") $("#keyGo").click(); };
    if ($("#sso")) $("#sso").onclick = async () => startTask(await call("nexus_sso"), (res) => { S.boot.nexus.user = res.user; RENDER.nexus(el); });
    return;
  }
  await refreshMods();
  const ups = S.mods.filter((m) => m.update?.update);
  const unlinked = S.mods.filter((m) => m.source === "loose" && !m.nexus_id && !m.github && (S.boot.settings.queue_include_disabled || m.enabled)).length;
  const checked = S.mods.some((m) => m.update);
  el.innerHTML = `<div class="nxh-slot">${nexusHealthBanner()}</div><div class="grid cols-2">
    <div class="panel"><div class="user">${u.avatar ? `<img src="${esc(u.avatar)}" alt="">` : ""}<div><b>${esc(u.name)}</b>
      ${u.is_premium ? `<span class="pill">Premium</span>` : `<span class="muted">Free account</span>`}</div>
      <button class="btn small" id="logout" style="margin-left:auto">Disconnect</button></div>
      ${st.rate?.daily != null ? `<p class="muted" style="margin:12px 0 0">API requests left today: ${st.rate.daily}</p>` : ""}</div>
    <div class="panel"><h2>Sync</h2><div class="btn-row">
      <button class="btn primary" id="chk">Check for updates</button>
      <button class="btn" id="ident" ${unlinked ? "" : "disabled"}>Find ${plural(unlinked, "unlinked mod")} on Nexus</button>
      <button class="btn" id="trackAll">Track all installed mods</button></div></div></div>
    <div class="panel" style="margin-top:18px"><h2>Updates <span class="hint">${checked ? `${ups.length} available` : "Not checked yet"}</span></h2>
      ${ups.length ? `<ul class="updates">${ups.map((m) => `<li>${m.update.picture ? `<img src="${esc(m.update.picture)}" alt="">` : `<span></span>`}
        <div><b>${esc(m.name)}</b> <span class="src ${m.source}">${SRC[m.source]}</span><div class="v">${esc(m.update.installed || "?")} → <b>${esc(m.update.latest)}</b>${m.update.updated ? ` · ${fmtDate(m.update.updated)}` : ""}</div></div>
        <button class="btn small primary" data-upd="${esc(m.key)}">${m.source === "loose" && u.is_premium ? "Update" : "Get update"}</button></li>`).join("")}</ul>`
      : `<p class="muted">${checked ? "Everything linked to Nexus is up to date." : "Check for updates to compare your installed versions with Nexus."}</p>`}
    </div>
    <div class="panel" style="margin-top:18px" id="sugPanel" hidden></div>
    <div class="panel" style="margin-top:18px"><h2>Where downloads are matched from</h2>
      <p class="muted" style="margin-top:-4px;max-width:80ch">Mods are matched to the archives you downloaded from Nexus. The file names contain the mod ID and version, and the contents are checked against what's installed. Keep your downloads around and matching is exact.</p>
      <div id="dlFolders"></div><button class="btn small" id="dlAdd" style="margin-top:10px">Add a folder</button></div>
    <div class="panel" style="margin-top:18px" id="queuePanel"></div>
    <div class="panel" style="margin-top:18px"><h2>Tracking</h2>
      <label class="check"><input type="checkbox" id="autoTrack" ${S.boot.settings.auto_track ? "checked" : ""}>Track mods on Nexus automatically when they're linked</label>
      <div id="tracked" class="muted" style="margin-top:10px">Loading…</div></div>`;
  wireNexusLinks(el);
  $("#logout").onclick = async () => { await call("nexus_logout"); S.boot.nexus.user = null; renderUserChip(); RENDER.nexus(el); };
  $("#chk").onclick = runUpdateCheck;
  $("#ident").onclick = () => runIdentify(null);
  $("#trackAll").onclick = async () => startTask(await call("nexus_track_installed"), (res) => toast(`Now tracking ${res.tracked} more mod${res.tracked === 1 ? "" : "s"}.`, "ok"));
  $$("[data-upd]", el).forEach((b) => (b.onclick = async () => {
    const r = await call("nexus_update", b.dataset.upd);
    if (r.task) startTask(r, () => { toast("Mod updated.", "ok"); RENDER.nexus(el); }); else result(r);
  }));
  renderSuggestions();
  renderDlFolders();
  $("#dlAdd").onclick = async () => { await call("add_download_folder"); renderDlFolders(); };
  $("#autoTrack").onchange = async (e) => { const r = await call("save_settings", { auto_track: e.target.checked }); if (r.ok) S.boot.settings = r.settings; };
  renderQueue();
  renderTracked();
};

async function renderTracked() {
  const host = $("#tracked"); if (!host) return;
  const t = await call("nexus_tracked");
  if (!t.ok) { host.textContent = t.error; return; }
  const notTr = t.not_tracked, tr = t.tracked;
  host.className = "";
  host.innerHTML = `${notTr.length ? `<div class="upd-strip" style="margin-bottom:8px"><p>${plural(notTr.length, "linked mod")} ${notTr.length === 1 ? "isn't" : "aren't"} tracked on Nexus yet.</p>
      <button class="btn small primary" id="trkAll">Track ${notTr.length === 1 ? "it" : "all " + notTr.length}</button></div>` : `<p class="muted" style="margin:0 0 8px">Every linked mod is tracked.</p>`}
    <details><summary class="muted" style="cursor:pointer">Tracked on Nexus (${tr.length})</summary>
    ${tr.length ? `<table class="table"><tbody>${tr.map((x) => `<tr><td style="width:90px" class="muted">#${x.mod_id}</td>
      <td>${x.name ? esc(x.name) : `<span class="muted">Mod ${x.mod_id}</span>`}${x.installed ? "" : ` <span class="tag">Not installed</span>`}</td>
      <td style="text-align:right;white-space:nowrap"><button class="btn small" data-url="${esc(x.url)}">Open</button> <button class="btn small" data-untrack="${x.mod_id}">Untrack</button></td></tr>`).join("")}</tbody></table>`
      : `<p class="muted">You aren't tracking any Cyberpunk 2077 mods yet.</p>`}</details>`;
  wireCommon(host);
  if ($("#trkAll")) $("#trkAll").onclick = async () => startTask(await call("nexus_track_installed"), (res) => { toast(`Now tracking ${plural(res.tracked, "more mod")}.`, "ok"); refreshMods().then(renderTracked); });
  $$("[data-untrack]", host).forEach((b) => (b.onclick = async () => { if (result(await call("nexus_track", +b.dataset.untrack, false))) b.closest("tr").remove(); }));
}
async function renderQueue() {
  const host = $("#queuePanel"); if (!host) return;
  const sugKeys = new Set(((await call("get_suggestions")).suggestions || []).map((x) => x.key));
  const showDisabled = !!S.boot.settings.queue_include_disabled;
  const q = S.mods.filter((m) => m.source === "loose" && !m.nexus_id && !m.github && !sugKeys.has(m.key) && (showDisabled || m.enabled));
  if (!q.length) { host.hidden = true; return; }
  host.hidden = false;
  const PAGE = 12;
  host.innerHTML = `<h2>Link queue <span class="hint">${plural(q.length, "mod")} not linked</span></h2>
    <p class="muted" style="margin-top:-4px;max-width:80ch">These couldn't be matched automatically. Search Nexus or paste the mod's URL. Each mod you link is checked for updates${S.boot.settings.auto_track ? " and tracked" : ""}.</p>
    <div id="qRows">${q.slice(0, PAGE).map((m) => `<div class="queue-row" data-key="${esc(m.key)}"><div><button class="link plain qname" title="Show files and details"><b>${esc(m.name)}</b></button> ${m.locations.map((l) => `<span class="tag">${LOC[l] || l}</span>`).join("")}${m.enabled ? "" : ` <span class="tag">Disabled</span>`}</div>
      <div class="btn-row"><button class="btn small" data-find>Find on Nexus</button><button class="btn small" data-files>Files</button></div><div class="qs"></div></div>`).join("")}</div>
    ${q.length > PAGE ? `<p class="muted">Showing ${PAGE} of ${q.length}. Linked mods drop off the list. Filter the Mods page by <button class="link" id="qAll">Not linked</button> to see them all.</p>` : ""}`;
  $$(".queue-row", host).forEach((row) => {
    const key = row.dataset.key, m = S.mods.find((x) => x.key === key);
    $("[data-find]", row).onclick = (e) => {
      const host = $(".qs", row), btn = e.currentTarget;
      if (host.childElementCount) { host.innerHTML = ""; btn.textContent = "Find on Nexus"; btn.setAttribute("aria-expanded", "false"); return; }
      mountLinkSearch(host, key, niceName(m.name), () => renderQueue());
      btn.textContent = "Close search"; btn.setAttribute("aria-expanded", "true");
    };
    $("[data-files]", row).onclick = () => openDrawer(key);
    $(".qname", row).onclick = () => (drawerShows(key) ? closeDrawer() : openDrawer(key));
  });
  if ($("#qAll")) $("#qAll").onclick = async () => { S.filter.state = "unlinked"; await go("mods"); };
}
async function renderDlFolders() {
  const r = await call("get_download_folders");
  const host = $("#dlFolders"); if (!host) return;
  host.innerHTML = r.folders.length ? r.folders.map((f) => `<div class="field" style="grid-template-columns:1fr auto;padding:6px 0"><span class="path">${esc(f)}</span>
    ${r.extra.includes(f) ? `<button class="link" data-rmdl="${esc(f)}">Remove</button>` : `<span class="muted">found automatically</span>`}</div>`).join("") : `<p class="muted">No download folders found.</p>`;
  $$("[data-rmdl]", host).forEach((b) => (b.onclick = async () => { await call("remove_download_folder", b.dataset.rmdl); renderDlFolders(); }));
}
async function renderSuggestions() {
  const host = $("#sugPanel"); if (!host) return;
  const r = await call("get_suggestions");
  const list = r.suggestions || [];
  if (!list.length) { host.hidden = true; return; }
  host.hidden = false;
  host.innerHTML = `<h2>Review possible matches <span class="hint">${plural(list.length, "mod")}</span></h2>
    <p class="muted" style="margin-top:-4px">These names are close but not exact. Pick the right Nexus mod, or skip it.</p>
    <div class="upd-rows sug">${list.map((sg) => `<div class="n">${esc(sg.local)}</div>
      <div><select data-sug="${esc(sg.key)}">${sg.options.map((o) => `<option value="${o.mod_id}">${esc(o.name)} (#${o.mod_id})</option>`).join("")}</select></div>
      <div class="d"><button class="link" data-view="${esc(sg.key)}">View</button></div>
      <div class="btn-row" style="flex-wrap:nowrap"><button class="btn small primary" data-ok="${esc(sg.key)}">Link</button><button class="btn small" data-no="${esc(sg.key)}">Not it</button></div>`).join("")}</div>`;
  const sel = (k) => $(`select[data-sug="${CSS.escape(k)}"]`, host);
  $$("[data-view]", host).forEach((b) => (b.onclick = () => call("open_url", `https://www.nexusmods.com/cyberpunk2077/mods/${sel(b.dataset.view).value}`)));
  $$("[data-ok]", host).forEach((b) => (b.onclick = async () => { await call("resolve_suggestion", b.dataset.ok, +sel(b.dataset.ok).value); await refreshMods(); renderSuggestions(); }));
  $$("[data-no]", host).forEach((b) => (b.onclick = async () => { await call("resolve_suggestion", b.dataset.no, null); renderSuggestions(); renderQueue(); }));
}

/* ------------------------------------------------------------------ BROWSE */
S.browse = { kind: "trending", term: "" };
RENDER.browse = async (el) => {
  if (!S.boot.nexus.user) {
    el.innerHTML = `<div class="panel"><div class="empty"><b>Connect Nexus Mods to browse</b>Browsing uses your Nexus account to load mods and files.<br><br>
      <button class="btn primary" data-go="nexus">Connect Nexus Mods</button> <button class="btn" id="bwSite">Open the Nexus website in your browser</button></div></div>`;
    wireCommon(el);
    $("#bwSite").onclick = () => call("open_url", "https://www.nexusmods.com/games/cyberpunk2077/mods");
    return;
  }
  const b = S.browse;
  el.innerHTML = `<div class="nxh-slot">${nexusHealthBanner()}</div><div class="toolbar">
      <div class="seg" id="bwKind">${[["trending", "Trending", "Mods published in the last 7 days, most endorsed first"], ["latest_added", "New", "Newest mods first"],
        ["latest_updated", "Recently updated", "Most recently updated mods first"]]
        .map(([k, l, t]) => `<button data-k="${k}" title="${t}" class="${b.kind === k ? "on" : ""}">${l}</button>`).join("")}</div>
      <div class="search"><input type="search" id="bwQ" placeholder="Search Cyberpunk 2077 mods, or paste a Nexus URL" value="${esc(b.term)}" aria-label="Search Nexus"></div>
      <button class="btn" id="bwSite" title="Opens nexusmods.com in your browser. Mod Manager Download links still install here when that's turned on in Settings.">Open full Nexus site</button>
    </div>
    <div id="bwGrid" class="cards"><p class="muted">Loading…</p></div>
    <div class="more-row"><button class="btn" id="bwMore" hidden>+ Load more</button><span class="muted small" id="bwNote"></span></div>`;
  $$("#bwKind button", el).forEach((x) => (x.onclick = () => { b.kind = x.dataset.k; b.term = ""; RENDER.browse(el); }));
  $("#bwSite").onclick = () => call("open_url", "https://www.nexusmods.com/games/cyberpunk2077/mods");
  let t = null;
  $("#bwQ").oninput = (e) => { clearTimeout(t); t = setTimeout(() => { b.term = e.target.value.trim(); b.kind = b.term ? "search" : "trending"; loadCards(); }, 450); };
  $("#bwQ").onkeydown = (e) => { if (e.key === "Enter") { clearTimeout(t); b.term = e.target.value.trim(); b.kind = b.term ? "search" : "trending"; loadCards(); } };
  loadCards();
};
const PAGE_SIZE = 12;
function cardHtml(m) {
  return `<button class="card" data-id="${m.mod_id}">
      <span class="thumb">${m.picture_url ? `<img src="${esc(m.picture_url)}" alt="" loading="lazy" class="${m.contains_adult_content ? "adult" : ""}">` : ""}
        ${m.installed_key ? `<span class="badge">Installed</span>` : ""}</span>
      <span class="cbody"><b>${esc(m.name)}</b><span class="muted small">by ${esc(m.author || "unknown")}${m.version ? ` · v${esc(m.version)}` : ""}</span>
        <span class="sum">${esc((m.summary || "").replace(/<[^>]+>/g, ""))}</span>
        <span class="meta small">♥ ${Number(m.endorsement_count || 0).toLocaleString()}${m.updated_timestamp ? ` · ${fmtDate(m.updated_timestamp)}` : ""}</span></span></button>`;
}
async function loadCards(append = false) {
  const grid = $("#bwGrid"), b = S.browse, more = $("#bwMore"), note = $("#bwNote");
  if (!grid) return;
  $$("#bwKind button").forEach((x) => x.classList.toggle("on", x.dataset.k === b.kind));
  if (!append) {
    b.offset = 0; b.seen = new Set();
    grid.innerHTML = `<p class="muted">${b.kind === "search" ? `Searching for “${esc(b.term)}”…` : "Loading…"}</p>`;
  }
  more.hidden = true; note.textContent = append ? "Loading…" : "";
  const r = await call("nexus_browse", b.kind, b.term, b.offset, PAGE_SIZE);
  if (!$("#bwGrid")) return;
  note.textContent = "";
  if (!r.ok) { if (!append) grid.innerHTML = `<p class="muted">${esc(r.error)}</p>`; else note.textContent = r.error; return; }
  const fresh = r.mods.filter((m) => !b.seen.has(m.mod_id));
  fresh.forEach((m) => b.seen.add(m.mod_id));
  if (!append) grid.innerHTML = "";
  if (!append && !fresh.length) { grid.innerHTML = `<div class="empty"><b>No mods found</b>Try fewer or different words.</div>`; return; }
  grid.insertAdjacentHTML("beforeend", fresh.map(cardHtml).join(""));
  $$(".card:not([data-wired])", grid).forEach((c) => { c.dataset.wired = 1; c.onclick = () => (drawerShows(`browse:${c.dataset.id}`) ? closeDrawer() : openBrowseDrawer(+c.dataset.id)); });
  b.offset += PAGE_SIZE;
  more.hidden = !r.more;
  more.onclick = () => loadCards(true);
  if (!r.more && b.kind === "trending") note.textContent = "That's every mod published in the last 7 days. Try New or Recently updated for more.";
}
async function openBrowseDrawer(id) {
  S.drawerKey = `browse:${id}`;
  const d = $("#drawer");
  d.innerHTML = `<button class="close" aria-label="Close">×</button><header><h3>Loading…</h3></header>`;
  d.classList.add("open"); d.setAttribute("aria-hidden", "false");
  $(".close", d).onclick = closeDrawer;
  const r = await call("nexus_mod_page", id);
  if (S.drawerKey !== `browse:${id}`) return;
  if (!r.ok) { $("header h3", d).textContent = r.error; return; }
  const m = r.mod;
  d.innerHTML = `<button class="close" aria-label="Close">×</button>
    <header><h3><button class="link plain hero-name" id="bName" title="Open on Nexus Mods">${esc(m.name)}</button></h3><span class="muted">by ${esc(m.author || "unknown")}</span>${r.installed_key ? ` <span class="src loose" style="margin-left:6px">Installed</span>` : ""}</header>
    <div class="body">
      <div class="hero">${m.picture_url ? `<img src="${esc(m.picture_url)}" alt="" class="${m.contains_adult_content ? "adult" : ""}">` : ""}
        <div class="hero-body"><span class="muted small">v${esc(m.version || "?")} · ♥ ${Number(m.endorsement_count || 0).toLocaleString()}${m.updated_timestamp ? ` · updated ${fmtDate(m.updated_timestamp)}` : ""}</span>
        <p>${esc((m.summary || "").replace(/<[^>]+>/g, ""))}</p></div></div>
      <div class="btn-row"><button class="btn" id="bPage">Open on Nexus</button>
        ${r.installed_key ? `<button class="btn" id="bLocal">Show installed mod</button>` : ""}
        <label class="check" style="margin-left:6px"><input type="checkbox" id="bTrack">Track</label></div>
      <h4>Files</h4>
      ${!r.premium && !r.nxm ? `<div class="note">Free accounts install through Nexus's Mod Manager Download button. Turn on <b>Install "Mod Manager Download" files here</b> in Settings and Install will open the file on Nexus for one click.</div>` : ""}
      <div class="flist">${r.files.map((f) => `<div class="frow"><div><b>${esc(f.name)}</b> <span class="tag">${esc((f.category || "").toLowerCase())}</span>
          <div class="muted small">v${esc(f.version || "?")}${f.size_kb ? ` · ${fmtSize(f.size_kb * 1024)}` : ""}${f.uploaded ? ` · ${fmtDate(f.uploaded)}` : ""}</div>
          ${f.description ? `<div class="muted small fdesc">${esc(f.description)}</div>` : ""}</div>
        <button class="btn small ${f.category === "MAIN" ? "primary" : ""}" data-fid="${f.file_id}">${r.premium ? "Install" : "Get"}</button></div>`).join("") || `<p class="muted">No downloadable files.</p>`}</div>
    </div>`;
  $(".close", d).onclick = closeDrawer;
  $("#bPage").onclick = () => call("open_url", m.url);
  $("#bName").onclick = () => call("open_url", m.url);
  if ($("#bLocal")) $("#bLocal").onclick = async () => { await go("mods"); openDrawer(r.installed_key); };
  const tr = $("#bTrack");
  tr.checked = !!S.mods.find((x) => x.nexus_id === id && x.tracked);
  tr.onchange = async (e) => result(await call("nexus_track", id, e.target.checked), e.target.checked ? "Tracking on Nexus." : "No longer tracked.");
  $$("[data-fid]", d).forEach((b) => (b.onclick = async () => {
    const res = await call("nexus_install", id, +b.dataset.fid);
    if (res.task) return startTask(res, async (out) => { toast(`Installed <b>${esc(out.name)}</b>${out.version ? ` ${esc(out.version)}` : ""}.`, "ok", 7000); await refreshMods(true); poll(); openBrowseDrawer(id); });
    if (res.needs_nxm) return doUpdateNxmPrompt(res.note);
    result(res);
  }));
}
function doUpdateNxmPrompt(note) {
  modal(`<h3>Install from the website</h3><p>${esc(note || "")}</p>
    <p class="muted">Turn on Mod Manager Download handling and the button on Nexus installs the file here. Links for other games still go to the app that handled them before.</p>
    <div class="btn-row"><button class="btn" data-close>Not now</button><button class="btn primary" id="nxmOn2">Turn it on</button></div>`,
    (mm, close) => { $("#nxmOn2", mm).onclick = async () => { close(); result(await call("nxm_set", true), "Mod Manager Downloads will install here."); }; });
}

/* ------------------------------------------------------------------ SETTINGS */
RENDER.settings = async (el) => {
  const boot = await call("bootstrap");
  S.boot = boot;
  const s = boot.settings, g = boot.game, mg = boot.managers;
  const cands = (await call("detect_game_dirs")) || [];
  const mo2 = mg.mo2;
  const nx = await call("nxm_status");
  el.innerHTML = `<div class="panel"><h2>Game</h2>
      <div class="field"><label>Game folder</label><div class="stack"><span class="path">${g.valid ? esc(g.dir) : "Not set"}</span>
        <div class="btn-row"><button class="btn" id="pickDir">Change folder</button>${g.valid ? `<button class="btn" id="openDir">Open folder</button>` : ""}</div>
        ${cands.filter((c) => c.path.toLowerCase() !== (g.dir || "").toLowerCase()).map((c) => `<button class="link" data-cand="${esc(c.path)}">Use the ${esc(c.store)} install at ${esc(c.path)}</button>`).join("")}</div></div>
      <div class="field"><label for="launchVia">Launch game through</label><select id="launchVia">
        <option value="auto">Cyberpunk2077.exe (through MO2 when you use MO2)</option>
        <option value="exe">Cyberpunk2077.exe, always</option><option value="store">Steam client</option>${mo2 ? `<option value="mo2">Mod Organizer 2</option>` : ""}</select></div>
    </div>
    <div class="panel" style="margin-top:18px"><h2>Mod managers</h2>
      <div class="field"><label for="mgrMode">Read mods from</label><select id="mgrMode">
        <option value="auto">Vortex and MO2, when found</option><option value="vortex">Vortex only</option><option value="mo2">MO2 only</option><option value="none">Game folder only</option></select></div>
      <div class="field"><label>Vortex</label><div>${mg.vortex.detected ? `Found ${mg.vortex.files} deployed files. Vortex mods are shown with their Vortex names and Nexus IDs, and stay under Vortex's control.`
        : mg.vortex.installed ? "Vortex is installed but hasn't deployed mods to this game folder." : "Not detected."}</div></div>
      <div class="field"><label>Mod Organizer 2</label><div class="stack">
        ${mo2 ? `<span class="path">${esc(mo2.path)}</span>` : `<span class="muted">${mg.mo2_candidates.length ? "An instance was found but it points at a different game folder." : "No instance found."}</span>`}
        <div class="btn-row"><button class="btn" id="pickMo2">${mo2 ? "Change instance" : "Choose MO2 instance"}</button>${s.mo2_instance ? `<button class="btn" id="clrMo2">Use automatic detection</button>` : ""}</div></div></div>
      ${mo2 ? `<div class="field"><label for="mo2Prof">MO2 profile</label><select id="mo2Prof">${mo2.profiles.map((p) => `<option ${p === mo2.profile ? "selected" : ""}>${esc(p)}</option>`).join("")}</select></div>
      <div class="field"><label for="mo2Exe">MO2 launches</label><select id="mo2Exe">${mo2.executables.map((x) => `<option ${x.title === (s.mo2_executable || mo2.default_executable) ? "selected" : ""}>${esc(x.title)}</option>`).join("")}</select></div>` : ""}
    </div>
    <div class="panel" style="margin-top:18px"><h2>Mod list file</h2>
      <div class="field"><label>Save to</label><div class="stack"><span class="path">${esc(s.output_dir_effective)}</span><button class="btn" id="pickOut">Change folder</button></div></div>
      <div class="field"><label>Options</label><div>
        <label class="check"><input type="checkbox" data-opt="ask_report_path" ${s.ask_report_path ? "checked" : ""}>Ask for a file name and location each time</label>
        <label class="check"><input type="checkbox" data-opt="auto_open_output" ${s.auto_open_output ? "checked" : ""}>Open the file after it's created</label>
        <label class="check"><input type="checkbox" data-opt="auto_select_all_logs" ${s.auto_select_all_logs ? "checked" : ""}>Include every log by default</label>
        <label class="check"><input type="checkbox" data-opt="include_errors_in_output" ${s.include_errors_in_output ? "checked" : ""}>List log errors at the top</label>
        <label class="check"><input type="checkbox" data-opt="include_grouped_in_output" ${s.include_grouped_in_output !== false ? "checked" : ""}>Include the "Installed Mods" section (each mod with its source, version and Nexus link)</label>
        <label class="check"><input type="checkbox" data-opt="include_disabled_in_output" ${s.include_disabled_in_output ? "checked" : ""}>Include disabled mods</label></div></div>
    </div>
    <div class="panel" style="margin-top:18px"><h2>Backups</h2>
      <p class="muted" style="margin-top:-4px;max-width:85ch">Full backups of your manually installed mods and core frameworks. Vortex and MO2 keep their own copies, so their mods aren't included.</p>
      <div id="setBackups"><p class="muted">Loading backups…</p></div>
      <h3 class="sub-h">Replaced files</h3>
      <p class="muted" style="max-width:85ch">Updating a mod replaces its files in the game folder, so only the new version loads. The old files are moved to
        <b>Temporarily Disabled Mods\\_Backups (replaced files)</b>, which the game never loads, so you can roll back if an update breaks something.
        Only the most recent updates are kept, and older copies are deleted automatically.</p>
      <div class="field"><label for="repKeep">Keep old files from</label><select id="repKeep">
        <option value="1">The last update only</option><option value="3">The last 3 updates</option><option value="10">The last 10 updates</option>
        <option value="-1">Every update (never delete)</option><option value="0">None (Delete old files when updating)</option></select></div>
      <div class="upd-strip"><p id="bkInfo">Checking…</p><button class="btn small" id="bkOpen">Open folder</button><button class="btn small danger" id="bkClear">Delete replaced files</button></div>
    </div>
    <div class="panel" style="margin-top:18px"><h2>Linking mods to Nexus</h2>
      <div class="field"><label>Link queue</label><div>
        <label class="check"><input type="checkbox" data-opt="queue_include_disabled" ${s.queue_include_disabled ? "checked" : ""}>Show disabled mods in the link queue</label></div></div>
      <div class="field"><label>Mod file grouping</label><div class="stack">
        <label class="check"><input type="checkbox" data-opt="group_mod_files" ${s.group_mod_files !== false ? "checked" : ""}>Group files that belong to the same Nexus mod into one entry</label>
        <span class="muted">For example, Appearance Menu Mod's CET folder and its archive files are listed and counted as one mod. Files you installed together from one archive with Install mod are always grouped.</span></div></div>
    </div>
    <div class="panel" style="margin-top:18px"><h2>Nexus downloads</h2>
      <div class="field"><label>Mod Manager Download</label><div class="stack">
        <label class="check"><input type="checkbox" id="nxmToggle" ${nx.registered ? "checked" : ""}>Install "Mod Manager Download" files for Cyberpunk 2077 here</label>
        <span class="muted">${nx.registered ? (nx.previous ? "Links for other games are passed to the app that handled them before." : "") : nx.owner ? `Currently handled by ${esc(nx.owner)}. Turning this on keeps forwarding other games' links to it.` : "Lets free Nexus accounts update mods with one click from the website."}</span></div></div>
    </div>
    <div class="panel" style="margin-top:18px"><h2>About</h2>
      <p>Cyberpunk 2077 Mod List Tool ${esc(boot.app.version)} by Sammmy1036. <button class="link" data-url="${esc(boot.app.nexus_page)}">Nexus page</button> · <button class="link" id="dbgLog">Open debug log</button></p>
      <p class="muted" style="max-width:85ch">Unofficial fan-made tool, not affiliated with or endorsed by CD PROJEKT S.A. Cyberpunk 2077 is a trademark of CD PROJEKT S.A. Back up your game before disabling frameworks or importing presets. Released under the MIT License.</p></div>`;
  $("#launchVia").value = s.launch_via;
  $("#mgrMode").value = s.manager_mode;
  wireCommon(el);
  $("#pickDir").onclick = pickGameDir;
  renderSettingsBackups();
  const bk = await call("backups_info");
  $("#repKeep").value = String(s.replaced_keep ?? 1);
  $("#repKeep").onchange = async (e) => { const r = await call("save_settings", { replaced_keep: +e.target.value }); if (r.ok) { S.boot.settings = r.settings; toast("Saved.", "ok", 1500); RENDER.settings(el); } };
  $("#bkInfo").textContent = bk.files ? `${plural(bk.files, "file")} from ${plural(bk.sets, "install")}, ${fmtSize(bk.size)}.` : "Nothing has been replaced yet.";
  $("#bkOpen").disabled = $("#bkClear").disabled = !bk.files;
  $("#bkOpen").onclick = async () => result(await call("open_backups"));
  $("#bkClear").onclick = async () => {
    if (await confirmBox("Delete replaced files?", `This permanently deletes ${plural(bk.files, "replaced file")} (${fmtSize(bk.size)}). Installed mods aren't affected, but you won't be able to roll back earlier updates.`, "Delete replaced files", true)) {
      if (result(await call("clear_backups"), "Replaced files deleted.")) RENDER.settings(el);
    }
  };
  $("#nxmToggle").onchange = async (e) => { result(await call("nxm_set", e.target.checked), e.target.checked ? "Mod Manager Downloads will install here." : "Restored the previous link handler."); RENDER.settings(el); };
  $("#dbgLog").onclick = async () => result(await call("open_debug_log"));
  if ($("#openDir")) $("#openDir").onclick = () => call("open_game_folder", "");
  $$("[data-cand]", el).forEach((b) => (b.onclick = async () => { const r = await call("set_game_dir", b.dataset.cand); if (result(r, "Game folder set.")) { S.boot.game = r.game; RENDER.settings(el); } }));
  const save = async (vals) => { const r = await call("save_settings", vals); if (r.ok) { S.boot.settings = r.settings; toast("Saved.", "ok", 1500); } };
  $("#launchVia").onchange = async (e) => { await save({ launch_via: e.target.value }); poll(); };
  $("#mgrMode").onchange = async (e) => { await save({ manager_mode: e.target.value }); RENDER.settings(el); };
  $$("[data-opt]", el).forEach((c) => (c.onchange = () => save({ [c.dataset.opt]: c.checked })));
  $("#pickOut").onclick = async () => { const r = await call("browse_output_dir"); if (r.ok) RENDER.settings(el); };
  $("#pickMo2").onclick = async () => { const r = await call("browse_mo2_instance"); if (result(r, "MO2 instance set.")) RENDER.settings(el); };
  if ($("#clrMo2")) $("#clrMo2").onclick = async () => { await call("clear_mo2_instance"); RENDER.settings(el); };
  if ($("#mo2Prof")) $("#mo2Prof").onchange = (e) => save({ mo2_profile: e.target.value });
  if ($("#mo2Exe")) $("#mo2Exe").onchange = (e) => save({ mo2_executable: e.target.value });
};

/* ------------------------------------------------------------------ boot */
async function start() {
  const msg = (t) => { const m = $("#splashMsg"); if (m) m.textContent = t; };
  msg("Starting up…");
  await loadLogo();                 // first, so the loading screen shows the logo
  msg("Connecting…");
  S.boot = await call("bootstrap");
  msg("Loading your profile…");
  await Promise.all([loadGameIcon(), preloadImage(S.boot.nexus?.user?.avatar)]);
  renderUserChip();
  $("#userChip").onclick = () => go("nexus");
  $("#appVersion").textContent = `v${S.boot.app.version}`;
  $("#sbNexusPage").onclick = (e) => { e.preventDefault(); call("open_url", S.boot.app.nexus_page); };
  $$(".nav").forEach((b) => (b.onclick = () => {
    if (b.dataset.page === S.page) { closeDrawer(); return; }   // already here: no reload, no Nexus requests
    go(b.dataset.page);
  }));
  $("#launchBtn").onclick = async () => {
    const r = await call("launch_game");
    if (result(r)) { toast(`Launching Cyberpunk 2077 through ${esc(r.via)}.`, "ok", 3000); applyRunning({ launching: true }); }
  };
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { if (!$("#modal").hidden) { $("#modal").hidden = true; $("#modal").innerHTML = ""; } else closeDrawer(); }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "f" && S.page === "mods") { e.preventDefault(); $("#q")?.focus(); }
  });
  if (S.boot.game.valid) { msg("Reading your mods…"); await refreshMods(); }
  await go(S.boot.game.valid ? "overview" : "settings");
  if (S.boot.game.valid) loadCulprits();   // lets the mod side pane offer Fix on any page
  $("#splash").classList.add("done");
  setTimeout(() => $("#splash")?.remove(), 400);
  poll();
  setInterval(poll, 5000);
  setInterval(pollRunning, 1500);
}
if (typeof window.pywebview?.api?.bootstrap === "function") start();
else window.addEventListener("pywebviewready", start, { once: true });
