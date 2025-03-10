import tkinter as tk
import os
import sys
import webbrowser
import datetime
from tkinter import messagebox, ttk, filedialog
import tempfile
import shutil
import time
import psutil
import zipfile

try:
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

# Default game version if retrieval fails
DEFAULT_GAME_VERSION = "Unknown"

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

# Define mod directories
MOD_DIRECTORIES = [
    "archive/pc/mod",
    "bin/x64/plugins/cyber_engine_tweaks/mods",
    "r6/scripts",
    "r6/tweaks"
]

# Temporary disabled mods folder
TEMP_DISABLED_DIR = "Temporarily Disabled Mods"

# Global flag to track if View Mod List window is open
mod_window_open = False

# Caching for game running check
_game_running_cache = None
_cache_timestamp = 0
CACHE_TIMEOUT = 2  # Cache for 2 seconds

def on_closing():
    """Clean up lock file on exit."""
    global mod_window_open
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
        except OSError:
            pass
    mod_window_open = False  # Reset flag when main window closes
    window.destroy()

def check_single_instance():
    """Check if another instance is running using a lock file."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, 'r') as f:
                pid = f.read().strip()
                if pid and os.path.exists(f"/proc/{pid}"):  # Unix-like check
                    return False
                elif pid and sys.platform == "win32":  # Windows check
                    try:
                        os.kill(int(pid), 0)  # Check if process exists
                        return False
                    except OSError:
                        pass  # Process doesn't exist, proceed to overwrite
        except Exception:
            pass  # If lock file is corrupted, proceed to overwrite
    with open(LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))
    return True

def get_game_version(file_path):
    """Retrieve the Product Version of the Cyberpunk 2077 executable."""
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

def is_phantom_liberty_installed(current_dir):
    """Check if Phantom Liberty DLC is installed by looking for specific files/folders."""
    ep1_folder = os.path.join(current_dir, "archive", "pc", "ep1")
    tweakdb_ep1 = os.path.join(current_dir, "r6", "cache", "tweakdb_ep1.bin")
    if os.path.exists(ep1_folder) and any(f.endswith('.archive') for f in os.listdir(ep1_folder)):
        return True
    if os.path.exists(tweakdb_ep1):
        return True
    return False

def is_game_running():
    """Check if Cyberpunk2077.exe is running using psutil with caching."""
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
    """Toggle visibility of mod management buttons with side-by-side Disable/Enable and spaced others."""
    if disable_button.winfo_viewable():
        disable_button.place_forget()
        enable_button.place_forget()
        view_mod_list_button.place_forget()
        export_mod_preset_button.place_forget()  # Hide export button
        more_options_button.config(text="More Options")
    else:
        # Place Disable All Mods and Enable All Mods side by side at the same y level
        disable_button.place(x=120, y=550)
        enable_button.place(x=330, y=550)

        # Define the vertical range and spacing for the remaining two buttons
        start_y = 600  # Starting y position after Disable/Enable
        end_y = 700    # Ending y position
        num_buttons = 2  # Number of remaining buttons (View Mod List and Export Mod Preset)
        spacing = (end_y - start_y) / (num_buttons + 1)  # Space between buttons

        # Place the remaining buttons with equal spacing, centered horizontally
        view_mod_list_button.place(relx=0.5, y=start_y + spacing * 1, anchor="center")
        export_mod_preset_button.place(relx=0.5, y=start_y + spacing * 2, anchor="center")
        more_options_button.config(text="Hide Options")

def disable_all_mods():
    """Disable all mods by moving them to a 'Temporarily Disabled Mods' folder."""
    if is_game_running():
        messagebox.showwarning("Game Running", "Cannot modify mods while Cyberpunk 2077 is running!")
        return

    if not messagebox.askyesno("Confirm Disable", "This will move all mods to the 'Temporarily Disabled Mods' folder. Proceed?"):
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
        status_label.config(text="All mods have been disabled.")
    update_mod_count_label()

def enable_all_mods():
    """Enable all mods by moving them back from 'Temporarily Disabled Mods' to original locations."""
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
    """Remove the Temporarily Disabled Mods folder and its empty subdirectories if no mods remain."""
    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)
    if not os.path.exists(temp_disabled_path):
        return

    # First pass: Attempt to remove empty subdirectories
    for root, dirs, files in os.walk(temp_disabled_path, topdown=False):
        if files:
            print(f"Found files in {root}: {files}")
            return  # If there are files, folder is not empty, stop cleanup
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                if not os.listdir(dir_path):  # Check if subdirectory is empty
                    os.rmdir(dir_path)
                    print(f"Removed empty subdirectory: {dir_path}")
            except OSError as e:
                print(f"Failed to remove subdirectory {dir_path}: {str(e)}")

    # Second pass: Check if the top-level folder is empty and remove it
    try:
        if os.path.exists(temp_disabled_path):
            if not os.listdir(temp_disabled_path):
                os.rmdir(temp_disabled_path)
                print(f"Removed empty {TEMP_DISABLED_DIR} folder.")
            else:
                print(f"{TEMP_DISABLED_DIR} folder still contains items: {os.listdir(temp_disabled_path)}")
    except OSError as e:
        print(f"Failed to remove {TEMP_DISABLED_DIR} folder: {str(e)}")

def view_mod_list():
    """Open a window to view and manage individual mods, allowing only one instance, with scrollbars."""
    global mod_window_open
    if mod_window_open:
        messagebox.showinfo("Window Limit", "Only one View Mod List window can be open at a time.")
        return

    current_dir = os.getcwd()
    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)

    # Create mod list window
    mod_window = tk.Toplevel(window)
    mod_window.title("View Mod List")
    mod_window.geometry("1100x800")
    mod_window.resizable(True, True)
    mod_window.configure(bg="#000000")
    mod_window.protocol("WM_DELETE_WINDOW", lambda: on_mod_window_close(mod_window))  # Set close handler

    # Center the window on the screen
    screen_width = mod_window.winfo_screenwidth()
    screen_height = mod_window.winfo_screenheight()
    window_width = 1100
    window_height = 800
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    mod_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # Set the same icon as the main window
    if os.path.exists(ICON_PATH):
        try:
            mod_window.iconbitmap(ICON_PATH)
        except tk.TclError as e:
            print(f"Warning: Failed to set icon for View Mod List window from '{ICON_PATH}': {e}. Using default icon.")
    else:
        print(f"Warning: Icon file '{ICON_PATH}' not found for View Mod List window. Using default icon.")

    # Mod data structure: {display_name: (original_dir, mod_name, current_path)}
    mods = {}
    for mod_dir in MOD_DIRECTORIES:
        full_dir = os.path.join(current_dir, mod_dir)
        temp_mod_dir = os.path.join(temp_disabled_path, mod_dir)
        # Enabled mods
        if os.path.exists(full_dir):
            for item in os.listdir(full_dir):
                display_name = f"{item} ({mod_dir})"
                mods[display_name] = (mod_dir, item, os.path.join(full_dir, item))
        # Disabled mods
        if os.path.exists(temp_mod_dir):
            for item in os.listdir(temp_mod_dir):
                display_name = f"{item} ({mod_dir})"
                mods[display_name] = (mod_dir, item, os.path.join(temp_mod_dir, item))

    # Frames for layout
    enabled_frame = tk.Frame(mod_window, bg="#000000")
    enabled_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)
    disabled_frame = tk.Frame(mod_window, bg="#000000")
    disabled_frame.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.BOTH, expand=True)

    # Enabled mods listbox with scrollbar
    tk.Label(enabled_frame, text="Enabled Mods", font=("Arial", 12), fg="white", bg="#000000").pack()
    
    # Create a frame to hold the listbox and scrollbar
    enabled_list_frame = tk.Frame(enabled_frame, bg="#000000")
    enabled_list_frame.pack(pady=5, fill=tk.BOTH, expand=True)

    # Add scrollbar
    enabled_scrollbar = tk.Scrollbar(enabled_list_frame, orient=tk.VERTICAL)
    enabled_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Create the listbox and configure it with the scrollbar (changed to tk.EXTENDED)
    enabled_listbox = tk.Listbox(enabled_list_frame, font=("Arial", 10), width=40, bg="#333333", fg="white", selectmode=tk.EXTENDED)
    enabled_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Bind the scrollbar to the listbox
    enabled_listbox.config(yscrollcommand=enabled_scrollbar.set)
    enabled_scrollbar.config(command=enabled_listbox.yview)

    # Disabled mods listbox with scrollbar
    tk.Label(disabled_frame, text="Disabled Mods", font=("Arial", 12), fg="white", bg="#000000").pack()
    
    # Create a frame to hold the listbox and scrollbar
    disabled_list_frame = tk.Frame(disabled_frame, bg="#000000")
    disabled_list_frame.pack(pady=5, fill=tk.BOTH, expand=True)

    # Add scrollbar
    disabled_scrollbar = tk.Scrollbar(disabled_list_frame, orient=tk.VERTICAL)
    disabled_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Create the listbox and configure it with the scrollbar (changed to tk.EXTENDED)
    disabled_listbox = tk.Listbox(disabled_list_frame, font=("Arial", 10), width=40, bg="#333333", fg="white", selectmode=tk.EXTENDED)
    disabled_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Bind the scrollbar to the listbox
    disabled_listbox.config(yscrollcommand=disabled_scrollbar.set)
    disabled_scrollbar.config(command=disabled_listbox.yview)

    # Populate listboxes
    for display_name, (mod_dir, mod_name, current_path) in sorted(mods.items()):
        if TEMP_DISABLED_DIR in current_path:
            disabled_listbox.insert(tk.END, display_name)
        else:
            enabled_listbox.insert(tk.END, display_name)

    def disable_selected():
        """Move selected mods from enabled to disabled."""
        if is_game_running():
            messagebox.showwarning("Game Running", "Cannot modify mods while Cyberpunk 2077 is running!")
            return

        selected = enabled_listbox.curselection()
        if not selected:
            return
        errors = []
        for idx in selected[::-1]:  # Reverse to avoid index shifting
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

    def enable_selected():
        """Move selected mods from disabled to enabled and remove empty Temporarily Disabled Mods folder."""
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

        # Repopulate both listboxes to reflect the updated state
        enabled_listbox.delete(0, tk.END)
        disabled_listbox.delete(0, tk.END)
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
        for display_name, (mod_dir, mod_name, current_path) in sorted(mods.items()):
            if TEMP_DISABLED_DIR in current_path:
                disabled_listbox.insert(tk.END, display_name)
            else:
                enabled_listbox.insert(tk.END, display_name)

        update_mod_count_label()

    # Place Disable Selected button under Enabled Mods
    disable_selected_button = tk.Button(enabled_frame, text="Disable Selected", command=disable_selected, font=("Arial", 12), bg="#FF0000", fg="white")
    disable_selected_button.pack(pady=5)

    # Place Enable Selected button under Disabled Mods
    enable_selected_button = tk.Button(disabled_frame, text="Enable Selected", command=enable_selected, font=("Arial", 12), bg="#00FF00", fg="black")
    enable_selected_button.pack(pady=5)

    # Add hover effects to View Mod List window buttons
    disable_selected_button.bind("<Enter>", lambda e: disable_selected_button.config(bg="#CC0000", fg="white"))  # Darker red
    disable_selected_button.bind("<Leave>", lambda e: disable_selected_button.config(bg="#FF0000", fg="white"))
    enable_selected_button.bind("<Enter>", lambda e: enable_selected_button.config(bg="#00CC00", fg="black"))  # Darker green
    enable_selected_button.bind("<Leave>", lambda e: enable_selected_button.config(bg="#00FF00", fg="black"))

    mod_window_open = True  # Set flag when window is opened

def on_mod_window_close(mod_window):
    """Handle closing of the View Mod List window."""
    global mod_window_open
    mod_window_open = False
    mod_window.destroy()

def update_mod_count_label():
    """Update the mod count label based on current enabled mods, counting folders for CET mods."""
    current_dir = os.getcwd()
    mod_count = 0
    for mod_dir in MOD_DIRECTORIES:
        full_dir = os.path.join(current_dir, mod_dir)
        if os.path.exists(full_dir):
            if mod_dir == "bin/x64/plugins/cyber_engine_tweaks/mods":
                # Count only folders for CET mods
                mod_count += len([item for item in os.listdir(full_dir) if os.path.isdir(os.path.join(full_dir, item))])
            else:
                # Count all items (files and folders) for other directories
                mod_count += len(os.listdir(full_dir))
    mod_count_label.config(text=f"Total Mods: {mod_count}")

def extract_log_errors(log_path):
    """Extract lines containing potential errors from a log file."""
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
    """Check for errors in log files and return True if errors are found."""
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

def export_mods():
    """Export selected mod folders to a ZIP file with a progress bar."""
    if is_game_running():
        messagebox.showwarning("Game Running", "Cannot export mods while Cyberpunk 2077 is running!")
        return

    current_dir = os.getcwd()

    # Create selection window for mod folders
    selection_window = tk.Toplevel(window)
    selection_window.title("Select Mod Folders to Export")
    selection_window.geometry("300x200")
    selection_window.resizable(False, False)
    selection_window.configure(bg="#000000")
    selection_window.transient(window)  # Keep it on top of the main window
    selection_window.grab_set()  # Make it modal

    # Set the same icon as the main window for the selection window
    if os.path.exists(ICON_PATH):
        try:
            selection_window.iconbitmap(ICON_PATH)
        except tk.TclError as e:
            print(f"Warning: Failed to set icon for Selection window from '{ICON_PATH}': {e}. Using default icon.")
    else:
        print(f"Warning: Icon file '{ICON_PATH}' not found for Selection window. Using default icon.")

    # Center the selection window
    screen_width = selection_window.winfo_screenwidth()
    screen_height = selection_window.winfo_screenheight()
    window_width = 300
    window_height = 200
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    selection_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # Variables to track selected folders
    folder_vars = {mod_dir: tk.BooleanVar(value=True) for mod_dir in MOD_DIRECTORIES}

    # Checkboxes for each mod folder
    for i, mod_dir in enumerate(MOD_DIRECTORIES):
        full_dir = os.path.join(current_dir, mod_dir)
        enabled = os.path.exists(full_dir)
        cb = tk.Checkbutton(selection_window, text=mod_dir, variable=folder_vars[mod_dir],
                            font=("Arial", 10), bg="#000000", fg="white", selectcolor="#333333",
                            activebackground="#000000", activeforeground="white", state="normal" if enabled else "disabled")
        cb.pack(pady=5, anchor="w", padx=10)

    # Confirm button
    def on_confirm():
        selected_folders = [mod_dir for mod_dir, var in folder_vars.items() if var.get() and os.path.exists(os.path.join(current_dir, mod_dir))]
        if not selected_folders:
            messagebox.showwarning("No Selection", "Please select at least one mod folder to export.")
            return
        selection_window.destroy()
        _export_with_progress(selected_folders)

    confirm_button = tk.Button(selection_window, text="Confirm", command=on_confirm, font=("Arial", 12),
                               bg="#00FF00", fg="black")
    confirm_button.pack(pady=10)

    # Add hover effects to confirm button
    confirm_button.bind("<Enter>", lambda e: confirm_button.config(bg="#00CC00", fg="black"))  # Darker green
    confirm_button.bind("<Leave>", lambda e: confirm_button.config(bg="#00FF00", fg="black"))

    selection_window.wait_window()  # Wait for the selection window to close

def _export_with_progress(selected_folders):
    """Helper function to handle the export process with progress bar."""
    current_dir = os.getcwd()
    # Prompt user for save location and filename
    default_filename = f"Mod_Preset_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    save_path = filedialog.asksaveasfilename(
        defaultextension=".zip",
        filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
        initialfile=default_filename,
        title="Save Mod Preset As"
    )
    if not save_path:
        return  # User cancelled the dialog

    # Create progress window
    progress_window = tk.Toplevel(window)
    progress_window.title("Exporting Mod Preset")
    progress_window.geometry("300x100")
    progress_window.resizable(False, False)
    progress_window.configure(bg="#000000")
    progress_window.transient(window)  # Keep it on top of the main window
    progress_window.grab_set()  # Make it modal

    # Set the same icon as the main window for the progress window
    if os.path.exists(ICON_PATH):
        try:
            progress_window.iconbitmap(ICON_PATH)
        except tk.TclError as e:
            print(f"Warning: Failed to set icon for Progress window from '{ICON_PATH}': {e}. Using default icon.")
    else:
        print(f"Warning: Icon file '{ICON_PATH}' not found for Progress window. Using default icon.")

    # Center the progress window
    screen_width = progress_window.winfo_screenwidth()
    screen_height = progress_window.winfo_screenheight()
    window_width = 300
    window_height = 100
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    progress_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # Progress bar and label
    tk.Label(progress_window, text="Exporting mod preset...", fg="white", bg="#000000", font=("Arial", 10)).pack(pady=10)
    progress_bar = ttk.Progressbar(progress_window, length=250, mode="determinate")
    progress_bar.pack(pady=10)
    status_label_progress = tk.Label(progress_window, text="", fg="white", bg="#000000", font=("Arial", 8))
    status_label_progress.pack()

    # Calculate total number of files
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
        include_logs_checkbox.place_forget()  # Hide checkbox if not in correct location
        return False

    # Show the checkbox if in the correct location
    include_logs_checkbox.place(relx=0.5, y=450, anchor="center")

    now = datetime.datetime.now()
    archivemods = os.path.join("archive", "pc", "mod")
    cetmods = os.path.join("bin", "x64", "plugins", "cyber_engine_tweaks", "mods")
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
            if path == path2:  # CET mods directory
                mod_count += len([item for item in os.listdir(path) if os.path.isdir(os.path.join(path, item))])
            else:
                mod_count += len(os.listdir(path))

    temp_disabled_path = os.path.join(current_dir, TEMP_DISABLED_DIR)

    # Extract errors from log files
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

    with open('Cyberpunk 2077 Mod List.txt', 'w') as file:
        # Header
        file.write(f"Cyberpunk 2077 Mod List Tool by Sammmy1036\n")
        file.write(f"Tool Version: 1.0.0.3\n")
        file.write(f"Nexus Mod Page https://www.nexusmods.com/cyberpunk2077/mods/20113\n")
        file.write(f"List created on {now.strftime('%B %d, %Y at %I:%M:%S %p')}\n")
        file.write(f"Game Version: {game_version}\n")
        file.write(f"Phantom Liberty DLC Installed: {'Yes' if phantom_liberty_installed else 'No'}\n")
        file.write(f"Total Mods Installed: {mod_count}\n")
        file.write("-" * 120 + "\n")

        # Potential Errors Section (only if errors are detected)
        if log_errors:
            file.write("\nPotential Errors to Review\n")
            file.write("=" * 120 + "\n")
            for log_name, errors in log_errors.items():
                file.write(f"\n{log_name} Errors:\n")
                file.write("-" * 120 + "\n")
                for error in errors:
                    file.write(f"{error}\n")
            file.write("=" * 120 + "\n")

        # Mod List Section
        def write_items_from_dir(directory, folder_name, temp_dir):
            if os.path.exists(directory):
                file.write(f"\nMods located in {folder_name}:\n")
                file.write("-" * 120 + "\n")
                if folder_name == "bin/x64/plugins/cyber_engine_tweaks/mods":
                    # List only folders for CET mods
                    for item in os.listdir(directory):
                        full_path = os.path.join(directory, item)
                        if os.path.isdir(full_path):
                            file.write(f"{item}\n")
                else:
                    for item in os.listdir(directory):
                        full_path = os.path.join(directory, item)
                        if os.path.isfile(full_path) or os.path.isdir(full_path):
                            file.write(f"{item}\n")
            else:
                file.write(f"\nError: The subfolder(s) {folder_name} were not found in the current location! Please ensure that the Cyberpunk 2077 Mod List Tool is installed in your Cyberpunk 2077 Directory!\n")
            disabled_dir = os.path.join(temp_dir, folder_name)
            if os.path.exists(disabled_dir):
                file.write(f"\nDisabled mods in {TEMP_DISABLED_DIR}/{folder_name}:\n")
                file.write("-" * 120 + "\n")
                if folder_name == "bin/x64/plugins/cyber_engine_tweaks/mods":
                    # List only folders for CET mods in disabled section
                    for item in os.listdir(disabled_dir):
                        full_path = os.path.join(disabled_dir, item)
                        if os.path.isdir(full_path):
                            file.write(f"{item}\n")
                else:
                    # List all items for other directories
                    for item in os.listdir(disabled_dir):
                        file.write(f"{item}\n")

        write_items_from_dir(path1, archivemods, temp_disabled_path)
        write_items_from_dir(path2, cetmods, temp_disabled_path)
        write_items_from_dir(path3, r6scripts, temp_disabled_path)
        write_items_from_dir(path4, r6tweaks, temp_disabled_path)

        # Full Logs Section (if included)
        if include_logs_var.get():
            for log_name, log_path in log_files.items():
                if os.path.exists(log_path):
                    file.write(f"\n{log_name} Log:\n")
                    file.write("-" * 120 + "\n")
                    try:
                        with open(log_path, 'r', encoding='utf-8') as input_file:
                            file.write(input_file.read())
                            file.write("\n")
                    except (OSError, UnicodeDecodeError) as e:
                        file.write(f"Error reading {log_name}.log: {str(e)}\n")
                else:
                    file.write(f"\n{log_name} Log:")
                    file.write("\n" + "-" * 120)
                    file.write(f"\nThe {log_name} log could not be found! Log not provided!\n")

    # Update labels only if in correct location
    mod_count_label.place(x=10, y=760)
    game_version_label.place(x=10, y=780)
    log_errors_label.place(x=430, y=760)
    pl_dlc_label.place(x=430, y=780)
    mod_count_label.config(text=f"Total Mods: {mod_count}")
    game_version_label.config(text=f"Game Version: {game_version}")
    log_errors_label.config(text=f"Log Errors Detected: {'Yes' if log_errors else 'No'}")
    pl_dlc_label.config(text=f"Phantom Liberty DLC: {'Yes' if phantom_liberty_installed else 'No'}")
    status_label.config(text="Success! Check Cyberpunk 2077 Mod List.txt")
    return bool(log_errors)

def open_url(event):
    webbrowser.open("https://www.nexusmods.com/cyberpunk2077/mods/20113")

if not check_single_instance():
    messagebox.showinfo("Instance Check", "Another instance of Cyberpunk 2077 Mod List Tool is already running.")
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
else:
    print(f"Warning: Icon file '{ICON_PATH}' not found. Using default icon.")

current_dir = os.getcwd()
game_path = os.path.join(current_dir, "bin", "x64", "Cyberpunk2077.exe")
initial_game_version = get_game_version(game_path)
initial_phantom_liberty_installed = is_phantom_liberty_installed(current_dir)

# Check for log errors on startup
initial_log_errors = check_log_errors(current_dir)

initial_mod_count = 0
for mod_dir in MOD_DIRECTORIES:
    full_dir = os.path.join(current_dir, mod_dir)
    if os.path.exists(full_dir):
        if mod_dir == "bin/x64/plugins/cyber_engine_tweaks/mods":
            initial_mod_count += len([item for item in os.listdir(full_dir) if os.path.isdir(os.path.join(full_dir, item))])
        else:
            initial_mod_count += len(os.listdir(full_dir))

try:
    image = tk.PhotoImage(file=IMAGE_PATH)
    orig_width = image.width()
    orig_height = image.height()
    print(f"Original image size: {orig_width}x{orig_height}")
    if orig_width != 600 or orig_height != 800:
        image = image.zoom(600 // orig_width, 800 // orig_height)
    print(f"Resized image size: {image.width()}x{image.height()}")
    image_label = tk.Label(window, image=image)
    image_label.place(x=0, y=0, width=600, height=800)
    image_label.image = image
except tk.TclError as e:
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
# Placement is handled dynamically below

more_options_button = tk.Button(window, text="More Options", command=toggle_mod_buttons, font=("Arial", 12), width=12,
                                bg="#FFFF00", fg="black")
if os.path.exists(os.path.join(current_dir, "archive")):
    more_options_button.place(relx=0.5, y=500, anchor="center")
else:
    status_label.config(text="Please place application in the Cyberpunk 2077 Directory!")

disable_button = tk.Button(window, text="Disable All Mods", command=disable_all_mods, font=("Arial", 12), width=15,
                           bg="#FF0000", fg="white")
# Initially not placed

enable_button = tk.Button(window, text="Enable All Mods", command=enable_all_mods, font=("Arial", 12), width=15,
                          bg="#00FF00", fg="black")
# Initially not placed

view_mod_list_button = tk.Button(window, text="View Mod List", command=view_mod_list, font=("Arial", 12), width=15,
                                 bg="#FFFF00", fg="black")
# Initially not placed

export_mod_preset_button = tk.Button(window, text="Export Mod Preset", command=export_mods, font=("Arial", 12), width=15,
                                     bg="#00FFFF", fg="black")  # Cyan color for distinction
# Initially not placed

# Add hover effects to main window buttons
start_button.bind("<Enter>", lambda e: start_button.config(bg="#D4D400", fg="black"))  # Lighter yellow
start_button.bind("<Leave>", lambda e: start_button.config(bg="#FEFE00", fg="black"))
include_logs_checkbox.bind("<Enter>", lambda e: include_logs_checkbox.config(bg="#1A1A1A", fg="white"))  # Darker gray
include_logs_checkbox.bind("<Leave>", lambda e: include_logs_checkbox.config(bg="#000000", fg="white"))
more_options_button.bind("<Enter>", lambda e: more_options_button.config(bg="#E6E600", fg="black"))  # Lighter yellow
more_options_button.bind("<Leave>", lambda e: more_options_button.config(bg="#FFFF00", fg="black"))
disable_button.bind("<Enter>", lambda e: disable_button.config(bg="#CC0000", fg="white"))  # Darker red
disable_button.bind("<Leave>", lambda e: disable_button.config(bg="#FF0000", fg="white"))
enable_button.bind("<Enter>", lambda e: enable_button.config(bg="#00CC00", fg="black"))  # Darker green
enable_button.bind("<Leave>", lambda e: enable_button.config(bg="#00FF00", fg="black"))
view_mod_list_button.bind("<Enter>", lambda e: view_mod_list_button.config(bg="#E6E600", fg="black"))  # Lighter yellow
view_mod_list_button.bind("<Leave>", lambda e: view_mod_list_button.config(bg="#FFFF00", fg="black"))
export_mod_preset_button.bind("<Enter>", lambda e: export_mod_preset_button.config(bg="#00CCCC", fg="black"))  # Darker cyan
export_mod_preset_button.bind("<Leave>", lambda e: export_mod_preset_button.config(bg="#00FFFF", fg="black"))

link_canvas = tk.Canvas(window, width=100, height=20, highlightthickness=0, bg="#000000", bd=0)
link_canvas.place(relx=0.5, y=770, anchor="center")
link_canvas.config(cursor="hand2")
link_canvas.create_text(50, 10, text="Nexus Mod Page", font=("Arial", 10, "underline"), fill="orange")
link_canvas.bind("<Button-1>", open_url)

version_canvas = tk.Canvas(window, width=100, height=20, highlightthickness=0, bg="#000000", bd=0)
version_canvas.place(relx=0.5, y=790, anchor="center")
version_canvas.create_text(50, 10, text="Version 1.0.0.3", font=("Arial", 10), fill="white")

# Create labels but don't place them initially
mod_count_label = tk.Label(window, text="Total Mods: 0", font=("Arial", 10), fg="white", bg="#000000")
game_version_label = tk.Label(window, text="Game Version: Unknown", font=("Arial", 10), fg="white", bg="#000000")
log_errors_label = tk.Label(window, text="Log Errors Detected: No", font=("Arial", 10), fg="white", bg="#000000")
pl_dlc_label = tk.Label(window, text="Phantom Liberty DLC: No", font=("Arial", 10), fg="white", bg="#000000")

# Place labels and checkbox only if in correct location on startup
if os.path.exists(os.path.join(current_dir, "archive")):
    mod_count_label.place(x=10, y=760)
    game_version_label.place(x=10, y=780)
    log_errors_label.place(x=430, y=760)
    pl_dlc_label.place(x=430, y=780)
    include_logs_checkbox.place(relx=0.5, y=450, anchor="center")  # Place checkbox here
    mod_count_label.config(text=f"Total Mods: {initial_mod_count}")
    game_version_label.config(text=f"Game Version: {initial_game_version}")
    log_errors_label.config(text=f"Log Errors Detected: {'Yes' if initial_log_errors else 'No'}")
    pl_dlc_label.config(text=f"Phantom Liberty DLC: {'Yes' if initial_phantom_liberty_installed else 'No'}")
else:
    status_label.config(text="Please place application in the Cyberpunk 2077 Directory!")

image_label.lower()

window.protocol("WM_DELETE_WINDOW", on_closing)

window.mainloop()
