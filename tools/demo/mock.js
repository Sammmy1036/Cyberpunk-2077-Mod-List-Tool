/* Demo backend: stands in for the Python API (window.pywebview.api) with sample data.
   Everything here is fictional: mod names, authors, IDs and versions are made up for the demo. */
"use strict";
(() => {
  const now = Math.floor(Date.now() / 1000), day = 86400;
  const pic = (title, hue) => "data:image/svg+xml;utf8," + encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
     <stop offset="0" stop-color="hsl(${hue},70%,22%)"/><stop offset="1" stop-color="hsl(${(hue + 60) % 360},80%,8%)"/></linearGradient></defs>
     <rect width="320" height="180" fill="url(#g)"/>
     <g stroke="hsl(${hue},90%,60%)" stroke-width="2" fill="none" opacity=".5"><path d="M0 140 H90 L120 110 H210 L240 140 H320"/><path d="M40 0 V60 L70 90"/></g>
     <rect x="18" y="18" width="6" height="40" fill="#FCEE0A"/>
     <text x="34" y="44" font-family="Arial Narrow, Arial" font-weight="700" font-size="22" fill="#fff">${title.replace(/&/g, "&amp;")}</text></svg>`);

  const C = (location, name, paths, is_dir = true, disabled = false) => ({ location, name, is_dir, disabled, paths });
  const mods = [
    { key: "loose:neonnightsweather", name: "NeonNightsWeather", nexus_id: 90011, version: "3.2.0", enabled: true,
      components: [C("archive", "NeonNightsWeather", ["archive/pc/mod/NeonNightsWeather.archive", "archive/pc/mod/NeonNightsWeather.archive.xl"], false), C("tweak", "NeonNightsWeather", ["r6/tweaks/NeonNightsWeather"])],
      size: 412e6, link: { mod_id: 90011, name: "Neon Nights Weather Overhaul", method: "in_files" }, tracked: true },
    { key: "loose:minimalhud", name: "MinimalHUD", nexus_id: 90022, version: "1.4.1", enabled: true,
      components: [C("redscript", "MinimalHUD", ["r6/scripts/MinimalHUD/HUDCore.reds", "r6/scripts/MinimalHUD/HUDConfig.reds"], false), C("archive", "MinimalHUD", ["archive/pc/mod/MinimalHUD.archive"], false)],
      size: 3.1e6, link: { mod_id: 90022, name: "Minimal HUD", method: "download", archive: "Minimal HUD-90022-1-4-1-1760000000.zip" }, tracked: true,
      update: { mod_id: 90022, latest: "1.5.0", installed: "1.4.1", basis: "exact", update: true, updated: now - 2 * day, nexus_name: "Minimal HUD" },
      files: ["r6/scripts/MinimalHUD/HUDCore.reds", "r6/scripts/MinimalHUD/HUDConfig.reds", "archive/pc/mod/MinimalHUD.archive"] },
    { key: "loose:ripperdocexpanded", name: "RipperdocExpanded", nexus_id: 90033, enabled: true,
      components: [C("archive", "RipperdocExpanded", ["archive/pc/mod/RipperdocExpanded.archive", "archive/pc/mod/RipperdocExpanded.xl"], false), C("redscript", "RipperdocExpanded", ["r6/scripts/RipperdocExpanded"]), C("tweak", "RipperdocExpanded", ["r6/tweaks/RipperdocExpanded.yaml"], false)],
      size: 58e6, link: { mod_id: 90033, name: "Ripperdoc Expanded", method: "verified", version: "2.0.3" }, tracked: true,
      update: { mod_id: 90033, latest: "2.1.0", installed: "2.0.3", basis: "estimated", update: true, updated: now - 5 * day, nexus_name: "Ripperdoc Expanded" } },
    { key: "loose:afterlifeboothsunlocked", name: "AfterlifeBoothsUnlocked", nexus_id: 90044, version: "1.0.2", enabled: true,
      components: [C("archive", "AfterlifeBoothsUnlocked", ["archive/pc/mod/AfterlifeBoothsUnlocked.archive", "archive/pc/mod/AfterlifeBoothsUnlocked.archive.xl"], false)],
      size: 9.4e6, link: { mod_id: 90044, name: "Afterlife Booths Unlocked", method: "name" }, tracked: false },
    { key: "loose:photomodeextras", name: "PhotoModeExtras", nexus_id: 90055, version: "4.0.0", enabled: true,
      components: [C("cet", "PhotoModeExtras", ["bin/x64/plugins/cyber_engine_tweaks/mods/PhotoModeExtras"]), C("archive", "PhotoModeExtras", ["archive/pc/mod/PhotoModeExtras.archive"], false)],
      size: 22e6, link: { mod_id: 90055, name: "Photo Mode Extras", method: "in_files" }, tracked: true },
    { key: "loose:nightcitytraffic", name: "NightCityTrafficPlus", nexus_id: 90066, enabled: true,
      components: [C("tweak", "NightCityTrafficPlus", ["r6/tweaks/NightCityTrafficPlus"]), C("redscript", "NightCityTrafficPlus", ["r6/scripts/NightCityTrafficPlus"])],
      size: 1.2e6, link: { mod_id: 90066, name: "Night City Traffic+", method: "verified", version: "1.9" }, tracked: true },
    { key: "loose:hotreloadtools", name: "HotReloadTools", enabled: true, version: "1.3.0",
      components: [C("red4ext", "HotReloadTools", ["red4ext/plugins/HotReloadTools"])], size: 2.4e6,
      github: { repo: "example/cp2077-hot-reload-tools", method: "in_files" } },
    { key: "loose:betterscopes", name: "BetterScopes", enabled: true,
      components: [C("archive", "BetterScopes", ["archive/pc/mod/#BetterScopes.archive", "archive/pc/mod/#BetterScopes.archive.xl"], false)], size: 31e6 },
    { key: "loose:cozyapartmentlights", name: "cozyapartmentlights", enabled: true,
      components: [C("archive", "cozyapartmentlights", ["archive/pc/mod/cozyapartmentlights.archive"], false)], size: 4.8e6 },
    { key: "loose:oldradiopack", name: "OldRadioPack", enabled: false,
      components: [C("redmod", "OldRadioPack", ["mods/OldRadioPack"], true, true)], size: 120e6 },
    { key: "vortex:streetvendors", name: "Street Vendors Reborn", source: "vortex", nexus_id: 90077, version: "2.2.0", enabled: true, manager_ref: "Street Vendors Reborn-90077-2-2-0-1760000000",
      components: [C("archive", "StreetVendors", ["archive/pc/mod/StreetVendors.archive"], false), C("cet", "StreetVendors", ["bin/x64/plugins/cyber_engine_tweaks/mods/StreetVendors"])], size: 64e6, tracked: true },
  ];
  for (const m of mods) {
    m.source = m.source || "loose"; m.partial = false; m.github = m.github || null; m.link = m.link || null; m.update = m.update || null;
    m.tracked = m.tracked ?? null; m.locations = [...new Set(m.components.map((c) => c.location))].sort();
    m.files = m.files || m.components.flatMap((c) => c.paths); m.file_count = m.files.length;
  }
  const byKey = (k) => mods.find((m) => m.key === k);

  const core = [
    ["RED4ext", 2380, "1.27.0", "Native plugin loader required by ArchiveXL, TweakXL and Codeware."],
    ["Redscript", 1511, "0.5.28", "Script compiler for .reds mods."],
    ["Cyber Engine Tweaks", 107, "1.35.1", "Lua scripting framework and in-game overlay."],
    ["ArchiveXL", 4198, "1.24.3", "Loads custom resources, appearances and world edits."],
    ["TweakXL", 4197, "1.10.8", "Loads TweakDB edits from r6/tweaks."],
    ["Codeware", 7780, "1.17.0", "Redscript library many UI and gameplay mods depend on."],
    ["EquipmentEx", 6945, "1.2.9", "Outfit system used by many clothing mods."],
  ].map(([name, nexus_id, version, desc]) => ({ name, nexus_id, version, desc, installed: true, disabled: false, version_source: "file", update: null }));

  const LOG_OK = {
    "RED4ext": ["[info] RED4ext (v1.27.0) is initializing...", "[info] Loading plugins...", "[info] ArchiveXL loaded", "[info] TweakXL loaded", "[info] Codeware loaded", "[info] HotReloadTools loaded", "[info] 4 plugins loaded"],
    "ArchiveXL": ["[info] ArchiveXL 1.24.3 is initializing...", "[info] Scanning archives...", "[info] NeonNightsWeather.archive.xl: 12 resources registered", "[info] AfterlifeBoothsUnlocked.archive.xl: 3 world edits applied"],
    "Cyber Engine Tweaks": ["[info] CET version v1.35.1", "[info] Loaded mod PhotoModeExtras", "[info] Loaded mod StreetVendors"],
  };
  const REDSCRIPT_OK = ["INFO - redscript compiler v0.5.28", "INFO - Using defaults for the script manifest", "INFO - Compiling 214 files", "INFO - Output successfully saved"];
  const REDSCRIPT_ERR = ["INFO - redscript compiler v0.5.28", "INFO - Using defaults for the script manifest", "INFO - Compiling 214 files",
    "ERROR - At r6/scripts/MinimalHUD/HUDCore.reds:42:12:",
    "ERROR -     let health = player.GetPlayerHealth();",
    "ERROR - Function 'GetPlayerHealth' not found on 'PlayerPuppet' (the game's update renamed it)",
    "WARN - r6/scripts/NightCityTrafficPlus/Spawner.reds:88:4: unused variable 'density'",
    "ERROR - Compilation failed. Scripts were not updated."];

  const D = window.DEMO = {
    running: false, launching: false, broken: false, nexus: true, updatesChecked: now - 300, tasks: {}, seq: 0,
    settings: { auto_open_output: false, auto_select_all_logs: true, include_errors_in_output: true, include_disabled_in_output: false,
      include_grouped_in_output: true, ask_report_path: false, queue_include_disabled: false, output_dir: "", output_dir_effective: "C:\\Users\\You\\Documents",
      manager_mode: "auto", launch_via: "auto", auto_track: true, mo2_instance: "", mo2_profile: "", mo2_executable: "", game_dir: "D:\\Games\\Cyberpunk 2077" },
    reportPath: "C:\\Users\\You\\Documents\\Cyberpunk 2077 Mod List.txt",
    breakGame() { D.broken = true; D.running = true; },
    note(msg) { window.cp && window.cpDemoToast ? window.cpDemoToast(msg) : null; },
  };
  const ok = (x = {}) => Promise.resolve({ ok: true, ...x });
  const later = (v, ms = 120) => new Promise((r) => setTimeout(() => r(v), ms));

  function logs() {
    const out = Object.entries(LOG_OK).map(([name, lines]) => ({ name, lines }));
    out.push({ name: "Redscript", lines: D.broken ? REDSCRIPT_ERR : REDSCRIPT_OK });
    return out.map((l) => {
      const k = l.lines.map((t) => (/^ERROR\b|\[error\]/i.test(t) ? "error" : /^WARN\b|\[warn/i.test(t) ? "warning" : null));
      return { ...l, kinds: k, errors: k.filter((x) => x === "error").length, warnings: k.filter((x) => x === "warning").length };
    });
  }
  function summary() {
    return { total: mods.length, enabled: mods.filter((m) => m.enabled).length, disabled: mods.filter((m) => !m.enabled).length,
      loose: mods.filter((m) => m.source === "loose").length, vortex: mods.filter((m) => m.source === "vortex").length, mo2: 0,
      updates: mods.filter((m) => m.enabled && m.update?.update).length };
  }
  D.backups = [
    { path: "demo-1", name: "a", created: now - 2 * day - 3600 * 5, size: 398e6, kind: "scheduled", mods: 9, files: 209 },
    { path: "demo-2", name: "b", created: now - 9 * day - 3600 * 2, size: 371e6, kind: "manual", mods: 8, files: 188 },
  ];
  function startTask(name, ms, result, steps) {
    const id = "t" + (++D.seq);
    D.tasks[id] = { id, name, t0: Date.now(), ms, result, steps: steps || [] };
    return { ok: true, task: id, name };
  }
  function reportText() {
    const L = logs(), red = L.find((l) => l.name === "Redscript");
    const errs = red.lines.filter((_, i) => red.kinds[i] === "error");
    const rule = "-".repeat(100);
    return [
      "Cyberpunk 2077 Mod List Tool v3.0.0 by Sammmy1036",
      "Nexus Mod Page https://www.nexusmods.com/cyberpunk2077/mods/20113",
      `List created on ${new Date().toLocaleString()}`,
      "Game Version: 2.3.1.0 | Store: Steam | Phantom Liberty DLC Installed: Yes",
      "All Core Mods Installed: Yes",
      `Total Mods Installed: ${summary().enabled} enabled, ${summary().disabled} disabled`, rule, "",
      "Core Frameworks", rule, ...core.map((c) => `${c.name.padEnd(22)} Installed  ${c.version}`), rule,
      ...(errs.length ? ["", "Potential Errors to Review", "=".repeat(100), "", `Redscript (${errs.length}):`, rule, ...errs, "=".repeat(100)] : []),
      "", `Installed Mods (${summary().enabled})`, rule,
      ...mods.filter((m) => m.enabled).map((m) => [m.name, m.version ? "v" + m.version : "", `[${{ loose: "Manual", vortex: "Vortex" }[m.source]}]`,
        `(${m.locations.join(", ")})`, m.nexus_id ? `https://www.nexusmods.com/cyberpunk2077/mods/${m.nexus_id}` : ""].filter(Boolean).join("  ")),
      rule, "", "Redscript Log:", rule, ...red.lines, rule,
    ].join("\n");
  }

  const nexusPool = [
    [90101, "Corpo Plaza Night Lights", "Warmer lighting around the plaza at night."], [90102, "Pacifica Boardwalk Revival", "Adds vendors and life to the boardwalk."],
    [90103, "Better Car Radio UI", "Cleaner radio station list with logos."], [90104, "Vehicle Paint Studio", "Repaint any car in a garage menu."],
    [90105, "Rainy Night City LUT", "Moody, filmic colour grading for rain."], [90106, "Quick Hack Hotkeys", "Bind your favourite quickhacks to keys."],
    [90107, "Apartment Decor Pack", "Furniture and props for V's apartments."], [90108, "Netrunner Suits Collection", "Twelve new netrunner outfits."],
    [90109, "Smarter Police AI", "Police respond more believably."], [90110, "Megabuilding Elevator Music", "Replaces elevator music with new tracks."],
    [90111, "Street Food Overhaul", "Every food stall gets a real menu."], [90112, "Dynamic Crowds", "Crowd density that follows time of day."],
    [90113, "Rockerboy Guitar Sounds", "New guitar audio set."], [90114, "Badlands Wind Storms", "Rare dust storms in the Badlands."],
    [90115, "Better Map Markers", "Clearer icons on the world map."], [90116, "Cyberdeck Rebalance", "Rebalanced RAM and cooldowns."],
    [90117, "Neon Signs Restored", "Brings back broken neon signs."], [90118, "Kabuki Market Stalls", "More stalls and NPC vendors."],
    [90119, "Ambulance Siren Pack", "New siren audio."], [90120, "Hidden Gems Map", "Marks hidden locations on the map."],
    [90121, "Bike Lean Physics", "More natural motorcycle lean."], [90122, "Wardrobe Presets", "Save and load outfit presets."],
    [90123, "Photo Mode Poses Pack", "120 new poses."], [90124, "Afterlife Music Rework", "New tracks for the Afterlife."],
  ].map(([mod_id, name, summary_], i) => ({ mod_id, name, summary: summary_, author: ["chromecat", "nightshift", "glitchwerk", "mox_dev"][i % 4],
    version: `${1 + (i % 3)}.${i % 7}`, endorsement_count: 9000 - i * 311, updated_timestamp: now - i * day * 2, picture_url: pic(name, (i * 37) % 360) }));
  const own = mods.filter((m) => m.nexus_id).map((m, i) => ({ mod_id: m.nexus_id, name: m.link?.name || m.name, summary: "A sample mod used in this demo.",
    author: "demo", version: m.version || "1.0", endorsement_count: 4200 - i * 300, updated_timestamp: now - (i + 3) * day, picture_url: pic(m.link?.name || m.name, (i * 53 + 180) % 360) }));
  const allNexus = [...own, ...nexusPool];
  const findNexus = (id) => allNexus.find((x) => x.mod_id === +id);

  const api = {
    bootstrap: () => ok({ app: { name: "Cyberpunk 2077 Mod List Tool", version: "3.0.0", nexus_page: "https://www.nexusmods.com/cyberpunk2077/mods/20113" },
      settings: D.settings, game: { dir: D.settings.game_dir, valid: true, version: "2.3.1.0", store: "Steam", phantom_liberty: true },
      managers: { mode: "auto", vortex: { detected: true, installed: true, files: 6, manifests: [] }, mo2: null, mo2_candidates: [], running: {} },
      nexus: { user: D.nexus ? { name: "DemoRunner", is_premium: true, avatar: "" } : null, sso: false, api_key_page: "https://next.nexusmods.com/settings/api-keys" } }),
    app_logo: () => ok({ ok: false }), game_icon: () => ok({ ok: false }),
    get_running: () => ok({ game: D.running && !D.launching, launching: D.launching, mo2: false, vortex: false }),
    get_status: () => {
      const L = logs(), errs = L.filter((l) => l.errors);
      return ok({ running: { game: D.running && !D.launching, launching: D.launching }, valid: true, nxm_tasks: { tasks: [], errors: [] },
        changed: false, summary: summary(), log_errors: errs.reduce((a, l) => a + l.errors, 0), log_warnings: L.reduce((a, l) => a + l.warnings, 0),
        logs_with_errors: errs.map((l) => l.name), log_errors_fresh: D.running, core_ok: true, core_missing: [],
        backup: { last: D.backups[0]?.created || null, schedule: D.settings.backup_schedule || "off", running: false } });
    },
    get_mods: () => later({ ok: true, mods: JSON.parse(JSON.stringify(mods)), summary: summary() }, 60),
    set_mods_enabled: (keys, enable) => {
      if (D.running) return ok({ ok: false, error: "Close Cyberpunk 2077 first. Mod files can't be changed while the game is running." });
      keys.forEach((k) => { const m = byKey(k); if (m && m.source === "loose") { m.enabled = enable; m.components.forEach((c) => (c.disabled = !enable)); } });
      return ok({ moved: keys.length, errors: [], notes: keys.some((k) => byKey(k)?.source === "vortex") ? ["Vortex mods stay under Vortex's control."] : [] });
    },
    set_all_enabled: (enable) => api.set_mods_enabled(mods.filter((m) => m.source === "loose").map((m) => m.key), enable),
    get_core: () => ok({ core: JSON.parse(JSON.stringify(core)) }),
    get_logs: () => ok({ logs: logs().map((l) => ({ name: l.name, path: `D:\\Games\\Cyberpunk 2077\\logs\\${l.name}.log`, file: `${l.name.toLowerCase().replace(/ /g, "_")}.log`,
      errors: l.errors, warnings: l.warnings, modified: now - (l.errors ? 30 : 600), size: 4096 })) }),
    read_log: (name) => { const l = logs().find((x) => x.name === name); return ok({ name, path: "", lines: l.lines.map((t, i) => ({ t, k: l.kinds[i] })) }); },
    generate_report: () => later({ ok: true, path: D.reportPath }, 400),
    copy_report: () => ok({ text: reportText() }),
    open_path: (p) => { if (String(p).toLowerCase().endsWith(".txt")) window.demoShowReport?.(reportText()); else D.note("In the app this opens the folder in File Explorer."); return ok(); },
    open_mod_folder: () => { D.note("In the app this opens the mod's folder in File Explorer."); return ok(); },
    open_game_folder: () => { D.note("In the app this opens the folder in File Explorer."); return ok(); },
    open_url: (u) => { D.note("In the app this opens " + String(u).replace(/^https?:\/\//, "") + " in your browser."); return ok(); },
    launch_game: () => {
      if (D.running) return ok({ ok: false, error: "Cyberpunk 2077 is already running." });
      D.launching = true; D.running = true;
      setTimeout(() => { D.launching = false; }, 2500);
      return ok({ via: "Cyberpunk 2077" });
    },
    get_task: (id) => {
      const t = D.tasks[id]; if (!t) return ok({ ok: false, error: "Unknown task" });
      const p = Math.min(1, (Date.now() - t.t0) / t.ms), done = p >= 1;
      const msg = t.steps.length ? t.steps[Math.min(t.steps.length - 1, Math.floor(p * t.steps.length))] : "";
      if (done && !t.applied) { t.applied = true; t.result = typeof t.result === "function" ? t.result() : t.result; }
      return ok({ id, name: t.name, progress: p, message: msg, done, result: done ? t.result : null, error: null });
    },
    cancel_task: () => ok(),
    get_updates: () => ok({ connected: D.nexus, premium: true, checked: D.updatesChecked,
      updates: mods.filter((m) => m.enabled && m.update?.update).map((m) => ({ key: m.key, name: m.name, source: m.source, core: false, ...m.update })) }),
    nexus_check_updates: (keys) => startTask("updates", 1600, () => { D.updatesChecked = Math.floor(Date.now() / 1000); return { checked: 9, updates: summary().updates }; },
      ["1/9  Neon Nights Weather Overhaul", "4/9  Minimal HUD", "7/9  Night City Traffic+", "9/9  Street Vendors Reborn"]),
    mark_up_to_date: (key) => { const m = byKey(key); if (m?.update) { m.update.update = false; m.version = m.update.latest; } return ok(); },
    nexus_update: (key) => startTask("update", 1800, () => {
      const m = byKey(key); m.version = m.update.latest; m.update.update = false; m.update.installed = m.update.latest;
      if (key === "loose:minimalhud") D.broken = false;   // the update fixes the script error
      return { name: m.link?.name || m.name, version: m.version, installed: m.files, displaced: [] };
    }, ["Downloading 1.2 / 3.1 MB", "Downloading 3.1 / 3.1 MB", "Backing up replaced files", "Installing"]),
    nexus_identify: () => startTask("identify", 2400, () => {
      const b = byKey("loose:betterscopes"); b.nexus_id = 90088; b.link = { mod_id: 90088, name: "Better Scopes", method: "verified", version: "1.1" };
      b.update = { mod_id: 90088, latest: "1.1", installed: "1.1", update: false };
      D.suggest = true;
      return { checked: 3, identified: 1, by_url: 0, by_download: 0, verified: 1, by_name: 0, by_github: 0, suggested: 1, unlinked: 0, logged_in: true };
    }, ["Reading mod files 2/3: BetterScopes", "Reading downloads 14/20", "Checking Nexus 1/2: BetterScopes", "Checking Nexus 2/2: cozyapartmentlights"]),
    get_suggestions: () => ok({ suggestions: D.suggest && !byKey("loose:cozyapartmentlights").nexus_id ? [{ key: "loose:cozyapartmentlights", local: "cozyapartmentlights", score: 0.82,
      options: [{ mod_id: 90107, name: "Apartment Decor Pack" }, { mod_id: 90131, name: "Cozy Apartment Lighting" }] }] : [] }),
    resolve_suggestion: (key, mod_id) => { D.suggest = false; if (mod_id) { const m = byKey(key); m.nexus_id = mod_id; m.link = { mod_id, name: mod_id === 90131 ? "Cozy Apartment Lighting" : findNexus(mod_id)?.name, method: "confirmed" }; } return ok(); },
    nexus_search: (q) => {
      const t = String(q).toLowerCase(), words = t.split(/\s+/).filter(Boolean);
      const res = allNexus.filter((x) => words.some((w) => x.name.toLowerCase().includes(w))).slice(0, 12).map(({ mod_id, name, version }) => ({ mod_id, name, version }));
      return later({ ok: true, results: res }, 250);
    },
    nexus_mod_info: (id) => { const m = findNexus(id) || { mod_id: id, name: "Cozy Apartment Lighting", author: "lumen", version: "1.2", summary: "Softer lamps in every apartment.", picture_url: pic("Cozy Apartment Lighting", 40) }; return ok({ mod: m }); },
    nexus_link: (key, text) => { const id = +String(text).match(/(\d+)/)?.[1]; if (!id) return ok({ ok: false, error: "Paste a Nexus mod URL or ID." });
      const m = byKey(key); m.nexus_id = id; m.link = { mod_id: id, name: findNexus(id)?.name || `Mod ${id}`, method: "manual" }; return ok({ link: m.link }); },
    nexus_unlink: (key) => { const m = byKey(key); m.nexus_id = null; m.link = null; m.update = null; return ok(); },
    nexus_track: (id, on) => { mods.filter((m) => m.nexus_id === +id).forEach((m) => (m.tracked = !!on)); return ok(); },
    nexus_track_installed: () => startTask("track-all", 900, () => { let n = 0; mods.forEach((m) => { if (m.nexus_id && !m.tracked) { m.tracked = true; n++; } }); return { tracked: n }; }),
    nexus_tracked: () => ok({ tracked: mods.filter((m) => m.tracked).map((m) => ({ mod_id: m.nexus_id, name: m.link?.name || m.name, installed: true, url: "" })),
      not_tracked: mods.filter((m) => m.nexus_id && !m.tracked).map((m) => ({ key: m.key, name: m.name, mod_id: m.nexus_id })) }),
    nexus_status: () => ok({ user: D.nexus ? { name: "DemoRunner", is_premium: true, avatar: "" } : null, has_key: D.nexus, rate: { daily: 19840, hourly: 497 } }),
    nexus_logout: () => { D.nexus = false; return ok(); },
    nexus_login_key: () => { D.nexus = true; return ok({ user: { name: "DemoRunner", is_premium: true, avatar: "" } }); },
    mod_details: (key) => {
      const m = byKey(key), n = m.nexus_id ? findNexus(m.nexus_id) : null;
      return ok({ nexus: n ? { ...n, url: "" } : (m.nexus_id ? { mod_id: m.nexus_id, name: m.link?.name, summary: "", picture_url: pic(m.link?.name || m.name, 90) } : null),
        github: m.github ? { repo: m.github.repo, description: "Hot reload for archives, scripts and tweaks", stars: 214, latest: "1.3.0", latest_date: now - 9 * day } : null });
    },
    github_link: (key, text) => { const m = byKey(key); const repo = (String(text).match(/github\.com\/([^/\s]+\/[^/\s?#]+)/) || [])[1]; if (!repo) return ok({ ok: false, error: "Paste a GitHub repository URL." }); m.github = { repo }; return ok({ repo }); },
    github_unlink: (key) => { byKey(key).github = null; return ok(); },
    nexus_browse: (kind, term, offset = 0, count = 12) => {
      let list = kind === "search" ? allNexus.filter((x) => x.name.toLowerCase().includes(String(term).toLowerCase())) : kind === "trending" ? nexusPool.slice(0, 10) : nexusPool.slice().reverse();
      const page = list.slice(offset, offset + count).map((x) => ({ ...x, installed_key: mods.find((m) => m.nexus_id === x.mod_id)?.key || null }));
      return later({ ok: true, mods: page, more: kind !== "trending" && offset + count < list.length }, 300);
    },
    nexus_mod_page: (id) => { const m = findNexus(id); return ok({ mod: { ...m, url: "https://www.nexusmods.com/cyberpunk2077/mods/" + id }, premium: true, nxm: true,
      installed_key: mods.find((x) => x.nexus_id === +id)?.key || null,
      files: [{ file_id: id * 10, name: m.name, version: m.version, category: "MAIN", size_kb: 18200, uploaded: m.updated_timestamp, description: "Main file." },
        { file_id: id * 10 + 1, name: m.name + " (Lite)", version: m.version, category: "OPTIONAL", size_kb: 6400, uploaded: m.updated_timestamp, description: "Smaller version without extras." }] }); },
    nexus_install: (id) => startTask("update", 1500, () => ({ name: findNexus(id)?.name, version: findNexus(id)?.version, installed: [], displaced: [] }),
      ["Downloading", "Installing"]),
    nxm_status: () => ok({ registered: true, owner: "this tool", previous: "" }),
    nxm_set: () => ok({ registered: true }),
    save_settings: (v) => { Object.assign(D.settings, v); return ok({ settings: D.settings }); },
    backups_info: () => ok({ size: 18.4e6, files: 6, sets: 2 }),
    mod_backups_list: () => ok({ folder: "C:\\Users\\You\\Documents\\Cyberpunk 2077 Mod Backups", custom_folder: false,
      backups: D.backups, schedule: D.settings.backup_schedule || "off", keep: D.settings.backup_keep || 5,
      state: { last: D.backups[0]?.created || null, schedule: D.settings.backup_schedule || "off", running: false } }),
    mod_backup_create: (kind) => startTask("backup", 1600, () => {
      const t = Math.floor(Date.now() / 1000), b = { path: "demo-" + t, name: "demo", created: t, size: 412e6, kind: kind === "scheduled" ? "scheduled" : "manual", mods: 9, files: 214 };
      D.backups.unshift(b); return { ...b, pruned: 0 };
    }, ["Packing archive/pc/mod", "Packing r6/scripts", "Packing red4ext/plugins"]),
    mod_backup_restore: () => D.running ? ok({ ok: false, error: "Close Cyberpunk 2077 first." }) : startTask("restore", 1500, () => ({ restored: 214, replaced: 3, overwrite: false }), ["Extracting", "Restoring"]),
    mod_backup_delete: (path) => { D.backups = D.backups.filter((b) => b.path !== path); return ok({}); },
    mod_backup_browse_dir: () => ok({ ok: false }),
    mod_backup_reset_dir: () => api.mod_backups_list(),
    open_mod_backups: () => ok({}),
    get_download_folders: () => ok({ folders: ["C:\\Users\\You\\Downloads", "C:\\Users\\You\\AppData\\Roaming\\Vortex\\downloads\\cyberpunk2077"], extra: [] }),
    detect_game_dirs: () => Promise.resolve([{ path: "D:\\Games\\Cyberpunk 2077", store: "Steam" }]),
    export_formats: () => Promise.resolve(["zip", "7z"]),
    export_preset: () => startTask("export", 1400, { mods: 10, files: 46, path: "C:\\Users\\You\\Desktop\\Cyberpunk2077_Mod_Preset.zip" }, ["Packing archive/pc/mod", "Packing r6/scripts"]),
    install_archive: () => startTask("install", 1300, () => ({ installed: ["archive/pc/mod/NewMod.archive", "archive/pc/mod/NewMod.archive.xl"], displaced: [] }), ["Extracting", "Installing"]),
  };
  const fallback = () => (...args) => { D.note("That action needs the real app."); return ok(); };
  window.pywebview = { api: new Proxy(api, { get: (t, k) => (k in t ? t[k] : fallback()) }) };
})();
