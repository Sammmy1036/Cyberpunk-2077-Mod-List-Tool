import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import base64
import os
import msvcrt
import sys
import tempfile
import webbrowser
import datetime
import time
import re
import shutil
import psutil
import zipfile
import winreg
import platform
from io import BytesIO
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image

try:
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

# Get the base directory for the application
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

current_page = "home"

image_files = [
    "mod_list_tool.png",
    "home_icon.png",
    "mods_icon.png",
    "settings_icon.png",
    "core_icon.png",
    "log_icon.png",
    "game_icon.png"
]

image_dir = os.path.join(SCRIPT_DIR, "icons")

def get_game_version(file_path):
    if platform.system() != "Windows" or not WIN32_AVAILABLE:
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

def convert_image_to_base64(image_path):
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return encoded_string
    except (FileNotFoundError, IOError) as e:
        print(f"Error converting {image_path} to base64: {e}")
        return None

# Generate base64 strings in memory
base64_strings = {}
for image_file in image_files:
    full_path = os.path.join(image_dir, image_file)
    if os.path.exists(full_path):
        base64_string = convert_image_to_base64(full_path)
        if base64_string:
            base64_strings[image_file] = base64_string
            print(f"Converted {image_file} to base64 (in memory)")

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

NEON_YELLOW = "#fcee09"
DARK_BG = "#111111"
NEON_GREEN = "#5BDE7B"
TEXT_COLOR = "#fcee09"
ACCENT_RED = "#DB002F"
tool_Version = "2.0.0.0"
DEFAULT_GAME_VERSION = "Unknown"
REGISTRY_KEY = r"Software\Cyberpunk2077ModListTool"
REGISTRY_VALUE = "GameDir"
LOCK_FILE = os.path.join(tempfile.gettempdir(), "Cyberpunk2077ModListTool.lock")
TEMP_DISABLED_DIR = "Temporarily Disabled Mods"
CACHE_TIMEOUT = 5
MOD_DIRECTORIES = [
    os.path.join("archive", "pc", "mod"),
    os.path.join("bin", "x64", "plugins", "cyber_engine_tweaks", "mods"),
    os.path.join("r6", "scripts"),
    os.path.join("r6", "tweaks")
]
# Core dependencies and their Nexus Mod IDs with expected paths
CORE_DEPENDENCIES = {
    "ArchiveXL": {
        "id": "4198",
        "path": [
            "r6/config/redsUserHints/ArchiveXL.toml",
            "red4ext/plugins/ArchiveXL/Bundle/ArchiveXL.archive",
            "red4ext/plugins/ArchiveXL/Bundle/Migration.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PhotoModeScope.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerBaseScope.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationBeardFix.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationBeardScope.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationBrowsFix.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationBrowsPatch.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationBrowsScope.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationEyesFix.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationEyesPatch.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationHairFix.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationHairPatch.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationHairScope.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationLashesFix.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationLashesPatch.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationLashesScope.xl",
            "red4ext/plugins/ArchiveXL/Bundle/PlayerCustomizationScope.xl",
            "red4ext/plugins/ArchiveXL/Bundle/QuestBaseScope.xl",
            "red4ext/plugins/ArchiveXL/Scripts/ArchiveXL.DynamicAppearance.reds",
            "red4ext/plugins/ArchiveXL/Scripts/ArchiveXL.Global.reds",
            "red4ext/plugins/ArchiveXL/Scripts/ArchiveXL.reds",
            "red4ext/plugins/ArchiveXL/THIRD_PARTY_LICENSES",
            "red4ext/plugins/ArchiveXL/LICENSE",
            "red4ext/plugins/ArchiveXL/ArchiveXL.dll"],
        "log_path": "red4ext/plugins/ArchiveXL/ArchiveXL.log",
        "log_pattern": "red4ext/plugins/ArchiveXL/ArchiveXL-*.log"
    },
    "Codeware": {
        "id": "7780",
        "path": [
            "red4ext/plugins/Codeware/Data/KnownHashes.txt",
            "red4ext/plugins/Codeware/Scripts/Codeware.Global.reds",
            "red4ext/plugins/Codeware/Scripts/Codeware.Localization.reds",
            "red4ext/plugins/Codeware/Scripts/Codeware.UI.TextInput.reds",
            "red4ext/plugins/Codeware/Scripts/Codeware.UI.reds",
            "red4ext/plugins/Codeware/Scripts/Codeware.reds",
            "red4ext/plugins/Codeware/LICENSE",
            "red4ext/plugins/Codeware/THIRD_PARTY_LICENSES",
            "red4ext/plugins/Codeware/Codeware.dll"],
        "log_path": "red4ext/plugins/Codeware/Codeware.log",
        "log_pattern": "red4ext/plugins/Codeware/Codeware-*.log"
    },
    "Cyber Engine Tweaks": {
        "id": "107",
        "path": [
            "bin/x64/global.ini",
            "bin/x64/LICENSE",
            "bin/x64/version.dll",
            "bin/x64/plugins/cyber_engine_tweaks.asi",
            "bin/x64/plugins/cyber_engine_tweaks/ThirdParty_LICENSES",
            "bin/x64/plugins/cyber_engine_tweaks/fonts/materialdesignicons.ttf",
            "bin/x64/plugins/cyber_engine_tweaks/fonts/NotoSansJP-Regular.otf",
            "bin/x64/plugins/cyber_engine_tweaks/fonts/NotoSansKR-Regular.otf",
            "bin/x64/plugins/cyber_engine_tweaks/fonts/NotoSansMono-Regular.ttf",
            "bin/x64/plugins/cyber_engine_tweaks/fonts/NotoSans-Regular.ttf",
            "bin/x64/plugins/cyber_engine_tweaks/fonts/NotoSansSC-Regular.otf",
            "bin/x64/plugins/cyber_engine_tweaks/fonts/NotoSansTC-Regular.otf",
            "bin/x64/plugins/cyber_engine_tweaks/fonts/NotoSansThai-Regular.ttf",
            "bin/x64/plugins/cyber_engine_tweaks/scripts/IconGlyphs/icons.lua",
            "bin/x64/plugins/cyber_engine_tweaks/scripts/json/json.lua",
            "bin/x64/plugins/cyber_engine_tweaks/scripts/json/LICENSE",
            "bin/x64/plugins/cyber_engine_tweaks/scripts/json/README.md",
            "bin/x64/plugins/cyber_engine_tweaks/tweakdb/tweakdbstr.kark",
            "bin/x64/plugins/cyber_engine_tweaks/tweakdb/usedhashes.kark"],
        "log_path": "bin/x64/plugins/cyber_engine_tweaks/cyber_engine_tweaks.log"
    },
    "EquipmentEx": {
        "id": "6945",
        "path": [
            "r6/scripts/EquipmentEx/EquipmentEx.Global.reds",
            "r6/scripts/EquipmentEx/EquipmentEx.reds",
            "r6/scripts/EquipmentEx/LICENSE",
            "r6/config/redsUserHints/EquipmentEX.toml",
            "archive/pc/mod/EquipmentEx.archive",
            "archive/pc/mod/EquipmentEx.archive.xl"]
    },
    "RED4ext": {
        "id": "2380",
        "path": [
            "bin/x64/winmm.dll",
            "red4ext/LICENSE.txt",
            "red4ext/THIRD_PARTY_LICENSES.txt",
            "red4ext/RED4ext.dll"],
        "log_path": "red4ext/logs/red4ext.log",
        "log_pattern": "red4ext/logs/red4ext-*.log"
    },
    "Redscript": {
        "id": "1511",
        "path": [
            "engine/config/base/scripts.ini",
            "engine/tools/scc.exe",
            "engine/tools/scc_lib.dll",
            "r6/config/cybercmd/scc.toml"],
        "log_path": "r6/logs/redscript_rCURRENT.log",
        "log_pattern": "r6/logs/redscript_r*.log"
    },
    "TweakXL": {
        "id": "4197",
        "path": [
            "red4ext/plugins/TweakXL/Data/ExtraFlats.dat",
            "red4ext/plugins/TweakXL/Data/InheritanceMap.dat",
            "red4ext/plugins/TweakXL/Scripts/TweakXL.Global.reds",
            "red4ext/plugins/TweakXL/Scripts/TweakXL.reds",
            "red4ext/plugins/TweakXL/LICENSE",
            "red4ext/plugins/TweakXL/THIRD_PARTY_LICENSES",
            "red4ext/plugins/TweakXL/TweakXL.dll"],
        "log_path": "red4ext/plugins/TweakXL/TweakXL.log",
        "log_pattern": "red4ext/plugins/TweakXL/TweakXL-*.log"
    }
}

# Log files for checkbox display
LOG_FILES = {
    "ArchiveXL": {
        "log_path": "red4ext/plugins/ArchiveXL/ArchiveXL.log",
        "log_pattern": "red4ext/plugins/ArchiveXL/ArchiveXL-*.log"
    },
    "Codeware": {
        "log_path": "red4ext/plugins/Codeware/Codeware.log",
        "log_pattern": "red4ext/plugins/Codeware/Codeware-*.log"
    },
    "Cyber Engine Tweaks": {
        "log_path": "bin/x64/plugins/cyber_engine_tweaks/cyber_engine_tweaks.log"
    },
    "Input Loader": {
        "log_path": "red4ext/logs/input_loader.log"
    },
    "Mod Settings": {
        "log_path": "red4ext/logs/mod_settings.log",
        "log_pattern": "red4ext/logs/mod_settings-*.log"
    },
    "RED4ext": {
        "log_path": "red4ext/logs/red4ext.log",
        "log_pattern": "red4ext/logs/red4ext-*.log"
    },
    "Redscript": {
        "log_path": "r6/logs/redscript_rCURRENT.log",
        "log_pattern": "r6/logs/redscript_r*.log"
    },
    "TweakXL": {
        "log_path": "red4ext/plugins/TweakXL/TweakXL.log",
        "log_pattern": "red4ext/plugins/TweakXL/TweakXL-*.log"
    }
}

# Get the base directory for the application
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define paths for the icon
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

ICON_PATH = os.path.join(SCRIPT_DIR, "Cyberpunk 2077 Mod List Tool.ico")

def set_window_icon(window):
    if not os.path.exists(ICON_PATH):
        print(f"Icon file not found at: {ICON_PATH}")
        return
    try:
        # Ensure window is fully initialized
        window.update_idletasks()
        # Set icon using iconbitmap for Windows
        if platform.system() == "Windows":
            window.after(200, lambda: window.iconbitmap(ICON_PATH))
        # Fallback to iconphoto for cross-platform compatibility
        try:
            img = tk.PhotoImage(file=os.path.join(SCRIPT_DIR, "icons", "mod_list_tool.png"))
            window.iconphoto(True, img)
            print(f"Set iconphoto for window: {window.title()}")
        except tk.TclError as e:
            print(f"Failed to set iconphoto for window {window.title()}: {e}")
        print(f"Successfully set icon for window: {window.title()}")
    except tk.TclError as e:
        print(f"Failed to set icon for window {window.title()}: {e}")

# Global variables
game_dir = None
mod_observer = None
last_core_mods_status = None
_game_running_cache = None
_cache_timestamp = 0
log_vars = {} 

def save_game_dir_to_registry():
    global game_dir
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
        winreg.SetValueEx(key, REGISTRY_VALUE, 0, winreg.REG_SZ, game_dir)
        winreg.CloseKey(key)
        print(f"Saved game_dir to registry: {game_dir}")
    except Exception as e:
        print(f"Failed to save game_dir to registry: {e}")

def load_game_dir_from_registry():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, REGISTRY_VALUE)
        winreg.CloseKey(key)
        if value and os.path.exists(os.path.join(value, "bin", "x64", "Cyberpunk2077.exe")):
            print(f"Loaded game_dir from registry: {value}")
            return value
        else:
            print("Registry game_dir invalid or not found.")
            return None
    except FileNotFoundError:
        print("Registry key not found.")
        return None
    except Exception as e:
        print(f"Failed to load game_dir from registry: {e}")
        return None

def change_game_directory():
    global game_dir
    new_dir = filedialog.askdirectory(title="Select Cyberpunk 2077 Game Directory", initialdir=game_dir or "C:\Program Files (x86)\Steam\steamapps\common\Cyberpunk 2077")
    if new_dir:
        game_exe = os.path.join(new_dir, "bin", "x64", "Cyberpunk2077.exe")
        if os.path.exists(game_exe):
            game_dir = new_dir
            save_game_dir_to_registry()
            messagebox.showinfo("Success", f"Game directory set to: {game_dir}")
            update_initial_ui()  # Refresh footer labels
            show_settings()  # Refresh settings page to update current_dir_text
            print(f"Game directory changed to: {game_dir}")
        else:
            messagebox.showerror("Invalid Directory", "Selected directory does not contain Cyberpunk2077.exe!")
            print(f"Invalid directory selected: {new_dir}")
    else:
        print("Directory selection cancelled")

