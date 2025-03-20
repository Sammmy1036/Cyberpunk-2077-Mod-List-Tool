# Cyberpunk 2077 Mod List Tool

**DESCRIPTION**

The Cyberpunk 2077 Mod List Tool is a utility designed to catalog all mod files and folders currently installed for Cyberpunk 2077, alongside compiling log data, game version details, and Phantom Liberty DLC status. The tool outputs this information into a .txt file for easy reference.

Simplifies the process of documenting extensive mod collections, logs, and critical game information. It provides a streamlined solution for users managing hundreds of mods, enabling them to share detailed troubleshooting data with mod authors and community supporters efficiently.

________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________

**KEY FEATURES**

Generates lists of mods from key directories:

-Cyber Engine Tweaks (CET) mods in Cyberpunk 2077\bin\x64\plugins\cyber_engine_tweaks\mods.

-R6 scripts and tweaks in Cyberpunk 2077\r6.

-Archive mods in Cyberpunk 2077\archive\pc\mod.



Optionally includes the most recent logs from ArchiveXL, Codeware, and TweakXL (via a checkbox, enabled by default).

Displays the current game version and Phantom Liberty DLC installation status.

Highlights potential errors in log files for review.

Monitors and displays the installation status and versions of essential dependencies (ArchiveXL, Codeware, Cyber Engine Tweaks, EquipmentEx, RED4ext, Redscript, TweakXL), with real-time updates in the GUI.

Offers features to temporarily disable or enable mods (collectively or individually) while protecting core mods from modification.

Allows exporting selected mod folders to a .zip file with a progress bar.

Displays real-time data on total installed mods, game version, log error detection, and core mod status upon launch.

Tracks mod directory changes (additions, deletions, moves) and updates the mod count dynamically.

Additional data previously exclusive to the .txt output—such as the number of installed mods, game version, log error detection, and core mod status—is now integrated into the graphical user interface (GUI) for immediate visibility.

________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________

**INSTALLATION**
Unlike previous versions, the tool no longer requires placement in the game directory. You can now set the game directory at launch of the application or via the "Settings" option within the tool. The path will be saved to the Windows Registry for persistence.

________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________

HOW TO USE
Compiling Mod and Log Lists
Launch the application by double-clicking Cyberpunk 2077 Mod List Tool.exe.
If you prefer not to include log files in the output, uncheck the "Include Logs" checkbox (checked by default).
Click Start. The tool will generate Cyberpunk 2077 Mod List.txt in the same directory as the executable, containing your mod list, logs (if selected), and game information.
Setting the Game Directory
If the tool is not in your game directory or you wish to use a different location, click Settings.
Select your Cyberpunk 2077 root directory (e.g., where Cyberpunk2077.exe resides) and confirm. The path will be saved for future use.
Core Mods Status
Click Core Mods Status to open a window detailing the following dependencies:
ArchiveXL: Displays version and installation status of required files.
Codeware: Displays version and installation status of required files.
Cyber Engine Tweaks: Displays version (from log, if available) and installation status.
EquipmentEx: Displays installation status (no version due to lack of references).
RED4ext: Displays version and installation status of required files.
Redscript: Displays installation status (no version due to lack of references).
TweakXL: Displays version and installation status of required files.
Core mods are excluded from total mod counts, remain untouched during enable/disable operations, and are not listed in the "View Mod List" window.
Missing core mods include a clickable "Install" button linking to their Nexus Mods page.
More Options - Enable/Disable All Mods
Disable All Mods: Creates a Temporarily Disabled Mods folder in your game directory and moves all non-core mods there.

Enable All Mods: Restores all mods from the Temporarily Disabled Mods folder to their original locations, deleting the folder if empty.
More Options - View Mod List

Opens a window listing all installed and disabled mods.

Features a search bar and directory filter to refine the view.

Allows individual mod management:
Example: Select MyMod.archive from the "Enabled Mods" list (left side), click Disable Selected, and it moves to Temporarily Disabled Mods. Disabled mods appear on the right side for re-enabling.
More Options - Export Mod Preset
Click Export Mod Preset to open a folder selection window.
Check the boxes for mod folders to export (e.g., archive/pc/mod, r6/scripts) and click Confirm.
Choose a save location and filename in the "Save Mod Preset As" dialog, then click Save.
A progress bar tracks the export, followed by a completion notification.

________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________

**UNINSTALL**
Simply delete Cyberpunk 2077 Mod List Tool.exe from its location. If using a custom game directory, you may also clear the registry entry under HKEY_CURRENT_USER\Software\Cyberpunk2077ModListTool (optional).

________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________

**PLEASE NOTE**
Antivirus Flags: Windows Defender or other antivirus software may flag this tool as a potentially unwanted program or virus due to its lack of a digital signature from a recognized publisher. The application is safe and has been submitted to Microsoft for whitelisting, which should resolve this over time.
Requirements: The tool must have access to a valid Cyberpunk 2077 directory (set via Settings if not placed there) to function fully.
