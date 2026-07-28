import json
import os
import random
import threading
import time
import tkinter as tk
import customtkinter as ctk
from pynput import keyboard
from pynput.mouse import Button, Controller

# Minecraft Dark Theme Palette
MC_DARK_BG = "#1A1A1A"        # Dark Bedrock
MC_GUI_BG = "#2B2B2B"         # Dark Stone Frame
MC_CARD_BG = "#1f1f1f"        # Item Slot Panel
MC_GREEN_TEXT = "#55FF55"     # Active HUD Text
MC_RED_TEXT = "#FF5555"       # Disabled Text
MC_YELLOW_TEXT = "#FFFF55"    # Gold Header
MC_FONT = ("Consolas", 12, "bold")

# Global UI Theme Settings
ctk.set_appearance_mode("Dark")

SETTINGS_FILE = "settings.json"
DEFAULT_SETTINGS = {
    "hold_min": 100,
    "hold_max": 200,
    "wait_min": 500,
    "wait_max": 1000
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                for k, v in DEFAULT_SETTINGS.items():
                    data.setdefault(k, v)
                return data
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Error saving settings: {e}")


class OverlayWindow(tk.Toplevel):
    """Floating Minecraft HUD Item Tooltip Overlay."""
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.90)
        self.config(bg="#2A0845")  # Minecraft purple tooltip glow border

        inner_frame = tk.Frame(self, bg="#100010", bd=2, relief="solid")
        inner_frame.pack(padx=3, pady=3, fill="both", expand=True)

        screen_w = self.winfo_screenwidth()
        width, height = 200, 48
        self.geometry(f"{width}x{height}+{screen_w - width - 20}+20")
        
        self.label = tk.Label(
            inner_frame, 
            text="[ ACTIVE - F6 ]", 
            font=("Consolas", 11, "bold"), 
            fg=MC_GREEN_TEXT, 
            bg="#AAAAAA"
        )
        self.label.pack(expand=True, fill="both", padx=10, pady=5)
        self.withdraw()

    def show(self):
        self.deiconify()

    def hide(self):
        self.withdraw()


class AutoClickerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Minecraft AutoClicker")
        self.geometry("420x420")
        self.resizable(False, False)
        self.configure(fg_color=MC_DARK_BG)

        # Core State & Settings
        self.settings = load_settings()
        self.mouse = Controller()
        self.is_running = False
        self.click_thread = None

        # Build UI & Center Window
        self.setup_ui()
        self.center_window(420, 420)

        # Custom Overlay
        self.overlay = OverlayWindow(self)

        # Global Hotkey Listener
        self.hotkey_listener = keyboard.Listener(on_press=self.on_key_press)
        self.hotkey_listener.start()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def center_window(self, width, height):
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w // 2) - (width // 2)
        y = (screen_h // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def setup_ui(self):
        # Main Outer Container Frame
        main_container = ctk.CTkFrame(
            self, 
            fg_color=MC_GUI_BG, 
            corner_radius=0, 
            border_width=3, 
            border_color="#444444"
        )
        main_container.pack(fill="both", expand=True, padx=12, pady=12)

        # Header Title
        title_label = ctk.CTkLabel(
            main_container, 
            text="MINECRAFT CLICKER", 
            font=("Consolas", 18, "bold"), 
            text_color=MC_YELLOW_TEXT
        )
        title_label.pack(pady=(15, 2))

        subtitle_label = ctk.CTkLabel(
            main_container, 
            text="-- Right-Click Automation --", 
            font=("Consolas", 11), 
            text_color="gray"
        )
        subtitle_label.pack(pady=(0, 15))

        # Config Frame (Delay Inputs)
        config_frame = ctk.CTkFrame(
            main_container, 
            fg_color=MC_CARD_BG, 
            corner_radius=0, 
            border_width=2, 
            border_color="#111111"
        )
        config_frame.pack(fill="x", padx=20, pady=5)

        # 1. Hold Time Inputs
        hold_label = ctk.CTkLabel(
            config_frame, 
            text="Click Hold Delay (ms):", 
            font=MC_FONT, 
            text_color="#FFFFFF"
        )
        hold_label.pack(anchor="w", padx=15, pady=(12, 2))

        hold_box = ctk.CTkFrame(config_frame, fg_color="transparent")
        hold_box.pack(fill="x", padx=15, pady=(0, 10))

        self.entry_hold_min = ctk.CTkEntry(
            hold_box, width=80, font=MC_FONT, 
            fg_color="#000000", text_color=MC_GREEN_TEXT, 
            border_width=2, border_color="#555555", corner_radius=0
        )
        self.entry_hold_min.insert(0, str(self.settings["hold_min"]))
        self.entry_hold_min.pack(side="left", padx=(0, 5))

        lbl_to1 = ctk.CTkLabel(hold_box, text="to", font=MC_FONT, text_color="gray")
        lbl_to1.pack(side="left", padx=8)

        self.entry_hold_max = ctk.CTkEntry(
            hold_box, width=80, font=MC_FONT, 
            fg_color="#000000", text_color=MC_GREEN_TEXT, 
            border_width=2, border_color="#555555", corner_radius=0
        )
        self.entry_hold_max.insert(0, str(self.settings["hold_max"]))
        self.entry_hold_max.pack(side="left")

        # 2. Wait Time Inputs
        wait_label = ctk.CTkLabel(
            config_frame, 
            text="Interval Between Clicks (ms):", 
            font=MC_FONT, 
            text_color="#FFFFFF"
        )
        wait_label.pack(anchor="w", padx=15, pady=(5, 2))

        wait_box = ctk.CTkFrame(config_frame, fg_color="transparent")
        wait_box.pack(fill="x", padx=15, pady=(0, 12))

        self.entry_wait_min = ctk.CTkEntry(
            wait_box, width=80, font=MC_FONT, 
            fg_color="#000000", text_color=MC_GREEN_TEXT, 
            border_width=2, border_color="#555555", corner_radius=0
        )
        self.entry_wait_min.insert(0, str(self.settings["wait_min"]))
        self.entry_wait_min.pack(side="left", padx=(0, 5))

        lbl_to2 = ctk.CTkLabel(wait_box, text="to", font=MC_FONT, text_color="gray")
        lbl_to2.pack(side="left", padx=8)

        self.entry_wait_max = ctk.CTkEntry(
            wait_box, width=80, font=MC_FONT, 
            fg_color="#000000", text_color=MC_GREEN_TEXT, 
            border_width=2, border_color="#555555", corner_radius=0
        )
        self.entry_wait_max.insert(0, str(self.settings["wait_max"]))
        self.entry_wait_max.pack(side="left")

        # Status Display Box
        status_card = ctk.CTkFrame(
            main_container, 
            fg_color="#000000", 
            corner_radius=0, 
            border_width=2, 
            border_color="#555555"
        )
        status_card.pack(fill="x", padx=20, pady=10)

        self.status_label = ctk.CTkLabel(
            status_card, 
            text="STATUS: OFF", 
            font=("Consolas", 14, "bold"), 
            text_color=MC_RED_TEXT
        )
        self.status_label.pack(pady=8)

        # Toggle Button
        self.toggle_btn = ctk.CTkButton(
            main_container, 
            text="START [F6]", 
            font=("Consolas", 14, "bold"), 
            fg_color="#555555", 
            hover_color="#777777", 
            text_color="#FFFFFF", 
            border_width=2, 
            border_color="#111111", 
            corner_radius=0, 
            height=40, 
            command=self.toggle_clicker
        )
        self.toggle_btn.pack(fill="x", padx=20, pady=(5, 15))

    def get_delays_from_ui(self):
        try:
            h_min = max(10, int(self.entry_hold_min.get()))
            h_max = max(h_min, int(self.entry_hold_max.get()))
            w_min = max(10, int(self.entry_wait_min.get()))
            w_max = max(w_min, int(self.entry_wait_max.get()))

            self.settings = {
                "hold_min": h_min,
                "hold_max": h_max,
                "wait_min": w_min,
                "wait_max": w_max
            }
            save_settings(self.settings)

            return (h_min / 1000.0, h_max / 1000.0, w_min / 1000.0, w_max / 1000.0)
        except ValueError:
            return (
                self.settings["hold_min"] / 1000.0,
                self.settings["hold_max"] / 1000.0,
                self.settings["wait_min"] / 1000.0,
                self.settings["wait_max"] / 1000.0
            )

    def on_key_press(self, key):
        if key == keyboard.Key.f6:
            self.after(0, self.toggle_clicker)

    def toggle_clicker(self):
        if self.is_running:
            self.stop_clicker()
        else:
            self.start_clicker()

    def start_clicker(self):
        self.is_running = True
        self.status_label.configure(text="STATUS: ACTIVE [F6]", text_color=MC_GREEN_TEXT)
        self.toggle_btn.configure(text="STOP [F6]", fg_color="#A83232", hover_color="#C73E3E")
        
        self.overlay.show()

        self.click_thread = threading.Thread(target=self.click_loop, daemon=True)
        self.click_thread.start()

    def stop_clicker(self):
        self.is_running = False
        
        # Absolute safety key/mouse release
        self.mouse.release(Button.right)
        
        self.status_label.configure(text="STATUS: OFF", text_color=MC_RED_TEXT)
        self.toggle_btn.configure(text="START [F6]", fg_color="#555555", hover_color="#777777")
        
        self.overlay.hide()

    def click_loop(self):
        while self.is_running:
            h_min_s, h_max_s, w_min_s, w_max_s = self.get_delays_from_ui()

            # Right Click Down
            self.mouse.press(Button.right)
            
            hold_time = random.uniform(h_min_s, h_max_s)
            time.sleep(hold_time)
            
            # Right Click Up
            self.mouse.release(Button.right)
            
            wait_time = random.uniform(w_min_s, w_max_s)
            
            elapsed = 0.0
            step = 0.02
            while self.is_running and elapsed < wait_time:
                time.sleep(step)
                elapsed += step

        # Final safety release
        self.mouse.release(Button.right)

    def on_close(self):
        self.stop_clicker()
        self.get_delays_from_ui()
        self.hotkey_listener.stop()
        self.destroy()


if __name__ == "__main__":
    app = AutoClickerApp()
    app.mainloop()