def on_closing():
    global mod_observer
    print("Closing application")
    if hasattr(sys, 'lock_file_handle') and sys.lock_file_handle:
        try:
            msvcrt.locking(sys.lock_file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            sys.lock_file_handle.close()
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
                print(f"Lock file {LOCK_FILE} removed")
        except (OSError, IOError) as e:
            print(f"Error releasing lock or removing lock file: {e}")
    if mod_observer:
        try:
            mod_observer.stop()
            mod_observer.join()
        except Exception as e:
            print(f"Error stopping mod observer: {e}")
    app.destroy()

def check_single_instance():
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
    ep1_folder = os.path.join(current_dir, "archive", "pc", "ep1")
    tweakdb_ep1 = os.path.join(current_dir, "r6", "cache", "tweakdb_ep1.bin")
    if os.path.exists(ep1_folder) and any(f.endswith('.archive') for f in os.listdir(ep1_folder)):
        return True
    if os.path.exists(tweakdb_ep1):
        return True
    return False

def get_most_recent_log(directory, pattern):
    import glob
    pattern = os.path.join(directory, pattern)
    log_files = glob.glob(pattern)
    if not log_files:
        return None
    log_files.sort(key=os.path.getmtime, reverse=True)
    return log_files[0]

def is_game_running():
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

def create_progress_window(title, total_items):
    # Check if a progress window is already open
    for child in app.winfo_children():
        if isinstance(child, ctk.CTkToplevel) and child.title().startswith(title):
            print(f"Progress window '{title}' already open, skipping creation")
            return None, None, None

    progress_window = ctk.CTkToplevel(app)
    progress_window.title(title)
    progress_window.geometry("400x150")
    progress_window.resizable(False, False)
    progress_window.configure(fg_color=DARK_BG)

    # Center the window relative to the main app window
    app_x = app.winfo_x()
    app_y = app.winfo_y()
    app_width = app.winfo_width()
    app_height = app.winfo_height()
    window_width = 400
    window_height = 150
    x = app_x + (app_width - window_width) // 2
    y = app_y + (app_height - window_height) // 2
    progress_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # Add widgets after geometry
    ctk.CTkLabel(progress_window, text=f"{title}...", text_color=TEXT_COLOR, font=("Arial", 14)).pack(pady=20)
    progress_bar = ctk.CTkProgressBar(progress_window, width=350)
    progress_bar.pack(pady=20)
    progress_bar.set(0)
    status_label_progress = ctk.CTkLabel(progress_window, text=f"Processing: 0/{total_items}", text_color=TEXT_COLOR, font=("Arial", 12))
    status_label_progress.pack(pady=10)

    # Set modal properties after widgets
    progress_window.transient(app)
    progress_window.grab_set()

    # Set icon after all properties and widgets
    set_window_icon(progress_window)

    return progress_window, progress_bar, status_label_progress

def rebuild_mods_dictionary(current_dir, temp_disabled_path):
    mods = {}
    core_mods = ["archivexl", "codeware", "tweakxl"]
    equipment_ex_paths = CORE_DEPENDENCIES["EquipmentEx"]["path"]
    for mod_dir in MOD_DIRECTORIES + ["red4ext/plugins"]:
        try:
            full_dir = os.path.join(current_dir, mod_dir)
            temp_mod_dir = os.path.join(temp_disabled_path, mod_dir)
            if os.path.exists(full_dir):
                for item in os.listdir(full_dir):
                    display_name = f"{item} ({mod_dir})"
                    full_item_path = os.path.join(full_dir, item)
                    rel_path = os.path.relpath(full_item_path, current_dir)
                    normalized_rel = rel_path.replace("\\", "/").lower()
                    is_equipment_ex = (
                        normalized_rel == "r6/scripts/equipmentex" or
                        normalized_rel.startswith("r6/scripts/equipmentex/") or
                        any(normalized_rel == equip_path.replace("\\", "/").lower() for equip_path in equipment_ex_paths)
                    )
                    is_core_red4ext = (mod_dir == "red4ext/plugins" and item.lower() in core_mods)
                    if not is_equipment_ex and not is_core_red4ext:
                        mods[display_name] = (mod_dir, item, full_item_path)
                        print(f"Added enabled mod: {display_name}")
            if os.path.exists(temp_mod_dir):
                for item in os.listdir(temp_mod_dir):
                    display_name = f"{item} ({mod_dir})"
                    full_item_path = os.path.join(temp_mod_dir, item)
                    rel_path = os.path.relpath(full_item_path, current_dir)
                    normalized_rel = rel_path.replace("\\", "/").lower()
                    is_equipment_ex = (
                        normalized_rel == "r6/scripts/equipmentex" or
                        normalized_rel.startswith("r6/scripts/equipmentex/") or
                        any(normalized_rel == equip_path.replace("\\", "/").lower() for equip_path in equipment_ex_paths)
                    )
                    is_core_red4ext = (mod_dir == "red4ext/plugins" and item.lower() in core_mods)
                    if not is_equipment_ex and not is_core_red4ext:
                        mods[display_name] = (mod_dir, item, full_item_path)
                        print(f"Added disabled mod: {display_name}")
        except OSError as e:
            print(f"Error accessing directory {mod_dir}: {e}")
    return mods

def disable_all_mods(enabled_listbox, disabled_listbox, selected_dir_var, search_var, mods):
    try:
        if is_game_running():
            messagebox.showwarning("Game Running", "Cannot modify mods while Cyberpunk 2077 is running!")
            return
        if not game_dir:
            messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
            return
        if not messagebox.askyesno("Confirm Disable", "This will move all non-core mods to the 'Temporarily Disabled Mods' folder. Proceed?"):
            return
        current_dir = game_dir
        temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
        os.makedirs(temp_disabled_path, exist_ok=True)
        errors = []
        total_mods = sum(1 for display_name, (mod_dir, _, _) in mods.items()
                         if mod_dir in MOD_DIRECTORIES + ["red4ext/plugins"] and
                         not any(excluded in display_name.lower() for excluded in ["archivexl", "codeware", "tweakxl", "equipmentex"]))
        if total_mods == 0:
            messagebox.showinfo("No Mods", "No non-core mods found to disable.")
            return
        progress_window, progress_bar, status_label_progress = create_progress_window("Disabling All Mods", total_mods)
        mods_moved = 0
        moved_items = []
        for mod_dir in MOD_DIRECTORIES + ["red4ext/plugins"]:
            full_dir = os.path.join(current_dir, mod_dir)
            temp_mod_dir = os.path.join(temp_disabled_path, mod_dir)
            if os.path.exists(full_dir):
                os.makedirs(temp_mod_dir, exist_ok=True)
                for item in os.listdir(full_dir):
                    source = os.path.join(full_dir, item)
                    rel_path = os.path.relpath(source, current_dir)
                    normalized_rel = rel_path.replace("\\", "/").lower()
                    is_equipment_ex = (
                        normalized_rel == "r6/scripts/equipmentex" or
                        normalized_rel.startswith("r6/scripts/equipmentex/") or
                        any(normalized_rel == equip_path.replace("\\", "/").lower() for equip_path in CORE_DEPENDENCIES["EquipmentEx"]["path"])
                    )
                    is_core_red4ext = (mod_dir == "red4ext/plugins" and item.lower() in ["archivexl", "codeware", "tweakxl"])
                    display_name = f"{item} ({mod_dir})"
                    if not is_equipment_ex and not is_core_red4ext and display_name in mods:
                        dest = os.path.join(temp_mod_dir, item)
                        try:
                            shutil.move(source, dest)
                            moved_items.append((display_name, mod_dir, item, dest))
                            mods_moved += 1
                            progress_bar.set(mods_moved / total_mods)
                            status_label_progress.configure(text=f"Processing: {mods_moved}/{total_mods}")
                            progress_window.update()
                        except (shutil.Error, OSError) as e:
                            errors.append(f"Failed to disable {display_name}: {str(e)}")
        for display_name, mod_dir, item, dest in moved_items:
            mods[display_name] = (mod_dir, item, dest)
        mods.update(rebuild_mods_dictionary(current_dir, temp_disabled_path))
        progress_window.destroy()
        if errors:
            messagebox.showerror("Errors Occurred", "\n".join(errors))
            status_label.configure(text="Some non-core mods could not be disabled. Check details.")
        else:
            status_label.configure(text="All non-core mods have been disabled.")
        update_mod_count_label()
        show_mods()
        update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_var.get())
    except Exception as e:
        if 'progress_window' in locals():
            progress_window.destroy()
        messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")

def enable_all_mods(enabled_listbox, disabled_listbox, selected_dir_var, search_var, mods):
    try:
        if is_game_running():
            messagebox.showwarning("Game Running", "Cannot modify mods while Cyberpunk 2077 is running!")
            return
        if not game_dir:
            messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
            return

        if not messagebox.askyesno("Confirm Enable", "This will move all mods back from 'Temporarily Disabled Mods' to their original locations and remove the folder. Proceed?"):
            return
        current_dir = game_dir
        temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
        errors = []

        # Count total mods to move
        total_mods = 0
        core_mods = ["archivexl", "codeware", "tweakxl"]
        equipment_ex_paths = CORE_DEPENDENCIES["EquipmentEx"]["path"]
        if os.path.exists(temp_disabled_path):
            for mod_dir in MOD_DIRECTORIES + ["red4ext/plugins"]:
                temp_mod_dir = os.path.join(temp_disabled_path, mod_dir)
                if os.path.exists(temp_mod_dir):
                    for item in os.listdir(temp_mod_dir):
                        source = os.path.join(temp_mod_dir, item)
                        rel_path = os.path.relpath(source, current_dir)
                        normalized_rel = rel_path.replace("\\", "/").lower()
                        is_equipment_ex = (
                            normalized_rel == "r6/scripts/equipmentex" or
                            normalized_rel.startswith("r6/scripts/equipmentex/") or
                            any(normalized_rel == equip_path.replace("\\", "/").lower() for equip_path in equipment_ex_paths)
                        )
                        is_core_red4ext = (mod_dir == "red4ext/plugins" and item.lower() in core_mods)
                        display_name = f"{item} ({mod_dir})"
                        if not is_equipment_ex and not is_core_red4ext and display_name in mods:
                            total_mods += 1

        if total_mods == 0:
            messagebox.showinfo("No Mods", "No mods found in 'Temporarily Disabled Mods' to enable.")
            if os.path.exists(temp_disabled_path) and not os.listdir(temp_disabled_path):
                os.rmdir(temp_disabled_path)
            return

        # Create progress window
        progress_window, progress_bar, status_label_progress = create_progress_window("Enabling All Mods", total_mods)
        mods_moved = 0
        moved_items = []

        # Move mods back
        print("Starting file moves...")
        if os.path.exists(temp_disabled_path):
            for mod_dir in MOD_DIRECTORIES + ["red4ext/plugins"]:
                temp_mod_dir = os.path.join(temp_disabled_path, mod_dir)
                full_dir = os.path.join(current_dir, mod_dir)
                if os.path.exists(temp_mod_dir):
                    os.makedirs(full_dir, exist_ok=True)
                    for item in os.listdir(temp_mod_dir):
                        source = os.path.join(temp_mod_dir, item)
                        dest = os.path.join(full_dir, item)
                        rel_path = os.path.relpath(source, current_dir)
                        normalized_rel = rel_path.replace("\\", "/").lower()
                        is_equipment_ex = (
                            normalized_rel == "r6/scripts/equipmentex" or
                            normalized_rel.startswith("r6/scripts/equipmentex/") or
                            any(normalized_rel == equip_path.replace("\\", "/").lower() for equip_path in equipment_ex_paths)
                        )
                        is_core_red4ext = (mod_dir == "red4ext/plugins" and item.lower() in core_mods)
                        display_name = f"{item} ({mod_dir})"
                        if not is_equipment_ex and not is_core_red4ext and display_name in mods:
                            try:
                                if os.path.isdir(source):
                                    shutil.move(source, dest)
                                    print(f"Moved folder back: {source} to {dest}")
                                elif os.path.isfile(source):
                                    shutil.move(source, dest)
                                    print(f"Moved file back: {source} to {dest}")
                                moved_items.append((display_name, mod_dir, item, dest))
                                mods_moved += 1
                                progress_bar.set(mods_moved / total_mods)
                                status_label_progress.configure(text=f"Processing: {mods_moved}/{total_mods}")
                                progress_window.update()
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

            # Update mods dictionary with moved items
            for display_name, mod_dir, item, dest in moved_items:
                mods[display_name] = (mod_dir, item, dest)
            print(f"Mods dictionary after moves: {mods}")

        # Rebuild mods dictionary
        mods.clear()
        mods.update(rebuild_mods_dictionary(current_dir, temp_disabled_path))
        print(f"Rebuilt mods dictionary: {mods}")

        # Close progress window
        progress_window.destroy()

        # Force UI update
        main.update()
        main.update_idletasks()

        if errors:
            messagebox.showerror("Errors Occurred", "\n".join(errors))
            status_label.configure(text="Some mods could not be enabled or folder not fully removed. Check details.")
        else:
            status_label.configure(text="All mods have been enabled and Temporarily Disabled Mods folder removed.")
        update_mod_count_label()

        # Force page reload and update mod list
        show_mods()
        update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_var.get())

    except Exception as e:
        print(f"Error in enable_all_mods: {e}")
        if 'progress_window' in locals():
            progress_window.destroy()
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")

def disable_core_mods():
    if is_game_running():
        messagebox.showwarning("Game Running", "Cannot modify core mods while Cyberpunk 2077 is running!")
        return
    if not game_dir:
        messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
        return

    if not messagebox.askyesno("Confirm Disable", "This will move all core mods to the 'Temporarily Disabled Mods' folder. Proceed?"):
        return
    current_dir = game_dir
    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
    os.makedirs(temp_disabled_path, exist_ok=True)
    errors = []

    for mod_name, info in CORE_DEPENDENCIES.items():
        paths = info["path"] if isinstance(info["path"], list) else [info["path"]]
        for path in paths:
            full_path = os.path.join(current_dir, path)
            if os.path.exists(full_path):
                rel_path = os.path.relpath(full_path, current_dir)
                temp_dest = os.path.join(temp_disabled_path, rel_path)
                os.makedirs(os.path.dirname(temp_dest), exist_ok=True)
                try:
                    shutil.move(full_path, temp_dest)
                except Exception as e:
                    errors.append(f"Failed to disable {mod_name} file {path}: {str(e)}")

    if errors:
        messagebox.showerror("Errors Occurred", "\n".join(errors))
        status_label.configure(text="Some core mods could not be disabled. Check details.")
    else:
        status_label.configure(text="All core mods have been disabled.")
    update_core_mods_label()
    show_core_mods()

