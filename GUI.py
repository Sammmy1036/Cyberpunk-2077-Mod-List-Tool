import customtkinter as ctk
import webbrowser

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

app = ctk.CTk()
app.geometry("1000x650")
app.title("Cyberpunk 2077 Mod Manager")

NEON_YELLOW = "#fcee09"
DARK_BG = "#111111"
NEON_GREEN = "#39ff14"
TEXT_COLOR = "#fcee09"
ACCENT_RED = "#ff2052"

def show_home():
    clear_main()
    ctk.CTkLabel(main, text="Generate Mod List", font=("Orbitron", 22, "bold"), text_color=TEXT_COLOR).pack(pady=20)
    ctk.CTkButton(main, text="Generate Mod List", fg_color=NEON_YELLOW, text_color="black").pack(pady=10)

    ctk.CTkLabel(main, text="Select Logs to Include:", text_color=TEXT_COLOR).pack(pady=(20, 5))
    logs = ["ArchiveXL", "Codeware", "Cyber Engine Tweaks", "Input Loader", "Mod Settings", "Red4Ext", "Redscript", "TweakXL", "All Logs"]
    for log in logs:
        ctk.CTkCheckBox(main, text=log, checkbox_height=18, checkbox_width=18, border_color=NEON_YELLOW, text_color=TEXT_COLOR).pack(anchor="w", padx=60)

def show_core_mods():
    clear_main()
    ctk.CTkLabel(main, text="Core Mods Status", font=("Orbitron", 22, "bold"), text_color=TEXT_COLOR).pack(pady=20)
    core_mods = ["ArchiveXL", "Codeware", "Cyber Engine Tweaks", "EquipmentEx", "RED4ext", "Redscript", "TweakXL"]
    for mod in core_mods:
        ctk.CTkLabel(main, text=f"{mod}: Installed", text_color=NEON_GREEN).pack(anchor="w", padx=60)

    ctk.CTkButton(main, text="Disable Core Mods Temporarily", fg_color=ACCENT_RED).pack(pady=10)
    ctk.CTkButton(main, text="Enable Core Mods Temporarily", fg_color=NEON_YELLOW, text_color="black").pack(pady=10)

def show_mods():
    clear_main()
    ctk.CTkLabel(main, text="Mod Management", font=("Orbitron", 22, "bold"), text_color=TEXT_COLOR).pack(pady=20)
    ctk.CTkButton(main, text="View Mod List", fg_color=NEON_YELLOW, text_color="black").pack(pady=5)
    ctk.CTkButton(main, text="Enable All Mods", fg_color=NEON_GREEN).pack(pady=5)
    ctk.CTkButton(main, text="Disable All Mods", fg_color=ACCENT_RED).pack(pady=5)
    ctk.CTkButton(main, text="Export / Backup Mod Preset", fg_color=NEON_YELLOW, text_color="black").pack(pady=5)

def show_settings():
    clear_main()
    ctk.CTkLabel(main, text="Settings", font=("Orbitron", 22, "bold"), text_color=TEXT_COLOR).pack(pady=20)
    ctk.CTkButton(main, text="Reselect Game Directory", fg_color=NEON_YELLOW, text_color="black").pack(pady=10)

def clear_main():
    for widget in main.winfo_children():
        widget.destroy()

sidebar = ctk.CTkFrame(app, width=200, corner_radius=10, fg_color=DARK_BG)
sidebar.pack(side="left", fill="y", padx=10, pady=10)

ctk.CTkLabel(sidebar, text="CYBERPUNK TOOL", font=("Orbitron", 16, "bold"), text_color=TEXT_COLOR).pack(pady=(10, 20))

ctk.CTkButton(sidebar, text="Home", command=show_home, fg_color=NEON_YELLOW, text_color="black").pack(pady=5)
ctk.CTkButton(sidebar, text="Core Mods", command=show_core_mods, fg_color=NEON_YELLOW, text_color="black").pack(pady=5)
ctk.CTkButton(sidebar, text="Mods", command=show_mods, fg_color=NEON_YELLOW, text_color="black").pack(pady=5)
ctk.CTkButton(sidebar, text="Settings", command=show_settings, fg_color=NEON_YELLOW, text_color="black").pack(pady=5)

ctk.CTkButton(sidebar, text="Launch Game", fg_color=NEON_GREEN).pack(side="bottom", pady=10)

main = ctk.CTkFrame(app, corner_radius=10, fg_color="#1a1a1a")
main.pack(expand=True, fill="both", padx=10, pady=10)

footer = ctk.CTkFrame(app, height=40, fg_color="#0e0e0e")
footer.pack(side="bottom", fill="x")

ctk.CTkLabel(footer, text="Total Mods: 108", text_color=TEXT_COLOR).pack(side="left", padx=10)
ctk.CTkLabel(footer, text="Game Version: 2.3.0.0", text_color=TEXT_COLOR).pack(side="left", padx=10)
ctk.CTkLabel(footer, text="Tool Version: 1.0.0.4", text_color=TEXT_COLOR).pack(side="left", padx=10)
ctk.CTkLabel(footer, text="Log Errors Detected: No", text_color=TEXT_COLOR).pack(side="left", padx=10)
ctk.CTkLabel(footer, text="Core Mods Installed: Yes", text_color=TEXT_COLOR).pack(side="left", padx=10)

link = ctk.CTkLabel(footer, text="Nexus Mod Page", text_color=NEON_YELLOW, cursor="hand2")
link.pack(side="right", padx=10)
link.bind("<Button-1>", lambda e: webbrowser.open_new("https://www.nexusmods.com/cyberpunk2077"))

# === Default View ===
show_home()
app.mainloop()
