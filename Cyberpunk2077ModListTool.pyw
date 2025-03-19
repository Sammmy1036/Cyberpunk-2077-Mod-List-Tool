import tkinter as tk  # Imported for GUI
import os  # imported for accessing files and executing system directory operations
import msvcrt  # imported and used to lock certain windows inside the application itself
import sys  # imported for lock mechanism of application ensuring only one instance can run
import tempfile  # imported to generate a temporary file path
import webbrowser  # imported for opening Nexus Mod Page links
import datetime  # imported to print the date of text file generation
import time  # imported to print the time of text file generation
import re  # imported specifically to parse CET log for regex pattern to determine version
import shutil  # imported for enabling/disabling mods
import psutil  # imported to check if the game is running
import zipfile  # imported for exporting mods to a zip file
from tkinter import messagebox, ttk, filedialog  # imported for dialogs, styling, and file saving
from watchdog.observers import Observer  # imported for updating the mod counter in the GUI
from watchdog.events import FileSystemEventHandler  # imported for updating the mod counter in the GUI

# Cyberpunk 2077 Mod List Tool Version
tool_Version = "1.0.0.4"

try:
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

# Default game version if retrieval fails
DEFAULT_GAME_VERSION = "Unknown"

# Core dependencies and their Nexus Mod IDs with expected paths (relative to the current directory)
CORE_DEPENDENCIES = {
    "ArchiveXL": {
        "id": "4198",
        "path": [
            "red4ext/plugins/ArchiveXL/Bundle/ArchiveXL.archive",
            "red4ext/plugins/ArchiveXL/Bundle/PhotoModeScope.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerBaseScope.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationBeardFix.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationBeardScope.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationBrowsFix.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationBrowsPatch.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationBrowsScope.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationHairFix.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationHairPatch.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationHairScope.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationLashesFix.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationLashesPatch.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationLashesScope.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationScope.xl",
            "red4ext/plugins/ArchiveXL/Scripts/ArchiveXL.Global.reds",
            "red4ext/plugins/ArchiveXL/Scripts/ArchiveXL.reds",
            "red4ext/plugins/ArchiveXL/ArchiveXL.dll"]},
    "Codeware": {
        "id": "7780",
        "path": [
            "red4ext/plugins/Codeware/Data/KnownHashes.txt",
            "red4ext/plugins/Codeware/Scripts/Codeware.Global.reds",
            "red4ext/plugins/Codeware/Scripts/Codeware.Localization.reds",
            "red4ext/plugins/Codeware/Scripts/Codeware.UI.TextInput.reds",
            "red4ext/plugins/Codeware/Scripts/Codeware.UI.reds",
            "red4ext/plugins/Codeware/Scripts/Codeware.reds",
            "red4ext/plugins/Codeware/Codeware.dll"]},
    "Cyber Engine Tweaks": {"id": "107", "path": "bin/x64/version.dll", "log_path": "bin/x64/plugins/cyber_engine_tweaks/cyber_engine_tweaks.log"},
    "EquipmentEx": {"id": "6945", "path": ["r6/scripts/EquipmentEx/EquipmentEx.Global.reds", "r6/scripts/EquipmentEx/EquipmentEx.reds", "archive/pc/mod/EquipmentEx.archive", "archive/pc/mod/EquipmentEx.archive.xl"]},
    "RED4ext": {"id": "2380", "path": ["bin/x64/winmm.dll", "red4ext/RED4ext.dll"]},
    "Redscript": {"id": "1511", "path": ["engine/config/base/scripts.ini", "engine/tools/scc.exe", "engine/tools/scc_lib.dll", "r6/config/cybercmd/scc.toml"]},
    "TweakXL": {
        "id": "4197",
        "path": [
            "red4ext/plugins/TweakXL/Data/ExtraFlats.dat", 
            "red4ext/plugins/TweakXL/Data/InheritanceMap.dat", 
            "red4ext/plugins/TweakXL/Scripts/TweakXL.Global.reds", 
            "red4ext/plugins/TweakXL/Scripts/TweakXL.reds", 
            "red4ext/plugins/TweakXL/TweakXL.dll"]}
}

# Get the base directory for the application
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define paths for the icon and image files
ICON_PATH = os.path.join(SCRIPT_DIR, "Cyberpunk 2077 Mod List Tool.ico")
IMAGE_PATH = os.path.join(SCRIPT_DIR, "Cyberpunk 2077 Mod List Tool.png")

# Lock file for single instance checking
LOCK_FILE = os.path.join(tempfile.gettempdir(), "Cyberpunk2077ModListTool.lock")

# Define mod directories (relative to the current directory)
MOD_DIRECTORIES = [
    "archive/pc/mod",
    "bin/x64/plugins/cyber_engine_tweaks/mods",
    "r6/scripts",
    "r6/tweaks"
]

# Temporary disabled mods folder
TEMP_DISABLED_DIR = "Temporarily Disabled Mods"

# Global flag to track if View Mod List or Core Mods window is open
mod_window_open = False
core_window_open = False

# Caching for game running check
_game_running_cache = None
_cache_timestamp = 0
CACHE_TIMEOUT = 2  # Cache for 2 seconds

# Global observer for watchdog
mod_observer = None