def enable_core_mods():
    if is_game_running():
        messagebox.showwarning("Game Running", "Cannot modify core mods while Cyberpunk 2077 is running!")
        return
    if not game_dir:
        messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
        return

    if not messagebox.askyesno("Confirm Enable", "This will move all core mods back from 'Temporarily Disabled Mods' to their original locations. Proceed?"):
        return
    current_dir = game_dir
    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
    errors = []

    if os.path.exists(temp_disabled_path):
        for mod_name, info in CORE_DEPENDENCIES.items():
            paths = info["path"] if isinstance(info["path"], list) else [info["path"]]
            for path in paths:
                temp_path = os.path.join(temp_disabled_path, path)
                full_path = os.path.join(current_dir, path)
                if os.path.exists(temp_path):
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    try:
                        shutil.move(temp_path, full_path)
                    except Exception as e:
                        errors.append(f"Failed to enable {mod_name} file {path}: {str(e)}")

        try:
            for root, dirs, _ in os.walk(temp_disabled_path, topdown=False):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
            if os.path.exists(temp_disabled_path) and not os.listdir(temp_disabled_path):
                os.rmdir(temp_disabled_path)
        except Exception as e:
            errors.append(f"Failed to clean up {TEMP_DISABLED_DIR}: {str(e)}")

    if errors:
        messagebox.showerror("Errors Occurred", "\n".join(errors))
        status_label.configure(text="Some core mods could not be enabled. Check details.")
    else:
        status_label.configure(text="All core mods have been enabled.")
    update_core_mods_label()
    show_core_mods()

def cleanup_temp_disabled_folder(current_dir):
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
    status_data = {}
    for mod_name, info in CORE_DEPENDENCIES.items():
        is_installed = False
        paths = info["path"] if isinstance(info["path"], list) else [info["path"]]
        try:
            if mod_name in ["ArchiveXL", "Codeware", "EquipmentEx", "RED4ext", "Redscript", "TweakXL"]:
                is_installed = all(os.path.exists(os.path.join(current_dir, path)) for path in paths)
            else:
                is_installed = any(os.path.exists(os.path.join(current_dir, path)) for path in paths)
        except Exception as e:
            print(f"Error checking {mod_name} at {paths}: {e}")

        version = None
        if mod_name in ["ArchiveXL", "RED4ext", "Codeware", "TweakXL"] and is_installed:
            dll_path = next((p for p in paths if p.endswith(".dll")), paths[0])
            version = get_dll_version(os.path.join(current_dir, dll_path))
        elif mod_name == "Cyber Engine Tweaks" and "log_path" in info and is_installed:
            log_path = os.path.join(current_dir, info["log_path"])
            version = get_cet_version(log_path)

        status_data[mod_name] = {
            "installed": is_installed,
            "path": info["path"],
            "version": version
        }
        print(f"Debug: Checking {mod_name} - Exists: {is_installed} - Version: {version if version else 'N/A'} - Paths: {paths}")
    return status_data

def check_all_core_mods_installed(current_dir):
    status_data = view_core_mods_status(current_dir)
    for mod_name, info in status_data.items():
        if not info["installed"]:
            return False
    return True

def update_core_mods_label():
    global last_core_mods_status
    if not game_dir:
        return
    current_dir = game_dir
    all_core_mods_installed = check_all_core_mods_installed(current_dir)
    
    if last_core_mods_status != all_core_mods_installed:
        core_mods_label.configure(text=f"Core Mods Installed: {'Yes' if all_core_mods_installed else 'No'}")
        last_core_mods_status = all_core_mods_installed
        print(f"Updated core mods status: {'Yes' if all_core_mods_installed else 'No'}")

    if app.winfo_exists():
        app.after(5000, update_core_mods_label)

def update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_term=""):
    if not (enabled_listbox.winfo_exists() and disabled_listbox.winfo_exists()):
        print("Error: One or both listboxes do not exist. Skipping update.")
        return
    selected_dir = selected_dir_var.get()
    print(f"Updating mod list for directory: {selected_dir}, search term: {search_term}")
    enabled_listbox.delete(0, tk.END)
    disabled_listbox.delete(0, tk.END)
    search_term = search_term.lower()
    filtered_mods = [
        (display_name, data) for display_name, data in sorted(mods.items())
        if (selected_dir == "All" or data[0] == selected_dir) and
           (not search_term or search_term in display_name.lower())
    ]
    for display_name, (mod_dir, mod_name, current_path) in filtered_mods:
        if TEMP_DISABLED_DIR in os.path.normpath(current_path):
            disabled_listbox.insert(tk.END, display_name)
            print(f"Inserted disabled mod: {display_name}")
        else:
            enabled_listbox.insert(tk.END, display_name)
            print(f"Inserted enabled mod: {display_name}")
    print(f"Mod list updated: {enabled_listbox.size()} enabled, {disabled_listbox.size()} disabled")

def show_mods():
    global status_label, enabled_listbox, disabled_listbox, selected_dir_var, search_var, mods, current_page
    current_page = "mods"
    clear_main()
    if not game_dir:
        messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
        return

    current_dir = game_dir
    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)

    # Place the image at the very top, centered with y=-70
    img_path = os.path.join(SCRIPT_DIR, "icons", "mod_list_tool.png")

    if os.path.exists(img_path):
        img = ctk.CTkImage(Image.open(img_path), size=(250, 250))
        image_label = ctk.CTkLabel(main, image=img, text="")
        image_label.place(x=(main.winfo_width() - 250) // 2, y=-70)
    else:
        ctk.CTkLabel(main, text="Mod Management", font=("Orbitron", 22, "bold"), text_color=TEXT_COLOR).grid(row=0, column=0, pady=10, sticky="n")

    # Configure grid to start content just below image
    main.grid_columnconfigure(0, weight=1)
    main.grid_rowconfigure(3, weight=1)  # Ensure row 3 (list_frame) expands vertically

    button_frame = ctk.CTkFrame(main, fg_color=DARK_BG)
    button_frame.grid(row=0, column=0, pady=(120, 10), sticky="n")

    ctk.CTkButton(button_frame, text="Disable All Mods", command=lambda: disable_all_mods(enabled_listbox, disabled_listbox, selected_dir_var, search_var, mods), fg_color=ACCENT_RED, text_color="white", hover_color="#94160C").pack(side="left", padx=5)
    ctk.CTkButton(button_frame, text="Enable All Mods", command=lambda: enable_all_mods(enabled_listbox, disabled_listbox, selected_dir_var, search_var, mods), fg_color=NEON_GREEN, text_color="black", hover_color="#1ADB00").pack(side="left", padx=5)
    ctk.CTkButton(button_frame, text="Export / Backup Mod Preset", command=export_mods, fg_color=NEON_YELLOW, text_color="black", hover_color="#DBBE00").pack(side="left", padx=5)
    ctk.CTkButton(button_frame, text="Import Mod Preset", command=import_mods, fg_color=NEON_YELLOW, text_color="black", hover_color="#DBBE00").pack(side="left", padx=5)

    search_frame = ctk.CTkFrame(main, fg_color=DARK_BG)
    search_frame.grid(row=1, column=0, pady=5, sticky="ew", padx=10)
    search_frame.grid_columnconfigure(0, weight=1)

    search_var = tk.StringVar()
    search_entry = ctk.CTkEntry(search_frame, textvariable=search_var, font=("Arial", 12), fg_color="#1A1A1A", text_color="white")
    search_entry.grid(row=0, column=0, sticky="ew")
    search_button = ctk.CTkButton(search_frame, text="Search", font=("Arial", 12), fg_color=NEON_YELLOW, text_color="black", hover_color="#DBBE00")
    search_button.grid(row=0, column=1, padx=(5, 0))
    clear_button = ctk.CTkButton(search_frame, text="Clear", font=("Arial", 12), fg_color=ACCENT_RED, text_color="white", hover_color="#94160C")
    clear_button.grid(row=0, column=2, padx=(5, 0))

    selected_dir_var = tk.StringVar(value="All")
    combobox = ctk.CTkComboBox(
        main,
        values=["All"] + MOD_DIRECTORIES + ["red4ext/plugins"],
        variable=selected_dir_var,
        font=("Arial", 12),
        fg_color="#1A1A1A",
        text_color="white",
        dropdown_fg_color="#1A1A1A",
        state="readonly"
    )
    combobox.grid(row=2, column=0, pady=5, padx=10, sticky="ew")
    # Add binding to open dropdown on click anywhere on the combobox
    combobox.bind("<Button-1>", lambda event: combobox._open_dropdown_menu())

    # Build mods dictionary
    mods = rebuild_mods_dictionary(current_dir, temp_disabled_path)

    list_frame = ctk.CTkFrame(main, fg_color=DARK_BG)
    list_frame.grid(row=3, column=0, pady=10, padx=10, sticky="nsew")
    list_frame.grid_rowconfigure(0, weight=1)
    list_frame.grid_columnconfigure((0, 1), weight=1)

    enabled_frame = ctk.CTkFrame(list_frame, fg_color=DARK_BG)
    enabled_frame.grid(row=0, column=0, padx=10, sticky="nsew")
    disabled_frame = ctk.CTkFrame(list_frame, fg_color=DARK_BG)
    disabled_frame.grid(row=0, column=1, padx=10, sticky="nsew")

    ctk.CTkLabel(enabled_frame, text="Enabled Mods", font=("Arial", 12), text_color=TEXT_COLOR).pack()
    enabled_list_frame = ctk.CTkFrame(enabled_frame, fg_color=DARK_BG)
    enabled_list_frame.pack(pady=5, fill="both", expand=True)
    enabled_scrollbar = ctk.CTkScrollbar(enabled_list_frame, orientation="vertical")
    enabled_scrollbar.pack(side="right", fill="y")
    enabled_listbox = tk.Listbox(enabled_list_frame, font=("Arial", 10), width=40, height=15, bg="#333333", fg="white", selectmode=tk.EXTENDED)
    enabled_listbox.pack(side="left", fill="both", expand=True)
    enabled_listbox.configure(yscrollcommand=enabled_scrollbar.set)
    enabled_scrollbar.configure(command=enabled_listbox.yview)

    ctk.CTkLabel(disabled_frame, text="Disabled Mods", font=("Arial", 12), text_color=TEXT_COLOR).pack()
    disabled_list_frame = ctk.CTkFrame(disabled_frame, fg_color=DARK_BG)
    disabled_list_frame.pack(pady=5, fill="both", expand=True)
    disabled_scrollbar = ctk.CTkScrollbar(disabled_list_frame, orientation="vertical")
    disabled_scrollbar.pack(side="right", fill="y")
    disabled_listbox = tk.Listbox(disabled_list_frame, font=("Arial", 10), width=40, height=15, bg="#333333", fg="white", selectmode=tk.EXTENDED)
    disabled_listbox.pack(side="left", fill="both", expand=True)
    disabled_listbox.configure(yscrollcommand=disabled_scrollbar.set)
    disabled_scrollbar.configure(command=disabled_listbox.yview)

    def on_search():
        search_term = search_var.get()
        print(f"Search triggered with term: {search_term}, directory: {selected_dir_var.get()}")
        update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_term)

    def on_clear():
        search_var.set("")
        print("Clear button clicked, resetting search term.")
        update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, "")

    def on_combobox_select(event=None):
        selected_dir = selected_dir_var.get()
        print(f"Combobox selected: {selected_dir}, updating mod list")
        try:
            update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_var.get())
            print(f"Successfully updated mod list for directory: {selected_dir}")
        except Exception as e:
            print(f"Error updating mod list: {e}")
            status_label.configure(text=f"Error updating mod list: {str(e)}")

    def disable_selected():
        if is_game_running():
            messagebox.showwarning("Game Running", "Cannot modify mods while Cyberpunk 2077 is running!")
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
                print(f"Disabled mod: {display_name}")
            except Exception as e:
                errors.append(f"Failed to disable {display_name}: {str(e)}")
        if errors:
            messagebox.showerror("Errors Occurred", "\n".join(errors))
        update_mod_count_label()
        update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_var.get())

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
                enabled_listbox.insert(tk.END, display_name)
                print(f"Enabled mod: {display_name}")
            except Exception as e:
                errors.append(f"Failed to enable {display_name}: {str(e)}")
        if errors:
            messagebox.showerror("Errors Occurred", "\n".join(errors))
        else:
            cleanup_temp_disabled_folder(current_dir)
        update_mod_count_label()
        update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_var.get())

    # Bind commands
    search_button.configure(command=on_search)
    clear_button.configure(command=on_clear)
    search_entry.bind("<Return>", lambda event: on_search())

    # Bind ComboboxSelected event and add trace for debugging
    combobox.bind("<<ComboboxSelected>>", on_combobox_select)
    selected_dir_var.trace_add("write", lambda *args: on_combobox_select())
    print(f"Initial directory selection: {selected_dir_var.get()}")

    ctk.CTkButton(enabled_frame, text="Disable Selected", command=disable_selected, font=("Arial", 12), fg_color=ACCENT_RED, text_color="white", hover_color="#94160C").pack(pady=5)
    ctk.CTkButton(disabled_frame, text="Enable Selected", command=enable_selected, font=("Arial", 12), fg_color=NEON_GREEN, text_color="black", hover_color="#1ADB00").pack(pady=5)

    # Recreate status_label to ensure it exists
    status_label = ctk.CTkLabel(main, text="Click 'Enable/Disable All Mods' to manage mods!", font=("Arial", 12, "bold"), text_color=TEXT_COLOR)
    status_label.grid(row=4, column=0, pady=10, sticky="n")

    # Initial population of mod list
    try:
        update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_var.get())
        print("Initial mod list population completed")
    except Exception as e:
        print(f"Error during initial mod list population: {e}")
        status_label.configure(text=f"Error loading mod list: {str(e)}")

