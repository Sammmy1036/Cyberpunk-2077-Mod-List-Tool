import dearpygui.dearpygui as dpg
import os
import sys
import webbrowser
import datetime
import tempfile
import shutil
import time
import psutil

try:
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

# Constants
DEFAULT_GAME_VERSION = "Unknown"
SCRIPT_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(SCRIPT_DIR, "Cyberpunk 2077 Mod List Tool.ico")
IMAGE_PATH = os.path.join(SCRIPT_DIR, "Cyberpunk 2077 Mod List Tool.png")
LOCK_FILE = os.path.join(tempfile.gettempdir(), "Cyberpunk2077ModListTool.lock")
MOD_DIRECTORIES = ["archive/pc/mod", "bin/x64/plugins/cyber_engine_tweaks/mods", "r6/scripts", "r6/tweaks"]
TEMP_DISABLED_DIR = "Temporarily Disabled Mods"

# Global variables
mod_window_open = False
_game_running_cache = None
_cache_timestamp = 0
CACHE_TIMEOUT = 2
mods = {}

def check_single_instance():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, 'r') as f:
                pid = f.read().strip()
                if pid and os.path.exists(f"/proc/{pid}"):
                    return False
                elif pid and sys.platform == "win32":
                    try:
                        os.kill(int(pid), 0)
                        return False
                    except OSError:
                        pass
        except Exception:
            pass
    with open(LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))
    return True

def get_game_version(file_path):
    if not WIN32_AVAILABLE:
        return DEFAULT_GAME_VERSION
    try:
        if not os.path.exists(file_path):
            return DEFAULT_GAME_VERSION
        info = win32api.GetFileVersionInfo(file_path, "\\")
        ms = info.get("ProductVersionMS", 0)
        ls = info.get("ProductVersionLS", 0)
        return f"{(ms >> 16) & 0xffff}.{(ms) & 0xffff}.{(ls >> 16) & 0xffff}.{(ls) & 0xffff}"
    except (win32api.error, FileNotFoundError):
        return DEFAULT_GAME_VERSION

def is_phantom_liberty_installed(current_dir):
    ep1_folder = os.path.join(current_dir, "archive", "pc", "ep1")
    tweakdb_ep1 = os.path.join(current_dir, "r6", "cache", "tweakdb_ep1.bin")
    return (os.path.exists(ep1_folder) and any(f.endswith('.archive') for f in os.listdir(ep1_folder))) or os.path.exists(tweakdb_ep1)

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
        print(f"Warning: Failed to check if game is running: {e}. Assuming falsely.")
        _game_running_cache = False
    _cache_timestamp = current_time
    return _game_running_cache

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
        if os.path.exists(temp_disabled_path) and not os.listdir(temp_disabled_path):
            os.rmdir(temp_disabled_path)
            print(f"Removed empty {TEMP_DISABLED_DIR} folder.")
    except OSError as e:
        print(f"Failed to REMOVE {TEMP_DISABLED_DIR} folder: {str(e)}")

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

