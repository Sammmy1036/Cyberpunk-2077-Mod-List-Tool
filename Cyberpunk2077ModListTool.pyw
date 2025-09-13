from io import BytesIO
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image
from threading import Thread, Timer
from tkinter import messagebox, filedialog
from win32file import CreateFile, SetFileTime, CloseHandle
from win32con import FILE_SHARE_READ, FILE_SHARE_WRITE, OPEN_EXISTING
import customtkinter as ctk
import tkinter as tk
import base64
import tempfile
import webbrowser
import datetime, time
import re
import shutil, psutil
import zipfile, py7zr, rarfile, pyunpack, patoolib
import winreg
import requests
import hashlib
import chardet
import subprocess, sys, platform, os, threading

if platform.system() == "Windows":
    import msvcrt
else:
    msvcrt = None

try:
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

if getattr(sys, 'frozen', False):
    SCRIPT_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    from win32con import FILE_WRITE_ATTRIBUTES
except Exception:
    FILE_WRITE_ATTRIBUTES = 0x0100

manual_versions = {}  # Store user-entered versions
manual_version_checksums = {}  

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

auto_open_output = None  
auto_select_all_logs = None  

def open_folder(path: str):
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif sys.platform == "darwin":  
            subprocess.Popen(["open", path])
        else: 
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print(f"Failed to open folder {path}: {e}")

def get_file_checksum(file_path):
    try:
        if not os.path.exists(file_path):
            return None
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        return None

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
        return None

base64_strings = {}
for image_file in image_files:
    full_path = os.path.join(image_dir, image_file)
    if os.path.exists(full_path):
        base64_string = convert_image_to_base64(full_path)
        if base64_string:
            base64_strings[image_file] = base64_string

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

NEON_YELLOW = "#fcee09"
DARK_BG = "#111111"
NEON_GREEN = "#5BDE7B"
TEXT_COLOR = "#fcee09"
ACCENT_RED = "#DB002F"
tool_Version = "2.0.0.2"
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

ICON_PATH = os.path.join(SCRIPT_DIR, "Cyberpunk 2077 Mod List Tool.ico")

def set_window_icon(window):
    if not os.path.exists(ICON_PATH):
        return
    try:
        window.update_idletasks()
        if platform.system() == "Windows":
            window.after(200, lambda: window.iconbitmap(ICON_PATH))
        try:
            img = tk.PhotoImage(file=os.path.join(SCRIPT_DIR, "icons", "mod_list_tool.png"))
            window.iconphoto(True, img)
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
mods = {}  
update_debounce_timer = None 
include_errors_in_output = None
include_disabled_in_output = None
after_tasks = []
current_page = None
image_cache = {}
current_image_label = None
status_labels = {}
mod_observer_lock = threading.Lock()

def get_cached_image(size):
    key = tuple(size)
    if key not in image_cache:
        img_path = os.path.join(SCRIPT_DIR, "icons", "mod_list_tool.png")
        if os.path.exists(img_path):
            try:
                pil_img = Image.open(img_path)
                image_cache[key] = ctk.CTkImage(light_image=pil_img, size=size)
            except Exception as e:
                print(f"Failed to load image for size {size}: {e}")
                image_cache[key] = None
        else:
            image_cache[key] = None
    return image_cache[key]


class ModDirectoryHandler(FileSystemEventHandler):
    def __init__(self, current_dir, enabled_listbox, disabled_listbox, selected_dir_var, search_var):
        self.current_dir = current_dir
        self.enabled_listbox = enabled_listbox
        self.disabled_listbox = disabled_listbox
        self.selected_dir_var = selected_dir_var
        self.search_var = search_var
        self.temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)

    def on_any_event(self, event):
        global update_debounce_timer
        if event.is_directory and event.src_path.endswith(TEMP_DISABLED_DIR):
            return 
        if event.src_path.lower().endswith(('.log', '.ini', '.tmp')):
            return
        if update_debounce_timer:
            update_debounce_timer.cancel()
        update_debounce_timer = Timer(0.5, self.update_ui)
        update_debounce_timer.start()

    def update_ui(self):
        global mods
        if not game_dir:
            return
        mods = rebuild_mods_dictionary(self.current_dir, self.temp_disabled_path)
        update_mod_count_label()
        if current_page == "mods" and self.enabled_listbox.winfo_exists() and self.disabled_listbox.winfo_exists():
            update_mod_list(self.enabled_listbox, self.disabled_listbox, self.selected_dir_var, mods, self.search_var.get())

def update_mods_after_page_load():
    global mods
    if not game_dir:
        return
    current_dir = game_dir
    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
    mods = rebuild_mods_dictionary(current_dir, temp_disabled_path)
    update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_var.get())
    start_mod_observer()

def save_game_dir_to_registry():
    global game_dir, auto_open_output, auto_select_all_logs, include_errors_in_output, include_disabled_in_output, manual_versions
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
        try:
            if game_dir:
                winreg.SetValueEx(key, REGISTRY_VALUE, 0, winreg.REG_SZ, game_dir)

            def _set_dword(name, var):
                if var is not None:
                    winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, int(bool(var.get())))

            _set_dword("AutoOpenOutput", auto_open_output)
            _set_dword("AutoSelectAllLogs", auto_select_all_logs)
            _set_dword("IncludeErrorsInOutput", include_errors_in_output)
            _set_dword("IncludeDisabledInOutput", include_disabled_in_output)

            # Save manual mod versions
            for mod_name, version in manual_versions.items():
                winreg.SetValueEx(key, f"{mod_name}_Version", 0, winreg.REG_SZ, version or "")
        finally:
            winreg.CloseKey(key)
    except PermissionError:
        messagebox.showerror("Error", "Insufficient permissions to save settings to registry. Run as administrator.")
    except OSError as e:
        messagebox.showerror("Error", f"Failed to save settings to registry: {e}")
    except Exception as e:
        messagebox.showerror("Error", f"Unexpected error saving settings: {e}")


def async_save_game_dir():
    Thread(target=save_game_dir_to_registry, daemon=True).start()

def load_game_dir_from_registry():
    global game_dir, auto_open_output, auto_select_all_logs, include_errors_in_output, include_disabled_in_output, manual_versions
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_READ)

        def _get_value(name, default=None):
            try:
                val, _ = winreg.QueryValueEx(key, name)
                return val
            except FileNotFoundError:
                return default

        value = _get_value(REGISTRY_VALUE)
        auto_open_value          = int(bool(_get_value("AutoOpenOutput", 0)))
        auto_select_logs_value   = int(bool(_get_value("AutoSelectAllLogs", 1)))
        include_errors_value     = int(bool(_get_value("IncludeErrorsInOutput", 0)))
        include_disabled_value   = int(bool(_get_value("IncludeDisabledInOutput", 0)))

        for mod_name in ["EquipmentEx", "Redscript"]:
            manual_versions[mod_name] = _get_value(f"{mod_name}_Version", "") or ""

        winreg.CloseKey(key)

        if value and os.path.exists(os.path.join(value, "bin", "x64", "Cyberpunk2077.exe")):
            game_dir = value
            if auto_open_output is not None:
                auto_open_output.set(bool(auto_open_value))
            if auto_select_all_logs is not None:
                auto_select_all_logs.set(bool(auto_select_logs_value))
            if include_errors_in_output is not None:
                include_errors_in_output.set(bool(include_errors_value))
            if include_disabled_in_output is not None:
                include_disabled_in_output.set(bool(include_disabled_value))
            return value
        return None
    except FileNotFoundError:
        return None
    except Exception:
        return None

def change_game_directory():
    global game_dir, mod_observer, status_label, game_dir_label

    new_dir = filedialog.askdirectory(
        title="Select Cyberpunk 2077 Game Directory",
        initialdir=game_dir or r"C:\Program Files (x86)\Steam\steamapps\common\Cyberpunk 2077"
    )
    if not new_dir:
        return

    game_exe = os.path.join(new_dir, "bin", "x64", "Cyberpunk2077.exe")
    if not os.path.exists(game_exe):
        messagebox.showerror("Invalid Directory", "Selected directory does not contain Cyberpunk2077.exe!")
        return

    with mod_observer_lock:
        if mod_observer:
            try:
                mod_observer.stop()
                mod_observer.join(timeout=5.0)
            except Exception as e:
                print(f"Error stopping existing mod_observer: {e}")
            finally:
                mod_observer = None

    game_dir = new_dir
    save_game_dir_to_registry()
    messagebox.showinfo("Success", f"Game directory set to: {game_dir}")

    if 'game_dir_label' in globals() and game_dir_label and game_dir_label.winfo_exists():
        game_dir_label.configure(text=f"Current Game Directory: {game_dir}")

    if status_label and status_label.winfo_exists():
        status_label.configure(text="Game directory updated successfully.")
        def _reset_status():
            if current_page == "settings" and status_label.winfo_exists():
                status_label.configure(text="")
        after_id = app.after(5000, _reset_status)
        after_tasks.append(after_id)

    update_initial_ui()
    show_settings()
    if current_page == "mods":
        start_mod_observer()