def disable_all_mods(enabled_listbox, disabled_listbox, selected_dir_var, search_var, mods):
    try:
        if is_game_running():
            messagebox.showwarning("Game Running", "Cannot modify mods while Cyberpunk 2077 is running!")
            return
        if not game_dir:
            messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
            return

        if not messagebox.askyesno("Confirm Disable", "This will move all non-core mods to the 'Temporarily Disabled Mods' folder located in your Cyberpunk 2077 directory. Proceed?"):
            return
        current_dir = game_dir
        temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
        os.makedirs(temp_disabled_path, exist_ok=True)
        errors = []

        # Count total mods to move
        total_mods = 0
        core_mods = ["archivexl", "codeware", "tweakxl"]
        equipment_ex_paths = CORE_DEPENDENCIES["EquipmentEx"]["path"]
        for mod_dir in MOD_DIRECTORIES + ["red4ext/plugins"]:
            full_dir = os.path.join(current_dir, mod_dir)
            if os.path.exists(full_dir):
                for item in os.listdir(full_dir):
                    source = os.path.join(full_dir, item)
                    rel_path = os.path.relpath(source, current_dir)
                    normalized_rel = rel_path.replace("\\", "/").lower()
                    is_equipment_ex = (
                        normalized_rel == "r6/scripts/equipmentex" or
                        normalized_rel.startswith("r6/scripts/equipmentex/") or
                        any(normalized_rel == equip_path.replace("\\", "/").lower() for equip_path in equipment_ex_paths)
                    )
                    is_core_red4ext = (mod_dir == "red4ext/plugins" and item.lower() in core_mods)
                    display_name = f"{item} ({mod_dir})"
                    if not is_equipment_ex and not is_core_red4ext and display_name in mods:
                        total_mods += 1

        if total_mods == 0:
            messagebox.showinfo("No Mods", "No non-core mods found to disable.")
            return

        # Create progress window
        progress_window, progress_bar, status_label_progress = create_progress_window("Disabling All Mods", total_mods)
        mods_moved = 0
        moved_items = []

        # Move non-core mods
        print("Starting file moves...")
        for mod_dir in MOD_DIRECTORIES + ["red4ext/plugins"]:
            full_dir = os.path.join(current_dir, mod_dir)
            temp_mod_dir = os.path.join(temp_disabled_path, mod_dir)
            if os.path.exists(full_dir):
                os.makedirs(temp_mod_dir, exist_ok=True)
                for item in os.listdir(full_dir):
                    source = os.path.join(full_dir, item)
                    rel_path = os.path.relpath(source, current_dir)
                    normalized_rel = rel_path.replace("\\", "/").lower()
                    is_equipment_ex = (
                        normalized_rel == "r6/scripts/equipmentex" or
                        normalized_rel.startswith("r6/scripts/equipmentex/") or
                        any(normalized_rel == equip_path.replace("\\", "/").lower() for equip_path in equipment_ex_paths)
                    )
                    is_core_red4ext = (mod_dir == "red4ext/plugins" and item.lower() in core_mods)
                    display_name = f"{item} ({mod_dir})"
                    if not is_equipment_ex and not is_core_red4ext and display_name in mods:
                        dest = os.path.join(temp_mod_dir, item)
                        try:
                            shutil.move(source, dest)
                            print(f"Moved: {source} to {dest}")
                            moved_items.append((display_name, mod_dir, item, dest))
                            mods_moved += 1
                            progress_bar.set(mods_moved / total_mods)
                            status_label_progress.configure(text=f"Processing: {mods_moved}/{total_mods}")
                            progress_window.update()
                        except Exception as e:
                            errors.append(f"Failed to disable {item} in {mod_dir}: {str(e)}")

        # Update mods dictionary with moved items
        for display_name, mod_dir, item, dest in moved_items:
            mods[display_name] = (mod_dir, item, dest)
        print(f"Mods dictionary after moves: {mods}")

        # Rebuild mods dictionary
        mods.clear()
        mods.update(rebuild_mods_dictionary(current_dir, temp_disabled_path))
        print(f"Rebuilt mods dictionary: {mods}")

        # Close progress window
        progress_window.destroy()

        # Refresh UI and get new listbox references
        show_mods()
        print(f"Checking listbox existence - enabled: {enabled_listbox.winfo_exists()}, disabled: {disabled_listbox.winfo_exists()}")
        update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_var.get())

        # Update status if widget exists
        if status_label.winfo_exists():
            if errors:
                messagebox.showerror("Errors Occurred", "\n".join(errors))
                status_label.configure(text="Some non-core mods could not be disabled. Check details.")
            else:
                status_label.configure(text="All non-core mods have been disabled.")
        update_mod_count_label()

    except Exception as e:
        print(f"Error in disable_all_mods: {e}")
        if 'progress_window' in locals():
            progress_window.destroy()
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")

def enable_all_mods(enabled_listbox, disabled_listbox, selected_dir_var, search_var, mods):
    try:
        if is_game_running():
            messagebox.showwarning("Game Running", "Cannot modify mods while Cyberpunk 2077 is running!")
            return
        if not game_dir:
            messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
            return

        if not messagebox.askyesno("Confirm Enable", "This will move all mods back from 'Temporarily Disabled Mods' to their original locations and remove the folder. Proceed?"):
            return
        current_dir = game_dir
        temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
        errors = []

        # Count total mods to move
        total_mods = 0
        core_mods = ["archivexl", "codeware", "tweakxl"]
        equipment_ex_paths = CORE_DEPENDENCIES["EquipmentEx"]["path"]
        if os.path.exists(temp_disabled_path):
            for mod_dir in MOD_DIRECTORIES + ["red4ext/plugins"]:
                temp_mod_dir = os.path.join(temp_disabled_path, mod_dir)
                if os.path.exists(temp_mod_dir):
                    for item in os.listdir(temp_mod_dir):
                        source = os.path.join(temp_mod_dir, item)
                        rel_path = os.path.relpath(source, current_dir)
                        normalized_rel = rel_path.replace("\\", "/").lower()
                        is_equipment_ex = (
                            normalized_rel == "r6/scripts/equipmentex" or
                            normalized_rel.startswith("r6/scripts/equipmentex/") or
                            any(normalized_rel == equip_path.replace("\\", "/").lower() for equip_path in equipment_ex_paths)
                        )
                        is_core_red4ext = (mod_dir == "red4ext/plugins" and item.lower() in core_mods)
                        display_name = f"{item} ({mod_dir})"
                        if not is_equipment_ex and not is_core_red4ext and display_name in mods:
                            total_mods += 1

        if total_mods == 0:
            messagebox.showinfo("No Mods", "No mods found in 'Temporarily Disabled Mods' to enable.")
            if os.path.exists(temp_disabled_path) and not os.listdir(temp_disabled_path):
                os.rmdir(temp_disabled_path)
            return

        # Create progress window
        progress_window, progress_bar, status_label_progress = create_progress_window("Enabling All Mods", total_mods)
        mods_moved = 0
        moved_items = []

        # Move mods back
        print("Starting file moves...")
        if os.path.exists(temp_disabled_path):
            for mod_dir in MOD_DIRECTORIES + ["red4ext/plugins"]:
                temp_mod_dir = os.path.join(temp_disabled_path, mod_dir)
                full_dir = os.path.join(current_dir, mod_dir)
                if os.path.exists(temp_mod_dir):
                    os.makedirs(full_dir, exist_ok=True)
                    for item in os.listdir(temp_mod_dir):
                        source = os.path.join(temp_mod_dir, item)
                        dest = os.path.join(full_dir, item)
                        rel_path = os.path.relpath(source, current_dir)
                        normalized_rel = rel_path.replace("\\", "/").lower()
                        is_equipment_ex = (
                            normalized_rel == "r6/scripts/equipmentex" or
                            normalized_rel.startswith("r6/scripts/equipmentex/") or
                            any(normalized_rel == equip_path.replace("\\", "/").lower() for equip_path in equipment_ex_paths)
                        )
                        is_core_red4ext = (mod_dir == "red4ext/plugins" and item.lower() in core_mods)
                        display_name = f"{item} ({mod_dir})"
                        if not is_equipment_ex and not is_core_red4ext and display_name in mods:
                            try:
                                if os.path.isdir(source):
                                    shutil.move(source, dest)
                                    print(f"Moved folder back: {source} to {dest}")
                                elif os.path.isfile(source):
                                    shutil.move(source, dest)
                                    print(f"Moved file back: {source} to {dest}")
                                moved_items.append((display_name, mod_dir, item, dest))
                                mods_moved += 1
                                progress_bar.set(mods_moved / total_mods)
                                status_label_progress.configure(text=f"Processing: {mods_moved}/{total_mods}")
                                progress_window.update()
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

            # Update mods dictionary with moved items
            for display_name, mod_dir, item, dest in moved_items:
                mods[display_name] = (mod_dir, item, dest)
            print(f"Mods dictionary after moves: {mods}")

        # Rebuild mods dictionary
        mods.clear()
        mods.update(rebuild_mods_dictionary(current_dir, temp_disabled_path))
        print(f"Rebuilt mods dictionary: {mods}")

        # Close progress window
        progress_window.destroy()

        # Refresh UI and get new listbox references
        show_mods()
        print(f"Checking listbox existence - enabled: {enabled_listbox.winfo_exists()}, disabled: {disabled_listbox.winfo_exists()}")
        update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_var.get())

        # Update status if widget exists
        if status_label.winfo_exists():
            if errors:
                messagebox.showerror("Errors Occurred", "\n".join(errors))
                status_label.configure(text="Some mods could not be enabled or folder not fully removed. Check details.")
            else:
                status_label.configure(text="All mods have been enabled and Temporarily Disabled Mods folder removed.")
        update_mod_count_label()

    except Exception as e:
        print(f"Error in enable_all_mods: {e}")
        if 'progress_window' in locals():
            progress_window.destroy()
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")

def open_settings():
    global status_label
    clear_main()
    if not game_dir:
        messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
        return

    ctk.CTkLabel(main, text="Settings", font=("Orbitron", 22, "bold"), text_color=TEXT_COLOR).pack(pady=20)
    ctk.CTkButton(main, text="Change Game Directory", command=open_settings, fg_color=NEON_YELLOW, text_color="black").pack(pady=10)
    
    # Recreate status_label to ensure it exists
    status_label = ctk.CTkLabel(main, text="Click 'Change Game Directory' to update the game path!", font=("Arial", 12, "bold"), text_color=TEXT_COLOR)
    status_label.pack(pady=20)

class ModChangeHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            update_mod_count_label()
        elif os.path.normpath(os.path.relpath(event.src_path, game_dir)).startswith("bin/x64/plugins/cyber_engine_tweaks/mods"):
            update_mod_count_label()

    def on_deleted(self, event):
        if not event.is_directory:
            update_mod_count_label()
        elif os.path.normpath(os.path.relpath(event.src_path, game_dir)).startswith("bin/x64/plugins/cyber_engine_tweaks/mods"):
            update_mod_count_label()

    def on_moved(self, event):
        if not event.is_directory:
            update_mod_count_label()
        elif os.path.normpath(os.path.relpath(event.src_path, game_dir)).startswith("bin/x64/plugins/cyber_engine_tweaks/mods") or \
             (event.dest_path and os.path.normpath(os.path.relpath(event.dest_path, game_dir)).startswith("bin/x64/plugins/cyber_engine_tweaks/mods")):
            update_mod_count_label()

def start_mod_watcher():
    global mod_observer
    if not game_dir:
        return None
    current_dir = game_dir
    event_handler = ModChangeHandler()
    mod_observer = Observer()
    for mod_dir in MOD_DIRECTORIES:
        full_dir = os.path.join(current_dir, mod_dir)
        if os.path.exists(full_dir):
            mod_observer.schedule(event_handler, full_dir, recursive=False)
    mod_observer.start()
    return mod_observer

def update_mod_count_label():
    if not game_dir:
        mod_count_label.configure(text="Total Mods: Unknown")
        return
    current_dir = game_dir
    mod_count = 0
    for mod_dir in MOD_DIRECTORIES:
        full_dir = os.path.join(current_dir, mod_dir)
        if os.path.exists(full_dir):
            for item in os.listdir(full_dir):
                full_item_path = os.path.join(full_dir, item)
                rel_path = os.path.relpath(full_item_path, current_dir)
                normalized_rel = rel_path.replace("\\", "/").lower()
                is_equipment_ex = (
                    normalized_rel.startswith("r6/scripts/equipmentex/") or
                    normalized_rel.startswith("archive/pc/mod/equipmentex/") or
                    normalized_rel == "r6/scripts/equipmentex" or
                    any(normalized_rel == equip_path.replace("\\", "/").lower()
                        for equip_path in CORE_DEPENDENCIES["EquipmentEx"]["path"])
                )
                if not is_equipment_ex:
                    if mod_dir == os.path.normpath("bin/x64/plugins/cyber_engine_tweaks/mods"):
                        if os.path.isdir(full_item_path):
                            mod_count += 1
                            print(f"Counting directory mod: {item} in {mod_dir}")
                    else:
                        mod_count += 1
                        print(f"Counting file mod: {item} in {mod_dir}")
    red4ext_plugins_dir = os.path.join(current_dir, "red4ext", "plugins")
    if os.path.exists(red4ext_plugins_dir):
        for item in os.listdir(red4ext_plugins_dir):
            full_item_path = os.path.join(red4ext_plugins_dir, item)
            if os.path.isdir(full_item_path):
                normalized_name = item.lower()
                if normalized_name not in ["archivexl", "codeware", "tweakxl"]:
                    mod_count += 1
                    print(f"Counting red4ext plugin mod: {item} in red4ext/plugins")
    mod_count_label.configure(text=f"Total Mods: {mod_count}")
    print(f"Updated mod count: {mod_count}")