def on_closing():
    # Clean up lock file and stop watchdog observer on exit
    global mod_window_open, core_window_open, mod_observer
    print("Closing application")
    if hasattr(sys, 'lock_file_handle') and sys.lock_file_handle:
        try:
            msvcrt.locking(sys.lock_file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            sys.lock_file_handle.close()
            os.remove(LOCK_FILE)
        except (OSError, IOError) as e:
            print(f"Error releasing lock or removing lock file: {e}")
    if mod_observer:
        mod_observer.stop()
        mod_observer.join()
    mod_window_open = False
    core_window_open = False
    window.destroy()

def check_single_instance():
    # Check if another instance is running using msvcrt file locking
    try:
        lock_file_handle = open(LOCK_FILE, 'wb+')
        msvcrt.locking(lock_file_handle.fileno(), msvcrt.LK_NBLCK, 1)
        sys.lock_file_handle = lock_file_handle
        lock_file_handle.write(str(os.getpid()).encode('utf-8'))
        lock_file_handle.flush()
        print("Single instance check passed")
        return True
    except IOError as e:
        if e.errno == 13:
            print("Another instance is already running.")
            return False
        else:
            print(f"Unexpected error checking lock file: {e}")
            return False
    except Exception as e:
        print(f"Error in single instance check: {e}")
        return False

def get_game_version(file_path):
    # Retrieve the Product Version of the Cyberpunk 2077 executable
    if not WIN32_AVAILABLE:
        return DEFAULT_GAME_VERSION
    try:
        if not os.path.exists(file_path):
            return DEFAULT_GAME_VERSION
        info = win32api.GetFileVersionInfo(file_path, "\\")
        ms = info.get("ProductVersionMS", 0)
        ls = info.get("ProductVersionLS", 0)
        major = (ms >> 16) & 0xffff
        minor = ms & 0xffff
        build = (ls >> 16) & 0xffff
        revision = ls & 0xffff
        return f"{major}.{minor}.{build}.{revision}"
    except (win32api.error, FileNotFoundError):
        return DEFAULT_GAME_VERSION

def get_dll_version(file_path):
    # Retrieve the Product Version of a DLL file
    if not WIN32_AVAILABLE:
        return "Unknown"
    try:
        if not os.path.exists(file_path):
            return "Unknown"
        info = win32api.GetFileVersionInfo(file_path, "\\")
        ms = info.get("ProductVersionMS", 0)
        ls = info.get("ProductVersionLS", 0)
        major = (ms >> 16) & 0xffff
        minor = ms & 0xffff
        build = (ls >> 16) & 0xffff
        revision = ls & 0xffff
        return f"{major}.{minor}.{build}.{revision}"
    except (win32api.error, FileNotFoundError) as e:
        print(f"Error getting version for {file_path}: {e}")
        return "Unknown"

def get_cet_version(log_path):
    # Retrieve the Cyber Engine Tweaks version from its log file
    if not os.path.exists(log_path):
        return "Unknown"
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.search(r"CET version v([\d\.]+)", line)
                if match:
                    return match.group(1)
    except (OSError, UnicodeDecodeError) as e:
        print(f"Error reading CET log {log_path}: {e}")
    return "Unknown"

def is_phantom_liberty_installed(current_dir):
    # Check if Phantom Liberty DLC is installed by looking for specific files/folders
    ep1_folder = os.path.join(current_dir, "archive", "pc", "ep1")
    tweakdb_ep1 = os.path.join(current_dir, "r6", "cache", "tweakdb_ep1.bin")
    if os.path.exists(ep1_folder) and any(f.endswith('.archive') for f in os.listdir(ep1_folder)):
        return True
    if os.path.exists(tweakdb_ep1):
        return True
    return False

def get_most_recent_log(directory, base_name):
    """Find the most recent log file in the directory matching the base_name pattern."""
    import glob
    pattern = os.path.join(directory, f"{base_name}-*.log")
    log_files = glob.glob(pattern)
    if not log_files:
        return None
    # Sort by modification time, most recent first
    log_files.sort(key=os.path.getmtime, reverse=True)
    return log_files[0]  # Return the most recent file

def is_game_running():
    # Check if Cyberpunk2077.exe is running using psutil with caching
    global _game_running_cache, _cache_timestamp
    current_time = time.time()
    if _game_running_cache is not None and (current_time - _cache_timestamp) < CACHE_TIMEOUT:
        return _game_running_cache

    try:
        for process in psutil.process_iter(['name']):
            if process.info['name'].lower() == "cyberpunk2077.exe":
                _game_running_cache = True
                break
        else:
            _game_running_cache = False
    except (psutil.Error, Exception) as e:
        print(f"Warning: Failed to check if game is running: {e}. Assuming it is not.")
        _game_running_cache = False
    _cache_timestamp = current_time
    return _game_running_cache

def toggle_mod_buttons():
    # Toggle visibility of mod management buttons with side-by-side Disable/Enable and spaced others
    if disable_button.winfo_viewable():
        disable_button.place_forget()
        enable_button.place_forget()
        view_mod_list_button.place_forget()
        export_mod_preset_button.place_forget()
        more_options_button.config(text="More Options")
    else:
        disable_button.place(x=120, y=600)
        enable_button.place(x=330, y=600)
        start_y = 650
        end_y = 750
        num_buttons = 2
        spacing = (end_y - start_y) / (num_buttons + 1)
        view_mod_list_button.place(relx=0.5, y=start_y + spacing * 1, anchor="center")
        export_mod_preset_button.place(relx=0.5, y=start_y + spacing * 2, anchor="center")
        more_options_button.config(text="Hide Options")

def disable_all_mods():
    # Disable all mods by moving them to a 'Temporarily Disabled Mods' folder, excluding EquipmentEx components
    if is_game_running():
        messagebox.showwarning("Game Running", "Cannot modify mods while Cyberpunk 2077 is running!")
        return

    if not messagebox.askyesno("Confirm Disable", "This will move all mods to the 'Temporarily Disabled Mods' folder located in your Cyberpunk 2077 directory. Proceed?"):
        return
    current_dir = os.getcwd()
    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
    os.makedirs(temp_disabled_path, exist_ok=True)
    errors = []

    for mod_dir in MOD_DIRECTORIES:
        full_dir = os.path.join(current_dir, mod_dir)
        if os.path.exists(full_dir):
            temp_mod_dir = os.path.join(temp_disabled_path, mod_dir)
            os.makedirs(temp_mod_dir, exist_ok=True)
            for item in os.listdir(full_dir):
                # Skip EquipmentEx components
                norm_mod_dir = os.path.normpath(mod_dir)
                norm_item = item.lower()
                if (norm_mod_dir == os.path.normpath("r6/scripts") and norm_item == "equipmentex") or \
                   (norm_mod_dir == os.path.normpath("archive/pc/mod") and norm_item in ["equipmentex.archive", "equipmentex.archive.xl"]):
                    print(f"Skipping core mod component: {item} in {mod_dir}")
                    continue
                source = os.path.join(full_dir, item)
                dest = os.path.join(temp_mod_dir, item)
                try:
                    shutil.move(source, dest)
                except Exception as e:
                    errors.append(f"Failed to disable {item} in {mod_dir}: {str(e)}")

    if errors:
        messagebox.showerror("Errors Occurred", "\n".join(errors))
        status_label.config(text="Some mods could not be disabled. Check details.")
    else:
        status_label.config(text="All mods have been disabled (Core Mods Protected).")
    update_mod_count_label()

def enable_all_mods():
    # Enable all mods by moving them back from 'Temporarily Disabled Mods' to original locations
    if is_game_running():
        messagebox.showwarning("Game Running", "Cannot modify mods while Cyberpunk 2077 is running!")
        return

    if not messagebox.askyesno("Confirm Enable", "This will move all mods back from 'Temporarily Disabled Mods' to their original locations and remove the folder. Proceed?"):
        return
    current_dir = os.getcwd()
    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
    errors = []

    if os.path.exists(temp_disabled_path):
        for mod_dir in MOD_DIRECTORIES:
            temp_mod_dir = os.path.join(temp_disabled_path, mod_dir)
            full_dir = os.path.join(current_dir, mod_dir)
            if os.path.exists(temp_mod_dir):
                os.makedirs(full_dir, exist_ok=True)
                for item in os.listdir(temp_mod_dir):
                    source = os.path.join(temp_mod_dir, item)
                    dest = os.path.join(full_dir, item)
                    try:
                        shutil.move(source, dest)
                    except Exception as e:
                        errors.append(f"Failed to enable {item} in {mod_dir}: {str(e)}")
                try:
                    if not os.listdir(temp_mod_dir):
                        os.rmdir(temp_mod_dir)
                except OSError as e:
                    errors.append(f"Failed to remove {temp_mod_dir}: {str(e)}")

        try:
            if os.path.exists(temp_disabled_path):
                if not os.listdir(temp_disabled_path):
                    os.rmdir(temp_disabled_path)
                else:
                    shutil.rmtree(temp_disabled_path, ignore_errors=True)
        except Exception as e:
            errors.append(f"Failed to remove {TEMP_DISABLED_DIR}: {str(e)}")

    if errors:
        messagebox.showerror("Errors Occurred", "\n".join(errors))
        status_label.config(text="Some mods could not be enabled or folder not fully removed. Check details.")
    else:
        status_label.config(text="All mods have been enabled and Temporarily Disabled Mods folder removed.")
    update_mod_count_label()

def cleanup_temp_disabled_folder(current_dir):
    # Remove the Temporarily Disabled Mods folder and its empty subdirectories if no mods remain
    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
    if not os.path.exists(temp_disabled_path):
        return

    for root, dirs, files in os.walk(temp_disabled_path, topdown=False):
        if files:
            print(f"Found files in {root}: {files}")
            return
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    print(f"Removed empty subdirectory: {dir_path}")
            except OSError as e:
                print(f"Failed to remove subdirectory {dir_path}: {str(e)}")

    try:
        if os.path.exists(temp_disabled_path):
            if not os.listdir(temp_disabled_path):
                os.rmdir(temp_disabled_path)
                print(f"Removed empty {TEMP_DISABLED_DIR} folder.")
            else:
                print(f"{TEMP_DISABLED_DIR} folder still contains items: {os.listdir(temp_disabled_path)}")
    except OSError as e:
        print(f"Failed to remove {TEMP_DISABLED_DIR} folder: {str(e)}")

def view_core_mods_status(current_dir):
    # Check if core dependency mods are installed and retrieve their versions
    status_data = {}
    for mod_name, info in CORE_DEPENDENCIES.items():
        is_installed = False
        paths = info["path"] if isinstance(info["path"], list) else [info["path"]]  # Handle single path or list of paths
        try:
            # For core mods which have multiple files this ensures that if the mod is not fully installed and missing files it will list that install is required
            if mod_name in ["ArchiveXL", "Codeware", "EquipmentEx", "RED4ext", "Redscript", "TweakXL"]:
                is_installed = all(os.path.exists(os.path.join(current_dir, path)) for path in paths)
            else:
                # For other mods, any path existing is sufficient
                is_installed = any(os.path.exists(os.path.join(current_dir, path)) for path in paths)
        except Exception as e:
            print(f"Error checking {mod_name} at {paths}: {e}")

        # Determine version based on mod (only applies to DLLs or CET log)
        version = None
        if mod_name in ["ArchiveXL", "RED4ext", "Codeware", "TweakXL"] and is_installed:
            # Use the DLL path for version checking
            dll_path = next((p for p in paths if p.endswith(".dll")), paths[0])  # Use first .dll file or first path
            version = get_dll_version(os.path.join(current_dir, dll_path))
        elif mod_name == "Cyber Engine Tweaks" and "log_path" in info and is_installed:
            log_path = os.path.join(current_dir, info["log_path"])
            version = get_cet_version(log_path)
        # EquipmentEx doesn't have a version check since it’s not a DLL or log-based

        status_data[mod_name] = {
            "installed": is_installed,
            "path": info["path"],  # Keep the original path structure (list or string)
            "version": version
        }
        print(f"Debug: Checking {mod_name} - Exists: {is_installed} - Version: {version if version else 'N/A'} - Paths: {paths}")
    return status_data

def view_mod_list():
    # Open a window to view and manage individual mods with a dropdown to filter by directory, excluding EquipmentEx files
    global mod_window_open
    if mod_window_open:
        messagebox.showinfo("Cyberpunk 2077 Mod List Tool", "Only one View Mod List window can be open at a time.")
        return

    current_dir = os.getcwd()
    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)

    mod_window = tk.Toplevel(window)
    mod_window.title("View Mod List")
    mod_window.geometry("1100x800")
    mod_window.resizable(True, True)
    mod_window.configure(bg="#000000")
    mod_window.protocol("WM_DELETE_WINDOW", lambda: on_mod_window_close(mod_window))

    screen_width = mod_window.winfo_screenwidth()
    screen_height = mod_window.winfo_screenheight()
    window_width = 1100
    window_height = 800
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    mod_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    if os.path.exists(ICON_PATH):
        try:
            mod_window.iconbitmap(ICON_PATH)
        except tk.TclError as e:
            print(f"Warning: Failed to set icon for View Mod List window from '{ICON_PATH}': {e}. Using default icon.")

    # Custom style for modern combobox
    style = ttk.Style()
    style.theme_use('clam')  # Use a theme that supports customization
    style.configure("Custom.TCombobox", 
                    fieldbackground="#1A1A1A", 
                    background="#1A1A1A", 
                    foreground="white", 
                    selectbackground="#333333", 
                    selectforeground="white", 
                    borderwidth=1, 
                    relief="flat")
    style.map("Custom.TCombobox", 
              fieldbackground=[("active", "#2A2A2A"), ("disabled", "#1A1A1A")],
              background=[("active", "#2A2A2A"), ("disabled", "#1A1A1A")])

    # Dropdown for selecting mod directory using ttk.Combobox
    selected_dir_var = tk.StringVar(value="All")
    combobox = ttk.Combobox(mod_window, textvariable=selected_dir_var, values=["All"] + MOD_DIRECTORIES, 
                            style="Custom.TCombobox", state="readonly")
    combobox.config(font=("Arial", 12))
    combobox.bind("<<ComboboxSelected>>", lambda event: update_mod_list(mod_window, selected_dir_var, mods))
    combobox.pack(pady=5, padx=10, fill=tk.X)

    # Mod data structure: {display_name: (original_dir, mod_name, current_path)}, excluding EquipmentEx
    mods = {}
    for mod_dir in MOD_DIRECTORIES:
        full_dir = os.path.join(current_dir, mod_dir)
        temp_mod_dir = os.path.join(temp_disabled_path, mod_dir)
        if os.path.exists(full_dir):
            for item in os.listdir(full_dir):
                # Skip EquipmentEx related files and folders
                if (os.path.normpath(mod_dir) == os.path.normpath("archive/pc/mod") and item.lower() in ["equipmentex.archive", "equipmentex.archive.xl"]) or \
                   (os.path.normpath(mod_dir) == os.path.normpath("r6/scripts") and item.lower() == "equipmentex"):
                    print(f"Excluding EquipmentEx file/folder from View Mod List: {item} ({mod_dir})")
                    continue
                display_name = f"{item} ({mod_dir})"
                mods[display_name] = (mod_dir, item, os.path.join(full_dir, item))
        if os.path.exists(temp_mod_dir):
            for item in os.listdir(temp_mod_dir):
                # Skip EquipmentEx related files and folders
                if (os.path.normpath(mod_dir) == os.path.normpath("archive/pc/mod") and item.lower() in ["equipmentex.archive", "equipmentex.archive.xl"]) or \
                   (os.path.normpath(mod_dir) == os.path.normpath("r6/scripts") and item.lower() == "equipmentex"):
                    print(f"Excluding EquipmentEx file/folder from View Mod List: {item} ({mod_dir})")
                    continue
                display_name = f"{item} ({mod_dir})"
                mods[display_name] = (mod_dir, item, os.path.join(temp_mod_dir, item))

    enabled_frame = tk.Frame(mod_window, bg="#000000")
    enabled_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)
    disabled_frame = tk.Frame(mod_window, bg="#000000")
    disabled_frame.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.BOTH, expand=True)

    tk.Label(enabled_frame, text="Enabled Mods", font=("Arial", 12), fg="white", bg="#000000").pack()
    enabled_list_frame = tk.Frame(enabled_frame, bg="#000000")
    enabled_list_frame.pack(pady=5, fill=tk.BOTH, expand=True)
    enabled_scrollbar = tk.Scrollbar(enabled_list_frame, orient=tk.VERTICAL)
    enabled_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    enabled_listbox = tk.Listbox(enabled_list_frame, font=("Arial", 10), width=40, bg="#333333", fg="white", selectmode=tk.EXTENDED)
    enabled_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    enabled_listbox.config(yscrollcommand=enabled_scrollbar.set)
    enabled_scrollbar.config(command=enabled_listbox.yview)

    tk.Label(disabled_frame, text="Disabled Mods", font=("Arial", 12), fg="white", bg="#000000").pack()
    disabled_list_frame = tk.Frame(disabled_frame, bg="#000000")
    disabled_list_frame.pack(pady=5, fill=tk.BOTH, expand=True)
    disabled_scrollbar = tk.Scrollbar(disabled_list_frame, orient=tk.VERTICAL)
    disabled_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    disabled_listbox = tk.Listbox(disabled_list_frame, font=("Arial", 10), width=40, bg="#333333", fg="white", selectmode=tk.EXTENDED)
    disabled_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    disabled_listbox.config(yscrollcommand=disabled_scrollbar.set)
    disabled_scrollbar.config(command=disabled_listbox.yview)

    def update_mod_list(window, var, mod_dict):
        # Update the mod list based on the selected directory
        selected_dir = var.get()
        enabled_listbox.delete(0, tk.END)
        disabled_listbox.delete(0, tk.END)

        for display_name, (mod_dir, mod_name, current_path) in sorted(mod_dict.items()):
            if selected_dir == "All" or mod_dir == selected_dir:
                if TEMP_DISABLED_DIR in current_path:
                    disabled_listbox.insert(tk.END, display_name)
                else:
                    enabled_listbox.insert(tk.END, display_name)

    def disable_selected():
        if is_game_running():
            messagebox.showwarning("Cyberpunk 2077 Mod List Tool", "Cannot modify mods while Cyberpunk 2077 is running!")
            return

        selected = enabled_listbox.curselection()
        if not selected:
            return
        errors = []
        for idx in selected[::-1]:
            display_name = enabled_listbox.get(idx)
            mod_dir, mod_name, current_path = mods[display_name]
            dest_dir = os.path.join(temp_disabled_path, mod_dir)
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, mod_name)
            try:
                shutil.move(current_path, dest)
                mods[display_name] = (mod_dir, mod_name, dest)
                enabled_listbox.delete(idx)
                disabled_listbox.insert(tk.END, display_name)
            except Exception as e:
                errors.append(f"Failed to disable {display_name}: {str(e)}")
        if errors:
            messagebox.showerror("Errors Occurred", "\n".join(errors))
        update_mod_count_label()
        update_mod_list(mod_window, selected_dir_var, mods)  # Refresh list after modification

    def enable_selected():
        if is_game_running():
            messagebox.showwarning("Game Running", "Cannot modify mods while Cyberpunk 2077 is running!")
            return

        selected = disabled_listbox.curselection()
        if not selected:
            return
        errors = []
        for idx in selected[::-1]:
            display_name = disabled_listbox.get(idx)
            mod_dir, mod_name, current_path = mods[display_name]
            dest_dir = os.path.join(current_dir, mod_dir)
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, mod_name)
            try:
                shutil.move(current_path, dest)
                mods[display_name] = (mod_dir, mod_name, dest)
                disabled_listbox.delete(idx)
            except Exception as e:
                errors.append(f"Failed to enable {display_name}: {str(e)}")
        if errors:
            messagebox.showerror("Errors Occurred", "\n".join(errors))
        else:
            cleanup_temp_disabled_folder(current_dir)

        enabled_listbox.delete(0, tk.END)
        disabled_listbox.delete(0, tk.END)
        mods.clear()
        for mod_dir in MOD_DIRECTORIES:
            full_dir = os.path.join(current_dir, mod_dir)
            temp_mod_dir = os.path.join(temp_disabled_path, mod_dir)
            if os.path.exists(full_dir):
                for item in os.listdir(full_dir):
                    # Skip EquipmentEx related files and folders
                    if (os.path.normpath(mod_dir) == os.path.normpath("archive/pc/mod") and item.lower() in ["equipmentex.archive", "equipmentex.archive.xl"]) or \
                       (os.path.normpath(mod_dir) == os.path.normpath("r6/scripts") and item.lower() == "equipmentex"):
                        print(f"Excluding EquipmentEx file/folder from View Mod List: {item} ({mod_dir})")
                        continue
                    display_name = f"{item} ({mod_dir})"
                    mods[display_name] = (mod_dir, item, os.path.join(full_dir, item))
            if os.path.exists(temp_mod_dir):
                for item in os.listdir(temp_mod_dir):
                    # Skip EquipmentEx related files and folders
                    if (os.path.normpath(mod_dir) == os.path.normpath("archive/pc/mod") and item.lower() in ["equipmentex.archive", "equipmentex.archive.xl"]) or \
                       (os.path.normpath(mod_dir) == os.path.normpath("r6/scripts") and item.lower() == "equipmentex"):
                        print(f"Excluding EquipmentEx file/folder from View Mod List: {item} ({mod_dir})")
                        continue
                    display_name = f"{item} ({mod_dir})"
                    mods[display_name] = (mod_dir, item, os.path.join(temp_mod_dir, item))
        update_mod_count_label()
        update_mod_list(mod_window, selected_dir_var, mods)  # Refresh list after modification

    disable_selected_button = tk.Button(enabled_frame, text="Disable Selected", command=disable_selected, font=("Arial", 12), bg="#FF0000", fg="white")
    disable_selected_button.pack(pady=5)

    enable_selected_button = tk.Button(disabled_frame, text="Enable Selected", command=enable_selected, font=("Arial", 12), bg="#00FF00", fg="black")
    enable_selected_button.pack(pady=5)

    disable_selected_button.bind("<Enter>", lambda e: disable_selected_button.config(bg="#CC0000", fg="white"))
    disable_selected_button.bind("<Leave>", lambda e: disable_selected_button.config(bg="#FF0000", fg="white"))
    enable_selected_button.bind("<Enter>", lambda e: enable_selected_button.config(bg="#00CC00", fg="black"))
    enable_selected_button.bind("<Leave>", lambda e: enable_selected_button.config(bg="#00FF00", fg="black"))

    # Calculates the initial mod list
    update_mod_list(mod_window, selected_dir_var, mods)
    mod_window_open = True

