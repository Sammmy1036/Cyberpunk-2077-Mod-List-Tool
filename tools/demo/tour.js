/* Guided tour for the demo build. Drives the real UI (go, openDrawer, poll...) from app.js. */
"use strict";
(() => {
  const D = window.DEMO;
  window.cpDemoToast = (m) => toast(esc(m), "", 3800);
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const until = async (sel, ms = 4000) => { const t = Date.now(); while (!document.querySelector(sel) && Date.now() - t < ms) await wait(80); return document.querySelector(sel); };

  /* the generated mod list, with the error section highlighted */
  window.demoShowReport = (text) => {
    const lines = esc(text).split("\n");
    let inErr = false, rules = 0;
    const html = lines.map((l) => {
      if (l.startsWith("Potential Errors to Review")) { inErr = true; rules = 0; return `<mark>${l}</mark>`; }
      if (inErr) { if (/^={20,}/.test(l) && ++rules === 2) inErr = false; return `<mark>${l}</mark>`; }
      return /MinimalHUD/.test(l) || /^ERROR - /.test(l) ? `<mark>${l}</mark>` : l;
    }).join("\n");
    modal(`<h3>Cyberpunk 2077 Mod List.txt</h3><p class="muted small">This is the file the tool writes. Highlighted lines point at the problem: the error, the file and line, and the mod it belongs to.</p>
      <pre class="demo-report">${html}</pre><div class="btn-row"><button class="btn primary" data-close>Close</button></div>`);
    document.querySelector(".modal").classList.add("wide");
    setTimeout(() => document.querySelector(".demo-report mark")?.scrollIntoView({ block: "center" }), 50);
  };

  const steps = [
    { title: "Welcome to the Mod List Tool", body: "This is a working demo of the app with sample mods. The tour shows what it does: tracking mods, updating them, and tracking down errors. You can click around at any point, or use Next.",
      run: async () => { await go("overview"); }, target: ".slab" },
    { title: "Updates come first", body: "Mods with newer versions on Nexus are listed at the top. Update downloads and installs them, backing up the old files first. Dismiss hides an update you already have.",
      run: async () => { await go("overview"); await until("#updPanel .upd-rows"); }, target: "#updPanel" },
    { title: "Setup check", body: "Green means good to go: all core frameworks are installed and up to date, and the last game session logged no errors. Orange means outdated, red means something needs fixing.",
      target: ".alerts" },
    { title: "Every mod, grouped", body: "A mod's .archive, .xl, scripts and CET folder count as one mod, not four files. Switch mods on or off, filter by state, source or folder, and search across file names.",
      run: async () => { await go("mods"); await until("#modsTable tbody tr.row"); }, target: "#modsTable" },
    { title: "Mod details", body: "Click any mod to see its Nexus page preview, why it was linked, its version and its files. Wrong match? Not this mod unlinks it, and you can paste a URL or search Nexus to link it correctly.",
      run: async () => { await go("mods"); openDrawer("loose:neonnightsweather"); await until("#dHero .hero", 3000); }, target: "#drawer" },
    { title: "GitHub mods too", body: "Mods released on GitHub link to their repository. Update checks use its releases, and plugins report their own version.",
      run: async () => { openDrawer("loose:hotreloadtools"); await until("#dGhInfo"); }, target: "#drawer .linkbox" },
    { title: "Now, something breaks", body: "Let's launch the game. A recent game update renamed a function that MinimalHUD's script still calls, so the script compiler fails. The footer flags it right away, while the game is still running.",
      run: async () => { closeDrawer(); D.breakGame(); applyRunning({ game: true }); await go("overview"); await poll(); await until("#sbErr"); }, target: "#sbErr" },
    { title: "Follow the alert to the log", body: "Clicking the alert opens the Logs page, filtered to errors. The highlighted lines name the file and the line: r6/scripts/MinimalHUD/HUDCore.reds, line 42.",
      run: async () => { document.querySelector("#sbErr")?.click(); await until(".viewer pre div.error"); }, target: ".viewer" },
    { title: "Find the mod that owns the file", body: "Search the Mods page for that path, or open MinimalHUD. Its file list includes r6/scripts/MinimalHUD/HUDCore.reds, so this mod is the cause, and Open folder takes you straight to it.",
      run: async () => { await go("mods"); const q = await until("#q"); q.value = "HUDCore"; q.dispatchEvent(new Event("input")); await wait(150); openDrawer("loose:minimalhud"); await until("#drawer .files"); }, target: "#drawer .files" },
    { title: "It's in the mod list file too", body: "Generate mod list puts the errors at the top of the file, along with every installed mod and its Nexus link. Send that one file to a mod author and they can see the problem.",
      run: async () => { closeDrawer(); window.demoShowReport((await call("copy_report")).text); }, target: ".modal" },
    { title: "Fix it with one click", body: "MinimalHUD 1.5.0 is already out and supports the new game version. Close the game, then click Update: the new version is installed and the old files are backed up.",
      run: async () => { document.querySelector("#modal").hidden = true; D.running = false; applyRunning({ game: false }); await go("mods"); const q = $("#q"); if (q) { q.value = ""; q.dispatchEvent(new Event("input")); } openDrawer("loose:minimalhud"); await until("#dUpd"); }, target: "#dUpd" },
    { title: "Fixed", body: "Updated, and the next session compiles cleanly. The footer alert is gone and the Setup check is green again.",
      run: async () => { const b = $("#dUpd"); if (b) b.click(); await wait(2600); closeDrawer(); await go("overview"); await poll(); }, target: ".alerts" },
    { title: "Find your mods on Nexus", body: "Mods you installed by hand get matched to their Nexus pages: from links inside their files, your downloaded archives, and by comparing their files with Nexus. Anything left goes to the link queue.",
      run: async () => { await go("nexus"); await until("#ident"); }, target: "#ident" },
    { title: "Browse Nexus", body: "Trending, new and recently updated mods, plus search. Open one to see its files and install it directly.",
      run: async () => { await go("browse"); await until(".card"); }, target: "#bwGrid" },
    { title: "That's the tour", body: "Everything else is yours to explore: Core Frameworks, backups and presets under More actions, Settings and more. Restart the tour any time from the banner at the top.",
      run: async () => { await go("overview"); }, target: null },
  ];

  let i = -1, busy = false;
  const card = document.createElement("div");
  card.className = "tour"; card.setAttribute("role", "dialog"); card.setAttribute("aria-live", "polite");
  document.body.append(card);
  const banner = document.createElement("div");
  banner.className = "demo-banner";
  banner.innerHTML = `<b>Interactive demo</b><span>Sample mods and data. Nothing is installed or changed on your PC.</span><button class="btn small" id="tourStart">Take the tour</button>`;
  document.body.append(banner);

  let current = null;
  function highlight(sel) {
    current = sel;
    document.querySelectorAll(".tour-hl").forEach((e) => e.classList.remove("tour-hl"));
    const el = sel && document.querySelector(sel);
    if (el) { el.classList.add("tour-hl"); el.scrollIntoView({ block: "nearest", behavior: "smooth" }); }
  }
  // parts of the UI (footer, lists) redraw themselves: keep the highlight on the current target
  setInterval(() => {
    if (!current) return;
    const el = document.querySelector(current);
    if (el && !el.classList.contains("tour-hl")) el.classList.add("tour-hl");
  }, 300);
  async function show(n) {
    if (busy) return;
    busy = true;
    i = Math.max(0, Math.min(steps.length - 1, n));
    const s = steps[i];
    card.innerHTML = `<div class="tour-step">Step ${i + 1} of ${steps.length}</div><h3>${esc(s.title)}</h3><p>${esc(s.body)}</p>
      <div class="btn-row"><button class="btn small" id="tourEnd">Exit tour</button><span style="flex:1"></span>
      ${i ? `<button class="btn small" id="tourBack">Back</button>` : ""}<button class="btn small primary" id="tourNext">${i === steps.length - 1 ? "Finish" : "Next"}</button></div>`;
    card.classList.add("on");
    $("#tourEnd").onclick = end;
    if ($("#tourBack")) $("#tourBack").onclick = () => show(i - 1);
    $("#tourNext").onclick = () => (i === steps.length - 1 ? end() : show(i + 1));
    try { if (s.run) await s.run(); } catch (e) { console.warn(e); }
    await wait(120);
    highlight(s.target);
    busy = false;
  }
  function end() { card.classList.remove("on"); highlight(null); i = -1; }
  document.addEventListener("keydown", (e) => {
    if (i < 0 || busy) return;
    if (e.key === "ArrowRight") show(i + 1);
    if (e.key === "ArrowLeft") show(i - 1);
  });
  $("#tourStart").onclick = () => show(0);
  window.demoTour = { show, end, steps };
  // start once the app has finished loading
  const ready = setInterval(() => { if (document.querySelector("#splash") === null || document.querySelector("#splash.done")) { clearInterval(ready); setTimeout(() => show(0), 500); } }, 150);
})();