def on_closing():
    global mod_observer, update_debounce_timer

    try:
        if mod_observer:
            try:
                mod_observer.stop()
                mod_observer.join(timeout=5.0)
                if mod_observer.is_alive():
                    print("Closing application: Warning: mod_observer did not terminate within 5 seconds")
            except Exception as e:
                print(f"Closing application: Error stopping mod observer: {e}")
            finally:
                mod_observer = None

        if update_debounce_timer:
            try:
                update_debounce_timer.cancel()
            except Exception:
                pass

        if hasattr(sys, 'lock_file_handle') and sys.lock_file_handle:
            try:
                msvcrt.locking(sys.lock_file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            except Exception as e:
                print(f"Closing application: Error unlocking: {e}")
            try:
                sys.lock_file_handle.close()
            except Exception:
                pass
            try:
                if os.path.exists(LOCK_FILE):
                    os.remove(LOCK_FILE)
            except Exception as e:
                print(f"Closing application: Error removing lock file: {e}")

        for after_id in list(after_tasks):
            try:
                app.after_cancel(after_id)
            except Exception:
                pass
        after_tasks.clear()

        app.quit()
        sys.exit(0)
    except Exception:
        sys.exit(1)
def start_mod_observer():
    global mod_observer
    if not game_dir or not main.winfo_exists():
        return

    for name in ["enabled_listbox", "disabled_listbox", "selected_dir_var", "search_var"]:
        if name not in globals() or globals()[name] is None:
            return

    with mod_observer_lock:
        if mod_observer and mod_observer.is_alive():
            try:
                mod_observer.stop()
                mod_observer.join(timeout=5.0)
                if mod_observer.is_alive():
                    print("Warning: mod_observer did not terminate")
            except Exception as e:
                print(f"Error stopping mod_observer: {e}")
            finally:
                mod_observer = None

        observer = Observer()
        try:
            handler = ModDirectoryHandler(game_dir, enabled_listbox, disabled_listbox, selected_dir_var, search_var)

            watched_roots = MOD_DIRECTORIES + ["red4ext/plugins"]
            for rel in watched_roots:
                for root in (
                    os.path.join(game_dir, rel),
                    os.path.join(game_dir, TEMP_DISABLED_DIR, rel)
                ):
                    if os.path.exists(root):
                        try:
                            observer.schedule(handler, root, recursive=True)
                        except Exception as e:
                            print(f"Error scheduling observer for {root}: {e}")

            observer.start()
            mod_observer = observer
        except Exception as e:
            print(f"Failed to start file observer: {e}")
            mod_observer = None

def check_single_instance():
    try:
        lock_file_handle = open(LOCK_FILE, 'wb+')
        msvcrt.locking(lock_file_handle.fileno(), msvcrt.LK_NBLCK, 1)
        sys.lock_file_handle = lock_file_handle
        lock_file_handle.write(str(os.getpid()).encode('utf-8'))
        lock_file_handle.flush()
        return True
    except IOError as e:
        if e.errno == 13:
            return False
        else:
            return False
    except Exception as e:
        return False

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
        return "Unknown"

def get_cet_version(log_path):
    if not os.path.exists(log_path):
        return "Unknown"
    encoding = "utf-8"  # BUG FIX due to BOM issue uses a default fallback
    try:
        with open(log_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding'] if result['encoding'] else 'latin-1'
        with open(log_path, 'r', encoding=encoding) as f:
            for line in f:
                match = re.search(r"CET version v([\d\.]+)", line)
                if match:
                    return match.group(1)
    except (OSError, UnicodeDecodeError) as e:
        print(f"Error reading CET log {log_path} with encoding {encoding}: {e}")
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
        for p in psutil.process_iter(['name']):
            name = p.info.get('name') or ''
            if name.lower() == "cyberpunk2077.exe":
                _game_running_cache = True
                break
        else:
            _game_running_cache = False
    except psutil.Error:
        _game_running_cache = False
    _cache_timestamp = current_time
    return _game_running_cache

def create_progress_window(title, total_items):
    for child in app.winfo_children():
        if isinstance(child, ctk.CTkToplevel) and child.title().startswith(title):
            return None, None, None

    progress_window = ctk.CTkToplevel(app)
    progress_window.title(title)
    progress_window.geometry("400x150")
    progress_window.resizable(False, False)
    progress_window.configure(fg_color=DARK_BG)

    app_x = app.winfo_x()
    app_y = app.winfo_y()
    app_width = app.winfo_width()
    app_height = app.winfo_height()
    window_width = 400
    window_height = 150
    x = app_x + (app_width - window_width) // 2
    y = app_y + (app_height - window_height) // 2
    progress_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    ctk.CTkLabel(progress_window, text=f"{title}...", text_color=TEXT_COLOR, font=("Arial", 14)).pack(pady=20)
    progress_bar = ctk.CTkProgressBar(progress_window, width=350)
    progress_bar.pack(pady=20)
    progress_bar.set(0)
    status_label_progress = ctk.CTkLabel(progress_window, text=f"Processing: 0/{total_items}", text_color=TEXT_COLOR, font=("Arial", 12))
    status_label_progress.pack(pady=10)

    progress_window.transient(app)
    progress_window.grab_set()

    set_window_icon(progress_window)

    return progress_window, progress_bar, status_label_progress

def rebuild_mods_dictionary(current_dir, temp_disabled_path):
    mods = {}
    core_mods = ["archivexl", "codeware", "tweakxl"]
    equipment_ex_paths = CORE_DEPENDENCIES["EquipmentEx"]["path"]
    directories = MOD_DIRECTORIES + ["red4ext/plugins"]
    for mod_dir in directories:
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
                if mod_dir == os.path.normpath("bin/x64/plugins/cyber_engine_tweaks/mods") and not os.path.isdir(full_item_path):
                    continue  
                if not is_equipment_ex and not is_core_red4ext and not item.lower().endswith(('.log', '.ini', '.tmp')):
                    mods[display_name] = (mod_dir, item, full_item_path)
        if os.path.exists(temp_mod_dir):
            for item in os.listdir(temp_mod_dir):
                display_name = f"{item} ({mod_dir})"
                full_item_path = os.path.join(temp_mod_dir, item)
                rel_path = os.path.relpath(full_item_path, temp_disabled_path)  
                original_rel_path = os.path.relpath(os.path.join(current_dir, rel_path), current_dir)
                normalized_rel = original_rel_path.replace("\\", "/").lower()
                is_equipment_ex = (
                    normalized_rel == "r6/scripts/equipmentex" or
                    normalized_rel.startswith("r6/scripts/equipmentex/") or
                    any(normalized_rel == equip_path.replace("\\", "/").lower() for equip_path in equipment_ex_paths)
                )
                is_core_red4ext = (mod_dir == "red4ext/plugins" and item.lower() in core_mods)
                if mod_dir == os.path.normpath("bin/x64/plugins/cyber_engine_tweaks/mods") and not os.path.isdir(full_item_path):
                    continue 
                if not is_equipment_ex and not is_core_red4ext and not item.lower().endswith(('.log', '.ini', '.tmp')):
                    mods[display_name] = (mod_dir, item, full_item_path)
    return mods

def disable_core_mods(update_status_callback=None):
    global manual_versions, manual_version_checksums
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
                    if mod_name in ["EquipmentEx", "Redscript"]:
                        manual_version_checksums[mod_name] = get_file_checksum(full_path)  # Store checksum before moving
                        print(f"Stored checksum for {mod_name}: {manual_version_checksums[mod_name]}")
                except Exception as e:
                    errors.append(f"Failed to disable {mod_name} file {path}: {str(e)}")

    save_game_dir_to_registry()
    if errors:
        messagebox.showerror("Errors Occurred", "\n".join(errors))
        status_label.configure(text="Some core mods could not be disabled.")
    else:
        status_label.configure(text="All core mods have been disabled.")
    
    if update_status_callback:
        update_status_callback()
    update_core_mods_label()

def enable_core_mods(update_status_callback=None):
    global manual_versions, manual_version_checksums
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
                        if mod_name in ["EquipmentEx", "Redscript"]:
                            checksum = get_file_checksum(full_path)
                            if checksum and manual_version_checksums.get(mod_name) and checksum == manual_version_checksums[mod_name]:
                                print(f"Restored version for {mod_name}: {manual_versions.get(mod_name, 'N/A')}")
                            else:
                                manual_versions[mod_name] = manual_versions.get(mod_name, "")
                                manual_version_checksums[mod_name] = checksum
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

    save_game_dir_to_registry()
    if errors:
        messagebox.showerror("Errors Occurred", "\n".join(errors))
        status_label.configure(text="Some core mods could not be enabled.")
    else:
        status_label.configure(text="All core mods have been enabled.")

    if update_status_callback:
        update_status_callback()
    update_core_mods_label()

def cleanup_temp_disabled_folder(current_dir):
    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
    if not os.path.exists(temp_disabled_path):
        return

    for root, dirs, files in os.walk(temp_disabled_path, topdown=False):
        if files:
            return
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
            except OSError as e:
                print(f"Failed to remove subdirectory {dir_path}: {str(e)}")

    try:
        if os.path.exists(temp_disabled_path):
            if not os.listdir(temp_disabled_path):
                os.rmdir(temp_disabled_path)
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
        if mod_name in ["EquipmentEx", "Redscript"]:
            version = manual_versions.get(mod_name, "N/A") if is_installed else "N/A"
        elif mod_name in ["ArchiveXL", "RED4ext", "Codeware", "TweakXL"] and is_installed:
            dll_path = next((p for p in paths if p.endswith(".dll")), paths[0])
            version = get_dll_version(os.path.join(current_dir, dll_path))
        elif mod_name == "Cyber Engine Tweaks" and "log_path" in info and is_installed:
            log_path = os.path.join(current_dir, info["log_path"])
            version = get_cet_version(log_path)

        status_data[mod_name] = {
            "installed": is_installed,
            "path": info["path"],
            "version": version if version else "N/A"
        }
        print(f"Debug: Checking {mod_name} - Exists: {is_installed} - Version: {status_data[mod_name]['version']} - Paths: {paths}")
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

    if app.winfo_exists():
        after_id = app.after(5000, update_core_mods_label)
        after_tasks.append(after_id)

def update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_term=""):
    if not main.winfo_exists() or not (enabled_listbox.winfo_exists() and disabled_listbox.winfo_exists()):
        return

    selected_dir = selected_dir_var.get()
    search = (search_term or "").lower()

    enabled_listbox.delete(0, tk.END)
    disabled_listbox.delete(0, tk.END)

    for display_name, (mod_dir, _mod_name, current_path) in sorted(mods.items(), key=lambda x: x[0].lower()):
        if selected_dir != "All" and mod_dir != selected_dir:
            continue
        if search and search not in display_name.lower():
            continue

        if TEMP_DISABLED_DIR in os.path.normpath(current_path):
            disabled_listbox.insert(tk.END, display_name)
        else:
            enabled_listbox.insert(tk.END, display_name)

def open_temp_disabled_folder():
    if not game_dir:
        messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
        return

    temp_disabled_path = os.path.join(game_dir, TEMP_DISABLED_DIR)
    if os.path.exists(temp_disabled_path) and any(os.scandir(temp_disabled_path)):
        try:
            open_folder(temp_disabled_path) 
            status_label.configure(text=f"Opened folder: {TEMP_DISABLED_DIR}")
        except OSError as e:
            messagebox.showerror("Error", f"Failed to open folder {TEMP_DISABLED_DIR}: {str(e)}")
    else:
        messagebox.showinfo("No Disabled Mods", "There are currently no mods disabled.")
        status_label.configure(text="No mods are currently disabled.")

        def reset_status_label():
            if status_label.winfo_exists():
                status_label.configure(text="Manage your mods or use buttons to enable/disable all.")
        after_id = app.after(5000, reset_status_label)
        after_tasks.append(after_id)

def show_mods():
    global status_label, enabled_listbox, disabled_listbox, selected_dir_var, search_var, mods, current_page
    current_page = "mods"
    clear_main()
    update_active_button()
    if not game_dir:
        messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
        return

    current_dir = game_dir
    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)

    global current_image_label
    main.update()
    img = get_cached_image((250, 250))
    if img:
        current_image_label = ctk.CTkLabel(main, image=img, text="")
        current_image_label.place(x=(main.winfo_width() - 250) // 2, y=-70)
    else:
        ctk.CTkLabel(main, text="Mod Management", font=("Orbitron", 22, "bold"), text_color=TEXT_COLOR).grid(row=0, column=0, pady=10, sticky="n")

    main.grid_columnconfigure(0, weight=1)
    main.grid_rowconfigure(3, weight=1)
    button_frame = ctk.CTkFrame(main, fg_color="#222222")
    button_frame.grid(row=0, column=0, pady=(120, 10), sticky="n")
    ctk.CTkButton(button_frame, text="Disable All Mods", command=lambda: disable_all_mods(enabled_listbox, disabled_listbox, selected_dir_var, search_var, mods), fg_color=ACCENT_RED, text_color="white", hover_color="#94160C").pack(side="left", padx=5)
    ctk.CTkButton(button_frame, text="Enable All Mods", command=lambda: enable_all_mods(enabled_listbox, disabled_listbox, selected_dir_var, search_var, mods), fg_color=NEON_GREEN, text_color="black", hover_color="#1ADB00").pack(side="left", padx=5)
    ctk.CTkButton(button_frame, text="Export / Backup Mod Preset", command=export_mods, fg_color=NEON_YELLOW, text_color="black", hover_color="#DBBE00").pack(side="left", padx=5)
    ctk.CTkButton(button_frame, text="Import Mod Preset", command=import_mods, fg_color=NEON_YELLOW, text_color="black", hover_color="#DBBE00").pack(side="left", padx=5)
    ctk.CTkButton(button_frame, text="Temporarily Disabled Mods", command=open_temp_disabled_folder, fg_color=NEON_YELLOW, text_color="black", hover_color="#DBBE00").pack(side="left", padx=5)

    search_frame = ctk.CTkFrame(main, fg_color="#222222")
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
    combobox.bind("<Button-1>", lambda event: combobox._open_dropdown_menu())

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

    update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_var.get())
    start_mod_observer()  
    status_label = ctk.CTkLabel(main, text="Manage your mods or use buttons to enable/disable all.", font=("Arial", 12, "bold"), text_color=TEXT_COLOR)
    status_label.grid(row=4, column=0, pady=10, sticky="n")
    app.after(100, update_mods_after_page_load)


    def on_search():
        search_term = search_var.get()
        update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_term)

    def on_clear():
        search_var.set("")
        update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, "")

    def on_combobox_select(event=None):
        selected_dir = selected_dir_var.get()
        try:
            update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_var.get())
        except Exception as e:
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
            except Exception as e:
                errors.append(f"Failed to enable {display_name}: {str(e)}")
        if errors:
            messagebox.showerror("Errors Occurred", "\n".join(errors))
        else:
            cleanup_temp_disabled_folder(current_dir)
        update_mod_count_label()
        update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_var.get())

    search_button.configure(command=on_search)
    clear_button.configure(command=on_clear)
    search_entry.bind("<Return>", lambda event: on_search())

    combobox.bind("<<ComboboxSelected>>", on_combobox_select)
    selected_dir_var.trace_add("write", lambda *args: on_combobox_select())

    ctk.CTkButton(enabled_frame, text="Disable Selected", command=disable_selected, font=("Arial", 12), fg_color=ACCENT_RED, text_color="white", hover_color="#94160C").pack(pady=5)
    ctk.CTkButton(disabled_frame, text="Enable Selected", command=enable_selected, font=("Arial", 12), fg_color=NEON_GREEN, text_color="black", hover_color="#1ADB00").pack(pady=5)

def disable_all_mods(enabled_listbox, disabled_listbox, selected_dir_var, search_var, mods):
    try:
        if is_game_running():
            messagebox.showwarning("Game Running", "Cannot modify mods while Cyberpunk 2077 is running!")
            return
        if not game_dir:
            messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
            return
        if not messagebox.askyesno(
            "Confirm Disable",
            "This will move all non-core mods to the 'Temporarily Disabled Mods' folder located in your Cyberpunk 2077 directory. Proceed?"
        ):
            return

        current_dir = game_dir
        temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
        os.makedirs(temp_disabled_path, exist_ok=True)

        core_mods = {"archivexl", "codeware", "tweakxl"}
        equipment_ex_paths = CORE_DEPENDENCIES["EquipmentEx"]["path"]

        def _is_equipment_ex(rel_norm):
            return (
                rel_norm == "r6/scripts/equipmentex"
                or rel_norm.startswith("r6/scripts/equipmentex/")
                or any(rel_norm == p.replace("\\", "/").lower() for p in equipment_ex_paths)
            )

        eligible = []
        for mod_dir in MOD_DIRECTORIES + ["red4ext/plugins"]:
            full_dir = os.path.join(current_dir, mod_dir)
            if not os.path.exists(full_dir):
                continue
            for item in os.listdir(full_dir):
                source = os.path.join(full_dir, item)
                rel = os.path.relpath(source, current_dir).replace("\\", "/").lower()
                is_core_red4ext = (mod_dir == "red4ext/plugins" and item.lower() in core_mods)
                display_name = f"{item} ({mod_dir})"

                skip = (
                    _is_equipment_ex(rel)
                    or is_core_red4ext
                    or display_name not in mods
                    or item.lower().endswith(('.log', '.ini', '.tmp'))
                )
                if not skip:
                    eligible.append((mod_dir, item, source))

        if not eligible:
            messagebox.showinfo("No Mods", "No non-core mods found to disable.")
            return

        progress_window, progress_bar, status_label_progress = create_progress_window("Disabling All Mods", len(eligible))
        errors, moved_items = [], []
        try:
            for idx, (mod_dir, item, source) in enumerate(eligible, start=1):
                dest_dir = os.path.join(temp_disabled_path, mod_dir)
                os.makedirs(dest_dir, exist_ok=True)
                dest = os.path.join(dest_dir, item)
                try:
                    shutil.move(source, dest)
                    moved_items.append((f"{item} ({mod_dir})", mod_dir, item, dest))
                except Exception as e:
                    errors.append(f"Failed to disable {item} in {mod_dir}: {str(e)}")

                if progress_window is not None:
                    progress_bar.set(idx / len(eligible))
                    status_label_progress.configure(text=f"Processing: {idx}/{len(eligible)}")
                    progress_window.update()
        finally:
            if progress_window is not None and progress_window.winfo_exists():
                progress_window.destroy()

        for display_name, mod_dir, item, dest in moved_items:
            mods[display_name] = (mod_dir, item, dest)

        mods.clear()
        mods.update(rebuild_mods_dictionary(current_dir, temp_disabled_path))

        update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_var.get())
        update_mod_count_label()

        if status_label and status_label.winfo_exists():
            if errors:
                messagebox.showerror("Errors Occurred", "\n".join(errors))
                status_label.configure(text="Some non-core mods could not be disabled.")
            else:
                status_label.configure(text="All non-core mods have been disabled.")
            def _reset_status():
                if status_label.winfo_exists():
                    status_label.configure(text="Manage your mods or use buttons to enable/disable all.")
            after_id = app.after(5000, _reset_status)
            after_tasks.append(after_id)

    except Exception as e:
        print(f"Error in disable_all_mods: {e}")
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")