def on_mod_window_close(mod_window):
    # Handle closing of the View Mod List window
    global mod_window_open
    mod_window_open = False
    mod_window.destroy()

def view_core_mods():
    # Open a window to view the status of the core mods
    global core_window_open
    if core_window_open:
        messagebox.showinfo("Window Limit", "Only one Core Mods Status window can be open at a time.")
        return

    current_dir = os.getcwd()
    core_window = tk.Toplevel(window)
    core_window.title("Core Mods Status")
    core_window.geometry("400x250")
    core_window.resizable(False, False)
    core_window.configure(bg="#000000")
    core_window.protocol("WM_DELETE_WINDOW", lambda: on_core_window_close(core_window))

    screen_width = core_window.winfo_screenwidth()
    screen_height = core_window.winfo_screenheight()
    window_width = 400
    window_height = 250
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    core_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    if os.path.exists(ICON_PATH):
        try:
            core_window.iconbitmap(ICON_PATH)
        except tk.TclError as e:
            print(f"Warning: Failed to set icon for Core Mods Status window from '{ICON_PATH}': {e}. Using default icon.")

    main_frame = tk.Frame(core_window, bg="#000000")
    main_frame.pack(expand=True)

    # Store previous status to detect changes
    previous_status = {}

    def update_status():
        # Update the Core Mods Status window with current status
        nonlocal previous_status

        # Check current status
        try:
            status_data = view_core_mods_status(current_dir)
        except Exception as e:
            print(f"Error in status update: {e}")
            status_data = {mod_name: {"installed": False, "path": info["path"], "version": None} 
                          for mod_name, info in CORE_DEPENDENCIES.items()}  # Fallback to all not installed

        # Check if status has changed
        if previous_status != status_data:
            # Clear the frame
            for widget in main_frame.winfo_children():
                widget.destroy()

            # Display all core mods with status and clickable names
            for i, (mod_name, info) in enumerate(status_data.items()):
                frame = tk.Frame(main_frame, bg="#000000")
                frame.pack(fill=tk.X, padx=10, pady=5)

                # Clickable mod name
                name_label = tk.Label(frame, text=mod_name, font=("Arial", 10, "bold"), fg="white", bg="#000000", cursor="hand2")
                name_label.pack(side=tk.LEFT)
                name_label.bind("<Button-1>", lambda e, id=CORE_DEPENDENCIES[mod_name]["id"]: webbrowser.open(f"https://www.nexusmods.com/cyberpunk2077/mods/{id}"))

                # Version (if applicable and not "Unknown")
                if info["version"] and info["version"] != "Unknown":
                    version_label = tk.Label(frame, text=f"v{info['version']}", font=("Arial", 10), fg="white", bg="#000000")
                    version_label.pack(side=tk.LEFT, padx=5)

                # Installation status with checkbox symbol
                status_text = "Installed" if info["installed"] else "Not Installed"
                status_color = "green" if info["installed"] else "red"
                status_symbol = "✔" if info["installed"] else "✘"
                install_status = tk.Label(frame, text=f"{status_symbol} {status_text}", font=("Arial", 10), 
                                         fg=status_color, bg="#000000")
                install_status.pack(side=tk.LEFT, padx=5)

                # Install button if not installed
                if not info["installed"]:
                    install_button = tk.Button(frame, text="Install", 
                                               command=lambda name=mod_name: webbrowser.open(f"https://www.nexusmods.com/cyberpunk2077/mods/{CORE_DEPENDENCIES[name]['id']}"), 
                                               font=("Arial", 10), bg="#00FF00", fg="black")
                    install_button.pack(side=tk.RIGHT, padx=5)

        # Update previous status
        previous_status = status_data.copy()

        # Schedule the next update
        if core_window.winfo_exists():
            core_window.after(2000, update_status)  # Check every 2 seconds

    # Initial update
    update_status()
    core_window_open = True

