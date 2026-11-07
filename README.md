# Cyberpunk 2077 Mod List Tool

A companion app for Cyberpunk 2077 modding. It catalogs your mods, checks the core frameworks, reads framework logs, and builds a shareable mod list for troubleshooting. It works alongside **Vortex** and **Mod Organizer 2**, and connects to **Nexus Mods** to identify, track and update your mods.

## What's new in 3.0

- **New interface** built with pywebview (HTML/CSS). It's resizable and keyboard friendly, with a Cyberpunk-inspired look.
- **Accurate mod counts.** Files are grouped into mods. `Foo.archive`, `Foo.archive.xl` and `r6/scripts/Foo` count as one mod, not three. REDmod (`mods/`), Input Loader (`r6/input`) and ASI plugins are now detected too.
- **Vortex and MO2 support.**
  - *Vortex:* mods deployed by Vortex are recognised from `vortex.deployment.json` and shown with their Vortex name, version and Nexus ID. The tool never moves Vortex's files, so Vortex won't report them as externally changed.
  - *MO2:* mods are read from your instance and profile (`modlist.txt`, `meta.ini`). You can toggle them here while MO2 is closed, and the game can be launched through MO2 so its virtual filesystem is active.
- **Nexus Mods integration.** Connect with your personal API key (stored encrypted with Windows DPAPI).
  - Identify manually installed mods by file hash.
  - Check mods and core frameworks for updates.
  - Track everything you have installed.
  - Premium accounts can update manual installs in one click. Free accounts are sent to the Files tab.
- **Finding your mods on Nexus.** Nexus only indexes uploaded archives, not the files unpacked into your game, so manual installs are matched in layers:
  0. *Nexus links inside the mod's files.* Many authors put their mod page URL in `.xl`, `.reds`, `init.lua`, `.yaml` or readme files. Links to frameworks and other shared requirements are ignored.
  1. *Downloaded archives* (Downloads, the Vortex and MO2 download folders, plus folders you add). The file name gives the mod ID and version, and the contents are checked against what's installed. Exact.
  2. *Catalog plus file check.* The tool downloads Nexus's full Cyberpunk mod list once a week and fuzzy-matches every name a mod goes by: folders, archives, REDmod names. The best candidates' file lists (Nexus "content preview") are then compared with your installed files. A match confirms the mod, and matching file sizes give the exact version.
  3. *Review and link queue.* Close-but-unconfirmed matches wait for you to confirm. Anything else can be linked by searching Nexus (or pasting a URL) right in the app.