def run_script(sender, app_data, user_data):
    current_dir = os.getcwd()
    game_path = os.path.join(current_dir, "bin", "x64", "Cyberpunk2077.exe")
    game_version = get_game_version(game_path)
    phantom_liberty_installed = is_phantom_liberty_installed(current_dir)
    if not os.path.exists(os.path.join(current_dir, "archive")):
        dpg.set_value("status_text", "Application not installed in the correct location!")
        dpg.hide_item("mod_count_text")
        dpg.hide_item("game_version_text")
        dpg.hide_item("log_errors_text")
        dpg.hide_item("pl_dlc_text")
        return False
    now = datetime.datetime.now()
    paths = [os.path.join(current_dir, d) for d in MOD_DIRECTORIES]
    mod_count = 0
    for path in paths:
        if os.path.exists(path):
            if "cyber_engine_tweaks/mods" in path:
                mod_count += len([item for item in os.listdir(path) if os.path.isdir(os.path.join(path, item))])
            else:
                mod_count += len(os.listdir(path))
    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
    log_files = {
        "ArchiveXL": os.path.join(current_dir, "red4ext", "plugins", "ArchiveXL", "ArchiveXL.log"),
        "Codeware": os.path.join(current_dir, "red4ext", "plugins", "Codeware", "Codeware.log"),
        "TweakXL": os.path.join(current_dir, "red4ext", "plugins", "TweakXL", "TweakXL.log")
    }
    log_errors = {name: extract_log_errors(path) for name, path in log_files.items() if extract_log_errors(path)}
    
    with open('Cyberpunk 2077 Mod List.txt', 'w') as file:
        file.write(f"Cyberpunk 2077 Mod List Tool by Sammmy1036\n")
        file.write(f"Tool Version: 1.0.0.3\n")
        file.write(f"Nexus Mod Page https://www.nexusmods.com/cyberpunk2077/mods/20113\n")
        file.write(f"List created on {now.strftime('%B %d, %Y at %I:%M:%S %p')}\n")
        file.write(f"Game Version: {game_version}\n")
        file.write(f"Phantom Liberty DLC Installed: {'Yes' if phantom_liberty_installed else 'No'}\n")
        file.write(f"Total Mods Installed: {mod_count}\n")
        file.write("-" * 120 + "\n")
        if log_errors:
            file.write("\nPotential Errors to Review\n")
            file.write("=" * 120 + "\n")
            for log_name, errors in log_errors.items():
                file.write(f"\n{log_name} Errors:\n")
                file.write("-" * 120 + "\n")
                file.write("\n".join(errors) + "\n")
            file.write("=" * 120 + "\n")
        for i, folder in enumerate(MOD_DIRECTORIES):
            if os.path.exists(paths[i]):
                file.write(f"\nMods located in {folder}:\n")
                file.write("-" * 120 + "\n")
                for item in os.listdir(paths[i]):
                    full_path = os.path.join(paths[i], item)
                    if "cyber_engine_tweaks/mods" in folder:
                        if os.path.isdir(full_path):
                            file.write(f"{item}\n")
                    else:
                        file.write(f"{item}\n")
            else:
                file.write(f"\nError: The subfolder(s) {folder} were not found!\n")
            disabled_dir = os.path.join(temp_disabled_path, folder)
            if os.path.exists(disabled_dir):
                file.write(f"\nDisabled mods in {TEMP_DISABLED_DIR}/{folder}:\n")
                file.write("-" * 120 + "\n")
                for item in os.listdir(disabled_dir):
                    full_path = os.path.join(disabled_dir, item)
                    if "cyber_engine_tweaks/mods" in folder:
                        if os.path.isdir(full_path):
                            file.write(f"{item}\n")
                    else:
                        file.write(f"{item}\n")
        if dpg.get_value("include_logs_checkbox"):
            for log_name, log_path in log_files.items():
                if os.path.exists(log_path):
                    file.write(f"\n{log_name} Log:\n")
                    file.write("-" * 120 + "\n")
                    try:
                        with open(log_path, 'r', encoding='utf-8') as input_file:
                            file.write(input_file.read() + "\n")
                    except (OSError, UnicodeDecodeError) as e:
                        file.write(f"Error reading {log_name}.log: {str(e)}\n")
                else:
                    file.write(f"\n{log_name} Log:\n" + "-" * 120 + "\nThe {log_name} log could not be found! Log not provided!\n")
    
    dpg.set_value("mod_count_text", f"Total Mods: {mod_count}")
    dpg.set_value("game_version_text", f"Game Version: {game_version}")
    dpg.set_value("log_errors_text", f"Log Errors Detected: {'Yes' if log_errors else 'No'}")
    dpg.set_value("pl_dlc_text", f"Phantom Liberty DLC: {'Yes' if phantom_liberty_installed else 'No'}")
    dpg.set_value("status_text", "Success! Check Cyberpunk 2077 Mod List.txt")
    dpg.show_item("mod_count_text")
    dpg.show_item("game_version_text")
    dpg.show_item("log_errors_text")
    dpg.show_item("pl_dlc_text")
    return bool(log_errors)

def toggle_mod_buttons(sender, app_data, user_data):
    if dpg.is_item_shown("disable_button"):
        dpg.hide_item("disable_button")
        dpg.hide_item("enable_button")
        dpg.hide_item("view_mod_list_button")
        dpg.configure_item("more_options_button", label="More Options")
    else:
        dpg.show_item("disable_button")
        dpg.show_item("enable_button")
        dpg.show_item("view_mod_list_button")
        dpg.configure_item("more_options_button", label="Hide Options")