def on_core_window_close(core_window):
    # Handle closing of the Core Mods window
    global core_window_open
    core_window_open = False
    core_window.destroy()

class ModChangeHandler(FileSystemEventHandler):
    # Handle file system events for mod directories
    def on_created(self, event):
        # Called when a file or directory is created
        if not event.is_directory:  # Only count files, not directories (except for CET mods)
            update_mod_count_label()
        elif os.path.normpath(os.path.relpath(event.src_path, current_dir)).startswith("bin/x64/plugins/cyber_engine_tweaks/mods"):
            update_mod_count_label()

    def on_deleted(self, event):
        # Called when a file or directory is deleted
        if not event.is_directory:  # Only count files, not directories (except for CET mods)
            update_mod_count_label()
        elif os.path.normpath(os.path.relpath(event.src_path, current_dir)).startswith("bin/x64/plugins/cyber_engine_tweaks/mods"):
            update_mod_count_label()

    def on_moved(self, event):
        # Called when a file or directory is moved or renamed
        if not event.is_directory:  # Only count files, not directories (except for CET mods)
            update_mod_count_label()
        elif os.path.normpath(os.path.relpath(event.src_path, current_dir)).startswith("bin/x64/plugins/cyber_engine_tweaks/mods") or \
             (event.dest_path and os.path.normpath(os.path.relpath(event.dest_path, current_dir)).startswith("bin/x64/plugins/cyber_engine_tweaks/mods")):
            update_mod_count_label()