def extract_log_errors(log_path):
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
    log_files = {name: info.get("log_path") for name, info in LOG_FILES.items() if "log_path" in info}
    log_errors = {}
    for log_name, log_path in log_files.items():
        full_log_path = os.path.join(current_dir, log_path)
        errors = extract_log_errors(full_log_path)
        if not errors and "log_pattern" in LOG_FILES[log_name]:
            recent_log = get_most_recent_log(current_dir, LOG_FILES[log_name]["log_pattern"])
            if recent_log:
                errors = extract_log_errors(recent_log)
        if errors:
            log_errors[log_name] = errors
    return bool(log_errors)

def write_items_from_dir(file, directory, folder_name, temp_dir):
    if os.path.exists(directory):
        items = []
        if folder_name == "bin/x64/plugins/cyber_engine_tweaks/mods":
            for item in os.listdir(directory):
                full_path = os.path.join(directory, item)
                if os.path.isdir(full_path):
                    items.append(item)
                    print(f"Wrote directory mod: {item} in {folder_name}")
        else:
            items = os.listdir(directory)
            for item in items:
                print(f"Wrote file mod: {item} in {folder_name}")
        if not items:
            file.write(f"\nNo mods detected in \"{folder_name}\".\n")
            file.write("-" * 120 + "\n")
        else:
            file.write(f"\nMods located in {folder_name}:\n")
            file.write("-" * 120 + "\n")
            for item in items:
                file.write(f"{item}\n")
    else:
        file.write(f"\nError: The subfolder(s) {folder_name} were not found in the current location!\n")

def export_mods():
    if is_game_running():
        messagebox.showwarning("Game Running", "Cannot export mods while Cyberpunk 2077 is running!")
        return
    if not game_dir:
        messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
        return

    # Folder selection dialog
    class FolderSelectionWindow(ctk.CTkToplevel):
        def __init__(self, parent):
            super().__init__(parent)
            self.title("Select Folders to Export")
            self.geometry("400x300")
            self.resizable(False, False)
            self.configure(fg_color=DARK_BG)
            self.selected_folders = []
            self.transient(parent)
            self.grab_set()

            # Center the window
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()
            window_width = 400
            window_height = 300
            x = parent_x + (parent_width - window_width) // 2
            y = parent_y + (parent_height - window_height) // 2
            self.geometry(f"{window_width}x{window_height}+{x}+{y}")

            ctk.CTkLabel(self, text="Select mod folders to export:", font=("Arial", 14), text_color=TEXT_COLOR).pack(pady=10)
            self.folder_vars = {}
            for folder in MOD_DIRECTORIES + ["red4ext/plugins"]:
                var = tk.BooleanVar(value=True)
                self.folder_vars[folder] = var
                ctk.CTkCheckBox(self, text=folder, variable=var, font=("Arial", 12), text_color=TEXT_COLOR,
                                checkbox_height=18, checkbox_width=18, border_color=NEON_GREEN,
                                fg_color=NEON_GREEN, hover_color=NEON_GREEN).pack(pady=5)
            button_frame = ctk.CTkFrame(self, fg_color=DARK_BG)
            button_frame.pack(pady=20)
            ctk.CTkButton(button_frame, text="Confirm", command=self.confirm, fg_color=NEON_GREEN, text_color="black").pack(side="left", padx=10)
            ctk.CTkButton(button_frame, text="Cancel", command=self.cancel, fg_color=ACCENT_RED, text_color="white").pack(side="left", padx=10)

            set_window_icon(self)  # Set icon for folder selection window

        def confirm(self):
            self.selected_folders = [folder for folder, var in self.folder_vars.items() if var.get()]
            self.destroy()

        def cancel(self):
            self.selected_folders = []
            self.destroy()

    folder_window = FolderSelectionWindow(app)
    app.wait_window(folder_window)
    selected_folders = folder_window.selected_folders
    if not selected_folders:
        print("No folders selected, aborting export.")
        return

    save_path = filedialog.asksaveasfilename(
        defaultextension=".zip",
        filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
        title="Save Mod Preset As",
        initialfile=f"Cyberpunk2077_Mod_Preset_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    if not save_path:
        print("No save path selected, aborting export.")
        return

    current_dir = game_dir
    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
    mods = rebuild_mods_dictionary(current_dir, temp_disabled_path)
    core_mods = ["archivexl", "codeware", "tweakxl"]
    equipment_ex_paths = CORE_DEPENDENCIES["EquipmentEx"]["path"]

    # Count total files for progress
    total_files = 0
    for display_name, (mod_dir, mod_name, current_path) in mods.items():
        if TEMP_DISABLED_DIR not in os.path.normpath(current_path) and mod_dir in selected_folders:
            rel_path = os.path.relpath(current_path, current_dir)
            normalized_rel = rel_path.replace("\\", "/").lower()
            is_equipment_ex = (
                normalized_rel == "r6/scripts/equipmentex" or
                normalized_rel.startswith("r6/scripts/equipmentex/") or
                any(normalized_rel == equip_path.replace("\\", "/").lower() for equip_path in equipment_ex_paths)
            )
            is_core_red4ext = (mod_dir == "red4ext/plugins" and mod_name.lower() in core_mods)
            if not is_equipment_ex and not is_core_red4ext:
                if os.path.isfile(current_path):
                    total_files += 1
                elif os.path.isdir(current_path):
                    for root, _, files in os.walk(current_path):
                        total_files += len(files)

    if total_files == 0:
        messagebox.showinfo("No Mods", "No non-core mods found to export in selected folders.")
        return

    # Create progress window
    progress_window, progress_bar, status_label_progress = create_progress_window("Exporting Mod Preset", total_files)
    set_window_icon(progress_window)  # Set the icon for the progress window
    progress_bar.set(0)
    progress_window.update()

    errors = []
    files_processed = 0
    try:
        with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for display_name, (mod_dir, mod_name, current_path) in mods.items():
                if TEMP_DISABLED_DIR not in os.path.normpath(current_path) and mod_dir in selected_folders:
                    rel_path = os.path.relpath(current_path, current_dir)
                    normalized_rel = rel_path.replace("\\", "/").lower()
                    is_equipment_ex = (
                        normalized_rel == "r6/scripts/equipmentex" or
                        normalized_rel.startswith("r6/scripts/equipmentex/") or
                        any(normalized_rel == equip_path.replace("\\", "/").lower() for equip_path in equipment_ex_paths)
                    )
                    is_core_red4ext = (mod_dir == "red4ext/plugins" and mod_name.lower() in core_mods)
                    if not is_equipment_ex and not is_core_red4ext:
                        full_dir = os.path.join(current_dir, mod_dir, mod_name)
                        if os.path.isfile(full_dir):
                            arcname = os.path.relpath(full_dir, current_dir)
                            print(f"Attempting to add: {full_dir} as {arcname}")
                            try:
                                zipf.write(full_dir, arcname)
                                files_processed += 1
                                progress_bar.set(files_processed / total_files)
                                status_label_progress.configure(text=f"Processing: {files_processed}/{total_files}")
                                progress_window.update()
                                print(f"Successfully added: {full_dir}")
                            except Exception as e:
                                errors.append(f"Failed to add {full_dir} to archive: {str(e)}")
                                print(f"Error adding {full_dir}: {e}")
                            if files_processed % 10 == 0:
                                progress_window.update()
                        else:
                            for root, _, files in os.walk(full_dir):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    if os.path.isfile(file_path):
                                        arcname = os.path.relpath(file_path, current_dir)
                                        print(f"Attempting to add: {file_path} as {arcname}")
                                        try:
                                            zipf.write(file_path, arcname)
                                            files_processed += 1
                                            progress_bar.set(files_processed / total_files)
                                            status_label_progress.configure(text=f"Processing: {files_processed}/{total_files}")
                                            progress_window.update()
                                            print(f"Successfully added: {file_path}")
                                        except Exception as e:
                                            errors.append(f"Failed to add {file_path} to archive: {str(e)}")
                                            print(f"Error adding {file_path}: {e}")
                                        if files_processed % 10 == 0:
                                            progress_window.update()
    except Exception as e:
        errors.append(f"Failed to create zip file {save_path}: {str(e)}")
        print(f"Zip creation failed: {e}")
    finally:
        progress_window.destroy()

    if errors:
        messagebox.showinfo("Export Errors", "\n".join(errors))
        if status_label.winfo_exists():
            status_label.configure(text="Mod preset export completed with errors. Check details.")
    else:
        if os.path.exists(save_path):
            messagebox.showinfo("Export Successful", f"Mod preset exported to {save_path}")
            if status_label.winfo_exists():
                status_label.configure(text="Mod preset exported successfully!")
        else:
            messagebox.showerror("Export Failed", "The export process completed but no file was created.")
    update_mod_count_label()

def import_mods():
    if is_game_running():
        messagebox.showwarning("Game Running", "Cannot import mods while Cyberpunk 2077 is running!")
        return
    if not game_dir:
        messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
        return
    zip_path = filedialog.askopenfilename(
        filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
        title="Select Mod Preset to Import"
    )
    if not zip_path:
        print("No zip file selected, aborting import.")
        return

    # Create progress window
    progress_window, progress_bar, status_label_progress = create_progress_window("Importing Mod Preset", 1)
    progress_bar.set(0)
    progress_window.update()

    try:
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            # Count total files for progress
            total_files = len([name for name in zipf.namelist() if not name.endswith('/')])
            if total_files == 0:
                progress_window.destroy()
                messagebox.showinfo("No Files", "The selected zip file contains no files to import.")
                return
            progress_bar.configure(determinate_speed=1.0/total_files)
            files_processed = 0
            errors = []
            
            for file_info in zipf.infolist():
                if not file_info.filename.endswith('/'):
                    try:
                        zipf.extract(file_info, game_dir)
                        files_processed += 1
                        progress_bar.set(files_processed / total_files)
                        status_label_progress.configure(text=f"Processing: {files_processed}/{total_files}")
                        progress_window.update()
                        print(f"Extracted file: {file_info.filename}")
                        if files_processed % 10 == 0:
                            progress_window.update()
                    except Exception as e:
                        errors.append(f"Failed to extract {file_info.filename}: {str(e)}")
                        print(f"Error extracting {file_info.filename}: {e}")

        progress_window.destroy()
        if errors:
            messagebox.showerror("Import Errors", "\n".join(errors))
            status_label.configure(text="Mod preset import completed with errors. Check details.")
        else:
            messagebox.showinfo("Import Successful", f"Mod preset imported to {game_dir}")
            status_label.configure(text="Mod preset imported successfully!")
        update_initial_ui()
        show_mods()
    except Exception as e:
        progress_window.destroy()
        messagebox.showerror("Import Failed", f"Failed to import mod preset: {str(e)}")
        status_label.configure(text="Mod preset import failed.")

def run_script():
    global status_label, log_vars
    if not game_dir:
        messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
        return False

    current_dir = game_dir
    game_path = os.path.join(current_dir, "bin", "x64", "Cyberpunk2077.exe")
    game_version = get_game_version(game_path)
    phantom_liberty_installed = is_phantom_liberty_installed(current_dir)

    archivemods = os.path.join("archive", "pc", "mod")
    cetmods = os.path.join("bin/x64/plugins/cyber_engine_tweaks/mods")
    r6scripts = os.path.join("r6", "scripts")
    r6tweaks = os.path.join("r6", "tweaks")
    path1 = os.path.join(current_dir, archivemods)
    path2 = os.path.join(current_dir, cetmods)
    path3 = os.path.join(current_dir, r6scripts)
    path4 = os.path.join(current_dir, r6tweaks)

    mod_count = 0
    for path in [path1, path2, path3, path4]:
        if os.path.exists(path):
            mod_dir = os.path.relpath(path, current_dir)
            for item in os.listdir(path):
                if mod_dir == os.path.normpath("bin/x64/plugins/cyber_engine_tweaks/mods"):
                    if os.path.isdir(os.path.join(path, item)):
                        mod_count += 1
                        print(f"Counting directory mod: {item} in {mod_dir}")
                else:
                    mod_count += 1
                    print(f"Counting file mod: {item} in {mod_dir}")

    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)

    log_files = {name: info.get("log_path") for name, info in LOG_FILES.items() if "log_path" in info}
    log_errors = {}
    for log_name, log_path in log_files.items():
        full_log_path = os.path.join(current_dir, log_path)
        errors = extract_log_errors(full_log_path)
        if not errors and "log_pattern" in LOG_FILES[log_name]:
            recent_log = get_most_recent_log(current_dir, LOG_FILES[log_name]["log_pattern"])
            if recent_log:
                errors = extract_log_errors(recent_log)
        if errors:
            log_errors[log_name] = errors

    all_core_mods_installed = check_all_core_mods_installed(current_dir)
    core_mods_status = view_core_mods_status(current_dir)
    missing_core_mods = [mod_name for mod_name, info in core_mods_status.items() if not info["installed"]]
    global last_core_mods_status
    last_core_mods_status = all_core_mods_installed

    try:
        with open('Cyberpunk 2077 Mod List.txt', 'w') as file:
            file.write(f"Cyberpunk 2077 Mod List Tool v{tool_Version} by Sammmy1036\n")
            file.write(f"Nexus Mod Page https://www.nexusmods.com/cyberpunk2077/mods/20113\n")
            file.write(f"List created on {datetime.datetime.now().strftime('%B %d, %Y at %I:%M:%S %p')}\n")
            file.write(f"Game Version: {game_version} | Phantom Liberty DLC Installed: {'Yes' if phantom_liberty_installed else 'No'}\n")
            
            if all_core_mods_installed:
                file.write("All Core Mods Installed: Yes\n")
            else:
                missing_str = ", ".join(missing_core_mods)
                file.write(f"All Core Mods Installed: No. Missing Dependencies: {missing_str}\n")
            
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

            write_items_from_dir(file, path1, archivemods, temp_disabled_path)
            write_items_from_dir(file, path2, cetmods, temp_disabled_path)
            write_items_from_dir(file, path3, r6scripts, temp_disabled_path)
            write_items_from_dir(file, path4, r6tweaks, temp_disabled_path)

            red4ext_plugins_dir = os.path.join(current_dir, "red4ext", "plugins")
            if os.path.exists(red4ext_plugins_dir):
                plugins = [item for item in os.listdir(red4ext_plugins_dir) if os.path.isdir(os.path.join(red4ext_plugins_dir, item))]
                if plugins:
                    file.write(f"\nMods located in red4ext/plugins:\n")
                    file.write("-" * 120 + "\n")
                    for plugin in plugins:
                        normalized_name = plugin.lower()
                        if normalized_name not in ["archivexl", "codeware", "tweakxl"]:
                            file.write(f"{plugin}\n")
                            print(f"Wrote red4ext plugin mod: {plugin}")
                else:
                    file.write(f"\nNo mods detected in \"red4ext/plugins\" (excluding core mods).\n")
                    file.write("-" * 120 + "\n")
            else:
                file.write(f"\nError: The subfolder(s) red4ext/plugins were not found in the current location!\n")

            for log_name, var in log_vars.items():
                if not var.get():
                    continue
                log_path = LOG_FILES[log_name].get("log_path")
                if not log_path:
                    continue
                full_log_path = os.path.join(current_dir, log_path)
                file.write(f"\n{log_name} Log:\n")
                file.write("-" * 120 + "\n")
                log_read_success = False
                if os.path.exists(full_log_path):
                    try:
                        with open(full_log_path, 'r', encoding='utf-8') as input_file:
                            log_content = input_file.read()
                            if log_content.strip():
                                file.write(log_content)
                                file.write("\n")
                                log_read_success = True
                            else:
                                file.write(f"The {log_name} log is empty.\n")
                    except (OSError, UnicodeDecodeError) as e:
                        file.write(f"Error reading {log_name}.log: {str(e)}\n")
                if not log_read_success and "log_pattern" in LOG_FILES[log_name]:
                    recent_log = get_most_recent_log(current_dir, LOG_FILES[log_name]["log_pattern"])
                    if recent_log:
                        try:
                            with open(recent_log, 'r', encoding='utf-8') as input_file:
                                file.write(f"Using most recent log file: {os.path.basename(recent_log)}\n")
                                log_content = input_file.read()
                                if log_content.strip():
                                    file.write(log_content)
                                    file.write("\n")
                                    log_read_success = True
                                else:
                                    file.write(f"The recent {log_name} log ({os.path.basename(recent_log)}) is empty.\n")
                        except (OSError, UnicodeDecodeError) as e:
                            file.write(f"Error reading recent {log_name} log ({os.path.basename(recent_log)}): {str(e)}\n")
                if not log_read_success:
                    file.write(f"The {log_name} log could not be found or read! Log not provided!\n")

        # Update footer labels
        mod_count_label.configure(text=f"Total Mods: {mod_count}")
        game_version_label.configure(text=f"Game Version: {game_version}")
        log_errors_label.configure(text=f"Log Errors Detected: {'Yes' if log_errors else 'No'}")
        core_mods_label.configure(text=f"Core Mods Installed: {'Yes' if all_core_mods_installed else 'No'}")

        # Ensure status_label is valid and updated
        if status_label is None or not status_label.winfo_exists():
            print("Warning: status_label does not exist or is destroyed. Recreating status_label.")
            status_label = ctk.CTkLabel(main, text="Success! Check Cyberpunk 2077 Mod List.txt", font=("Arial", 12, "bold"), text_color=TEXT_COLOR)
            status_label.grid(row=3, column=0, pady=10, sticky="n")
        else:
            status_label.configure(text="Success! Check Cyberpunk 2077 Mod List.txt")
        print("Status label updated to: Success! Check Cyberpunk 2077 Mod List.txt")
        
        # Force UI update
        main.update()
        main.update_idletasks()
        app.update()

        return bool(log_errors)

    except Exception as e:
        print(f"Error in run_script: {e}")
        if status_label is None or not status_label.winfo_exists():
            status_label = ctk.CTkLabel(main, text=f"Error generating mod list: {str(e)}", font=("Arial", 12, "bold"), text_color=ACCENT_RED)
            status_label.grid(row=3, column=0, pady=10, sticky="n")
        else:
            status_label.configure(text=f"Error generating mod list: {str(e)}")
        main.update()
        main.update_idletasks()
        app.update()
        return False