def disable_all_mods(sender, app_data, user_data):
    if is_game_running():
        show_message("warning", "Game Running", "Cannot modify mods while Cyberpunk 2077 is running!")
        return
    if not show_confirm("Confirm Disable", "This will move all mods to the 'Temporarily Disabled Mods' folder. Proceed?"):
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
                try:
                    shutil.move(os.path.join(full_dir, item), os.path.join(temp_mod_dir, item))
                except Exception as e:
                    errors.append(f"Failed to disable {item} in {mod_dir}: {str(e)}")
    if errors:
        show_message("error", "Errors Occurred", "\n".join(errors))
        dpg.set_value("status_text", "Some mods could not be disabled. Check details.")
    else:
        dpg.set_value("status_text", "All mods have been disabled.")
    update_mod_count()

def enable_all_mods(sender, app_data, user_data):
    if is_game_running():
        show_message("warning", "Game Running", "Cannot modify mods while Cyberpunk 2077 is running!")
        return
    if not show_confirm("Confirm Enable", "This will move all mods back from 'Temporarily Disabled Mods' to their original locations and remove the folder. Proceed?"):
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
                    try:
                        shutil.move(os.path.join(temp_mod_dir, item), os.path.join(full_dir, item))
                    except Exception as e:
                        errors.append(f"Failed to enable {item} in {mod_dir}: {str(e)}")
                try:
                    if not os.listdir(temp_mod_dir):
                        os.rmdir(temp_mod_dir)
                except OSError as e:
                    errors.append(f"Failed to remove {temp_mod_dir}: {str(e)}")
        try:
            if os.path.exists(temp_disabled_path) and not os.listdir(temp_disabled_path):
                os.rmdir(temp_disabled_path)
            elif os.path.exists(temp_disabled_path):
                shutil.rmtree(temp_disabled_path, ignore_errors=True)
        except Exception as e:
            errors.append(f"Failed to remove {TEMP_DISABLED_DIR}: {str(e)}")
    if errors:
        show_message("error", "Errors Occurred", "\n".join(errors))
        dpg.set_value("status_text", "Some mods could not be enabled or folder not fully removed. Check details.")
    else:
        dpg.set_value("status_text", "All mods have been enabled and Temporarily Disabled Mods folder removed.")
    update_mod_count()

def update_mod_count():
    current_dir = os.getcwd()
    mod_count = 0
    for mod_dir in MOD_DIRECTORIES:
        full_dir = os.path.join(current_dir, mod_dir)
        if os.path.exists(full_dir):
            if mod_dir == "bin/x64/plugins/cyber_engine_tweaks/mods":
                mod_count += len([item for item in os.listdir(full_dir) if os.path.isdir(os.path.join(full_dir, item))])
            else:
                mod_count += len(os.listdir(full_dir))
    dpg.set_value("mod_count_text", f"Total Mods: {mod_count}")

def view_mod_list(sender, app_data, user_data):
    global mod_window_open, mods
    if mod_window_open:
        show_message("info", "Window Limit", "Only one View Mod List window can be open at a time.")
        return
    current_dir = os.getcwd()
    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
    mods.clear()
    for mod_dir in MOD_DIRECTORIES:
        full_dir = os.path.join(current_dir, mod_dir)
        temp_mod_dir = os.path.join(temp_disabled_path, mod_dir)
        if os.path.exists(full_dir):
            for item in os.listdir(full_dir):
                display_name = f"{item} ({mod_dir})"
                mods[display_name] = (mod_dir, item, os.path.join(full_dir, item))
        if os.path.exists(temp_mod_dir):
            for item in os.listdir(temp_mod_dir):
                display_name = f"{item} ({mod_dir})"
                mods[display_name] = (mod_dir, item, os.path.join(temp_mod_dir, item))

    with dpg.window(label="View Mod List", width=800, height=600, pos=[200, 100], no_resize=True, no_move=True, tag="mod_window", on_close=on_mod_window_close):
        with dpg.group(horizontal=True):
            with dpg.group():
                dpg.add_text("Enabled Mods", color=(255, 255, 255))
                enabled_items = [name for name, (_, _, path) in mods.items() if TEMP_DISABLED_DIR not in path]
                dpg.add_listbox(items=enabled_items, width=350, num_items=20, tag="enabled_listbox")
                dpg.add_button(label="Disable Selected", callback=disable_selected, width=150, user_data="enabled_listbox")
            with dpg.group():
                dpg.add_text("Disabled Mods", color=(255, 255, 255))
                disabled_items = [name for name, (_, _, path) in mods.items() if TEMP_DISABLED_DIR in path]
                dpg.add_listbox(items=disabled_items, width=350, num_items=20, tag="disabled_listbox")
                dpg.add_button(label="Enable Selected", callback=enable_selected, width=150, user_data="disabled_listbox")
    mod_window_open = True