def start_mod_watcher():
    # Looks for changes to the mod directories
    global mod_observer
    current_dir = os.getcwd()
    event_handler = ModChangeHandler()
    mod_observer = Observer()
    for mod_dir in MOD_DIRECTORIES:
        full_dir = os.path.join(current_dir, mod_dir)
        if os.path.exists(full_dir):
            mod_observer.schedule(event_handler, full_dir, recursive=False)
    mod_observer.start()
    return mod_observer

def update_mod_count_label():
    # Updates the mod count label based on current enabled mods, excluding core mods
    current_dir = os.getcwd()
    mod_count = 0
    for mod_dir in MOD_DIRECTORIES:
        full_dir = os.path.join(current_dir, mod_dir)
        if os.path.exists(full_dir):
            for item in os.listdir(full_dir):
                # Normalize paths and check for EquipmentEx files
                norm_mod_dir = os.path.normpath(mod_dir)
                norm_item = item.lower()
                if (norm_mod_dir == os.path.normpath("archive/pc/mod") and norm_item in ["equipmentex.archive", "equipmentex.archive.xl"]) or \
                   (norm_mod_dir == os.path.normpath("r6/scripts") and norm_item == "equipmentex"):
                    print(f"Excluding EquipmentEx file/folder from mod count: {item} ({mod_dir})")
                    continue
                if norm_mod_dir == os.path.normpath("bin/x64/plugins/cyber_engine_tweaks/mods"):
                    if os.path.isdir(os.path.join(full_dir, item)):
                        mod_count += 1
                        print(f"Counting directory mod: {item} in {mod_dir}")
                else:
                    mod_count += 1
                    print(f"Counting file mod: {item} in {mod_dir}")
    mod_count_label.config(text=f"Total Mods: {mod_count}")
    print(f"Updated mod count: {mod_count}")

def extract_log_errors(log_path):
    # Extract lines containing potential errors from a log file
    error_keywords = ["error", "failed", "exception", "warning"]
    errors = []
    if not os.path.exists(log_path):
        return errors

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and any(keyword in line.lower() for keyword in error_keywords):
                    errors.append(f"Line {line_num}: {line}")
    except (OSError, UnicodeDecodeError) as e:
        errors.append(f"Error reading log file: {str(e)}")
    return errors

def check_log_errors(current_dir):
    # Check for errors in log files and return True if errors are found
    log_files = {
        "ArchiveXL": os.path.join(current_dir, "red4ext", "plugins", "ArchiveXL", "ArchiveXL.log"),
        "Codeware": os.path.join(current_dir, "red4ext", "plugins", "Codeware", "Codeware.log"),
        "TweakXL": os.path.join(current_dir, "red4ext", "plugins", "TweakXL", "TweakXL.log")
    }
    log_errors = {}
    for log_name, log_path in log_files.items():
        errors = extract_log_errors(log_path)
        if errors:
            log_errors[log_name] = errors
    return bool(log_errors)

def write_items_from_dir(file, directory, folder_name, temp_dir):
    """Write mod items from a directory and its disabled counterpart to the file."""
    if os.path.exists(directory):
        file.write(f"\nMods located in {folder_name}:\n")
        file.write("-" * 120 + "\n")
        if folder_name == "bin/x64/plugins/cyber_engine_tweaks/mods":
            for item in os.listdir(directory):
                full_path = os.path.join(directory, item)
                if os.path.isdir(full_path):
                    norm_folder_name = os.path.normpath(folder_name)
                    norm_item = item.lower()
                    if (norm_folder_name == os.path.normpath("archive/pc/mod") and norm_item in ["equipmentex.archive", "equipmentex.archive.xl"]) or \
                       (norm_folder_name == os.path.normpath("r6/scripts") and norm_item == "equipmentex"):
                        print(f"Excluding EquipmentEx file/folder from mod list in .txt: {item} ({folder_name})")
                        continue
                    file.write(f"{item}\n")
                    print(f"Wrote directory mod: {item} in {folder_name}")
        else:
            for item in os.listdir(directory):
                norm_folder_name = os.path.normpath(folder_name)
                norm_item = item.lower()
                if (norm_folder_name == os.path.normpath("archive/pc/mod") and norm_item in ["equipmentex.archive", "equipmentex.archive.xl"]) or \
                   (norm_folder_name == os.path.normpath("r6/scripts") and norm_item == "equipmentex"):
                    print(f"Excluding EquipmentEx file/folder from mod list in .txt: {item} ({folder_name})")
                    continue
                file.write(f"{item}\n")
                print(f"Wrote file mod: {item} in {folder_name}")
    else:
        file.write(f"\nError: The subfolder(s) {folder_name} were not found in the current location!\n")
    
    disabled_dir = os.path.join(temp_dir, folder_name)
    if os.path.exists(disabled_dir):
        file.write(f"\nDisabled mods in {TEMP_DISABLED_DIR}/{folder_name}:\n")
        file.write("-" * 120 + "\n")
        if folder_name == "bin/x64/plugins/cyber_engine_tweaks/mods":
            for item in os.listdir(disabled_dir):
                full_path = os.path.join(disabled_dir, item)
                if os.path.isdir(full_path):
                    norm_folder_name = os.path.normpath(folder_name)
                    norm_item = item.lower()
                    if (norm_folder_name == os.path.normpath("archive/pc/mod") and norm_item in ["equipmentex.archive", "equipmentex.archive.xl"]) or \
                       (norm_folder_name == os.path.normpath("r6/scripts") and norm_item == "equipmentex"):
                        print(f"Excluding EquipmentEx file/folder from disabled mod list in .txt: {item} ({folder_name})")
                        continue
                    file.write(f"{item}\n")
                    print(f"Wrote disabled directory mod: {item} in {folder_name}")
        else:
            for item in os.listdir(disabled_dir):
                norm_folder_name = os.path.normpath(folder_name)
                norm_item = item.lower()
                if (norm_folder_name == os.path.normpath("archive/pc/mod") and norm_item in ["equipmentex.archive", "equipmentex.archive.xl"]) or \
                   (norm_folder_name == os.path.normpath("r6/scripts") and norm_item == "equipmentex"):
                    print(f"Excluding EquipmentEx file/folder from disabled mod list in .txt: {item} ({folder_name})")
                    continue
                file.write(f"{item}\n")
                print(f"Wrote disabled file mod: {item} in {folder_name}")