def enable_all_mods(enabled_listbox, disabled_listbox, selected_dir_var, search_var, mods):
    try:
        if is_game_running():
            messagebox.showwarning("Game Running", "Cannot modify mods while Cyberpunk 2077 is running!")
            return
        if not game_dir:
            messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
            return
        if not messagebox.askyesno(
            "Confirm Enable",
            "This will move all non-core mods back from 'Temporarily Disabled Mods' to their original locations. Core mods must be enabled separately. Proceed?"
        ):
            return

        current_dir = game_dir
        temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
        if not os.path.exists(temp_disabled_path):
            messagebox.showinfo("No Mods", "No non-core mods found in 'Temporarily Disabled Mods' to enable.")
            return

        core_mods = {"archivexl", "codeware", "tweakxl"}
        equipment_ex_paths = CORE_DEPENDENCIES["EquipmentEx"]["path"]

        def _is_equipment_ex(rel_norm):
            return (
                rel_norm == "r6/scripts/equipmentex"
                or rel_norm.startswith("r6/scripts/equipmentex/")
                or any(rel_norm == p.replace("\\", "/").lower() for p in equipment_ex_paths)
            )

        eligible = []
        for mod_dir in MOD_DIRECTORIES + ["red4ext/plugins"]:
            temp_mod_dir = os.path.join(temp_disabled_path, mod_dir)
            if not os.path.exists(temp_mod_dir):
                continue
            for item in os.listdir(temp_mod_dir):
                source = os.path.join(temp_mod_dir, item)
                rel = os.path.relpath(source, current_dir).replace("\\", "/").lower()
                is_core_red4ext = (mod_dir == "red4ext/plugins" and item.lower() in core_mods)
                display_name = f"{item} ({mod_dir})"
                skip = (
                    _is_equipment_ex(rel)
                    or is_core_red4ext
                    or display_name not in mods
                )
                if not skip:
                    eligible.append((mod_dir, item, source, os.path.join(current_dir, mod_dir, item)))

        if not eligible:
            messagebox.showinfo("No Mods", "No non-core mods found in 'Temporarily Disabled Mods' to enable.")
            cleanup_temp_disabled_folder(current_dir)
            return

        progress_window, progress_bar, status_label_progress = create_progress_window("Enabling All Mods", len(eligible))
        errors, moved_items = [], []
        try:
            for idx, (mod_dir, item, source, dest) in enumerate(eligible, start=1):
                try:
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    if os.path.isdir(dest):
                        shutil.rmtree(dest)
                    elif os.path.isfile(dest):
                        os.remove(dest)
                    shutil.move(source, dest)
                    moved_items.append((f"{item} ({mod_dir})", mod_dir, item, dest))
                except Exception as e:
                    errors.append(f"Failed to enable {item} in {mod_dir}: {str(e)}")

                if progress_window is not None:
                    progress_bar.set(idx / len(eligible))
                    status_label_progress.configure(text=f"Processing: {idx}/{len(eligible)}")
                    progress_window.update()
        finally:
            if progress_window is not None and progress_window.winfo_exists():
                progress_window.destroy()

        try:
            for root, dirs, files in os.walk(temp_disabled_path, topdown=False):
                for d in list(dirs):
                    p = os.path.join(root, d)
                    try:
                        if not os.listdir(p):
                            os.rmdir(p)
                    except OSError:
                        pass
            if os.path.exists(temp_disabled_path) and not os.listdir(temp_disabled_path):
                os.rmdir(temp_disabled_path)
        except Exception as e:
            errors.append(f"Failed to remove '{TEMP_DISABLED_DIR}' folder completely: {e}")

        for display_name, mod_dir, item, dest in moved_items:
            mods[display_name] = (mod_dir, item, dest)

        mods.clear()
        mods.update(rebuild_mods_dictionary(current_dir, os.path.join(current_dir, TEMP_DISABLED_DIR)))

        status_text = ("Some mods could not be enabled or folder not fully removed."
                       if errors else
                       "All non-core mods have been enabled. Enable core mods separately if needed.")

        update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_var.get())
        update_mod_count_label()

        if errors:
            messagebox.showerror("Errors Occurred", "\n".join(errors))
        if status_label and status_label.winfo_exists():
            status_label.configure(text=status_text)

    except Exception as e:
        print(f"Error in enable_all_mods: {e}")
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")

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

def update_mod_count_label():
    if not game_dir:
        mod_count_label.configure(text="Total Mods: Unknown")
        return

    current_dir = game_dir
    mod_count = 0
    core_mods = {"archivexl", "codeware", "tweakxl"}
    equipment_ex_paths = CORE_DEPENDENCIES["EquipmentEx"]["path"]

    def _is_equipment_ex(rel_norm):
        return (
            rel_norm == "r6/scripts/equipmentex"
            or rel_norm.startswith("r6/scripts/equipmentex/")
            or any(rel_norm == p.replace("\\", "/").lower() for p in equipment_ex_paths)
        )

    for mod_dir in MOD_DIRECTORIES:
        full_dir = os.path.join(current_dir, mod_dir)
        if not os.path.exists(full_dir):
            continue
        for item in os.listdir(full_dir):
            full_item_path = os.path.join(full_dir, item)
            rel_norm = os.path.relpath(full_item_path, current_dir).replace("\\", "/").lower()
            if _is_equipment_ex(rel_norm):
                continue
            if item.lower().endswith(('.log', '.ini', '.tmp')):
                continue

            if mod_dir == os.path.normpath("bin/x64/plugins/cyber_engine_tweaks/mods"):
                if os.path.isdir(full_item_path):
                    mod_count += 1
            elif mod_dir == os.path.normpath("archive/pc/mod"):
                if os.path.isfile(full_item_path):
                    mod_count += 1
            else:
                mod_count += 1

    red4ext_plugins_dir = os.path.join(current_dir, "red4ext", "plugins")
    if os.path.exists(red4ext_plugins_dir):
        for item in os.listdir(red4ext_plugins_dir):
            p = os.path.join(red4ext_plugins_dir, item)
            if os.path.isdir(p) and item.lower() not in core_mods:
                mod_count += 1

    mod_count_label.configure(text=f"Total Mods: {mod_count}")

def extract_log_errors(log_path):
    errors = []
    if not os.path.exists(log_path):
        return errors

    def parse_lines(file_obj):
        for line in file_obj:
            line = line.strip()
            if re.search(r'\[error\]|\[critical\]', line, re.IGNORECASE):
                errors.append(line)
            elif re.search(r'\[warning\]', line, re.IGNORECASE):
                if not re.search(r'warningVolume|warningLevel|warningSetting', line, re.IGNORECASE):
                    errors.append(line)
            elif re.search(r'failed|exception|crash|error', line, re.IGNORECASE):
                errors.append(line)

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            parse_lines(f)
    except UnicodeDecodeError:
        try:
            with open(log_path, 'r', encoding='latin-1') as f:
                parse_lines(f)
        except Exception as e:
            errors.append(f"Error reading log file with fallback encoding: {str(e)}")
    except Exception as e:
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

def schedule_log_errors_check():
    if not game_dir or not log_errors_label.winfo_exists():
        if app.winfo_exists():
            after_id = app.after(5000, schedule_log_errors_check)
            after_tasks.append(after_id)
        return

    current_dir = game_dir
    has_errors = check_log_errors(current_dir)
    log_errors_label.configure(text=f"Log Errors Detected: {'Yes' if has_errors else 'No'}")

    if app.winfo_exists():
        after_id = app.after(5000, schedule_log_errors_check)
        after_tasks.append(after_id)

def write_items_from_dir(file, path, mod_dir, temp_disabled_path):
    core_mods = ["archivexl", "codeware", "tweakxl"]
    equipment_ex_paths = CORE_DEPENDENCIES["EquipmentEx"]["path"]
    items = []
    
    if os.path.exists(path):
        for item in os.listdir(path):
            full_item_path = os.path.join(path, item)
            rel_path = os.path.relpath(full_item_path, game_dir)
            normalized_rel = rel_path.replace("\\", "/").lower()
            is_equipment_ex = (
                normalized_rel == "r6/scripts/equipmentex" or
                normalized_rel.startswith("r6/scripts/equipmentex/") or
                any(normalized_rel == equip_path.replace("\\", "/").lower() for equip_path in equipment_ex_paths)
            )
            if mod_dir == os.path.normpath("bin/x64/plugins/cyber_engine_tweaks/mods"):
                if os.path.isdir(full_item_path) and not is_equipment_ex:
                    items.append((item, False))
            elif mod_dir == os.path.normpath("archive/pc/mod"):
                if os.path.isfile(full_item_path) and not is_equipment_ex and not item.lower().endswith(('.log', '.ini', '.tmp')):
                    items.append((item, False))
            else:
                if not is_equipment_ex and not item.lower().endswith(('.log', '.ini', '.tmp')):
                    items.append((item, False))

    if include_disabled_in_output.get():
        temp_mod_dir = os.path.join(temp_disabled_path, mod_dir)
        if os.path.exists(temp_mod_dir):
            for item in os.listdir(temp_mod_dir):
                full_item_path = os.path.join(temp_mod_dir, item)
                rel_path = os.path.relpath(full_item_path, game_dir)
                normalized_rel = rel_path.replace("\\", "/").lower()
                is_equipment_ex = (
                    normalized_rel == "r6/scripts/equipmentex" or
                    normalized_rel.startswith("r6/scripts/equipmentex/") or
                    any(normalized_rel == equip_path.replace("\\", "/").lower() for equip_path in equipment_ex_paths)
                )
                if mod_dir == os.path.normpath("bin/x64/plugins/cyber_engine_tweaks/mods"):
                    if os.path.isdir(full_item_path) and not is_equipment_ex:
                        items.append((item, True))
                elif mod_dir == os.path.normpath("archive/pc/mod"):
                    if os.path.isfile(full_item_path) and not is_equipment_ex and not item.lower().endswith(('.log', '.ini', '.tmp')):
                        items.append((item, True))
                else:
                    if not is_equipment_ex and not item.lower().endswith(('.log', '.ini', '.tmp')):
                        items.append((item, True))

    if items:
        file.write(f"\nMods located in {mod_dir.replace(os.sep, '/')}:\n")
        file.write("-" * 120 + "\n")
        for item, is_disabled in sorted(items, key=lambda x: x[0].lower()):
            display_name = f"{item} (Disabled)" if is_disabled else item
            file.write(f"{display_name}\n")
        file.write("-" * 120 + "\n")
    else:
        file.write(f"\nNo mods located in {mod_dir.replace(os.sep, '/')}.\n")
        file.write("-" * 120 + "\n")

def set_creation_time(file_path, timestamp):
    try:
        if not os.path.exists(file_path):
            print(f"Path does not exist: {file_path}")
            return
        if os.path.isdir(file_path):
            for root, _, files in os.walk(file_path):
                for file in files:
                    sub_path = os.path.join(root, file)
                    try:
                        handle = CreateFile(sub_path, FILE_WRITE_ATTRIBUTES, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
                        creation_dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc).replace(tzinfo=None)
                        SetFileTime(handle, creation_dt, None, None)
                        CloseHandle(handle)
                        print(f"Set creation time for {sub_path} to {timestamp} ({datetime.datetime.fromtimestamp(timestamp)})")
                    except Exception as e:
                        print(f"Failed to set creation time for {sub_path}: {str(e)}")
        else:
            handle = CreateFile(file_path, FILE_WRITE_ATTRIBUTES, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
            creation_dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc).replace(tzinfo=None)
            SetFileTime(handle, creation_dt, None, None)
            CloseHandle(handle)
            print(f"Set creation time for {file_path} to {timestamp} ({datetime.datetime.fromtimestamp(timestamp)})")
    except Exception as e:
        print(f"Error in set_creation_time for {file_path}: {str(e)}")