def disable_selected(sender, app_data, user_data):
    if is_game_running():
        show_message("warning", "Game Running", "Cannot modify mods while Cyberpunk 2077 is running!")
        return
    selected = dpg.get_value(user_data)
    if not selected:
        return
    current_dir = os.getcwd()
    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
    errors = []
    for display_name in selected:
        mod_dir, mod_name, current_path = mods[display_name]
        dest_dir = os.path.join(temp_disabled_path, mod_dir)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, mod_name)
        try:
            shutil.move(current_path, dest)
            mods[display_name] = (mod_dir, mod_name, dest)
        except Exception as e:
            errors.append(f"Failed to disable {display_name}: {str(e)}")
    if errors:
        show_message("error", "Errors Occurred", "\n".join(errors))
    update_mod_list()
    update_mod_count()

def enable_selected(sender, app_data, user_data):
    if is_game_running():
        show_message("warning", "Game Running", "Cannot modify mods while Cyberpunk 2077 is running!")
        return
    selected = dpg.get_value(user_data)
    if not selected:
        return
    current_dir = os.getcwd()
    errors = []
    for display_name in selected:
        mod_dir, mod_name, current_path = mods[display_name]
        dest_dir = os.path.join(current_dir, mod_dir)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, mod_name)
        try:
            shutil.move(current_path, dest)
            mods[display_name] = (mod_dir, mod_name, dest)
        except Exception as e:
            errors.append(f"Failed to enable {display_name}: {str(e)}")
    if errors:
        show_message("error", "Errors Occurred", "\n".join(errors))
    else:
        cleanup_temp_disabled_folder(current_dir)
    update_mod_list()
    update_mod_count()

def update_mod_list():
    enabled_items = [name for name, (_, _, path) in mods.items() if TEMP_DISABLED_DIR not in path]
    disabled_items = [name for name, (_, _, path) in mods.items() if TEMP_DISABLED_DIR in path]
    dpg.configure_item("enabled_listbox", items=enabled_items)
    dpg.configure_item("disabled_listbox", items=disabled_items)

def on_mod_window_close(sender):
    global mod_window_open
    mod_window_open = False
    dpg.delete_item("mod_window")

def show_message(type, title, message):
    with dpg.window(label=title, modal=True, width=300, height=150, pos=[250, 325], no_close=True, tag=f"{type}_popup"):
        dpg.add_text(message, wrap=280)
        dpg.add_button(label="OK", width=100, pos=[100, 100], callback=lambda: dpg.delete_item(f"{type}_popup"))

def show_confirm(title, message):
    result = [False]
    def confirm_callback(sender, app_data, user_data):
        result[0] = True if user_data == "yes" else False
        dpg.delete_item("confirm_popup")
    with dpg.window(label=title, modal=True, width=300, height=150, pos=[250, 325], no_close=True, tag="confirm_popup"):
        dpg.add_text(message, wrap=280)
        with dpg.group(horizontal=True, pos=[50, 100]):
            dpg.add_button(label="Yes", width=80, callback=confirm_callback, user_data="yes")
            dpg.add_button(label="No", width=80, callback=confirm_callback, user_data="no")
    while dpg.does_item_exist("confirm_popup"):
        dpg.render_dearpygui_frame()
    return result[0]

def open_url(sender, app_data, user_data):
    webbrowser.open("https://www.nexusmods.com/cyberpunk2077/mods/20113")

def button_hover(sender, app_data, user_data):
    button_tag, is_hovered = user_data  # Unpack user_data: (button_tag, hover_state)
    colors = {
        "start_button": {"normal": "start_theme", "hover": "start_hover_theme"},
        "more_options_button": {"normal": "more_options_theme", "hover": "more_options_hover_theme"},
        "disable_button": {"normal": "disable_theme", "hover": "disable_hover_theme"},
        "enable_button": {"normal": "enable_theme", "hover": "enable_hover_theme"},
        "view_mod_list_button": {"normal": "view_mod_list_theme", "hover": "view_mod_list_hover_theme"},
        "nexus_link": {"normal": "nexus_link_theme", "hover": "nexus_link_hover_theme"}
    }
    theme = colors[button_tag]["hover"] if is_hovered else colors[button_tag]["normal"]
    dpg.bind_item_theme(button_tag, theme)