def export_mods():
    # Export selected mod folders to a ZIP file with a progress bar
    if is_game_running():
        messagebox.showwarning("Game Running", "Cannot export mods while Cyberpunk 2077 is running!")
        return

    current_dir = os.getcwd()

    selection_window = tk.Toplevel(window)
    selection_window.title("Select Mod Folders to Export")
    selection_window.geometry("300x200")
    selection_window.resizable(False, False)
    selection_window.configure(bg="#000000")
    selection_window.transient(window)
    selection_window.grab_set()

    if os.path.exists(ICON_PATH):
        try:
            selection_window.iconbitmap(ICON_PATH)
        except tk.TclError as e:
            print(f"Warning: Failed to set icon for Selection window from '{ICON_PATH}': {e}. Using default icon.")

    screen_width = selection_window.winfo_screenwidth()
    screen_height = selection_window.winfo_screenheight()
    window_width = 300
    window_height = 200
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    selection_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    folder_vars = {mod_dir: tk.BooleanVar(value=True) for mod_dir in MOD_DIRECTORIES}
    for i, mod_dir in enumerate(MOD_DIRECTORIES):
        full_dir = os.path.join(current_dir, mod_dir)
        enabled = os.path.exists(full_dir)
        cb = tk.Checkbutton(selection_window, text=mod_dir, variable=folder_vars[mod_dir],
                            font=("Arial", 10), bg="#000000", fg="white", selectcolor="#333333",
                            activebackground="#000000", activeforeground="white", state="normal" if enabled else "disabled")
        cb.pack(pady=5, anchor="w", padx=10)

    def on_confirm():
        selected_folders = [mod_dir for mod_dir, var in folder_vars.items() if var.get() and os.path.exists(os.path.join(current_dir, mod_dir))]
        if not selected_folders:
            messagebox.showwarning("No Selection", "Please select at least one mod folder to export.")
        else:
            selection_window.destroy()
            _export_with_progress(selected_folders)

    confirm_button = tk.Button(selection_window, text="Confirm", command=on_confirm, font=("Arial", 12),
                               bg="#00FF00", fg="black")
    confirm_button.pack(pady=10)
    confirm_button.bind("<Enter>", lambda e: confirm_button.config(bg="#00CC00", fg="black"))
    confirm_button.bind("<Leave>", lambda e: confirm_button.config(bg="#00FF00", fg="black"))

    selection_window.wait_window()

def _export_with_progress(selected_folders):
    # Helper function to handle the export process with progress bar
    current_dir = os.getcwd()
    default_filename = f"Mod_Preset_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    save_path = filedialog.asksaveasfilename(
        defaultextension=".zip",
        filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
        initialfile=default_filename,
        title="Save Mod Preset As"
    )
    if not save_path:
        return

    progress_window = tk.Toplevel(window)
    progress_window.title("Exporting Mod Preset")
    progress_window.geometry("300x100")
    progress_window.resizable(False, False)
    progress_window.configure(bg="#000000")
    progress_window.transient(window)
    progress_window.grab_set()

    if os.path.exists(ICON_PATH):
        try:
            progress_window.iconbitmap(ICON_PATH)
        except tk.TclError as e:
            print(f"Warning: Failed to set icon for Progress window from '{ICON_PATH}': {e}. Using default icon.")

    screen_width = progress_window.winfo_screenwidth()
    screen_height = progress_window.winfo_screenheight()
    window_width = 300
    window_height = 100
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    progress_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    tk.Label(progress_window, text="Exporting mod preset...", fg="white", bg="#000000", font=("Arial", 10)).pack(pady=10)
    progress_bar = ttk.Progressbar(progress_window, length=250, mode="determinate")
    progress_bar.pack(pady=10)
    status_label_progress = tk.Label(progress_window, text="", fg="white", bg="#000000", font=("Arial", 8))
    status_label_progress.pack()

    total_files = 0
    for mod_dir in selected_folders:
        full_dir = os.path.join(current_dir, mod_dir)
        if os.path.exists(full_dir):
            for root, _, files in os.walk(full_dir):
                total_files += len(files)
    if total_files == 0:
        messagebox.showinfo("No Mods", "No mods found to export in the selected folders.")
        progress_window.destroy()
        return

    progress_bar["maximum"] = total_files
    progress_bar["value"] = 0
    progress_window.update()

    errors = []
    files_processed = 0
    with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for mod_dir in selected_folders:
            full_dir = os.path.join(current_dir, mod_dir)
            if os.path.exists(full_dir):
                for root, _, files in os.walk(full_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, current_dir)
                        try:
                            zipf.write(file_path, arcname)
                            files_processed += 1
                            progress_bar["value"] = files_processed
                            status_label_progress.config(text=f"Processing: {files_processed}/{total_files}")
                            progress_window.update()
                        except Exception as e:
                            errors.append(f"Failed to add {file_path} to archive: {str(e)}")

    progress_window.destroy()

    if errors:
        messagebox.showerror("Export Errors", "\n".join(errors))
        status_label.config(text="Mod preset export completed with errors. Check details.")
    else:
        messagebox.showinfo("Export Successful", f"Mod preset exported to {save_path}")
        status_label.config(text="Mod preset exported successfully!")
    update_mod_count_label()