- **GitHub mods** (e.g. RedHotTools): link a mod to its GitHub repository (or let the scan find the repo URL in the mod's files). Update checks use GitHub releases, and Update installs the release download. Native plugins also report their own DLL version.
- **Browse Nexus**: trending, new and recently updated Cyberpunk 2077 mods, plus search, with pictures, summaries and per-file Install (Premium) or Mod Manager Download (free). "Open full Nexus site" opens nexusmods.com in your browser.
- **Wrong match?** Click "Not this mod" in the side panel. The link is removed, and automatic matching won't pick that page for the mod again. Mods whose names differ only by a number (H8 vs H10) are never matched automatically.
- **Tracking.** Linked mods can be tracked on Nexus automatically. The Nexus page shows what's installed but untracked (with "Track all") and everything you track.
- **Your Nexus account on every page.** Your profile picture and name sit under the logo, so you can always see you're signed in.
- **Updating in the app.** Premium accounts download and install updates directly. Free accounts can turn on *Install "Mod Manager Download" files here* in Settings; the button on a mod's Files tab then installs into this tool. Links for other games are passed to the app that handled them before (Vortex or MO2), and switching the option off restores it. Replaced files are backed up, never deleted.
- **Install mod / Install a mod preset** (More actions). Install a mod or preset from `.zip`, `.7z` or `.rar`. Any file it would overwrite is backed up first; for presets you can choose to overwrite existing files instead.
- **Mod backups** (More actions → Back up or restore mods). Zip snapshots of every manually installed mod (enabled or disabled) and the core frameworks, made on demand or daily/weekly/monthly while the tool is open. Restore any backup with one click. Saved to `Documents\Cyberpunk 2077 Mod Backups` by default; the Overview shows when you last backed up.
- **Launch lock.** After you click Launch Game, the button shows *Starting…* and then *Game Running*, and blocks a second launch until the game closes. Running-game detection uses the Windows process list directly.
- **Debug log** at `%APPDATA%\Cyberpunk2077ModListTool\cp77mlt.log` (Settings, then About).
- **Fixed: "Failed to remove temporary directory" pop-up** when closing the tool while the game is running. The game, your browser and your editor are now started in a clean environment, so they no longer lock the tool's temp folder.

## Using it

| Page | What it does |
|---|---|
| Overview | Available mod updates first (checked automatically when results are older than 6 hours), mod counts, problems that need attention, and **Generate mod list** (saved to Documents by default, with Open/Copy). |
| Mods | Search, filter by state/source/location, toggle mods, select several (checkbox or Ctrl+click) for bulk actions, and click a mod to see its files and Nexus link. |
| Core Frameworks | Install state and version of RED4ext, Redscript, CET, ArchiveXL, TweakXL, Codeware and EquipmentEx, plus disabling them for vanilla testing. |
| Logs | Framework logs with errors and warnings highlighted, and an errors-only filter. |
| Nexus Mods | Connect your account, check for updates, identify manual mods, and manage tracking. |
| Settings | Game folder (auto-detected for Steam, GOG and Epic), launch method (Cyberpunk2077.exe by default; Steam or MO2 optional), mod managers, and mod list options. |

Disabled mods are moved to `Temporarily Disabled Mods` inside your game folder, the same as in 2.x. When installing or updating a mod would overwrite files, the old files are moved to `Temporarily Disabled Mods\_Backups (replaced files)\<date>` instead of being deleted, so you can roll back. Settings shows how much space backups use, with buttons to open or empty the folder. (Older builds called this folder `_superseded`.)

Settings live in `%APPDATA%\Cyberpunk2077ModListTool\settings.json`. Your 2.x registry settings are migrated automatically on first launch.

## Building from source

**One click:** double-click `build_exe.bat`. It finds Python 3.10+, sets up a private build environment in `.venv-build` (first run only), installs the packages, runs the tests, builds `dist\Cyberpunk 2077 Mod List Tool.exe` and packs `dist\Cyberpunk 2077 Mod List Tool v<version>.zip` (exe + LICENSE + README) ready to upload. The version comes from `APP_VERSION` in `cp77mlt/__init__.py`. Options: `notest`, `noopen`, `nopause`, `fresh` (rebuild the environment).

Manually:

```
pip install -r requirements.txt
python Cyberpunk2077ModListTool.pyw          # run (add --debug for devtools)
pyinstaller Cyberpunk2077ModListTool.spec    # build the single-file exe
python -m pytest tests -q                    # backend tests
python tests/ui_harness.py out_dir --nexus   # screenshots the UI against a fake game folder
```

Put the original `icons/mod_list_tool.png` (sidebar logo) and `icons/game_icon.png` (launch-button fallback) next to the spec file before building; they're bundled automatically when present.

No pywin32 needed: file versions and DPAPI go through Windows APIs directly.

Requires Windows 10/11 with the Microsoft Edge WebView2 runtime (preinstalled on current Windows).

**Nexus SSO:** "Log in with Nexus" needs an application slug issued by Nexus Mods. Once you have one, set `NEXUS_APP_SLUG` in `cp77mlt/nexus.py` and the button appears. Until then, personal API keys work.

## Notes

- Antivirus tools may flag unsigned PyInstaller builds. Code-signing the exe avoids this.
- Make a mod backup (More actions) before disabling frameworks or importing presets.
- Unofficial fan-made tool, not affiliated with or endorsed by CD PROJEKT S.A. MIT License.