def load_game_icon(size=(40, 40)):
    try:
        base64_string = base64_strings.get("game_icon.png")
        if base64_string:
            img_data = base64.b64decode(base64_string)
            pil_image = Image.open(BytesIO(img_data))
            resampling = Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.BILINEAR
            pil_image = pil_image.resize(size, resampling)
            return ctk.CTkImage(pil_image, size=size)
        else:
            print("No base64 data for game_icon.png")
            return None
    except Exception as e:
        print(f"Error loading game icon: {e}")
        return None

def launch_game():
    if is_game_running():
        return
    if not game_dir:
        messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
        return
    game_path = os.path.join(game_dir, "bin", "x64", "Cyberpunk2077.exe")
    if os.path.exists(game_path):
        try:
            launch_button.configure(text="Game Launched", state="disabled")  # Set text and disable button
            os.startfile(game_path)
            print("Game launched successfully")
        except Exception as e:
            launch_button.configure(text="Launch Game", state="normal")  # Revert on failure
            messagebox.showerror("Error", f"Failed to launch game: {str(e)}")
    else:
        messagebox.showerror("Error", "Game executable not found!")

# Add a global variable to track the last known state
last_launch_button_state = None
last_launch_button_text = None

def update_launch_button():
    global last_launch_button_state, last_launch_button_text
    if not launch_button.winfo_exists():
        return
    if is_game_running():
        new_text = "Game Launched"
        new_state = "disabled"
    else:
        new_text = "Launch Game"
        new_state = "normal"
    if new_state != last_launch_button_state or new_text != last_launch_button_text:
        try:
            launch_button.configure(text=new_text, state=new_state)
            last_launch_button_state = new_state
            last_launch_button_text = new_text
            print(f"Updated launch button: text={new_text}, state={new_state}")
        except tk.TclError as e:
            print(f"Error updating launch button: {e}")
    if app.winfo_exists():
        app.after(5000, update_launch_button)