def run_script():
    current_dir = os.getcwd()
    game_path = os.path.join(current_dir, "bin", "x64", "Cyberpunk2077.exe")
    game_version = get_game_version(game_path)
    phantom_liberty_installed = is_phantom_liberty_installed(current_dir)

    if not os.path.exists(os.path.join(current_dir, "archive")):
        status_label.config(text="Application not installed in the correct location!")
        mod_count_label.place_forget()
        game_version_label.place_forget()
        log_errors_label.place_forget()
        pl_dlc_label.place_forget()
        include_logs_checkbox.place_forget()
        return False

    include_logs_checkbox.place(relx=0.5, y=450, anchor="center")

    now = datetime.datetime.now()
    archivemods = os.path.join("archive", "pc", "mod")
    cetmods = os.path.join("bin/x64/plugins/cyber_engine_tweaks/mods")
    r6scripts = os.path.join("r6", "scripts")
    r6tweaks = os.path.join("r6", "tweaks")
    archivexl = os.path.join("red4ext", "plugins", "ArchiveXL")
    codeware = os.path.join("red4ext", "plugins", "Codeware")
    tweakxl = os.path.join("red4ext", "plugins", "TweakXL")
    path1 = os.path.join(current_dir, archivemods)
    path2 = os.path.join(current_dir, cetmods)
    path3 = os.path.join(current_dir, r6scripts)
    path4 = os.path.join(current_dir, r6tweaks)

    mod_count = 0
    for path in [path1, path2, path3, path4]:
        if os.path.exists(path):
            mod_dir = os.path.relpath(path, current_dir)
            for item in os.listdir(path):
                norm_mod_dir = os.path.normpath(mod_dir)
                norm_item = item.lower()
                if (norm_mod_dir == os.path.normpath("archive/pc/mod") and norm_item in ["equipmentex.archive", "equipmentex.archive.xl"]) or \
                   (norm_mod_dir == os.path.normpath("r6/scripts") and norm_item == "equipmentex"):
                    print(f"Excluding EquipmentEx file/folder from mod count in run_script: {item} ({mod_dir})")
                    continue
                if norm_mod_dir == os.path.normpath("bin/x64/plugins/cyber_engine_tweaks/mods"):
                    if os.path.isdir(os.path.join(path, item)):
                        mod_count += 1
                        print(f"Counting directory mod: {item} in {mod_dir}")
                else:
                    mod_count += 1
                    print(f"Counting file mod: {item} in {mod_dir}")

    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)

    log_files = {
        "ArchiveXL": os.path.join(archivexl, "ArchiveXL.log"),
        "Codeware": os.path.join(codeware, "Codeware.log"),
        "TweakXL": os.path.join(tweakxl, "TweakXL.log")
    }
    log_errors = {}
    for log_name, log_path in log_files.items():
        errors = extract_log_errors(log_path)
        if errors:
            log_errors[log_name] = errors

    all_core_mods_installed = True
    for mod_name, info in CORE_DEPENDENCIES.items():
        paths = info["path"] if isinstance(info["path"], list) else [info["path"]]
        if mod_name == "EquipmentEx":
            if not all(os.path.exists(os.path.join(current_dir, path)) for path in paths):
                all_core_mods_installed = False
                break
        else:
            if not any(os.path.exists(os.path.join(current_dir, path)) for path in paths):
                all_core_mods_installed = False
                break

    with open('Cyberpunk 2077 Mod List.txt', 'w') as file:
        file.write(f"Cyberpunk 2077 Mod List Tool v{tool_Version} by Sammmy1036\n")
        file.write(f"Nexus Mod Page https://www.nexusmods.com/cyberpunk2077/mods/20113\n")
        file.write(f"List created on {now.strftime('%B %d, %Y at %I:%M:%S %p')}\n")
        file.write(f"Game Version: {game_version} | Phantom Liberty DLC Installed: {'Yes' if phantom_liberty_installed else 'No'}\n")
        file.write(f"All Core Mods Installed: {'Yes' if all_core_mods_installed else 'No'}\n")
        file.write(f"Total Mods Installed: {mod_count}\n")
        file.write("-" * 120 + "\n")

        if log_errors:
            file.write("\nPotential Errors to Review\n")
            file.write("=" * 120 + "\n")
            for log_name, errors in log_errors.items():
                file.write(f"\n{log_name} Errors:\n")
                file.write("-" * 120 + "\n")
                for error in errors:
                    file.write(f"{error}\n")
            file.write("=" * 120 + "\n")

        # Call write_items_from_dir for each directory
        write_items_from_dir(file, path1, archivemods, temp_disabled_path)
        write_items_from_dir(file, path2, cetmods, temp_disabled_path)
        write_items_from_dir(file, path3, r6scripts, temp_disabled_path)
        write_items_from_dir(file, path4, r6tweaks, temp_disabled_path)

        if include_logs_var.get():
            for log_name, primary_log_path in log_files.items():
                log_dir = os.path.dirname(primary_log_path)
                file.write(f"\n{log_name} Log:\n")
                file.write("-" * 120 + "\n")
                
                # Try the primary log file first
                log_path_to_use = primary_log_path
                log_read_success = False
                
                if os.path.exists(log_path_to_use):
                    try:
                        with open(log_path_to_use, 'r', encoding='utf-8') as input_file:
                            log_content = input_file.read()
                            file.write(log_content)
                            file.write("\n")
                            log_read_success = True
                    except (OSError, UnicodeDecodeError) as e:
                        file.write(f"Error reading {log_name}.log: {str(e)}\n")
                
                # If primary log doesn't exist or can't be read, try the most recent log
                if not log_read_success:
                    recent_log = get_most_recent_log(log_dir, log_name)
                    if recent_log:
                        log_path_to_use = recent_log
                        try:
                            with open(log_path_to_use, 'r', encoding='utf-8') as input_file:
                                file.write(f"Using most recent log file: {os.path.basename(log_path_to_use)}\n")
                                log_content = input_file.read()
                                file.write(log_content)
                                file.write("\n")
                                log_read_success = True
                        except (OSError, UnicodeDecodeError) as e:
                            file.write(f"Error reading recent {log_name} log ({os.path.basename(log_path_to_use)}): {str(e)}\n")
                
                # If no log could be read, write the not found message
                if not log_read_success:
                    file.write(f"The {log_name} log could not be found or read! Log not provided!\n")

    mod_count_label.place(x=10, y=760)
    game_version_label.place(x=10, y=780)
    log_errors_label.place(x=430, y=760)
    pl_dlc_label.place(x=430, y=780)
    mod_count_label.config(text=f"Total Mods: {mod_count}")
    game_version_label.config(text=f"Game Version: {game_version}")
    log_errors_label.config(text=f"Log Errors Detected: {'Yes' if log_errors else 'No'}")
    pl_dlc_label.config(text=f"Core Mods Installed: {'Yes' if all_core_mods_installed else 'No'}")
    status_label.config(text="Success! Check Cyberpunk 2077 Mod List.txt")
    return bool(log_errors)

def open_url(event):
    webbrowser.open("https://www.nexusmods.com/cyberpunk2077/mods/20113")

if not check_single_instance():
    messagebox.showinfo("Cyberpunk 2077 Mod List Tool", "Another instance of Cyberpunk 2077 Mod List Tool is already running.")
    sys.exit(0)

window = tk.Tk()
window.title("Cyberpunk 2077 Mod List Tool")
window.geometry("600x800")
window.resizable(False, False)
window.configure(bg="#000000")

screen_width = window.winfo_screenwidth()
screen_height = window.winfo_screenheight()
x = (screen_width - 600) // 2
y = (screen_height - 800) // 2
window.geometry(f"+{x}+{y}")

if os.path.exists(ICON_PATH):
    try:
        window.iconbitmap(ICON_PATH)
    except tk.TclError as e:
        print(f"Warning: Failed to set icon from '{ICON_PATH}': {e}. Using default icon.")

current_dir = os.getcwd()
game_path = os.path.join(current_dir, "bin", "x64", "Cyberpunk2077.exe")
initial_game_version = get_game_version(game_path)
initial_phantom_liberty_installed = is_phantom_liberty_installed(current_dir)
initial_log_errors = check_log_errors(current_dir)

# Check if all core mods are installed for initial UI setup
initial_all_core_mods_installed = True
for mod_name, info in CORE_DEPENDENCIES.items():
    paths = info["path"] if isinstance(info["path"], list) else [info["path"]]
    if mod_name == "EquipmentEx":
        # For EquipmentEx, all paths must exist
        if not all(os.path.exists(os.path.join(current_dir, path)) for path in paths):
            initial_all_core_mods_installed = False
            break
    else:
        # For other mods, any path existing is sufficient
        if not any(os.path.exists(os.path.join(current_dir, path)) for path in paths):
            initial_all_core_mods_installed = False
            break

