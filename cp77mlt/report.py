"""Generates the shareable 'Cyberpunk 2077 Mod List.txt' troubleshooting report."""
from __future__ import annotations

import datetime as _dt
import os

from . import APP_VERSION, NEXUS_PAGE, logs
from .scanner import Mod, raw_listing

RULE = "-" * 100
SOURCE_LABEL = {"loose": "Manual", "vortex": "Vortex", "mo2": "MO2"}


def generate(path: str, *, game_dir: str, game_version: str, phantom_liberty: bool, store: str,
             mods: list[Mod], core: list[dict], log_names: list[str], include_errors: bool,
             include_disabled: bool, manager: str | None, include_grouped: bool = True) -> str:
    enabled = [m for m in mods if m.enabled]
    disabled = [m for m in mods if not m.enabled]
    missing_core = [c["name"] for c in core if not c["installed"]]
    issues = logs.IssueCache().issues(game_dir) if include_errors else {}

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    # utf-8-sig so Notepad shows non-ASCII mod names correctly (v2 crashed on them)
    with open(path, "w", encoding="utf-8-sig", newline="\r\n") as f:
        w = f.write
        w(f"Cyberpunk 2077 Mod List Tool v{APP_VERSION} by Sammmy1036\n")
        w(f"Nexus Mod Page {NEXUS_PAGE}\n")
        w(f"List created on {_dt.datetime.now().strftime('%B %d, %Y at %I:%M:%S %p')}\n")
        w(f"Game Version: {game_version} | Store: {store} | Phantom Liberty DLC Installed: "
          f"{'Yes' if phantom_liberty else 'No'}\n")
        if manager:
            w(f"Mod Manager: {manager}\n")
        if missing_core:
            w(f"All Core Mods Installed: No. Missing Dependencies: {', '.join(missing_core)}\n")
        else:
            w("All Core Mods Installed: Yes\n")
        w(f"Total Mods Installed: {len(enabled)} enabled"
          f"{f', {len(disabled)} disabled' if disabled else ''}\n")
        w(RULE + "\n")

        w("\nCore Frameworks\n" + RULE + "\n")
        for c in core:
            state = "Installed" if c["installed"] else ("Disabled" if c.get("disabled") else "MISSING")
            w(f"{c['name']:<22} {state:<10} {c.get('version') or ''}\n")
        w(RULE + "\n")

        if include_errors:
            flagged = {k: v for k, v in issues.items() if v["errors"]}
            if flagged:
                w("\nPotential Errors to Review\n" + "=" * 100 + "\n")
                for name, data in flagged.items():
                    w(f"\n{name} ({len(data['errors'])}):\n{RULE}\n")
                    for line in data["errors"][:200]:
                        w(line + "\n")
                w("=" * 100 + "\n")

        if include_grouped:
            w(f"\nInstalled Mods ({len(enabled)})\n{RULE}\n")
            for m in enabled:
                w(_mod_line(m) + "\n")
            if include_disabled and disabled:
                w(f"\nDisabled Mods ({len(disabled)})\n{RULE}\n")
                for m in disabled:
                    w(_mod_line(m) + "\n")
            w(RULE + "\n")

        w("\nFolder Listing\n")
        for rel, items in raw_listing(game_dir, include_disabled).items():
            if not items:
                continue
            w(f"\n{rel}:\n{RULE}\n")
            for name, is_disabled in items:
                w(f"{name}{' (Disabled)' if is_disabled else ''}\n")
        w(RULE + "\n")

        mo2 = [m for m in mods if m.source == "mo2"]
        if mo2:
            w("\nNote: MO2 mods live in MO2's virtual filesystem and are not in the game folder.\n")

        avail = logs.available(game_dir)
        for name in log_names:
            w(f"\n{name} Log:\n{RULE}\n")
            p = avail.get(name)
            if not p:
                w(f"The {name} log could not be found.\n")
                continue
            try:
                text = logs.read_text(p)
                if os.path.basename(p) != os.path.basename(logs.LOG_FILES[name][0]):
                    w(f"(Using most recent log file: {os.path.basename(p)})\n")
                w(text.rstrip() + "\n" if text.strip() else f"The {name} log is empty.\n")
            except OSError as e:
                w(f"Error reading {name} log: {e}\n")
    return path


def _mod_line(m: Mod) -> str:
    bits = [m.name]
    if m.version:
        bits.append(f"v{m.version}")
    bits.append(f"[{SOURCE_LABEL.get(m.source, m.source)}]")
    if m.locations():
        bits.append("(" + ", ".join(m.locations()) + ")")
    if m.nexus_id:
        bits.append(f"https://www.nexusmods.com/cyberpunk2077/mods/{m.nexus_id}")
    if m.partial:
        bits.append("<partially disabled>")
    return "  ".join(bits)