def show_home():
    global status_label, current_page, log_vars
    current_page = "home"
    clear_main()

    # Force layout update
    main.update()

    # Place the image at the very top, centered with y=-70
    img_path = os.path.join(SCRIPT_DIR, "icons", "mod_list_tool.png")

    if os.path.exists(img_path):
        img = ctk.CTkImage(Image.open(img_path), size=(450, 450))
        image_label = ctk.CTkLabel(main, image=img, text="")
        image_label.place(x=(main.winfo_width() - 250) // 2.8, y=-160)
    else:
        ctk.CTkLabel(main, text="Generate Mod List", font=("Orbitron", 22, "bold"), text_color=TEXT_COLOR).grid(row=0, column=0, pady=10, sticky="n")

    # Configure grid to start content just below image
    main.grid_columnconfigure(0, weight=1)
    start_button = ctk.CTkButton(main, text="Generate Mod List", command=run_script, fg_color=NEON_YELLOW, text_color="black", hover_color="#DBBE00")
    start_button.grid(row=0, column=0, pady=(180, 25), sticky="n")

    ctk.CTkLabel(main, text="Select Logs to Include:", text_color=TEXT_COLOR).grid(row=1, column=0, pady=(0, 5), sticky="n")
    
    # Determine available logs dynamically
    available_logs = {}
    if game_dir:
        for log_name, info in LOG_FILES.items():
            log_path = info.get("log_path")
            if log_path:
                full_log_path = os.path.join(game_dir, log_path)
                if os.path.exists(full_log_path):
                    available_logs[log_name] = full_log_path
                elif "log_pattern" in info:
                    recent_log = get_most_recent_log(game_dir, info["log_pattern"])
                    if recent_log:
                        available_logs[log_name] = recent_log

    # Update global log_vars
    log_vars.clear()
    log_vars.update({log_name: tk.BooleanVar(value=True) for log_name in available_logs})

    # Calculate the number of rows needed
    num_logs = len(available_logs) + 1  # +1 for "Select All Logs"

    # Configure grid for dynamic centering
    main.grid_rowconfigure(0, weight=0)  # Image row
    main.grid_rowconfigure(1, weight=0)  # Label row
    for i in range(2, num_logs + 2):
        main.grid_rowconfigure(i, weight=1)  # Rows for checkboxes
    main.grid_rowconfigure(num_logs + 2, weight=1)  # Bottom padding
    main.grid_rowconfigure(num_logs + 3, weight=0)  # Status label row

    # Add "Select All Logs" checkbox
    select_all_var = tk.BooleanVar(value=True)
    def toggle_all_logs():
        state = select_all_var.get()
        for var in log_vars.values():
            var.set(state)
        print(f"Select All Logs toggled: {state}")
    
    ctk.CTkCheckBox(main, text="Select All Logs", variable=select_all_var, command=toggle_all_logs,
                    font=("Arial", 12), text_color=TEXT_COLOR, checkbox_height=18, checkbox_width=18,
                    border_color=NEON_GREEN, fg_color=NEON_GREEN, hover_color=NEON_GREEN).grid(row=2, column=0, pady=5)

    # Add individual log checkboxes
    for i, (log_name, _) in enumerate(available_logs.items(), start=3):
        ctk.CTkCheckBox(main, text=log_name, variable=log_vars[log_name], font=("Arial", 12), text_color=TEXT_COLOR,
                        checkbox_height=18, checkbox_width=18, border_color=NEON_GREEN, fg_color=NEON_GREEN, hover_color=NEON_GREEN).grid(row=i, column=0, pady=5)

    # Create or update status_label
    if status_label is None or not status_label.winfo_exists():
        status_label = ctk.CTkLabel(main, text="Click 'Generate Mod List' to compile the list!", font=("Arial", 12, "bold"), text_color=TEXT_COLOR)
        status_label.grid(row=num_logs + 3, column=0, pady=10, sticky="n")
    else:
        status_label.configure(text="Click 'Generate Mod List' to compile the list!")
        status_label.grid(row=num_logs + 3, column=0, pady=10, sticky="n")

def show_core_mods():
    global status_label, current_page
    current_page = "core_mods"
    clear_main()
    if not game_dir:
        messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
        return

    current_dir = game_dir
    # Place the image at the very top, centered with y=-70
    img_path = os.path.join(SCRIPT_DIR, "icons", "mod_list_tool.png")

    if os.path.exists(img_path):
        img = ctk.CTkImage(Image.open(img_path), size=(250, 250))
        image_label = ctk.CTkLabel(main, image=img, text="")
        image_label.place(x=(main.winfo_width() - 250) // 2, y=-70)
    else:
        ctk.CTkLabel(main, text="Core Mods Status", font=("Orbitron", 22, "bold"), text_color=TEXT_COLOR).grid(row=0, column=0, pady=10, sticky="n")

    # Configure main grid to allow status_frame to expand
    main.grid_columnconfigure(0, weight=1)
    main.grid_rowconfigure(0, weight=0)  # Image or title row
    main.grid_rowconfigure(1, weight=1)  # Status frame row (expandable)
    main.grid_rowconfigure(2, weight=0)  # Status label row
    main.grid_rowconfigure(3, weight=0)  # Button frame row

    status_frame = ctk.CTkFrame(main, fg_color=DARK_BG)
    status_frame.grid(row=1, column=0, pady=(120, 10), padx=10, sticky="nsew")  # Adjusted to start below image and expand
    status_frame.grid_columnconfigure(0, weight=1)  # Center content
    for i in range(len(CORE_DEPENDENCIES)):  # Configure rows dynamically based on number of dependencies
        status_frame.grid_rowconfigure(i, weight=1, minsize=40)  # Uniform row height

    # Status label moved above buttons
    status_label = ctk.CTkLabel(main, text="Click 'Enable/Disable Core Mods' to manage core mods!", font=("Arial", 12, "bold"), text_color=TEXT_COLOR)
    status_label.grid(row=2, column=0, pady=10, sticky="n")

    # Button frame moved below status label
    button_frame = ctk.CTkFrame(main, fg_color=DARK_BG)
    button_frame.grid(row=3, column=0, pady=10, sticky="n")
    ctk.CTkButton(button_frame, text="Disable Core Mods", command=disable_core_mods, fg_color=ACCENT_RED, text_color="white", hover_color="#94160C").pack(side="left", padx=5)
    ctk.CTkButton(button_frame, text="Enable Core Mods", command=enable_core_mods, fg_color=NEON_GREEN, text_color="black", hover_color="#1ADB00").pack(side="left", padx=5)

    previous_status = {}

    def update_status():
        nonlocal previous_status
        try:
            status_data = view_core_mods_status(current_dir)
        except Exception as e:
            print(f"Error in status update: {e}")
            status_data = {mod_name: {"installed": False, "path": info["path"], "version": None}
                          for mod_name, info in CORE_DEPENDENCIES.items()}

        if previous_status != status_data:
            for widget in status_frame.winfo_children():
                widget.destroy()

            # Use uniform grid for consistent column alignment across all rows
            for i, (mod_name, info) in enumerate(status_data.items()):
                # Outer frame for each mod
                outer_frame = ctk.CTkFrame(status_frame, fg_color=DARK_BG)
                outer_frame.grid(row=i, column=0, sticky="ew")  # Remove individual pady, rely on row configuration
                outer_frame.grid_columnconfigure(0, weight=1)  # Inner frame column
                outer_frame.grid_columnconfigure(1, weight=0, minsize=80)  # Install button column with fixed width

                # Inner frame for labels
                inner_frame = ctk.CTkFrame(outer_frame, fg_color=DARK_BG)
                inner_frame.grid(row=0, column=0, sticky="nsew")
                inner_frame.grid_columnconfigure(0, weight=1, uniform="col")  # Name column
                inner_frame.grid_columnconfigure(1, weight=1, uniform="col", minsize=100)  # Version column
                inner_frame.grid_columnconfigure(2, weight=1, uniform="col", minsize=120)  # Status column

                # Labels using grid with uniform alignment
                name_label = ctk.CTkLabel(inner_frame, text=mod_name, font=("Arial", 10, "bold"), text_color=TEXT_COLOR, cursor="hand2")
                name_label.grid(row=0, column=0, padx=5, pady=2, sticky="w")
                def open_mod_page(event, mod_id=CORE_DEPENDENCIES[mod_name]["id"]):
                    webbrowser.open(f"https://www.nexusmods.com/cyberpunk2077/mods/{mod_id}")
                name_label.bind("<Button-1>", open_mod_page)
                def on_enter(event, label=name_label):
                    label.configure(text_color="#E89202")
                    print(f"Hover enter on {mod_name} label")
                def on_leave(event, label=name_label):
                    label.configure(text_color=TEXT_COLOR)
                    print(f"Hover leave on {mod_name} label")
                name_label.bind("<Enter>", on_enter)
                name_label.bind("<Leave>", on_leave)
                print(f"Bound hover effects for {mod_name} label")

                version_text = f"v{info['version']}" if info["version"] and info["version"] != "Unknown" else "N/A"
                version_label = ctk.CTkLabel(inner_frame, text=version_text, font=("Arial", 10), text_color=TEXT_COLOR)
                version_label.grid(row=0, column=1, padx=5, pady=2, sticky="w")

                status_text = "Installed" if info["installed"] else "Not Installed"
                status_color = NEON_GREEN if info["installed"] else ACCENT_RED
                status_symbol = "✔" if info["installed"] else "✘"
                install_status = ctk.CTkLabel(inner_frame, text=f"{status_symbol} {status_text}", font=("Arial", 10), text_color=status_color)
                install_status.grid(row=0, column=2, padx=5, pady=2, sticky="e")

                if not info["installed"]:
                    install_button = ctk.CTkButton(outer_frame, text="Install",
                                                  command=lambda name=mod_name: webbrowser.open(f"https://www.nexusmods.com/cyberpunk2077/mods/{CORE_DEPENDENCIES[name]['id']}"),
                                                  font=("Arial", 10), fg_color=NEON_GREEN, text_color="black")
                    install_button.grid(row=0, column=1, padx=5, pady=2, sticky="e")

        previous_status = status_data.copy()

        if app.winfo_exists():
            app.after(2000, update_status)

    update_status()

    # Recreate status_label to ensure it exists
    status_label = ctk.CTkLabel(main, text="Click 'Enable/Disable Core Mods' to manage core mods!", font=("Arial", 12, "bold"), text_color=TEXT_COLOR)
    status_label.grid(row=2, column=0, pady=10, sticky="n")

def show_log_viewer():
    global status_label, current_page
    current_page = "log_viewer"
    clear_main()
    if not game_dir:
        messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
        return

    current_dir = game_dir
    # Place the image at the very top, centered with y=-70
    img_path = os.path.join(SCRIPT_DIR, "icons", "mod_list_tool.png")

    if os.path.exists(img_path):
        img = ctk.CTkImage(Image.open(img_path), size=(250, 250))
        image_label = ctk.CTkLabel(main, image=img, text="")
        image_label.place(x=(main.winfo_width() - 250) // 2, y=-70)
    else:
        ctk.CTkLabel(main, text="Log File Viewer", font=("Orbitron", 22, "bold"), text_color=TEXT_COLOR).grid(row=0, column=0, pady=10, sticky="n")

    # Configure main grid to allow log_frame to expand
    main.grid_columnconfigure(0, weight=1)
    main.grid_rowconfigure(0, weight=0)  # Image or title row
    main.grid_rowconfigure(1, weight=1)  # Log frame row (expandable)
    main.grid_rowconfigure(2, weight=0)  # Status label row

    log_frame = ctk.CTkFrame(main, fg_color=DARK_BG)
    log_frame.grid(row=1, column=0, pady=(120, 10), padx=10, sticky="nsew")  # Adjusted to start below image
    log_frame.grid_rowconfigure(0, weight=1)  # Allow listbox and text to expand
    log_frame.grid_columnconfigure(0, weight=1)  # Left column (listbox)
    log_frame.grid_columnconfigure(1, weight=2)  # Right column (text, slightly wider)

    # Log selection listbox
    log_list_frame = ctk.CTkFrame(log_frame, fg_color=DARK_BG)
    log_list_frame.grid(row=0, column=0, padx=10, sticky="nsew")
    log_list_frame.grid_rowconfigure(1, weight=1)  # Allow listbox to expand
    log_list_frame.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(log_list_frame, text="Available Logs", font=("Arial", 12), text_color=TEXT_COLOR).pack()
    
    log_scrollbar = ctk.CTkScrollbar(log_list_frame, orientation="vertical")
    log_scrollbar.pack(side="right", fill="y")
    log_listbox = tk.Listbox(log_list_frame, font=("Arial", 10), width=30, height=30, bg="#333333", fg="white", selectmode=tk.SINGLE)
    log_listbox.pack(side="left", fill="both", expand=True)  # Expand to fill available space
    log_listbox.configure(yscrollcommand=log_scrollbar.set)
    log_scrollbar.configure(command=log_listbox.yview)

    # Text area for log content
    text_frame = ctk.CTkFrame(log_frame, fg_color=DARK_BG)
    text_frame.grid(row=0, column=1, padx=10, sticky="nsew")
    text_frame.grid_rowconfigure(1, weight=1)  # Allow text widget to expand
    text_frame.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(text_frame, text="Log Viewer", font=("Arial", 12), text_color=TEXT_COLOR).pack()
    
    text_scrollbar = ctk.CTkScrollbar(text_frame, orientation="vertical")
    text_scrollbar.pack(side="right", fill="y")
    log_text = tk.Text(text_frame, font=("Arial", 10), bg="#333333", fg="white", wrap=tk.WORD, height=30)
    log_text.pack(side="left", fill="both", expand=True)  # Expand to fill available space
    log_text.configure(yscrollcommand=text_scrollbar.set, state="disabled")
    text_scrollbar.configure(command=log_text.yview)

    # Populate log listbox
    available_logs = {}
    for log_name, info in LOG_FILES.items():
        log_path = info.get("log_path")
        if not log_path:
            continue
        full_log_path = os.path.join(current_dir, log_path)
        if os.path.exists(full_log_path):
            available_logs[log_name] = full_log_path
        elif "log_pattern" in info:
            recent_log = get_most_recent_log(current_dir, info["log_pattern"])
            if recent_log:
                available_logs[log_name] = recent_log

    for log_name in sorted(available_logs.keys()):
        log_listbox.insert(tk.END, log_name)

    def display_log(event=None):
        selection = log_listbox.curselection()
        if not selection:
            return
        log_name = log_listbox.get(selection[0])
        log_path = available_logs.get(log_name)
        if not log_path:
            return

        log_text.configure(state="normal")
        log_text.delete("1.0", tk.END)
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                content = f.read()
                log_text.insert(tk.END, content)
        except (OSError, UnicodeDecodeError) as e:
            log_text.insert(tk.END, f"Error reading log file: {str(e)}")
        log_text.configure(state="disabled")
        status_label.configure(text=f"Viewing log: {log_name}")

    def open_log_file(event=None):
        selection = log_listbox.curselection()
        if not selection:
            return
        log_name = log_listbox.get(selection[0])
        log_path = available_logs.get(log_name)
        if not log_path:
            messagebox.showerror("Error", f"Log file path for {log_name} not found!")
            return
        try:
            os.startfile(log_path)  # Open the file with the default system application
            status_label.configure(text=f"Opened log file: {log_name}")
            print(f"Opened log file: {log_path}")
        except OSError as e:
            messagebox.showerror("Error", f"Failed to open log file {log_name}: {str(e)}")
            print(f"Error opening log file {log_path}: {e}")

    log_listbox.bind("<<ListboxSelect>>", display_log)
    log_listbox.bind("<Double-Button-1>", open_log_file)  # Bind double-click to open file

    # Recreate status_label
    status_label = ctk.CTkLabel(main, text="Select a log file to view its contents or double-click to open!", font=("Arial", 12, "bold"), text_color=TEXT_COLOR)
    status_label.grid(row=2, column=0, pady=10, sticky="n")

def show_license():
    # Check if license window is already open
    for child in app.winfo_children():
        if isinstance(child, ctk.CTkToplevel) and child.title() == "License":
            print("License window already open, skipping creation")
            return

    license_window = ctk.CTkToplevel(app)
    license_window.title("License")
    license_window.geometry("600x400")
    license_window.resizable(False, False)
    license_window.configure(fg_color=DARK_BG)

    # Center the window relative to the main app window
    app_x = app.winfo_x()
    app_y = app.winfo_y()
    app_width = app.winfo_width()
    app_height = app.winfo_height()
    window_width = 600
    window_height = 400
    x = app_x + (app_width - window_width) // 2
    y = app_y + (app_height - window_height) // 2
    license_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # Add widgets after geometry
    license_textbox = ctk.CTkTextbox(license_window, font=("Arial", 12), text_color="#FFFFFF", fg_color="#333333", wrap="word", height=350, width=550)
    license_textbox.pack(pady=10, padx=10, fill="both", expand=True)
    license_textbox.insert("0.0", """---

MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.""")
    license_textbox.configure(state="disabled")

    # Set modal properties after widgets
    license_window.transient(app)
    license_window.grab_set()

    # Set icon after all properties and widgets
    set_window_icon(license_window)

def show_disclaimer():
    # Check if disclaimer window is already open
    for child in app.winfo_children():
        if isinstance(child, ctk.CTkToplevel) and child.title() == "Disclaimer":
            print("Disclaimer window already open, skipping creation")
            return

    disclaimer_window = ctk.CTkToplevel(app)
    disclaimer_window.title("Disclaimer")
    disclaimer_window.geometry("600x400")
    disclaimer_window.resizable(False, False)
    disclaimer_window.configure(fg_color=DARK_BG)

    # Center the window relative to the main app window
    app_x = app.winfo_x()
    app_y = app.winfo_y()
    app_width = app.winfo_width()
    app_height = app.winfo_height()
    window_width = 600
    window_height = 400
    x = app_x + (app_width - window_width) // 2
    y = app_y + (app_height - window_height) // 2
    disclaimer_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # Add widgets after geometry
    disclaimer_textbox = ctk.CTkTextbox(disclaimer_window, font=("Arial", 12), text_color="#FFFFFF", fg_color="#333333", wrap="word", height=350, width=550)
    disclaimer_textbox.pack(pady=10, padx=10, fill="both", expand=True)
    disclaimer_textbox.insert("0.0", """---

Cyberpunk 2077 Mod List Tool is an unofficial, fan-made project and is not affiliated with, endorsed by, or supported by CD PROJEKT S.A. or its affiliates. All trademarks, logos, and game assets related to Cyberpunk 2077 are the property of CD PROJEKT S.A.

This tool is provided for non-commercial use only and is intended to assist users in managing mods for Cyberpunk 2077 in accordance with CD PROJEKT RED's Fan Content Guidelines and End User License Agreement (EULA). Users are responsible for ensuring that their use of this tool and any mods managed with it complies with CD PROJEKT RED's terms, available at regulations.cdprojektred.com and www.cyberpunk.net.

The developer of this tool is not responsible for any damage, loss, game instability, or bans resulting from the use of this tool or any mods managed with it. Users are advised to back up their game files before using this tool and to use it at their own risk. Modding may cause game instability or violate CD PROJEKT RED's terms, and users assume all associated risks.

For official modding support, refer to CD PROJEKT RED's REDmod tool and documentation.""")
    disclaimer_textbox.configure(state="disabled")

    # Set modal properties after widgets
    disclaimer_window.transient(app)
    disclaimer_window.grab_set()

    # Set icon after all properties and widgets
    set_window_icon(disclaimer_window)

def show_settings():
    global status_label, current_page
    current_page = "settings"
    clear_main()
    
    # Place the image at the very top, centered with y=-70
    img_path = os.path.join(SCRIPT_DIR, "icons", "mod_list_tool.png")

    if os.path.exists(img_path):
        img = ctk.CTkImage(Image.open(img_path), size=(600, 600))
        image_label = ctk.CTkLabel(main, image=img, text="")
        image_label.place(x=(main.winfo_width() - 250) // 4, y=-160)
    else:
        ctk.CTkLabel(main, text="Settings", font=("Orbitron", 22, "bold"), text_color=TEXT_COLOR).grid(row=0, column=0, pady=10, sticky="n")

    # Configure grid to start content just below image
    main.grid_columnconfigure(0, weight=1)
    main.grid_columnconfigure(1, weight=1)  # Add second column for side-by-side buttons
    ctk.CTkButton(main, text="Change Game Directory", command=change_game_directory, fg_color=NEON_YELLOW, text_color="black", hover_color="#DBBE00").grid(row=0, column=0, columnspan=2, pady=(300, 10), sticky="n")
    
    # Display current game directory
    current_dir_text = f"Current Game Directory: {game_dir if game_dir else 'Not Set'}"
    ctk.CTkLabel(main, text=current_dir_text, font=("Arial", 12), text_color=TEXT_COLOR).grid(row=1, column=0, columnspan=2, pady=10, sticky="n")
    
    # Status label moved above buttons
    status_label = ctk.CTkLabel(main, text="Click 'Change Game Directory' to update the game path!", font=("Arial", 12, "bold"), text_color=TEXT_COLOR)
    status_label.grid(row=2, column=0, columnspan=2, pady=10, sticky="n")
    
    # Side-by-side License and Disclaimer buttons directly in main
    ctk.CTkButton(main, text="View License", command=show_license, fg_color=NEON_YELLOW, text_color="black", hover_color="#DBBE00").grid(row=3, column=0, padx=10, pady=10, sticky="e")
    ctk.CTkButton(main, text="View Disclaimer", command=show_disclaimer, fg_color=NEON_YELLOW, text_color="black", hover_color="#DBBE00").grid(row=3, column=1, padx=10, pady=10, sticky="w")

def clear_main():
    # Reset all column configurations
    for i in range(main.grid_size()[0]):  # Get number of columns
        main.grid_columnconfigure(i, weight=0, minsize=0)
    # Reset all row configurations (if needed)
    for i in range(main.grid_size()[1]):  # Get number of rows
        main.grid_rowconfigure(i, weight=0)
    # Destroy all widgets
    for widget in main.winfo_children():
        widget.destroy()

def update_initial_ui():
    global last_core_mods_status, status_label
    if game_dir and os.path.exists(os.path.join(game_dir, "bin", "x64", "Cyberpunk2077.exe")):
        current_dir = game_dir
        initial_game_version = get_game_version(os.path.join(current_dir, "bin", "x64", "Cyberpunk2077.exe"))
        initial_phantom_liberty_installed = is_phantom_liberty_installed(current_dir)
        initial_log_errors = check_log_errors(current_dir)
        
        initial_all_core_mods_installed = check_all_core_mods_installed(current_dir)
        last_core_mods_status = initial_all_core_mods_installed

        initial_mod_count = 0
        for mod_dir in MOD_DIRECTORIES:
            full_dir = os.path.join(current_dir, mod_dir)
            if os.path.exists(full_dir):
                for item in os.listdir(full_dir):
                    if mod_dir == os.path.normpath("bin/x64/plugins/cyber_engine_tweaks/mods"):
                        if os.path.isdir(os.path.join(full_dir, item)):
                            initial_mod_count += 1
                    else:
                        initial_mod_count += 1

        mod_count_label.configure(text=f"Total Mods: {initial_mod_count}")
        game_version_label.configure(text=f"Game Version: {initial_game_version}")
        log_errors_label.configure(text=f"Log Errors Detected: {'Yes' if initial_log_errors else 'No'}")
        core_mods_label.configure(text=f"Core Mods Installed: {'Yes' if initial_all_core_mods_installed else 'No'}")
        if status_label.winfo_exists():
            if current_page == "settings":
                status_label.configure(text="Game directory updated successfully!" if game_dir else "Click 'Change Game Directory' to update the game path!")
            elif current_page == "home":
                status_label.configure(text="Click 'Generate Mod List' to compile the list!")
            # Add other page-specific messages if needed
        if mod_observer:
            mod_observer.stop()
            mod_observer.join()
        start_mod_watcher()
        update_core_mods_label()
    else:
        mod_count_label.configure(text="Total Mods: Unknown")
        game_version_label.configure(text="Game Version: Unknown")
        log_errors_label.configure(text="Log Errors Detected: Unknown")
        core_mods_label.configure(text="Core Mods Installed: Unknown")
        show_settings()

if not check_single_instance():
    messagebox.showinfo("Cyberpunk 2077 Mod List Tool", "Another instance of Cyberpunk 2077 Mod List Tool is already running.")
    sys.exit(0)

app = ctk.CTk()
app.geometry("1200x700")
app.title("Cyberpunk 2077 Mod Manager")
app.resizable(False, False)
set_window_icon(app)

screen_width = app.winfo_screenwidth()
screen_height = app.winfo_screenheight()
window_width = 1200
window_height = 700
x = (screen_width - window_width) // 2
y = (screen_height - window_height) // 2
app.geometry(f"{window_width}x{window_height}+{x}+{y}")

if os.path.exists(ICON_PATH):
    try:
        app.iconbitmap(ICON_PATH)
    except tk.TclError as e:
        print(f"Warning: Failed to set icon from '{ICON_PATH}': {e}. Using default icon.")

game_dir = load_game_dir_from_registry()
current_dir = os.getcwd()
if os.path.exists(os.path.join(current_dir, "bin", "x64", "Cyberpunk2077.exe")):
    game_dir = current_dir
    save_game_dir_to_registry()

# Configure grid layout for the main window
app.grid_columnconfigure(1, weight=1)
app.grid_rowconfigure(0, weight=1)
app.grid_rowconfigure(1, weight=0)  # Row for footer

sidebar = ctk.CTkFrame(app, width=250, corner_radius=0, fg_color=DARK_BG)
sidebar.grid(row=0, column=0, sticky="nsew")
sidebar.grid_rowconfigure(5, weight=1)  # Weight for the main content, adjusted for 6 rows

def load_icon(file_name, size=(20, 20)):
    try:
        # Use just the filename as the key, not the full path
        base64_string = base64_strings.get(os.path.basename(file_name))
        if base64_string:
            img_data = base64.b64decode(base64_string)
            pil_image = Image.open(BytesIO(img_data))
            resampling = Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.BILINEAR
            pil_image = pil_image.resize(size, resampling)
            return ctk.CTkImage(pil_image, size=size)
        else:
            print(f"No base64 data for {os.path.basename(file_name)}")
            return None
    except Exception as e:
        print(f"Error loading icon {file_name}: {e}")
        return None

home_icon = load_icon(os.path.join(SCRIPT_DIR, "icons", "home_icon.png"))
mods_icon = load_icon(os.path.join(SCRIPT_DIR, "icons", "mods_icon.png"))
settings_icon = load_icon(os.path.join(SCRIPT_DIR, "icons", "settings_icon.png"))
core_icon = load_icon(os.path.join(SCRIPT_DIR, "icons", "core_icon.png"))
log_icon = load_icon(os.path.join(SCRIPT_DIR, "icons", "log_icon.png"))
launch_icon = load_icon(os.path.join(SCRIPT_DIR, "icons", "game_icon.png"))

# Row 0-4: Menu buttons
ctk.CTkButton(sidebar, text="Home", command=show_home, image=home_icon, compound="left" if home_icon else "none", fg_color=DARK_BG, hover_color="#6B6B6B", anchor="w", font=("Arial", 12, "bold"), text_color="white", width=200, height=50, corner_radius=10).grid(row=0, column=0, pady=(20, 5), padx=10, sticky="w")
ctk.CTkButton(sidebar, text="Mod Management", command=show_mods, image=mods_icon, compound="left" if mods_icon else "none", fg_color=DARK_BG, hover_color="#6B6B6B", anchor="w", font=("Arial", 12, "bold"), text_color="white", width=200, height=50, corner_radius=10).grid(row=1, column=0, pady=5, padx=10, sticky="w")
ctk.CTkButton(sidebar, text="Core Mods Status", command=show_core_mods, image=core_icon, compound="left" if core_icon else "none", fg_color=DARK_BG, hover_color="#6B6B6B", anchor="w", font=("Arial", 12, "bold"), text_color="white", width=200, height=50, corner_radius=10).grid(row=2, column=0, pady=5, padx=10, sticky="w")
ctk.CTkButton(sidebar, text="Log File Viewer", command=show_log_viewer, image=log_icon, compound="left" if log_icon else "none", fg_color=DARK_BG, hover_color="#6B6B6B", anchor="w", font=("Arial", 12, "bold"), text_color="white", width=200, height=50, corner_radius=10).grid(row=3, column=0, pady=5, padx=10, sticky="w")
ctk.CTkButton(sidebar, text="Settings", command=show_settings, image=settings_icon, compound="left" if settings_icon else "none", fg_color=DARK_BG, hover_color="#6B6B6B", anchor="w", font=("Arial", 12, "bold"), text_color="white", width=200, height=50, corner_radius=10).grid(row=4, column=0, pady=5, padx=10, sticky="w")

# Launch Game Button
global launch_button
print(f"game_dir: {game_dir}")  # Debug print
game_icon = load_game_icon() or launch_icon  # Fallback to launch_icon if game_icon is None
print(f"game_icon: {game_icon}")  # Debug print
launch_button = ctk.CTkButton(sidebar, text="Launch Game", command=launch_game, image=game_icon, compound="left" if game_icon else "top", fg_color=DARK_BG, hover_color="#6B6B6B", anchor="w", font=("Arial", 12, "bold"), text_color="white", width=200, height=50, corner_radius=10)
launch_button.grid(row=6, column=0, pady=5, padx=10, sticky="w")

# Main content area
main = ctk.CTkFrame(app, corner_radius=0, fg_color="#222222")
main.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

# Footer (using grid with centered inner frame and adjusted column weights)
footer = ctk.CTkFrame(app, height=50, fg_color="#0e0e0e")  # Increased height to 50 for better spacing
footer.grid(row=1, column=0, columnspan=2, sticky="ew")
app.grid_rowconfigure(1, weight=0)  # Ensure footer doesn't stretch vertically

# Inner frame to manage content
footer_inner = ctk.CTkFrame(footer, fg_color="#0e0e0e")
footer_inner.grid(row=0, column=0, sticky="nsew")
footer.grid_columnconfigure(0, weight=1)  # Allow inner frame to expand and center

# Configure 8 columns with equal weights for spacing
footer_inner.grid_columnconfigure(0, weight=1)  # Left padding column
footer_inner.grid_columnconfigure(1, weight=1)  # Total Mods
footer_inner.grid_columnconfigure(2, weight=1)  # Game Version
footer_inner.grid_columnconfigure(3, weight=1)  # Tool Version
footer_inner.grid_columnconfigure(4, weight=1)  # Log Errors Detected
footer_inner.grid_columnconfigure(5, weight=1)  # Core Mods Installed
footer_inner.grid_columnconfigure(6, weight=1)  # Nexus Mod Page
footer_inner.grid_columnconfigure(7, weight=1)  # Right padding column

# Place widgets in the inner frame with uniform padding
mod_count_label = ctk.CTkLabel(footer_inner, text="Total Mods: Unknown", text_color=TEXT_COLOR)
mod_count_label.grid(row=0, column=1, sticky="w", padx=5, pady=5)  # Uniform padding

game_version_label = ctk.CTkLabel(footer_inner, text="Game Version: Unknown", text_color=TEXT_COLOR)
game_version_label.grid(row=0, column=2, sticky="nse", padx=5, pady=5)  # Uniform padding

tool_version_label = ctk.CTkLabel(footer_inner, text=f"Tool Version: {tool_Version}", text_color=TEXT_COLOR)
tool_version_label.grid(row=0, column=3, sticky="nse", padx=5, pady=5)  # Uniform padding

log_errors_label = ctk.CTkLabel(footer_inner, text="Log Errors Detected: Unknown", text_color=TEXT_COLOR)
log_errors_label.grid(row=0, column=4, sticky="nse", padx=5, pady=5)  # Uniform padding

core_mods_label = ctk.CTkLabel(footer_inner, text="Core Mods Installed: Unknown", text_color=TEXT_COLOR)
core_mods_label.grid(row=0, column=5, sticky="nse", padx=5, pady=5)  # Uniform padding

# Nexus Mod Page link with hover effect
link = ctk.CTkLabel(footer_inner, text="Nexus Mod Page", text_color=NEON_YELLOW, cursor="hand2")
link.grid(row=0, column=6, sticky="e", padx=5, pady=5)  # Uniform padding
link.bind("<Button-1>", lambda e: webbrowser.open_new("https://www.nexusmods.com/cyberpunk2077/mods/20113"))
link.bind("<Enter>", lambda e: link.configure(text_color="#E89202"))  # Orange on hover
link.bind("<Leave>", lambda e: link.configure(text_color=NEON_YELLOW))  # Revert to NEON_YELLOW

status_label = ctk.CTkLabel(main, text="", font=("Arial", 12), text_color=TEXT_COLOR)
show_home()
update_initial_ui()
update_launch_button()  # Ensure this is present
app.protocol("WM_DELETE_WINDOW", on_closing)
app.mainloop()