initial_mod_count = 0
for mod_dir in MOD_DIRECTORIES:
    full_dir = os.path.join(current_dir, mod_dir)
    if os.path.exists(full_dir):
        for item in os.listdir(full_dir):
            # Normalize paths and check for EquipmentEx files
            norm_mod_dir = os.path.normpath(mod_dir)
            norm_item = item.lower()
            if (norm_mod_dir == os.path.normpath("archive/pc/mod") and norm_item in ["equipmentex.archive", "equipmentex.archive.xl"]) or \
               (norm_mod_dir == os.path.normpath("r6/scripts") and norm_item == "equipmentex"):
                print(f"Excluding EquipmentEx file/folder from initial mod count: {item} ({mod_dir})")
                continue
            if norm_mod_dir == os.path.normpath("bin/x64/plugins/cyber_engine_tweaks/mods"):
                if os.path.isdir(os.path.join(full_dir, item)):
                    initial_mod_count += 1
                    print(f"Counting directory mod: {item} in {mod_dir}")
            else:
                initial_mod_count += 1
                print(f"Counting file mod: {item} in {mod_dir}")

try:
    image = tk.PhotoImage(file=IMAGE_PATH)
    orig_width = image.width()
    orig_height = image.height()
    if orig_width != 600 or orig_height != 800:
        image = image.zoom(600 // orig_width, 800 // orig_height)
    image_label = tk.Label(window, image=image)
    image_label.place(x=0, y=0, width=600, height=800)
    image_label.image = image
except tk.TclError as e:
    print(f"Error loading image: {e}")  # Debug print for image loading failure
    image_label = tk.Label(window, text=f"Error loading image: {e}", fg="red", bg="black")
    image_label.place(x=0, y=0)

status_label = tk.Label(window, text="Click 'Start' to compile the list!", font=("Arial", 12))
status_label.place(relx=0.5, rely=0.50, anchor="center")

start_button = tk.Button(window, text="Start", command=run_script, font=("Arial", 14), width=10,
                         bg="#FEFE00", fg="black")
start_button.place(relx=0.5, y=335, anchor="center")

include_logs_var = tk.BooleanVar(value=True)
include_logs_checkbox = tk.Checkbutton(window, text="Include Logs", variable=include_logs_var,
                                       font=("Arial", 12), bg="#000000", fg="white", selectcolor="#333333",
                                       activebackground="#000000", activeforeground="white")

core_mods_button = tk.Button(window, text="Core Mods Status", command=view_core_mods, font=("Arial", 12), width=15,
                             bg="#00FFFF", fg="black")
more_options_button = tk.Button(window, text="More Options", command=toggle_mod_buttons, font=("Arial", 12), width=15,
                               bg="#FFFF00", fg="black")
if os.path.exists(os.path.join(current_dir, "archive")):
    core_mods_button.place(relx=0.5, y=500, anchor="center")
    more_options_button.place(relx=0.5, y=550, anchor="center")
else:
    status_label.config(text="Please place application in the Cyberpunk 2077 Directory!")

disable_button = tk.Button(window, text="Disable All Mods", command=disable_all_mods, font=("Arial", 12), width=15,
                           bg="#FF0000", fg="white")

enable_button = tk.Button(window, text="Enable All Mods", command=enable_all_mods, font=("Arial", 12), width=15,
                          bg="#00FF00", fg="black")

view_mod_list_button = tk.Button(window, text="View Mod List", command=view_mod_list, font=("Arial", 12), width=15,
                                 bg="#FFFF00", fg="black")

export_mod_preset_button = tk.Button(window, text="Export Mod Preset", command=export_mods, font=("Arial", 12), width=15,
                                     bg="#00FFFF", fg="black")

start_button.bind("<Enter>", lambda e: start_button.config(bg="#D4D400", fg="black"))
start_button.bind("<Leave>", lambda e: start_button.config(bg="#FEFE00", fg="black"))
include_logs_checkbox.bind("<Enter>", lambda e: include_logs_checkbox.config(bg="#1A1A1A", fg="white"))
include_logs_checkbox.bind("<Leave>", lambda e: include_logs_checkbox.config(bg="#000000", fg="white"))
core_mods_button.bind("<Enter>", lambda e: core_mods_button.config(bg="#00CCCC", fg="black"))
core_mods_button.bind("<Leave>", lambda e: core_mods_button.config(bg="#00FFFF", fg="black"))
more_options_button.bind("<Enter>", lambda e: more_options_button.config(bg="#E6E600", fg="black"))
more_options_button.bind("<Leave>", lambda e: more_options_button.config(bg="#FFFF00", fg="black"))
disable_button.bind("<Enter>", lambda e: disable_button.config(bg="#CC0000", fg="white"))
disable_button.bind("<Leave>", lambda e: disable_button.config(bg="#FF0000", fg="white"))
enable_button.bind("<Enter>", lambda e: enable_button.config(bg="#00CC00", fg="black"))
enable_button.bind("<Leave>", lambda e: enable_button.config(bg="#00FF00", fg="black"))
view_mod_list_button.bind("<Enter>", lambda e: view_mod_list_button.config(bg="#E6E600", fg="black"))
view_mod_list_button.bind("<Leave>", lambda e: view_mod_list_button.config(bg="#FFFF00", fg="black"))
export_mod_preset_button.bind("<Enter>", lambda e: export_mod_preset_button.config(bg="#00CCCC", fg="black"))
export_mod_preset_button.bind("<Leave>", lambda e: export_mod_preset_button.config(bg="#00FFFF", fg="black"))

link_canvas = tk.Canvas(window, width=100, height=20, highlightthickness=0, bg="#000000", bd=0)
link_canvas.place(relx=0.5, y=770, anchor="center")
link_canvas.config(cursor="hand2")
link_canvas.create_text(50, 10, text="Nexus Mod Page", font=("Arial", 10, "underline"), fill="orange")
link_canvas.bind("<Button-1>", open_url)

version_canvas = tk.Canvas(window, width=100, height=20, highlightthickness=0, bg="#000000", bd=0)
version_canvas.place(relx=0.5, y=790, anchor="center")
version_canvas.create_text(50, 10, text=f"Version {tool_Version}", font=("Arial", 10), fill="white")

mod_count_label = tk.Label(window, text="Total Mods: Unknown", font=("Arial", 10), fg="white", bg="#000000")
game_version_label = tk.Label(window, text="Game Version: Unknown", font=("Arial", 10), fg="white", bg="#000000")
log_errors_label = tk.Label(window, text="Log Errors Detected: Unknown", font=("Arial", 10), fg="white", bg="#000000")
pl_dlc_label = tk.Label(window, text="Core Mods Installed: Unknown", font=("Arial", 10), fg="white", bg="#000000")

if os.path.exists(os.path.join(current_dir, "archive")):
    mod_count_label.place(x=10, y=760)
    game_version_label.place(x=10, y=780)
    log_errors_label.place(x=430, y=760)
    pl_dlc_label.place(x=430, y=780)
    include_logs_checkbox.place(relx=0.5, y=450, anchor="center")
    mod_count_label.config(text=f"Total Mods: {initial_mod_count}")
    game_version_label.config(text=f"Game Version: {initial_game_version}")
    log_errors_label.config(text=f"Log Errors Detected: {'Yes' if initial_log_errors else 'No'}")
    pl_dlc_label.config(text=f"Core Mods Installed: {'Yes' if initial_all_core_mods_installed else 'No'}")
    # Start the watchdog observer
    start_mod_watcher()
else:
    status_label.config(text="Please place application in the Cyberpunk 2077 Directory!")

image_label.lower()

window.protocol("WM_DELETE_WINDOW", on_closing)

window.mainloop()