if not check_single_instance():
    dpg.create_context()
    dpg.create_viewport(title="Instance Check", width=300, height=150)
    with dpg.window(label="Instance Check", modal=True, no_close=True):
        dpg.add_text("Another instance of Cyberpunk 2077 Mod List Tool is already running.")
        dpg.add_button(label="OK", callback=lambda: dpg.stop_dearpygui())
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    sys.exit(0)

dpg.create_context()
dpg.create_viewport(title="Cyberpunk 2077 Mod List Tool", width=600, height=800, resizable=False)

# Load Background Image
image_data = dpg.load_image(IMAGE_PATH)
if image_data is not None:
    width, height, channels, data = image_data
    print(f"Loaded image: {width}x{height}, channels={channels}")
    with dpg.texture_registry():
        dpg.add_static_texture(width=width, height=height, default_value=data, tag="background_texture")
else:
    print(f"Warning: Failed to load image from '{IMAGE_PATH}'. Using blank background.")
    with dpg.texture_registry():
        dpg.add_static_texture(width=600, height=800, default_value=[0.0] * (600 * 800 * 4), tag="background_texture")

dpg.setup_dearpygui()

# Define Themes for Buttons (Normal and Hover States)
with dpg.theme(tag="start_theme"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (254, 254, 0, 255))  # Yellow
with dpg.theme(tag="start_hover_theme"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (212, 212, 0, 255))  # Darker Yellow

with dpg.theme(tag="more_options_theme"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 0, 255))  # Bright Yellow
with dpg.theme(tag="more_options_hover_theme"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (230, 230, 0, 255))  # Darker Bright Yellow

with dpg.theme(tag="disable_theme"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 0, 0, 255))    # Red
with dpg.theme(tag="disable_hover_theme"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (204, 0, 0, 255))    # Darker Red

with dpg.theme(tag="enable_theme"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 255, 0, 255))   # Green
with dpg.theme(tag="enable_hover_theme"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 204, 0, 255))   # Darker Green

with dpg.theme(tag="view_mod_list_theme"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 0, 255))  # Bright Yellow
with dpg.theme(tag="view_mod_list_hover_theme"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (230, 230, 0, 255))  # Darker Bright Yellow

with dpg.theme(tag="nexus_link_theme"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 165, 0, 255))  # Orange
with dpg.theme(tag="nexus_link_hover_theme"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (230, 140, 0, 255))  # Darker Orange

current_dir = os.getcwd()
game_path = os.path.join(current_dir, "bin", "x64", "Cyberpunk2077.exe")
initial_game_version = get_game_version(game_path)
initial_phantom_liberty_installed = is_phantom_liberty_installed(current_dir)
initial_log_errors = check_log_errors(current_dir)
initial_mod_count = sum(len([item for item in os.listdir(os.path.join(current_dir, mod_dir)) 
                            if os.path.isdir(os.path.join(current_dir, mod_dir, item))]) 
                        if "cyber_engine_tweaks/mods" in mod_dir else len(os.listdir(os.path.join(current_dir, mod_dir))) 
                        for mod_dir in MOD_DIRECTORIES if os.path.exists(os.path.join(current_dir, mod_dir)))