def export_mods():
    if not hasattr(threading, 'Event'):
        messagebox.showerror("Error", "Threading module not properly imported. Please check your Python environment.")
        print("Error: threading module not properly imported.")
        return
    if is_game_running():
        messagebox.showwarning("Game Running", "Cannot export mods while Cyberpunk 2077 is running!")
        return
    if not game_dir:
        messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
        return

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
            ctk.CTkButton(button_frame, text="Confirm", command=self.confirm, fg_color=NEON_GREEN, text_color="black", hover_color="#1ADB00").pack(side="left", padx=10)
            ctk.CTkButton(button_frame, text="Cancel", command=self.cancel, fg_color=ACCENT_RED, text_color="white", hover_color="#94160C").pack(side="left", padx=10)
            set_window_icon(self)
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

    def is_rar_available():
        rar_path = shutil.which("rar")
        if rar_path:
            print(f"RAR found in PATH at: {rar_path}")
            return rar_path
        possible_paths = [
            r"C:\Program Files\WinRAR\rar.exe",
            r"C:\Program Files (x86)\WinRAR\rar.exe",
            r"C:\Users\Public\WinRAR\rar.exe"
        ]
        for path in possible_paths:
            if os.path.isfile(path):
                print(f"RAR found at: {path}")
                return path
        print("RAR not found in PATH or common locations.")
        return None

    filetypes = [("ZIP files", "*.zip"), ("7z files", "*.7z"), ("All files", "*.*")]
    rar_path = is_rar_available()
    if rar_path:
        filetypes.insert(1, ("RAR files", "*.rar"))
    save_path = filedialog.asksaveasfilename(
        defaultextension=".zip",
        filetypes=filetypes,
        title="Save Mod Preset As",
        initialfile=f"Cyberpunk2077_Mod_Preset_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    if not save_path:
        print("No save path selected, aborting export.")
        return

    current_dir = game_dir
    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
    try:
        mods = rebuild_mods_dictionary(current_dir, temp_disabled_path)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to rebuild mods dictionary: {str(e)}")
        print(f"Error rebuilding mods dictionary: {e}")
        return
    if not mods:
        messagebox.showinfo("No Mods", "No mods found in the selected directories.")
        return

    core_mods = ["archivexl", "codeware", "tweakxl"]
    equipment_ex_paths = CORE_DEPENDENCIES["EquipmentEx"]["path"]
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

    cancel_export = threading.Event()
    def create_progress_window_with_cancel(title, max_value):
        window = ctk.CTkToplevel(app)
        window.title(title)
        window.geometry("400x250")
        window.resizable(False, False)
        window.configure(fg_color=DARK_BG)
        window.transient(app)
        
        parent_x = app.winfo_x()
        parent_y = app.winfo_y()
        parent_width = app.winfo_width()
        parent_height = app.winfo_height()
        x = parent_x + (parent_width - 400) // 2
        y = parent_y + (parent_height - 250) // 2
        window.geometry(f"400x250+{x}+{y}")
        
        ctk.CTkLabel(window, text=title, font=("Arial", 14), text_color=TEXT_COLOR).pack(pady=10)
        progress = ctk.CTkProgressBar(window, width=300)
        progress.pack(pady=15)
        count_label = ctk.CTkLabel(window, text=f"Processing: 0/{max_value}", font=("Arial", 12), text_color=TEXT_COLOR)
        count_label.pack(pady=10)
        current_folder_label = ctk.CTkLabel(window, text="", font=("Arial", 12), text_color=TEXT_COLOR)
        current_folder_label.pack(pady=10)
        status_label = ctk.CTkLabel(window, text="Exporting", font=("Arial", 12), text_color=TEXT_COLOR)
        status_label.pack(pady=10)
        
        button_frame = ctk.CTkFrame(window, fg_color=DARK_BG, height=40)
        button_frame.pack(pady=15, fill="x")
        button_frame.pack_propagate(False)
        
        def cancel_action():
            cancel_export.set()
            status_label.configure(text="Cancelling...")
            window.update()
        
        cancel_button = ctk.CTkButton(
            button_frame, 
            text="Cancel", 
            command=cancel_action, 
            fg_color=ACCENT_RED, 
            text_color="white",
            width=100,
            height=30
        )
        cancel_button.pack(pady=5, padx=10, anchor="center")
        
        def on_close():
            cancel_export.set()
            window.destroy()
        
        window.protocol("WM_DELETE_WINDOW", on_close)
        
        set_window_icon(window)
        
        window.update_idletasks()
        window.wait_visibility()
        window.grab_set()
        window.focus_force()
        
        return window, progress, count_label, current_folder_label, status_label

    progress_window, progress_bar, count_label, current_folder_label, status_label = create_progress_window_with_cancel("Exporting Mod Preset", total_files)
    progress_bar.set(0)

    def export_task():
        nonlocal total_files
        errors = []
        files_processed = 0
        file_extension = os.path.splitext(save_path)[1].lower()
        temp_dir = None
        archive = None
        temp_save_path = None

        def update_progress():
            nonlocal files_processed
            if cancel_export.is_set():
                return
            progress_value = min(1.0, files_processed / total_files)
            app.after(0, lambda: progress_bar.set(progress_value))
            app.after(0, lambda: count_label.configure(text=f"Processing: {files_processed}/{total_files}"))
            app.after(0, lambda: progress_window.update())

        try:
            print(f"Starting export to {save_path} with {total_files} files")
            if file_extension == ".zip":
                temp_fd, temp_save_path = tempfile.mkstemp(suffix='.zip', dir=os.path.dirname(save_path))
                os.close(temp_fd)
                with zipfile.ZipFile(temp_save_path, 'w', zipfile.ZIP_DEFLATED) as archive:
                    for display_name, (mod_dir, mod_name, current_path) in mods.items():
                        if cancel_export.is_set():
                            print("Export cancelled by user")
                            break
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
                                app.after(0, lambda mod_dir=mod_dir, mod_name=mod_name: current_folder_label.configure(text=f"{mod_dir}/{mod_name}"))
                                full_dir = os.path.join(current_dir, mod_dir, mod_name)
                                if os.path.isfile(full_dir):
                                    arcname = os.path.relpath(full_dir, current_dir)
                                    print(f"Attempting to add: {full_dir} as {arcname}")
                                    try:
                                        archive.write(full_dir, arcname)
                                        files_processed += 1
                                        update_progress()
                                        print(f"Successfully added: {full_dir}")
                                    except Exception as e:
                                        errors.append(f"Failed to add {full_dir} to archive: {str(e)}")
                                else:
                                    for root, _, files in os.walk(full_dir):
                                        if cancel_export.is_set():
                                            print("Export cancelled during directory walk")
                                            break
                                        for file in files:
                                            if cancel_export.is_set():
                                                print("Export cancelled during file processing")
                                                break
                                            file_path = os.path.join(root, file)
                                            if os.path.isfile(file_path):
                                                arcname = os.path.relpath(file_path, current_dir)
                                                try:
                                                    archive.write(file_path, arcname)
                                                    files_processed += 1
                                                    update_progress()
                                                except Exception as e:
                                                    errors.append(f"Failed to add {file_path} to archive: {str(e)}")
            elif file_extension == ".7z":
                temp_fd, temp_save_path = tempfile.mkstemp(suffix='.7z', dir=os.path.dirname(save_path))
                os.close(temp_fd)
                archive = py7zr.SevenZipFile(temp_save_path, 'w')
                try:
                    for display_name, (mod_dir, mod_name, current_path) in mods.items():
                        if cancel_export.is_set():
                            print("Export cancelled by user")
                            break
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
                                app.after(0, lambda mod_dir=mod_dir, mod_name=mod_name: current_folder_label.configure(text=f"{mod_dir}/{mod_name}"))
                                full_dir = os.path.join(current_dir, mod_dir, mod_name)
                                if os.path.isfile(full_dir):
                                    arcname = os.path.relpath(full_dir, current_dir)
                                    print(f"Attempting to add: {full_dir} as {arcname}")
                                    try:
                                        archive.write(full_dir, arcname)
                                        files_processed += 1
                                        update_progress()
                                        print(f"Successfully added: {full_dir}")
                                    except Exception as e:
                                        errors.append(f"Failed to add {full_dir} to archive: {str(e)}")
                                else:
                                    for root, _, files in os.walk(full_dir):
                                        if cancel_export.is_set():
                                            print("Export cancelled during directory walk")
                                            break
                                        for file in files:
                                            if cancel_export.is_set():
                                                print("Export cancelled during file processing")
                                                break
                                            file_path = os.path.join(root, file)
                                            if os.path.isfile(file_path):
                                                arcname = os.path.relpath(file_path, current_dir)
                                                print(f"Attempting to add: {file_path} as {arcname}")
                                                try:
                                                    archive.write(file_path, arcname)
                                                    files_processed += 1
                                                    update_progress()
                                                    print(f"Successfully added: {file_path}")
                                                except Exception as e:
                                                    errors.append(f"Failed to add {file_path} to archive: {str(e)}")
                finally:
                    if archive:
                        archive.close()
            elif file_extension == ".rar" and rar_path:
                temp_dir = os.path.join(current_dir, "temp_rar_export")
                os.makedirs(temp_dir, exist_ok=True)
                try:
                    for display_name, (mod_dir, mod_name, current_path) in mods.items():
                        if cancel_export.is_set():
                            break
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
                                app.after(0, lambda mod_dir=mod_dir, mod_name=mod_name: current_folder_label.configure(text=f"{mod_dir}/{mod_name}"))
                                full_dir = os.path.join(current_dir, mod_dir, mod_name)
                                if os.path.isfile(full_dir):
                                    dest_path = os.path.join(temp_dir, os.path.relpath(full_dir, current_dir))
                                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                                    with open(full_dir, 'rb') as source, open(dest_path, 'wb') as dest:
                                        dest.write(source.read())
                                    files_processed += 1
                                    update_progress()
                                else:
                                    for root, _, files in os.walk(full_dir):
                                        if cancel_export.is_set():
                                            break
                                        for file in files:
                                            if cancel_export.is_set():
                                                break
                                            file_path = os.path.join(root, file)
                                            if os.path.isfile(file_path):
                                                rel_file_path = os.path.relpath(file_path, current_dir)
                                                dest_path = os.path.join(temp_dir, rel_file_path)
                                                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                                                with open(file_path, 'rb') as source, open(dest_path, 'wb') as dest:
                                                    dest.write(source.read())
                                                files_processed += 1
                                                update_progress()
                    if not cancel_export.is_set():
                        app.after(0, lambda: progress_bar.set(1.0))
                        app.after(0, lambda: status_label.configure(text="Finalizing..."))
                        app.after(0, progress_window.update())
                        print(f"Executing RAR command with path: {rar_path}")
                        result = subprocess.run(f'"{rar_path}" a -r "{save_path}" *', shell=True, cwd=temp_dir, check=True, capture_output=True, text=True)
                        if result.stderr:
                            print(f"RAR command error: {result.stderr}")
                except subprocess.CalledProcessError as e:
                    errors.append(f"Failed to create RAR archive {save_path}: {str(e)}")
                    if hasattr(e, 'stderr'):
                        print(f"Error details: {e.stderr}")
                except FileNotFoundError:
                    errors.append(f"RAR executable not found at {rar_path}")
                except PermissionError:
                    errors.append(f"Permission denied accessing RAR at {rar_path}")
                finally:
                    if temp_dir and os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir, ignore_errors=True)
            else:
                raise ValueError("Unsupported file extension. Please use .zip, .7z, or .rar")
        except Exception as e:
            errors.append(f"Failed to create archive file {save_path}: {str(e)}")
        finally:
            def show_message_and_close(title, message):
                def show_and_close():
                    messagebox.showinfo(title, message, parent=app)
                    app.after(500, progress_window.destroy)
                app.after(0, show_and_close)
            if cancel_export.is_set() or errors:
                if temp_save_path and os.path.exists(temp_save_path):
                    os.remove(temp_save_path)
                if os.path.exists(save_path):
                    os.remove(save_path)
                if cancel_export.is_set():
                    show_message_and_close("Export Cancelled", "Mod preset export was cancelled.")
                    if status_label.winfo_exists():
                        app.after(0, lambda: status_label.configure(text="Cancelled"))
                else:
                    show_message_and_close("Export Errors", "\n".join(errors))
                    if status_label.winfo_exists():
                        app.after(0, lambda: status_label.configure(text="Completed with errors"))
            else:
                if temp_save_path and os.path.exists(temp_save_path):
                    os.rename(temp_save_path, save_path)
                print(f"Checking file existence before success: {os.path.exists(save_path)}")
                if os.path.exists(save_path):
                    show_message_and_close("Export Successful", f"Mod preset exported to {save_path}")
                    if status_label.winfo_exists():
                        app.after(0, lambda: status_label.configure(text="Exported successfully!"))
                else:
                    show_message_and_close("Export Failed", "The export process completed but no file was created.")
                    if status_label.winfo_exists():
                        app.after(0, lambda: status_label.configure(text="Export failed"))
            app.after(0, update_mod_count_label)

    try:
        export_thread = threading.Thread(target=export_task, daemon=True)
        export_thread.start()
    except Exception as e:
        progress_window.destroy()
        messagebox.showerror("Error", f"Failed to start export thread: {str(e)}")

