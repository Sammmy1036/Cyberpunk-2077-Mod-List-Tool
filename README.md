# Cyberpunk 2077 Mod List Tool

The **Cyberpunk 2077 Mod List Tool** is a utility designed to catalog all mod files and folders installed for Cyberpunk 2077, compile log data, display game version details, and report Phantom Liberty DLC status. The tool outputs this information into a .txt file for easy reference and provides a modernized interface for managing mods efficiently. It simplifies documenting extensive mod collections, logs, and critical game information, enabling users to share detailed troubleshooting data with mod authors and community supporters.

_______________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________

# KEY FEATURES

**Mod List Generation**

Generates lists of mods from key directories:
Cyberpunk 2077\bin\x64\plugins\cyber_engine_tweaks\mods (Cyber Engine Tweaks mods).
Cyberpunk 2077\r6\scripts and Cyberpunk 2077\r6\tweaks (R6 scripts and tweaks).
Cyberpunk 2077\archive\pc\mod (Archive mods).
Cyberpunk 2077\red4ext\plugins (Additional mod detection for RED4ext plugins, excluding core mods like ArchiveXL, Codeware, TweakXL).

Optionally includes logs from ArchiveXL, Codeware, TweakXL, Cyber Engine Tweaks, RED4ext, Redscript, Input Loader, and Mod Settings (via dynamic checkbox selection, enabled by default).

**Mod Management**
Temporarily enable or disable all non-core mods or individual mods via a dual-listbox interface (Enabled/Disabled Mods) with search and directory filtering.

Import/Export mod presets from ZIP files with progress tracking and error handling.

**Core Mods Status**
Monitors and displays real-time status on game version, essential dependencies (ArchiveXL, Codeware, Cyber Engine Tweaks, EquipmentEx, RED4ext, Redscript, TweakXL), and detected errors.

**Log File Viewer**
New Log File Viewer page to display and interact with log file contents.

Supports dynamic detection of available logs (e.g., redscript_r*.log) and double-click functionality to open logs in the default system application.

**Game Launch Integration**
Includes a "Launch Game" button.

_______________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________

# INSTALLATION

The tool no longer requires placement in the Cyberpunk 2077 game directory. Set the game directory at launch via the Settings page. The selected path will be saved to the Windows Registry for persistence.

Download the latest Cyberpunk 2077 Mod List Tool.exe file either from Git or the Nexus Mods page.

Run the executable to launch the tool.

If prompted, select your Cyberpunk 2077 root directory in Settings. Common installation directories are listed below:
Steam:
C:\Program Files (x86)\Steam\steamapps\common\Cyberpunk 2077

GOG:
C:\Program Files (x86)\GOG Galaxy\Games\Cyberpunk 2077

Epic Games Store:
C:\Program Files\Epic Games\Cyberpunk2077

_______________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________

# HOW TO USE

**Home Page**

Launch Cyberpunk 2077 Mod List Tool.exe and on Select Home from the left hand navigation pane.

Select which logs to include using checkboxes (e.g., ArchiveXL, Redscript).

Click Generate Mod List to create Cyberpunk 2077 Mod List.txt in the same directory as this tool. 

<br />

**Mod Management Page**

Navigate to the Mod Management page via the sidebar.

View Enabled Mods and Disabled Mods in separate lists, filtered by directory (e.g., archive/pc/mod) or search term.

Select mods and use Disable Selected or Enable Selected to move them to/from the Temporarily Disabled Mods folder.

Use Disable All Mods or Enable All Mods for bulk operations (excludes core mods by default).

Click Export / Backup Mod Preset to save selected mod folders to a .zip file with a progress bar.

Click Import Mod Preset to extract mods from a .zip file to your game directory, with progress tracking.

<br />

**Core Mods Status Page**

Navigate to the Core Mods Status page via the sidebar.

View the status of dependencies (ArchiveXL, Codeware, etc.), including versions and installation status.

Click mod names to visit their Nexus Mods pages or use the Install button for missing mods.

Use Enable Core Mods or Disable Core Mods to manage core mod files (moves them to/from the Temporarily Disabled Mods folder).

<br />

Core mods are excluded from total mod counts, remain untouched during enable/disable operations, and are not listed in the "View Mod List" window.

Missing core mods include a clickable "Install" button linking to their Nexus Mods page.

<br />

**Log File Viewer**

Navigate to the Log File Viewer page via the sidebar.

Select a log from the list to view its contents in the text area.

Double-click a log to open it in your default system application (e.g., Notepad).

The tool dynamically detects available logs.

<br />

**Settings Page**

Navigate to the Settings page via the sidebar.

Click Change Game Directory and select your Cyberpunk 2077 root directory.

<br />

_______________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________

# UNINSTALL

Delete Cyberpunk2077ModListTool.exe from its location.

Optionally, clear the registry entry under HKEY_CURRENT_USER\Software\Cyberpunk2077ModListTool if a custom game directory was set.

_______________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________

# PLEASE NOTE

Antivirus Flags: Windows Defender or other antivirus software may flag this tool as a potentially unwanted program due to its lack of a digital signature. The application is safe and has been submitted to many antivirus providers for whitelisting.

Backup Recommendation: Always back up your game files before using features like mod import or core mod disabling, as these modify game directories.

Mod Preset Compatibility: The import feature assumes mod presets follow the same directory structure as exported presets.

_______________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________

# REQUIREMENTS

The tool must have access to a valid Cyberpunk 2077 directory (set via Settings) to function fully.

Windows operating system for full functionality (non-Windows platforms have limited support due to win32api dependencies).