with dpg.window(label="Main Window", width=600, height=800, no_title_bar=True, no_resize=True, no_move=True, tag="main_window"):
    with dpg.drawlist(width=600, height=800):
        dpg.draw_image("background_texture", (0, 0), (600, 800))

    dpg.add_text("Click 'Start' to compile the list!", pos=[150, 400], color=(255, 255, 255), tag="status_text")
    dpg.add_button(label="Start", width=120, height=40, pos=[240, 335], callback=run_script, tag="start_button")
    dpg.bind_item_theme("start_button", "start_theme")

    dpg.add_checkbox(label="Include Logs", pos=[260, 450], default_value=True, tag="include_logs_checkbox")

    if os.path.exists(os.path.join(current_dir, "archive")):
        dpg.add_button(label="More Options", width=150, height=30, pos=[225, 500], callback=toggle_mod_buttons, tag="more_options_button")
        dpg.bind_item_theme("more_options_button", "more_options_theme")
    else:
        dpg.set_value("status_text", "Application not installed in the correct location!")

    dpg.add_button(label="Disable All Mods", width=180, height=30, pos=[120, 550], callback=disable_all_mods, tag="disable_button", show=False)
    dpg.bind_item_theme("disable_button", "disable_theme")

    dpg.add_button(label="Enable All Mods", width=180, height=30, pos=[330, 550], callback=enable_all_mods, tag="enable_button", show=False)
    dpg.bind_item_theme("enable_button", "enable_theme")

    dpg.add_button(label="View Mod List", width=180, height=30, pos=[210, 600], callback=view_mod_list, tag="view_mod_list_button", show=False)
    dpg.bind_item_theme("view_mod_list_button", "view_mod_list_theme")

    dpg.add_button(label="Nexus Mod Page", width=100, height=20, pos=[250, 770], callback=open_url, tag="nexus_link")
    dpg.bind_item_theme("nexus_link", "nexus_link_theme")

    dpg.add_text(f"Total Mods: {initial_mod_count}", pos=[10, 760], color=(255, 255, 255), tag="mod_count_text")
    dpg.add_text(f"Game Version: {initial_game_version}", pos=[10, 780], color=(255, 255, 255), tag="game_version_text")
    dpg.add_text(f"Log Errors Detected: {'Yes' if initial_log_errors else 'No'}", pos=[430, 760], color=(255, 255, 255), tag="log_errors_text")
    dpg.add_text(f"Phantom Liberty DLC: {'Yes' if initial_phantom_liberty_installed else 'No'}", pos=[430, 780], color=(255, 255, 255), tag="pl_dlc_text")
    if not os.path.exists(os.path.join(current_dir, "archive")):
        dpg.hide_item("mod_count_text")
        dpg.hide_item("game_version_text")
        dpg.hide_item("log_errors_text")
        dpg.hide_item("pl_dlc_text")

# Define Handler Registries for Each Button
with dpg.item_handler_registry(tag="start_handler"):
    dpg.add_item_hover_handler(callback=button_hover, user_data=("start_button", True))
    dpg.add_item_hover_handler(callback=button_hover, user_data=("start_button", False), show=False)
dpg.bind_item_handler_registry("start_button", "start_handler")

with dpg.item_handler_registry(tag="more_options_handler"):
    dpg.add_item_hover_handler(callback=button_hover, user_data=("more_options_button", True))
    dpg.add_item_hover_handler(callback=button_hover, user_data=("more_options_button", False), show=False)
dpg.bind_item_handler_registry("more_options_button", "more_options_handler")

with dpg.item_handler_registry(tag="disable_handler"):
    dpg.add_item_hover_handler(callback=button_hover, user_data=("disable_button", True))
    dpg.add_item_hover_handler(callback=button_hover, user_data=("disable_button", False), show=False)
dpg.bind_item_handler_registry("disable_button", "disable_handler")

with dpg.item_handler_registry(tag="enable_handler"):
    dpg.add_item_hover_handler(callback=button_hover, user_data=("enable_button", True))
    dpg.add_item_hover_handler(callback=button_hover, user_data=("enable_button", False), show=False)
dpg.bind_item_handler_registry("enable_button", "enable_handler")

with dpg.item_handler_registry(tag="view_mod_list_handler"):
    dpg.add_item_hover_handler(callback=button_hover, user_data=("view_mod_list_button", True))
    dpg.add_item_hover_handler(callback=button_hover, user_data=("view_mod_list_button", False), show=False)
dpg.bind_item_handler_registry("view_mod_list_button", "view_mod_list_handler")

with dpg.item_handler_registry(tag="nexus_link_handler"):
    dpg.add_item_hover_handler(callback=button_hover, user_data=("nexus_link", True))
    dpg.add_item_hover_handler(callback=button_hover, user_data=("nexus_link", False), show=False)
dpg.bind_item_handler_registry("nexus_link", "nexus_link_handler")

def on_closing():
    global mod_window_open
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
        except OSError:
            pass
    mod_window_open = False
    dpg.destroy_context()

dpg.show_viewport()
dpg.set_exit_callback(on_closing)
dpg.start_dearpygui()