def import_mods():
    global status_label, mods
    if is_game_running():
        messagebox.showwarning("Game Running", "Cannot import mods while Cyberpunk 2077 is running!")
        return
    if not game_dir:
        messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
        return
    input_file = filedialog.askopenfilename(
        title="Select Mod Preset",
        filetypes=[("Archive files", "*.zip *.rar *.7z")]
    )
    if not input_file:
        return
    current_dir = game_dir
    errors = []
    try:
        ext = os.path.splitext(input_file)[1].lower()
        eligible = []
        core_mods = {"archivexl", "codeware", "tweakxl"}
        equipment_ex_paths = [p.replace("\\", "/").lower() for p in CORE_DEPENDENCIES["EquipmentEx"]["path"]]
        valid_extensions = ('.archive', '.xl', '.reds', '.lua', '.asi', '.dll', '.txt', '.toml', '.ini', '.otf', '.ttf', '.kark', '.json', '.png', '.dds')  # Kept for reference, but not used
        valid_dirs = [os.path.normpath(d).replace("\\", "/") for d in MOD_DIRECTORIES]
        def _is_equipment_ex(rel_norm):
            return (
                rel_norm == "r6/scripts/equipmentex"
                or rel_norm.startswith("r6/scripts/equipmentex/")
                or any(rel_norm == p for p in equipment_ex_paths)
            )
        def find_7z_executable():
            if platform.system() != "Windows":
                return None
            for path in os.environ.get("PATH", "").split(os.pathsep):
                exe_path = os.path.join(path, "7z.exe")
                if os.path.isfile(exe_path):
                    return exe_path
            default_path = r"C:\Program Files\7-Zip\7z.exe"
            if os.path.isfile(default_path):
                return default_path
            return None
        temp_extract_dir = None
        temp_zip_path = None
        members = []
        if ext in (".rar", ".7z"):
            seven_zip_path = find_7z_executable()
            if not seven_zip_path:
                messagebox.showwarning(
                    "7-Zip Required",
                    "To import .rar or .7z files, install 7-Zip (free at www.7-zip.org) or convert your archive to .zip manually and try again."
                )
                return
            progress_window, progress_bar, status_label_progress = create_progress_window("Extracting and Installing", 2) # 2 steps: extract, zip
            if not progress_window:
                return
            progress_window.update_idletasks()
            app.update()
            time.sleep(0.1)
            temp_extract_dir = os.path.join(tempfile.gettempdir(), "Cyberpunk2077ModListTool_Extract")
            os.makedirs(temp_extract_dir, exist_ok=True)
            try:
                kwargs = {}
                if platform.system() == "Windows":
                    kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                result = subprocess.run(
                    [seven_zip_path, "x", input_file, f"-o{temp_extract_dir}", "-y"], # -y = yes to all
                    check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kwargs
                )
                print(f"Archive extracted to temp dir: {temp_extract_dir}")
                progress_bar.set(0.5)
                status_label_progress.configure(text="Extracting Archive...")
                progress_window.update()
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Extraction Error", f"Failed to extract {ext} archive: {e.stderr}")
                if temp_extract_dir:
                    shutil.rmtree(temp_extract_dir, ignore_errors=True)
                progress_window.destroy()
                return
            except Exception as e:
                messagebox.showerror("Extraction Error", f"Unexpected error during extraction: {str(e)}")
                if temp_extract_dir:
                    shutil.rmtree(temp_extract_dir, ignore_errors=True)
                progress_window.destroy()
                return
            temp_zip_path = os.path.join(tempfile.gettempdir(), "temp_mod_preset.zip")
            try:
                with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, _, files in os.walk(temp_extract_dir):
                        for file in files:
                            full_path = os.path.join(root, file)
                            arcname = os.path.relpath(full_path, temp_extract_dir).replace("\\", "/")
                            zipf.write(full_path, arcname)
                input_file = temp_zip_path
                print("Archive converted to .zip successfully")
                progress_bar.set(1.0)
                status_label_progress.configure(text="Installation complete")
                progress_window.update()
                app.after(1000, progress_window.destroy)
            except Exception as e:
                messagebox.showerror("Conversion Error", f"Failed to convert {ext} to .zip: {str(e)}")
                if temp_extract_dir:
                    shutil.rmtree(temp_extract_dir, ignore_errors=True)
                if temp_zip_path and os.path.exists(temp_zip_path):
                    os.remove(temp_zip_path)
                progress_window.destroy()
                return
        with zipfile.ZipFile(input_file, 'r') as zf:
            members = [m for m in zf.infolist() if not m.is_dir() and not m.filename.endswith("metadata.json")]
            print(f"Processing files from {ext} archive: {[m.filename for m in members]}")
            progress_window, progress_bar, status_label_progress = create_progress_window("Importing Mod Preset", len(members))
            if not progress_window:
                return
            for idx, member in enumerate(members, 1):
                rel_path = os.path.normpath(member.filename).replace("\\", "/")
                parts = [p.lower() for p in rel_path.split("/")]  
                adjusted_path = rel_path  
                matched_dir = None
                for d in valid_dirs:
                    d_parts = [p.lower() for p in d.split("/")] 
                    if len(d_parts) <= len(parts) and parts[:len(d_parts)] == d_parts:  
                        adjusted_path = "/".join(parts)  
                        matched_dir = d
                        break
                normalized_rel = adjusted_path.lower()
                mod_dir = os.path.dirname(adjusted_path)
                item = os.path.basename(adjusted_path)
                is_core_red4ext = (mod_dir.lower() == "red4ext/plugins" and item.lower() in core_mods)
                is_equipment_ex = _is_equipment_ex(normalized_rel)
                file_ext = os.path.splitext(item)[1].lower()
                print(f"File: {adjusted_path}, Matched dir: {matched_dir}, Mod dir: {mod_dir}, Extension: {file_ext}, Core mod: {is_core_red4ext}, EquipmentEx: {is_equipment_ex}")
                if matched_dir and not is_equipment_ex and not is_core_red4ext:
                    try:
                        dest_dir = os.path.join(current_dir, mod_dir)
                        os.makedirs(dest_dir, exist_ok=True)
                        dest = os.path.join(dest_dir, item)
                        print(f"Attempting to extract to: {dest}")
                        with zf.open(member) as source, open(dest, 'wb') as target:
                            shutil.copyfileobj(source, target)
                        dt = datetime.datetime(*member.date_time) if hasattr(member, 'date_time') and member.date_time else datetime.datetime.now()
                        if dt.hour >= 20:
                            dt = dt - datetime.timedelta(hours=7)
                        date_time = dt.timestamp()
                        print(f"Extracted {adjusted_path} to {dest} with timestamp {datetime.datetime.fromtimestamp(date_time)}")
                        os.utime(dest, (date_time, date_time))
                        if platform.system() == "Windows" and WIN32_AVAILABLE:
                            set_creation_time(dest, date_time)
                        eligible.append((mod_dir, item, dest))
                    except Exception as e:
                        errors.append(f"Failed to extract {adjusted_path} to {dest}: {str(e)}")
                        print(f"Extraction error: {str(e)}")
                else:
                    print(f"Skipped {adjusted_path}: Invalid dir={matched_dir is None}, EquipmentEx={is_equipment_ex}, Core mod={is_core_red4ext}")
                    try:
                        fallback_dest_dir = os.path.join(current_dir, os.path.dirname(rel_path))
                        os.makedirs(fallback_dest_dir, exist_ok=True)
                        fallback_dest = os.path.join(fallback_dest_dir, os.path.basename(rel_path))
                        print(f"Fallback extracting to: {fallback_dest}")
                        with zf.open(member) as source, open(fallback_dest, 'wb') as target:
                            shutil.copyfileobj(source, target)
                        dt = datetime.datetime(*member.date_time) if hasattr(member, 'date_time') and member.date_time else datetime.datetime.now()
                        if dt.hour >= 20:
                            dt = dt - datetime.timedelta(hours=7)
                        date_time = dt.timestamp()
                        os.utime(fallback_dest, (date_time, date_time))
                        if platform.system() == "Windows" and WIN32_AVAILABLE:
                            set_creation_time(fallback_dest, date_time)
                        eligible.append((os.path.dirname(rel_path), os.path.basename(rel_path), fallback_dest))
                        print(f"Fallback extracted {rel_path} to {fallback_dest}")
                    except Exception as e:
                        errors.append(f"Fallback failed for {rel_path}: {str(e)}")
                        print(f"Fallback error: {str(e)}")
                progress_bar.set(idx / len(members))
                status_label_progress.configure(text=f"Processing: {idx}/{len(members)}")
                progress_window.update()
            progress_window.destroy()
        if temp_extract_dir:
            shutil.rmtree(temp_extract_dir, ignore_errors=True)
        if temp_zip_path and os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)
        if not eligible:
            messagebox.showinfo("No Mods", f"No valid mods found in the preset. Files scanned: {len(members)}\n\nCheck console for details on skipped files.")
            return
        mods = rebuild_mods_dictionary(current_dir, os.path.join(current_dir, TEMP_DISABLED_DIR))
        update_mod_count_label()
        if current_page == "mods":
            update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_var.get())
        start_mod_observer()
        if errors:
            messagebox.showerror("Errors Occurred", "\n".join(errors))
            status_label.configure(text="Some mods failed to import.")
        else:
            status_label.configure(text="Mod preset imported successfully.")
        app.after(5000, reset_status_label)
    except Exception as e:
        messagebox.showerror("Error", f"Unexpected error during import: {str(e)}")
        status_label.configure(text="Unexpected error during import.")
        app.after(5000, reset_status_label)

def run_script(num_logs):
    global status_label, game_version, phantom_liberty_installed
    if not game_dir:
        messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
        return False

    current_dir = game_dir
    game_version = get_game_version(os.path.join(current_dir, "bin", "x64", "Cyberpunk2077.exe"))
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
    core_mods = ["archivexl", "codeware", "tweakxl"]
    equipment_ex_paths = CORE_DEPENDENCIES["EquipmentEx"]["path"]

    for path in [path1, path2, path3, path4]:
        if os.path.exists(path):
            mod_dir = os.path.relpath(path, current_dir)
            for item in os.listdir(path):
                full_item_path = os.path.join(path, item)
                rel_path = os.path.relpath(full_item_path, current_dir)
                normalized_rel = rel_path.replace("\\", "/").lower()
                is_equipment_ex = (
                    normalized_rel == "r6/scripts/equipmentex" or
                    normalized_rel.startswith("r6/scripts/equipmentex/") or
                    any(normalized_rel == equip_path.replace("\\", "/").lower() for equip_path in equipment_ex_paths)
                )
                if mod_dir == os.path.normpath("bin/x64/plugins/cyber_engine_tweaks/mods"):
                    if os.path.isdir(full_item_path) and not is_equipment_ex:
                        mod_count += 1
                elif mod_dir == os.path.normpath("archive/pc/mod"):
                    if os.path.isfile(full_item_path) and not is_equipment_ex and not item.lower().endswith(('.log', '.ini', '.tmp')):
                        mod_count += 1
                else:
                    if not is_equipment_ex and not item.lower().endswith(('.log', '.ini', '.tmp')):
                        mod_count += 1

    red4ext_plugins_dir = os.path.join(current_dir, "red4ext", "plugins")
    if os.path.exists(red4ext_plugins_dir):
        for item in os.listdir(red4ext_plugins_dir):
            full_item_path = os.path.join(red4ext_plugins_dir, item)
            if os.path.isdir(full_item_path) and item.lower() not in core_mods:
                mod_count += 1

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

    output_file = 'Cyberpunk 2077 Mod List.txt'
    try:
        with open(output_file, 'w') as file:
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

            if include_errors_in_output.get():
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

            # Handle red4ext/plugins mods had to seperate as I could not figure out bug
            red4ext_plugins_mods = []
            red4ext_temp_disabled_dir = os.path.join(temp_disabled_path, "red4ext", "plugins")
            if os.path.exists(red4ext_plugins_dir):
                for item in os.listdir(red4ext_plugins_dir):
                    full_item_path = os.path.join(red4ext_plugins_dir, item)
                    if os.path.isdir(full_item_path) and item.lower() not in core_mods:
                        red4ext_plugins_mods.append((item, False))
                if include_disabled_in_output.get() and os.path.exists(red4ext_temp_disabled_dir):
                    for item in os.listdir(red4ext_temp_disabled_dir):
                        full_item_path = os.path.join(red4ext_temp_disabled_dir, item)
                        if os.path.isdir(full_item_path) and item.lower() not in core_mods:
                            red4ext_plugins_mods.append((item, True))
                file.write("\n")
                if red4ext_plugins_mods:
                    file.write(f"Mods located in red4ext/plugins:\n")
                    file.write("-" * 120 + "\n")
                    for plugin, is_disabled in sorted(red4ext_plugins_mods, key=lambda x: x[0].lower()):
                        display_name = f"{plugin} (Disabled)" if is_disabled else plugin
                        file.write(f"{display_name}\n")
                    file.write("-" * 120 + "\n")
                else:
                    file.write(f"No mods located in red4ext/plugins.\n")
                    file.write("-" * 120 + "\n")
            else:
                file.write(f"\nError: The subfolder(s) red4ext/plugins were not found in the current location!\n")
                file.write("-" * 120 + "\n")

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
                            log_content = input_file.read().replace('\ufeff', '')
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

        if auto_open_output is not None and auto_open_output.get():
            try:
                os.startfile(os.path.abspath(output_file))
            except OSError as e:
                if status_label and status_label.winfo_exists():
                    status_label.configure(text=f"Error auto-opening mod list: {str(e)}")
                    app.after(5000, reset_status_label)

        mod_count_label.configure(text=f"Total Mods: {mod_count}")
        game_version_label.configure(text=f"Game Version: {game_version}")
        log_errors_label.configure(text=f"Log Errors Detected: {'Yes' if log_errors else 'No'}")
        core_mods_label.configure(text=f"Core Mods Installed: {'Yes' if all_core_mods_installed else 'No'}")

        if current_page == "home" and status_label and status_label.winfo_exists():
            status_label.configure(text="Success! Check Cyberpunk 2077 Mod List.txt")
            app.after(5000, reset_status_label)
        elif current_page == "home":
            status_label = ctk.CTkLabel(main, text="Success! Check Cyberpunk 2077 Mod List.txt", font=("Arial", 12, "bold"), text_color=TEXT_COLOR)
            status_label.grid(row=num_logs + 3, column=0, pady=10, sticky="n")
            app.after(5000, reset_status_label)

        print("Status label updated to: Success! Check Cyberpunk 2077 Mod List.txt")
        main.update_idletasks()
        app.update_idletasks()
        return bool(log_errors)
    except Exception as e:
        if current_page == "home":
            if status_label and status_label.winfo_exists():
                status_label.configure(text=f"Error generating mod list: {str(e)}")
            else:
                status_label = ctk.CTkLabel(main, text=f"Error generating mod list: {str(e)}", font=("Arial", 12, "bold"), text_color=ACCENT_RED)
                status_label.grid(row=num_logs + 3, column=0, pady=10, sticky="n")
            app.after(5000, reset_status_label)
        main.update_idletasks()
        app.update_idletasks()
        return False

def reset_status_label():
    global status_label
    if current_page == "home" and status_label and status_label.winfo_exists():
        status_label.configure(text="Click 'Generate Mod List' to compile the list!")
    main.update_idletasks()
    app.update_idletasks()

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
            return None
    except Exception as e:
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

            if app.winfo_exists():
                after_id = app.after(5000, schedule_log_errors_check)
                after_tasks.append(after_id)

        except Exception as e:
            launch_button.configure(text="Launch Game", state="normal")  # Revert on failure
            messagebox.showerror("Error", f"Failed to launch game: {str(e)}")
    else:
        messagebox.showerror("Error", "Game executable not found!")

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
        except tk.TclError as e:
            print(f"Error updating launch button: {e}")
    if app.winfo_exists():
        app.after(5000, update_launch_button)

def switch_page(page_name):
    global current_page
    if current_page == page_name:
        return
    current_page = page_name
    if page_name == "home":
        show_home()
    elif page_name == "mods":
        show_mods()
    elif page_name == "settings":
        show_settings()
    elif page_name == "core_mods":
        show_core_mods()
    elif page_name == "log_viewer":
        show_log_viewer()
    app.update() 

def show_home():
    global status_label, current_page, log_vars, auto_select_all_logs, num_logs
    current_page = "home"
    clear_main()
    update_active_button()

    main.update()

    global current_image_label
    img = get_cached_image((450, 450))
    if img:
        current_image_label = ctk.CTkLabel(main, image=img, text="")
        current_image_label.place(x=(main.winfo_width() - 250) // 2.8, y=-160)
    else:
        ctk.CTkLabel(main, text="Generate Mod List", font=("Orbitron", 22, "bold"), text_color=TEXT_COLOR).grid(row=0, column=0, pady=10, sticky="n")

    main.grid_columnconfigure(0, weight=1)
    start_button = ctk.CTkButton(main, text="Generate Mod List", command=lambda: run_script(num_logs), fg_color=NEON_YELLOW, text_color="black", hover_color="#DBBE00")
    start_button.grid(row=0, column=0, pady=(180, 25), sticky="n")

    ctk.CTkLabel(main, text="Select Logs to Include:", text_color=TEXT_COLOR).grid(row=1, column=0, pady=(0, 5), sticky="n")
    
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

    log_vars.clear()
    log_vars.update({log_name: tk.BooleanVar(value=auto_select_all_logs.get() if auto_select_all_logs is not None else True) for log_name in available_logs})

    num_logs = len(available_logs) + 1  # +1 due to Select All Logs

    main.grid_rowconfigure(0, weight=0)  # Image row
    main.grid_rowconfigure(1, weight=0)  # Label row
    for i in range(2, num_logs + 2):
        main.grid_rowconfigure(i, weight=1)  # Rows for checkboxes
    main.grid_rowconfigure(num_logs + 2, weight=1)  # Bottom padding
    main.grid_rowconfigure(num_logs + 3, weight=0)  # Status label row

    # Select All Logs checkbox
    select_all_var = tk.BooleanVar(value=auto_select_all_logs.get() if auto_select_all_logs is not None else True)
    def toggle_all_logs():
        state = select_all_var.get()
        for var in log_vars.values():
            var.set(state)
    
    ctk.CTkCheckBox(main, text="Select All Logs", variable=select_all_var, command=toggle_all_logs,
                    font=("Arial", 12), text_color=TEXT_COLOR, checkbox_height=18, checkbox_width=18,
                    border_color=NEON_GREEN, fg_color=NEON_GREEN, hover_color=NEON_GREEN).grid(row=2, column=0, pady=5)

    # Individual log checkboxes
    for i, (log_name, _) in enumerate(available_logs.items(), start=3):
        ctk.CTkCheckBox(main, text=log_name, variable=log_vars[log_name], font=("Arial", 12), text_color=TEXT_COLOR,
                        checkbox_height=18, checkbox_width=18, border_color=NEON_GREEN, fg_color=NEON_GREEN, hover_color=NEON_GREEN).grid(row=i, column=0, pady=5)

    status_labels["home"] = ctk.CTkLabel(main, text="Click 'Generate Mod List' to compile the list!", font=("Arial", 12, "bold"), text_color=TEXT_COLOR)
    status_labels["home"].grid(row=num_logs + 3, column=0, pady=10, sticky="n")

def show_core_mods():
    global status_label, current_page
    current_page = "core_mods"
    clear_main()
    update_active_button()
    if not game_dir:
        messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
        return
    current_dir = game_dir
    global current_image_label
    img = get_cached_image((250, 250))
    if img:
        current_image_label = ctk.CTkLabel(main, image=img, text="")
        current_image_label.place(x=(main.winfo_width() - 250) // 2, y=-70)
    else:
        ctk.CTkLabel(main, text="Core Mods Status", font=("Orbitron", 22, "bold"), text_color=TEXT_COLOR).grid(row=0, column=0, pady=10, sticky="n")
    main.grid_columnconfigure(0, weight=1)
    main.grid_rowconfigure(0, weight=0)
    main.grid_rowconfigure(1, weight=1)
    main.grid_rowconfigure(2, weight=0)
    main.grid_rowconfigure(3, weight=0)
    status_frame = ctk.CTkFrame(main, fg_color=DARK_BG)
    status_frame.grid(row=1, column=0, pady=(120, 10), padx=20, sticky="nsew")
    status_frame.grid_columnconfigure(0, weight=1, uniform="col", minsize=150)
    status_frame.grid_columnconfigure(1, weight=1, uniform="col", minsize=150)
    status_frame.grid_columnconfigure(2, weight=1, uniform="col", minsize=150)
    status_frame.grid_columnconfigure(3, weight=1, uniform="col", minsize=150)
    for i in range(len(CORE_DEPENDENCIES) + 1):  # +1 for header row
        status_frame.grid_rowconfigure(i, weight=1, minsize=40)
    status_label = ctk.CTkLabel(main, text="Click 'Enable/Disable Core Mods' to manage core mods!", font=("Arial", 12, "bold"), text_color=TEXT_COLOR)
    status_label.grid(row=2, column=0, pady=10, sticky="n")
    button_frame = ctk.CTkFrame(main, fg_color="#222222")
    button_frame.grid(row=3, column=0, pady=10, sticky="n")
    ctk.CTkButton(button_frame, text="Disable Core Mods", command=lambda: disable_core_mods(update_status), fg_color=ACCENT_RED, text_color="white", hover_color="#94160C").pack(side="left", padx=5)
    ctk.CTkButton(button_frame, text="Enable Core Mods", command=lambda: enable_core_mods(update_status), fg_color=NEON_GREEN, text_color="black", hover_color="#1ADB00").pack(side="left", padx=5)
    widget_map = {}
    previous_status = {}

    def update_status():
        if not main.winfo_exists() or not status_frame.winfo_exists():
            return
        nonlocal previous_status, widget_map
        try:
            status_data = view_core_mods_status(current_dir)
        except Exception as e:
            status_data = {mod_name: {"installed": False, "path": info["path"], "version": None}
                           for mod_name, info in CORE_DEPENDENCIES.items()}
        if not widget_map: 
            # Header row
            ctk.CTkLabel(status_frame, text="Core Mod", font=("Arial", 12, "bold"), text_color=TEXT_COLOR).grid(row=0, column=0, padx=5, pady=2, sticky="nsew")
            ctk.CTkLabel(status_frame, text="Version", font=("Arial", 12, "bold"), text_color=TEXT_COLOR).grid(row=0, column=1, padx=5, pady=2, sticky="nsew")
            ctk.CTkLabel(status_frame, text="Status", font=("Arial", 12, "bold"), text_color=TEXT_COLOR).grid(row=0, column=2, padx=5, pady=2, sticky="nsew")
            ctk.CTkLabel(status_frame, text="Action", font=("Arial", 12, "bold"), text_color=TEXT_COLOR).grid(row=0, column=3, padx=5, pady=2, sticky="nsew")
            # Data rows
            for i, (mod_name, info) in enumerate(status_data.items(), start=1):
                name_label = ctk.CTkLabel(status_frame, text=mod_name, font=("Arial", 10, "bold"), text_color=TEXT_COLOR, cursor="hand2")
                name_label.grid(row=i, column=0, padx=5, pady=2, sticky="nsew")
                def open_mod_page(event, mod_id=CORE_DEPENDENCIES[mod_name]["id"]):
                    webbrowser.open(f"https://www.nexusmods.com/cyberpunk2077/mods/{mod_id}")
                name_label.bind("<Button-1>", open_mod_page)
                def on_enter(event, label=name_label):
                    label.configure(text_color="#E89202")
                def on_leave(event, label=name_label):
                    label.configure(text_color=TEXT_COLOR)
                name_label.bind("<Enter>", on_enter)
                name_label.bind("<Leave>", on_leave)
                version_text = (info["version"] if info["version"] and info["version"] != "Unknown" else
                               (manual_versions.get(mod_name, "N/A") if mod_name in ["EquipmentEx", "Redscript"] else "N/A"))
                version_widget = ctk.CTkLabel(status_frame, text=version_text, font=("Arial", 10), text_color=TEXT_COLOR)
                version_widget.grid(row=i, column=1, padx=5, pady=2, sticky="nsew")
                status_text = "Installed" if info["installed"] else "Not Installed"
                status_color = NEON_GREEN if info["installed"] else ACCENT_RED
                status_symbol = "✔" if info["installed"] else "✘"
                status_widget = ctk.CTkLabel(status_frame, text=f"{status_symbol} {status_text}", font=("Arial", 10), text_color=status_color)
                status_widget.grid(row=i, column=2, padx=5, pady=2, sticky="nsew")
                if info["installed"]:
                    action_button = ctk.CTkButton(
                        status_frame,
                        text="No Action Required",
                        font=("Arial", 10),
                        fg_color="#555555",  # Grey
                        text_color="#999999",  # Lighter grey 
                        hover=False,  # Disable hover effect
                        state="disabled",  # Makes the button non-clickable 
                        width=100,
                        height=25
                    )
                else:
                    action_button = ctk.CTkButton(
                        status_frame,
                        text="Install",
                        command=lambda name=mod_name: webbrowser.open(f"https://www.nexusmods.com/cyberpunk2077/mods/{CORE_DEPENDENCIES[name]['id']}"),
                        font=("Arial", 10),
                        fg_color=NEON_GREEN,
                        text_color="black",
                        hover_color="#1ADB00",
                        width=100,
                        height=25
                    )
                action_button.grid(row=i, column=3, padx=5, pady=2, sticky="n")
                widget_map[mod_name] = {
                    "name_label": name_label,
                    "version_widget": version_widget,
                    "status_widget": status_widget,
                    "action_button": action_button
                }
        if previous_status != status_data:
            for mod_name, info in status_data.items():
                widgets = widget_map.get(mod_name, {})
                if not widgets:
                    continue
                version_text = (info["version"] if info["version"] and info["version"] != "Unknown" else
                               (manual_versions.get(mod_name, "N/A") if mod_name in ["EquipmentEx", "Redscript"] else "N/A"))
                widgets["version_widget"].configure(text=version_text)
                status_text = "Installed" if info["installed"] else "Not Installed"
                status_color = NEON_GREEN if info["installed"] else ACCENT_RED
                status_symbol = "✔" if info["installed"] else "✘"
                widgets["status_widget"].configure(text=f"{status_symbol} {status_text}", text_color=status_color)
                widgets["action_button"].grid_remove()
                if info["installed"]:
                    new_button = ctk.CTkButton(
                        status_frame,
                        text="No Action Required",
                        font=("Arial", 10),
                        fg_color="#555555",
                        text_color="#999999",
                        hover=False,
                        state="disabled",
                        width=100,
                        height=25
                    )
                else:
                    new_button = ctk.CTkButton(
                        status_frame,
                        text="Install",
                        command=lambda name=mod_name: webbrowser.open(f"https://www.nexusmods.com/cyberpunk2077/mods/{CORE_DEPENDENCIES[name]['id']}"),
                        font=("Arial", 10),
                        fg_color=NEON_GREEN,
                        text_color="black",
                        hover_color="#1ADB00",
                        width=100,
                        height=25
                    )
                new_button.grid(row=list(status_data.keys()).index(mod_name) + 1, column=3, padx=5, pady=2, sticky="n")
                widgets["action_button"] = new_button
            previous_status = status_data.copy()
        if app.winfo_exists():
            app.after(2000, update_status)
    update_status()

def show_log_viewer():
    global status_label, current_page
    current_page = "log_viewer"
    clear_main()
    update_active_button()
    if not game_dir:
        messagebox.showwarning("No Game Directory", "Please set the Cyberpunk 2077 directory in Settings first!")
        return

    current_dir = game_dir

    global current_image_label
    img = get_cached_image((250, 250))
    if img:
        current_image_label = ctk.CTkLabel(main, image=img, text="")
        current_image_label.place(x=(main.winfo_width() - 250) // 2, y=-70)
    else:
        ctk.CTkLabel(main, text="Log File Viewer", font=("Orbitron", 22, "bold"), text_color=TEXT_COLOR).grid(row=0, column=0, pady=10, sticky="n")

    main.grid_columnconfigure(0, weight=1)
    main.grid_rowconfigure(0, weight=0)  # Image / title row
    main.grid_rowconfigure(1, weight=1)  # Log frame row
    main.grid_rowconfigure(2, weight=0)  # Status label row

    log_frame = ctk.CTkFrame(main, fg_color=DARK_BG)
    log_frame.grid(row=1, column=0, pady=(120, 10), padx=10, sticky="nsew")  
    log_frame.grid_rowconfigure(0, weight=1) 
    log_frame.grid_columnconfigure(0, weight=1)  # Left column listbox
    log_frame.grid_columnconfigure(1, weight=2)  # Right column text

    log_list_frame = ctk.CTkFrame(log_frame, fg_color=DARK_BG)
    log_list_frame.grid(row=0, column=0, padx=10, sticky="nsew")
    log_list_frame.grid_rowconfigure(1, weight=1) 
    log_list_frame.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(log_list_frame, text="Available Logs", font=("Arial", 12), text_color=TEXT_COLOR).pack()
    
    log_scrollbar = ctk.CTkScrollbar(log_list_frame, orientation="vertical")
    log_scrollbar.pack(side="right", fill="y")
    log_listbox = tk.Listbox(log_list_frame, font=("Arial", 10), width=30, height=30, bg="#333333", fg="white", selectmode=tk.SINGLE)
    log_listbox.pack(side="left", fill="both", expand=True) 
    log_listbox.configure(yscrollcommand=log_scrollbar.set)
    log_scrollbar.configure(command=log_listbox.yview)

    text_frame = ctk.CTkFrame(log_frame, fg_color=DARK_BG)
    text_frame.grid(row=0, column=1, padx=10, sticky="nsew")
    text_frame.grid_rowconfigure(1, weight=1) 
    text_frame.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(text_frame, text="Log Viewer", font=("Arial", 12), text_color=TEXT_COLOR).pack()
    
    text_scrollbar = ctk.CTkScrollbar(text_frame, orientation="vertical")
    text_scrollbar.pack(side="right", fill="y")
    log_text = tk.Text(text_frame, font=("Arial", 10), bg="#333333", fg="white", wrap=tk.WORD, height=30)
    log_text.pack(side="left", fill="both", expand=True)  
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
        except OSError as e:
            messagebox.showerror("Error", f"Failed to open log file {log_name}: {str(e)}")

    log_listbox.bind("<<ListboxSelect>>", display_log)
    log_listbox.bind("<Double-Button-1>", open_log_file)  # Bind double-click to open file

    status_label = ctk.CTkLabel(main, text="Select a log file to view its contents or double-click to open!", font=("Arial", 12, "bold"), text_color=TEXT_COLOR)
    status_label.grid(row=2, column=0, pady=10, sticky="n")

def show_license():
    for child in app.winfo_children():
        if isinstance(child, ctk.CTkToplevel) and child.title() == "License":
            return

    license_window = ctk.CTkToplevel(app)
    license_window.title("License")
    license_window.geometry("600x400")
    license_window.resizable(False, False)
    license_window.configure(fg_color=DARK_BG)

    app_x = app.winfo_x()
    app_y = app.winfo_y()
    app_width = app.winfo_width()
    app_height = app.winfo_height()
    window_width = 600
    window_height = 400
    x = app_x + (app_width - window_width) // 2
    y = app_y + (app_height - window_height) // 2
    license_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    license_textbox = ctk.CTkTextbox(license_window, font=("Arial", 12), text_color="#FFFFFF", fg_color="#333333", wrap="word", height=350, width=550)
    license_textbox.pack(pady=10, padx=10, fill="both", expand=True)
    license_textbox.insert("0.0", """---

MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.""")
    license_textbox.configure(state="disabled")

    license_window.transient(app)
    license_window.grab_set()

    set_window_icon(license_window)

def show_disclaimer():
    for child in app.winfo_children():
        if isinstance(child, ctk.CTkToplevel) and child.title() == "Disclaimer":
            return

    disclaimer_window = ctk.CTkToplevel(app)
    disclaimer_window.title("Disclaimer")
    disclaimer_window.geometry("600x400")
    disclaimer_window.resizable(False, False)
    disclaimer_window.configure(fg_color=DARK_BG)

    app_x = app.winfo_x()
    app_y = app.winfo_y()
    app_width = app.winfo_width()
    app_height = app.winfo_height()
    window_width = 600
    window_height = 400
    x = app_x + (app_width - window_width) // 2
    y = app_y + (app_height - window_height) // 2
    disclaimer_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    disclaimer_textbox = ctk.CTkTextbox(disclaimer_window, font=("Arial", 12), text_color="#FFFFFF", fg_color="#333333", wrap="word", height=350, width=550)
    disclaimer_textbox.pack(pady=10, padx=10, fill="both", expand=True)
    disclaimer_textbox.insert("0.0", """---

Disclaimer

Cyberpunk 2077 Mod List Tool is an unofficial, fan-made project and is not affiliated with, endorsed by, or supported by CD PROJEKT S.A. or its affiliates. All trademarks, logos, and game assets related to Cyberpunk 2077 are the property of CD PROJEKT S.A.

This tool is provided for non-commercial use only and is intended to assist users in managing mods for Cyberpunk 2077 in accordance with CD PROJEKT RED's Fan Content Guidelines and End User License Agreement (EULA). Users are responsible for ensuring that their use of this tool and any mods managed with it complies with CD PROJEKT RED's terms, available at regulations.cdprojektred.com and www.cyberpunk.net.

The developer of this tool is not responsible for any damage, loss, game instability, or bans resulting from the use of this tool or any mods managed with it. Users are advised to back up their game files before using this tool and to use it at their own risk. Modding may cause game instability or violate CD PROJEKT RED's terms, and users assume all associated risks.

For official modding support, refer to CD PROJEKT RED's REDmod tool and documentation.""")
    disclaimer_textbox.configure(state="disabled")

    disclaimer_window.transient(app)
    disclaimer_window.grab_set()

    set_window_icon(disclaimer_window)

def debounce_save_game_dir():
    try:
        if hasattr(debounce_save_game_dir, "save_timer") and debounce_save_game_dir.save_timer:
            debounce_save_game_dir.save_timer.cancel()
    except Exception:
        pass

    debounce_save_game_dir.save_timer = Timer(0.5, async_save_game_dir)
    debounce_save_game_dir.save_timer.start()

def show_version_dialog(mod_name):
    global app, manual_versions, manual_version_checksums, status_label
    current_value = manual_versions.get(mod_name, "").strip()

    dialog = ctk.CTkInputDialog(
        text=f"Enter version for {mod_name} (current: {current_value or 'N/A'}):",
        title=f"{mod_name} Version"
    )

    app.update_idletasks()
    app_x, app_y = app.winfo_x(), app.winfo_y()
    app_width, app_height = app.winfo_width(), app.winfo_height()
    dialog_width, dialog_height = 300, 200
    x = app_x + (app_width - dialog_width) // 2
    y = app_y + (app_height - dialog_height) // 2
    dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    set_window_icon(dialog)

    new_version = dialog.get_input()
    if new_version is None:
        return

    new_version = new_version.strip()
    if not new_version:
        return

    manual_versions[mod_name] = new_version

    paths = CORE_DEPENDENCIES[mod_name]["path"]
    first_path_abs = os.path.join(game_dir, paths[0]) if os.path.exists(os.path.join(game_dir, paths[0])) else None
    manual_version_checksums[mod_name] = get_file_checksum(first_path_abs) if first_path_abs else None

    if status_label and status_label.winfo_exists():
        status_label.configure(text=f"{mod_name} version set to '{new_version}'.")
        def _reset():
            if current_page == "settings" and status_label.winfo_exists():
                status_label.configure(text="")
        after_id = app.after(5000, _reset)
        after_tasks.append(after_id)

def show_mod_list_options_window():
    global auto_open_output, auto_select_all_logs, include_errors_in_output, include_disabled_in_output
    for child in app.winfo_children():
        if isinstance(child, ctk.CTkToplevel) and child.title() == "Mod List Options":
            return

    options_window = ctk.CTkToplevel(app)
    options_window.title("Mod List Options")
    options_window.geometry("600x400")
    options_window.resizable(False, False)
    options_window.configure(fg_color=DARK_BG)

    app_x = app.winfo_x()
    app_y = app.winfo_y()
    app_width = app.winfo_width()
    app_height = app.winfo_height()
    window_width = 600
    window_height = 400
    x = app_x + (app_width - window_width) // 2
    y = app_y + (app_height - window_height) // 2
    options_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    options_frame = ctk.CTkFrame(options_window, fg_color=DARK_BG)
    options_frame.pack(pady=20, padx=20, fill="both", expand=True)
    options_frame.grid_columnconfigure(0, weight=1)
    
    ctk.CTkLabel(options_frame, text="Generated Mod List Options", font=("Orbitron", 16, "bold"), text_color=TEXT_COLOR).grid(row=0, column=0, pady=(10, 20), sticky="n")

    if auto_open_output is not None:
        ctk.CTkCheckBox(options_frame, text="Automatically open the Mod List output file after generation", variable=auto_open_output, font=("Arial", 12), text_color=TEXT_COLOR,
                        checkbox_height=18, checkbox_width=18, border_color=NEON_GREEN, fg_color=NEON_GREEN, hover_color=NEON_GREEN,
                        command=debounce_save_game_dir).grid(row=1, column=0, pady=10, sticky="n")

    if auto_select_all_logs is not None:
        ctk.CTkCheckBox(options_frame, text="Automatically selects all logs by default when generating a Mod List", variable=auto_select_all_logs, font=("Arial", 12), text_color=TEXT_COLOR,
                        checkbox_height=18, checkbox_width=18, border_color=NEON_GREEN, fg_color=NEON_GREEN, hover_color=NEON_GREEN,
                        command=debounce_save_game_dir).grid(row=2, column=0, pady=10, sticky="n")

    if include_errors_in_output is not None:
        ctk.CTkCheckBox(options_frame, text="Include Potential Errors in Output File", variable=include_errors_in_output, font=("Arial", 12), text_color=TEXT_COLOR,
                        checkbox_height=18, checkbox_width=18, border_color=NEON_GREEN, fg_color=NEON_GREEN, hover_color=NEON_GREEN,
                        command=debounce_save_game_dir).grid(row=3, column=0, pady=10, sticky="n")

    if include_disabled_in_output is not None:
        ctk.CTkCheckBox(options_frame, text="Include Disabled Mods in Output File", variable=include_disabled_in_output, font=("Arial", 12), text_color=TEXT_COLOR,
                        checkbox_height=18, checkbox_width=18, border_color=NEON_GREEN, fg_color=NEON_GREEN, hover_color=NEON_GREEN,
                        command=debounce_save_game_dir).grid(row=4, column=0, pady=10, sticky="n")

    ctk.CTkButton(options_frame, text="Save", command=lambda: [debounce_save_game_dir(), options_window.destroy()], 
                  fg_color=NEON_YELLOW, text_color="black", hover_color="#DBBE00", font=("Arial", 12)).grid(row=5, column=0, pady=20, sticky="n")

    options_window.transient(app)
    options_window.grab_set()
    set_window_icon(options_window)

def on_click_disclaimer():
    return show_disclaimer()

def on_click_license():
    return show_license()

def show_settings():
    global status_label, game_dir_label, current_image_label, current_page, auto_open_output, auto_select_all_logs, include_errors_in_output, include_disabled_in_output
    current_page = "settings"
    clear_main()
    update_active_button()

    status_label = ctk.CTkLabel(main, text="", font=("Arial", 12, "bold"), text_color=TEXT_COLOR)
    status_label.grid(row=7, column=0, columnspan=2, pady=(0, 12), sticky="n")

    global current_image_label
    img = get_cached_image((600, 600))
    if img:
        current_image_label = ctk.CTkLabel(main, image=img, text="")
        current_image_label.place(x=(main.winfo_width() - 250) // 4, y=-160)
    else:
        ctk.CTkLabel(main, text="Settings", font=("Orbitron", 22, "bold"), text_color=TEXT_COLOR).grid(row=0, column=0, columnspan=2, pady=(10, 20), sticky="n")

    main.grid_columnconfigure(0, weight=1)
    main.grid_columnconfigure(1, weight=1)
    main.grid_rowconfigure(0, weight=0)  # Image row
    main.grid_rowconfigure(1, weight=1)  # Content row
    main.grid_rowconfigure(2, weight=0)  # Controls / labels

    # Change game directory button
    ctk.CTkButton(
        main,
        text="Change Game Directory",
        command=change_game_directory,
        fg_color=NEON_YELLOW,
        text_color="black",
        hover_color="#DBBE00"
    ).grid(row=2, column=0, columnspan=2, pady=10, sticky="n")

    game_dir_text = f"Current Game Directory: {game_dir if game_dir else 'Not Set'}"
    game_dir_label = ctk.CTkLabel(main, text=game_dir_text, font=("Arial", 12, "bold"), text_color=TEXT_COLOR)
    game_dir_label.grid(row=3, column=0, columnspan=2, pady=(0, 10), sticky="n")

    # Options button
    ctk.CTkButton(
        main,
        text="Mod List Options",
        command=show_mod_list_options_window,
        fg_color=NEON_YELLOW,
        text_color="black",
        hover_color="#DBBE00"
    ).grid(row=4, column=0, columnspan=2, pady=10, sticky="n")

    ctk.CTkButton(
        main,
        text="Set EquipmentEx Version",
        command=lambda: show_version_dialog("EquipmentEx"),
        font=("Arial", 12),
        fg_color=NEON_YELLOW,
        text_color="black",
        hover_color="#DBBE00"
    ).grid(row=6, column=0, padx=10, pady=10, sticky="e")

    ctk.CTkButton(
        main,
        text="Set Redscript Version",
        command=lambda: show_version_dialog("Redscript"),
        font=("Arial", 12),
        fg_color=NEON_YELLOW,
        text_color="black",
        hover_color="#DBBE00"
    ).grid(row=6, column=1, padx=10, pady=10, sticky="w")

    status_label.configure(text="Set mod versions above, then click Ok.")

    about_frame = ctk.CTkFrame(main, fg_color="transparent")
    about_frame.grid(row=8, column=0, columnspan=2, pady=(4, 8), sticky="n")

    disclaimer_btn = ctk.CTkButton(
        about_frame,
        text="Disclaimer",
        command=on_click_disclaimer, 
        fg_color="transparent",
        text_color=NEON_YELLOW,
        hover_color="#2B2B2B",
        border_width=0
    )
    disclaimer_btn.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="e")

    sep_label = ctk.CTkLabel(about_frame, text="|", text_color=TEXT_COLOR)
    sep_label.grid(row=0, column=1, padx=4, sticky="n")

    license_btn = ctk.CTkButton(
        about_frame,
        text="License",
        command=on_click_license, 
        fg_color="transparent",
        text_color=NEON_YELLOW,
        hover_color="#2B2B2B",
        border_width=0
    )
    license_btn.grid(row=0, column=2, padx=(8, 0), pady=0, sticky="w")

def clear_main():
    global current_image_label, after_tasks

    if current_image_label and current_image_label.winfo_exists():
        try:
            current_image_label.destroy()
            current_image_label = None
        except:
            pass
        current_image_label = None

    for after_id in list(after_tasks):
        try:
            app.after_cancel(after_id)
        except Exception:
            pass

    after_tasks.clear()

    if 'status_label' in globals() and status_label.winfo_exists():
        status_label.destroy()

    for widget in main.winfo_children():
        widget.destroy()

    for col in range(main.grid_size()[0]):
        main.grid_columnconfigure(col, weight=0)
    for row in range(main.grid_size()[1]):
        main.grid_rowconfigure(row, weight=0)

    for col in range(2):  
        main.grid_columnconfigure(col, weight=0)
    for row in range(20):  
        main.grid_rowconfigure(row, weight=0)

def update_initial_ui():
    global last_core_mods_status, status_label, mods
    if game_dir and os.path.exists(os.path.join(game_dir, "bin", "x64", "Cyberpunk2077.exe")):
        current_dir = game_dir
        initial_game_version = get_game_version(os.path.join(current_dir, "bin", "x64", "Cyberpunk2077.exe"))
        initial_phantom_liberty_installed = is_phantom_liberty_installed(current_dir)

        # Determines if there are any log errors at launch
        initial_log_errors = check_log_errors(current_dir)

        initial_all_core_mods_installed = check_all_core_mods_installed(current_dir)
        last_core_mods_status = initial_all_core_mods_installed

        initial_mod_count = 0
        core_mods = ["archivexl", "codeware", "tweakxl"]
        equipment_ex_paths = CORE_DEPENDENCIES["EquipmentEx"]["path"]
        temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
        mods = rebuild_mods_dictionary(current_dir, temp_disabled_path)

        # Count mods in the defined mod directories MOD_DIRECTORIES
        for mod_dir in MOD_DIRECTORIES:
            full_dir = os.path.join(current_dir, mod_dir)
            if os.path.exists(full_dir):
                for item in os.listdir(full_dir):
                    full_item_path = os.path.join(full_dir, item)
                    rel_path = os.path.relpath(full_item_path, current_dir)
                    normalized_rel = rel_path.replace("\\", "/").lower()
                    is_equipment_ex = (
                        normalized_rel == "r6/scripts/equipmentex" or
                        normalized_rel.startswith("r6/scripts/equipmentex/") or
                        any(normalized_rel == equip_path.replace("\\", "/").lower() for equip_path in equipment_ex_paths)
                    )
                    if mod_dir == os.path.normpath("bin/x64/plugins/cyber_engine_tweaks/mods"):
                        if os.path.isdir(full_item_path) and not is_equipment_ex:
                            initial_mod_count += 1
                    else:
                        if not is_equipment_ex:
                            initial_mod_count += 1

        # Counts any mods in red4ext/plugins had to seperate from mod directories couldnt figure out bug
        red4ext_plugins_dir = os.path.join(current_dir, "red4ext", "plugins")
        if os.path.exists(red4ext_plugins_dir):
            for item in os.listdir(red4ext_plugins_dir):
                full_item_path = os.path.join(red4ext_plugins_dir, item)
                if os.path.isdir(full_item_path) and item.lower() not in core_mods:
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
        update_core_mods_label()
        schedule_log_errors_check()
    else:
        mod_count_label.configure(text="Total Mods: Unknown")
        game_version_label.configure(text="Game Version: Unknown")
        log_errors_label.configure(text="Log Errors Detected: Unknown")
        core_mods_label.configure(text="Core Mods Installed: Unknown")
        show_settings()

def update_mods_after_page_load():
    global mods
    if not game_dir:
        return
    current_dir = game_dir
    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)

    mods = rebuild_mods_dictionary(current_dir, temp_disabled_path)
    update_mod_list(enabled_listbox, disabled_listbox, selected_dir_var, mods, search_var.get())
    start_mod_observer()

if not check_single_instance():
    messagebox.showinfo("Cyberpunk 2077 Mod List Tool", "Another instance of Cyberpunk 2077 Mod List Tool is already running.")
    sys.exit(0)

app = ctk.CTk()
auto_open_output = tk.BooleanVar(master=app, value=False)  
auto_select_all_logs = tk.BooleanVar(master=app, value=False)
include_errors_in_output = tk.BooleanVar(master=app, value=False) 
include_disabled_in_output = tk.BooleanVar(master=app, value=False)
app.geometry("1200x700")
app.title("Cyberpunk 2077 Mod List Tool")
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

app.grid_columnconfigure(1, weight=1)
app.grid_rowconfigure(0, weight=1)
app.grid_rowconfigure(1, weight=0)  # Row for footer

sidebar = ctk.CTkFrame(app, width=250, corner_radius=0, fg_color=DARK_BG)
sidebar.grid(row=0, column=0, sticky="nsew")
sidebar.grid_rowconfigure(5, weight=1)  # Weight for the main content, adjusted for 6 rows


def load_icon(file_name, size=(20, 20)):
    try:
        base64_string = base64_strings.get(os.path.basename(file_name))
        if base64_string:
            img_data = base64.b64decode(base64_string)
            pil_image = Image.open(BytesIO(img_data))
            resampling = Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.BILINEAR
            pil_image = pil_image.resize(size, resampling)
            return ctk.CTkImage(pil_image, size=size)
        else:
            return None
    except Exception as e:
        return None

home_icon = load_icon(os.path.join(SCRIPT_DIR, "icons", "home_icon.png"))
mods_icon = load_icon(os.path.join(SCRIPT_DIR, "icons", "mods_icon.png"))
settings_icon = load_icon(os.path.join(SCRIPT_DIR, "icons", "settings_icon.png"))
core_icon = load_icon(os.path.join(SCRIPT_DIR, "icons", "core_icon.png"))
log_icon = load_icon(os.path.join(SCRIPT_DIR, "icons", "log_icon.png"))
launch_icon = load_icon(os.path.join(SCRIPT_DIR, "icons", "game_icon.png"))

sidebar_buttons = {}

def update_active_button():
    for page, (button, underline_frame) in sidebar_buttons.items():
        if page == current_page:
            button.configure(fg_color="#2A2A2A", text_color=NEON_YELLOW) 
            underline_frame.configure(fg_color=NEON_YELLOW) 
        else:
            button.configure(fg_color=DARK_BG, text_color="white")  
            underline_frame.configure(fg_color=DARK_BG) 

# Sidebar creation
sidebar = ctk.CTkFrame(app, width=200, corner_radius=0, fg_color=DARK_BG)  
sidebar.grid(row=0, column=0, sticky="ns")  
app.grid_columnconfigure(0, weight=0, minsize=200) 

for i in range(12):  
    sidebar.grid_rowconfigure(i, weight=0, minsize=0)  
sidebar.grid_rowconfigure(10, weight=1)  

# Button configurations
button_configs = [
    ("home", "Home", show_home, home_icon),
    ("mods", "Mod Management", show_mods, mods_icon),
    ("core_mods", "Core Mods Status", show_core_mods, core_icon),
    ("log_viewer", "Log File Viewer", show_log_viewer, log_icon),
    ("settings", "Settings", show_settings, settings_icon)
]

# Sidebar buttons with underlined widget to show active window
for row, (page, text, command, icon) in enumerate(button_configs):
    button_frame = ctk.CTkFrame(sidebar, fg_color=DARK_BG)
    button_frame.grid(row=row * 2, column=0, pady=(20 if row == 0 else 5, 5), padx=0, sticky="ew")
    button_frame.grid_columnconfigure(0, weight=1)
    button = ctk.CTkButton(
        button_frame,
        text=text,
        command=lambda cmd=command, pg=page: [cmd(), update_active_button()] if current_page != pg else None,
        image=icon,
        compound="left" if icon else "none",
        fg_color=DARK_BG,
        hover_color="#6B6B6B",
        anchor="w",
        font=("Arial", 12, "bold"),
        text_color="white",
        width=200,
        height=50,
        corner_radius=10
    )
    button.grid(row=0, column=0, sticky="w")
    underline_frame = ctk.CTkFrame(button_frame, height=2, fg_color=DARK_BG)
    underline_frame.grid(row=1, column=0, sticky="ew", pady=(2, 0))
    sidebar_buttons[page] = (button, underline_frame)

# Launch Game Button
global launch_button
game_icon = load_game_icon() or launch_icon
launch_button_frame = ctk.CTkFrame(sidebar, fg_color=DARK_BG)
launch_button_frame.grid(row=11, column=0, pady=5, padx=0, sticky="sw") 
launch_button_frame.grid_columnconfigure(0, weight=1)
launch_button = ctk.CTkButton(
    launch_button_frame,
    text="Launch Game",
    command=lambda: launch_game() if not is_game_running() else None,
    image=game_icon,
    compound="left" if game_icon else "top",
    fg_color=DARK_BG,
    hover_color="#6B6B6B",
    anchor="w",
    font=("Arial", 12, "bold"),
    text_color="white",
    width=200,
    height=50,
    corner_radius=10
)
launch_button.grid(row=0, column=0, sticky="w")
underline_frame = ctk.CTkFrame(launch_button_frame, height=2, fg_color=DARK_BG)
underline_frame.grid(row=1, column=0, sticky="ew", pady=(2, 0))
sidebar_buttons["launch_game"] = (launch_button, underline_frame)

app.grid_rowconfigure(0, weight=1)

update_active_button()

main = ctk.CTkFrame(app, corner_radius=0, fg_color="#222222")
main.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

# Footer 
footer = ctk.CTkFrame(app, height=50, fg_color="#0e0e0e")  
footer.grid(row=1, column=0, columnspan=2, sticky="ew")
app.grid_rowconfigure(1, weight=0)  

footer_inner = ctk.CTkFrame(footer, fg_color="#0e0e0e")
footer_inner.grid(row=0, column=0, sticky="nsew")
footer.grid_columnconfigure(0, weight=1)  

footer_inner.grid_columnconfigure(0, weight=1)  # Left padding column
footer_inner.grid_columnconfigure(1, weight=1)  # Total Mods
footer_inner.grid_columnconfigure(2, weight=1)  # Game Version
footer_inner.grid_columnconfigure(3, weight=1)  # Tool Version
footer_inner.grid_columnconfigure(4, weight=1)  # Log Errors Detected
footer_inner.grid_columnconfigure(5, weight=1)  # Core Mods Installed
footer_inner.grid_columnconfigure(6, weight=1)  # Nexus Mod Page
footer_inner.grid_columnconfigure(7, weight=1)  # Right padding column

mod_count_label = ctk.CTkLabel(footer_inner, text="Total Mods: Unknown", text_color=TEXT_COLOR)
mod_count_label.grid(row=0, column=1, sticky="w", padx=5, pady=5)  

game_version_label = ctk.CTkLabel(footer_inner, text="Game Version: Unknown", text_color=TEXT_COLOR)
game_version_label.grid(row=0, column=2, sticky="nse", padx=5, pady=5)  

tool_version_label = ctk.CTkLabel(footer_inner, text=f"Tool Version: {tool_Version}", text_color=TEXT_COLOR)
tool_version_label.grid(row=0, column=3, sticky="nse", padx=5, pady=5) 

log_errors_label = ctk.CTkLabel(footer_inner, text="Log Errors Detected: Unknown", text_color=TEXT_COLOR)
log_errors_label.grid(row=0, column=4, sticky="nse", padx=5, pady=5) 

core_mods_label = ctk.CTkLabel(footer_inner, text="Core Mods Installed: Unknown", text_color=TEXT_COLOR)
core_mods_label.grid(row=0, column=5, sticky="nse", padx=5, pady=5) 

link = ctk.CTkLabel(footer_inner, text="Nexus Mod Page", text_color=NEON_YELLOW, cursor="hand2")
link.grid(row=0, column=6, sticky="e", padx=5, pady=5)  
link.bind("<Button-1>", lambda e: webbrowser.open_new("https://www.nexusmods.com/cyberpunk2077/mods/20113"))
link.bind("<Enter>", lambda e: link.configure(text_color="#E89202"))  
link.bind("<Leave>", lambda e: link.configure(text_color=NEON_YELLOW))  

status_label = ctk.CTkLabel(main, text="", font=("Arial", 12), text_color=TEXT_COLOR)
show_home()
update_initial_ui()
update_launch_button()  
app.protocol("WM_DELETE_WINDOW", on_closing)
app.mainloop()
