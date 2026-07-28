import json
import os
import random
import threading
import time
import tkinter as tk
import customtkinter as ctk
from pynput import keyboard
from pynput.mouse import Button, Controller

# File Paths
SETTINGS_FILE = "settings.json"
THEMES_FILE = "themes.json"

DEFAULT_THEMES = {
    "Minecraft": {
        "bg_main": "#1A100A",
        "container_bg": "#2C2018",
        "card_bg": "#1F1610",
        "slot_bg": "#100B07",
        "btn_bg": "#8B8B8B",
        "btn_hover": "#A0A0A0",
        "btn_border": "#383838",
        "border_color": "#55FF55",
        "title_color": "#FFFF55",
        "text_color": "#FFFFFF",
        "muted_text": "#AAAAAA",
        "active_color": "#55FF55",
        "off_color": "#FF5555",
        "font_family": "Consolas",
        "border_width": 3,
        "corner_radius": 0
    },
    
}

DEFAULT_SETTINGS = {
    "current_theme": "Minecraft",
    "hold_min": 100,
    "hold_max": 200,
    "wait_min": 500,
    "wait_max": 1000,
    "win_x": None,
    "win_y": None,
    "overlay_x": None,
    "overlay_y": None
}

def load_themes():
    if not os.path.exists(THEMES_FILE):
        try:
            with open(THEMES_FILE, "w") as f:
                json.dump(DEFAULT_THEMES, f, indent=4)
        except Exception as e:
            print(f"Error creating default themes file: {e}")
        return DEFAULT_THEMES.copy()
    
    try:
        with open(THEMES_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading themes.json: {e}")
        return DEFAULT_THEMES.copy()

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
    """Floating HUD Overlay styled dynamically according to JSON theme."""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 1.0)

        self.width, self.height = 210, 48
        
        saved_x = parent.settings.get("overlay_x")
        saved_y = parent.settings.get("overlay_y")
        
        if saved_x is not None and saved_y is not None:
            self.geometry(f"{self.width}x{self.height}+{saved_x}+{saved_y}")
        else:
            screen_w = self.winfo_screenwidth()
            self.geometry(f"{self.width}x{self.height}+{screen_w - self.width - 20}+20")

        self.outer_frame = tk.Frame(self)
        self.outer_frame.pack(fill="both", expand=True)

        self.inner_frame = tk.Frame(self.outer_frame)
        self.inner_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.label = tk.Label(
            self.inner_frame, 
            text="[ ACTIVE - F6 ]"
        )
        self.label.pack(expand=True, fill="both", padx=5, pady=2)

        self.apply_theme()
        self.withdraw()

    def apply_theme(self):
        theme = self.parent.theme
        self.config(bg=theme["border_color"])
        self.outer_frame.config(bg=theme["border_color"])
        self.inner_frame.config(bg=theme["btn_bg"])
        self.label.config(
            fg=theme["active_color"],
            bg=theme["btn_bg"],
            font=(theme["font_family"], 11, "bold")
        )

    def show(self):
        self.deiconify()

    def hide(self):
        self.withdraw()


class AutoClickerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Dynamic AutoClicker")
        self.geometry("440x500")
        self.resizable(False, False)

        # Load Themes and Settings
        self.themes = load_themes()
        self.settings = load_settings()
        self.current_theme_name = self.settings.get("current_theme", "Minecraft")
        
        if self.current_theme_name not in self.themes:
            self.current_theme_name = list(self.themes.keys())[0]

        self.theme = self.themes[self.current_theme_name]

        # Core State
        self.mouse = Controller()
        self.is_running = False
        self.click_thread = None

        # Build UI & Position Window
        self.setup_ui()
        self.setup_window_position(440, 500)

        # Custom Overlay
        self.overlay = OverlayWindow(self)

        # Global Hotkey Listener
        self.hotkey_listener = keyboard.Listener(on_press=self.on_key_press)
        self.hotkey_listener.start()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_window_position(self, width, height):
        self.update_idletasks()
        win_x = self.settings.get("win_x")
        win_y = self.settings.get("win_y")

        if win_x is not None and win_y is not None:
            self.geometry(f"{width}x{height}+{win_x}+{win_y}")
        else:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            x = (screen_w // 2) - (width // 2)
            y = (screen_h // 2) - (height // 2)
            self.geometry(f"{width}x{height}+{x}+{y}")

    def setup_ui(self):
        t = self.theme
        font_main = (t["font_family"], 12, "bold")
        font_title = (t["font_family"], 18, "bold")

        self.configure(fg_color=t["bg_main"])

        # Main Outer Border Container
        self.outer_border = ctk.CTkFrame(
            self, 
            fg_color=t["bg_main"], 
            corner_radius=t["corner_radius"], 
            border_width=t["border_width"], 
            border_color=t["border_color"]
        )
        self.outer_border.pack(fill="both", expand=True, padx=8, pady=8)

        # Main Content GUI Frame
        self.gui_frame = ctk.CTkFrame(
            self.outer_border, 
            fg_color=t["container_bg"], 
            corner_radius=t["corner_radius"], 
            border_width=t["border_width"], 
            border_color=t["slot_bg"]
        )
        self.gui_frame.pack(fill="both", expand=True, padx=4, pady=4)

        # Theme Switcher Selector Dropdown
        theme_selector_box = ctk.CTkFrame(self.gui_frame, fg_color="transparent")
        theme_selector_box.pack(fill="x", padx=20, pady=(10, 0))

        self.lbl_theme = ctk.CTkLabel(
            theme_selector_box, 
            text="Theme:", 
            font=font_main, 
            text_color=t["text_color"]
        )
        self.lbl_theme.pack(side="left")

        self.theme_dropdown = ctk.CTkOptionMenu(
            theme_selector_box,
            values=list(self.themes.keys()),
            command=self.change_theme,
            font=font_main,
            fg_color=t["btn_bg"],
            button_color=t["btn_border"],
            button_hover_color=t["btn_hover"],
            text_color=t["text_color"],
            dropdown_text_color=t["text_color"],
            dropdown_fg_color=t["container_bg"],
            corner_radius=t["corner_radius"]
        )
        self.theme_dropdown.set(self.current_theme_name)
        self.theme_dropdown.pack(side="right")

        # Header Title
        self.title_label = ctk.CTkLabel(
            self.gui_frame, 
            text="AUTO CLICKER", 
            font=font_title, 
            text_color=t["title_color"]
        )
        self.title_label.pack(pady=(10, 2))

        self.subtitle_label = ctk.CTkLabel(
            self.gui_frame, 
            text="-- Right-Click Automation --", 
            font=(t["font_family"], 11, "bold"), 
            text_color=t["muted_text"]
        )
        self.subtitle_label.pack(pady=(0, 10))

        # Config Panel
        self.config_frame = ctk.CTkFrame(
            self.gui_frame, 
            fg_color=t["card_bg"], 
            corner_radius=t["corner_radius"], 
            border_width=t["border_width"], 
            border_color=t["slot_bg"]
        )
        self.config_frame.pack(fill="x", padx=20, pady=5)

        # Hold Delay Row
        self.hold_label = ctk.CTkLabel(
            self.config_frame, 
            text="Click Hold Delay (ms):", 
            font=font_main, 
            text_color=t["text_color"]
        )
        self.hold_label.pack(anchor="w", padx=15, pady=(10, 2))

        hold_box = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        hold_box.pack(fill="x", padx=15, pady=(0, 10))

        self.entry_hold_min = ctk.CTkEntry(
            hold_box, width=85, font=font_main, 
            fg_color=t["slot_bg"], text_color=t["active_color"], 
            border_width=1, border_color=t["btn_border"], corner_radius=t["corner_radius"]
        )
        self.entry_hold_min.insert(0, str(self.settings["hold_min"]))
        self.entry_hold_min.pack(side="left", padx=(0, 5))

        self.lbl_to1 = ctk.CTkLabel(hold_box, text="to", font=font_main, text_color=t["muted_text"])
        self.lbl_to1.pack(side="left", padx=8)

        self.entry_hold_max = ctk.CTkEntry(
            hold_box, width=85, font=font_main, 
            fg_color=t["slot_bg"], text_color=t["active_color"], 
            border_width=1, border_color=t["btn_border"], corner_radius=t["corner_radius"]
        )
        self.entry_hold_max.insert(0, str(self.settings["hold_max"]))
        self.entry_hold_max.pack(side="left")

        # Wait Delay Row
        self.wait_label = ctk.CTkLabel(
            self.config_frame, 
            text="Interval Between Clicks (ms):", 
            font=font_main, 
            text_color=t["text_color"]
        )
        self.wait_label.pack(anchor="w", padx=15, pady=(5, 2))

        wait_box = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        wait_box.pack(fill="x", padx=15, pady=(0, 12))

        self.entry_wait_min = ctk.CTkEntry(
            wait_box, width=85, font=font_main, 
            fg_color=t["slot_bg"], text_color=t["active_color"], 
            border_width=1, border_color=t["btn_border"], corner_radius=t["corner_radius"]
        )
        self.entry_wait_min.insert(0, str(self.settings["wait_min"]))
        self.entry_wait_min.pack(side="left", padx=(0, 5))

        self.lbl_to2 = ctk.CTkLabel(wait_box, text="to", font=font_main, text_color=t["muted_text"])
        self.lbl_to2.pack(side="left", padx=8)

        self.entry_wait_max = ctk.CTkEntry(
            wait_box, width=85, font=font_main, 
            fg_color=t["slot_bg"], text_color=t["active_color"], 
            border_width=1, border_color=t["btn_border"], corner_radius=t["corner_radius"]
        )
        self.entry_wait_max.insert(0, str(self.settings["wait_max"]))
        self.entry_wait_max.pack(side="left")

        # Status Display Box
        self.status_card = ctk.CTkFrame(
            self.gui_frame, 
            fg_color=t["slot_bg"], 
            corner_radius=t["corner_radius"], 
            border_width=t["border_width"], 
            border_color=t["btn_border"]
        )
        self.status_card.pack(fill="x", padx=20, pady=10)

        self.status_label = ctk.CTkLabel(
            self.status_card, 
            text="STATUS: OFF", 
            font=(t["font_family"], 14, "bold"), 
            text_color=t["off_color"]
        )
        self.status_label.pack(pady=8)

        # Toggle Button
        self.toggle_btn = ctk.CTkButton(
            self.gui_frame, 
            text="START [F6]", 
            font=(t["font_family"], 14, "bold"), 
            fg_color=t["btn_bg"], 
            hover_color=t["btn_hover"], 
            text_color=t["text_color"], 
            border_width=t["border_width"], 
            border_color=t["btn_border"], 
            corner_radius=t["corner_radius"], 
            height=42, 
            command=self.toggle_clicker
        )
        self.toggle_btn.pack(fill="x", padx=20, pady=(5, 15))

    def change_theme(self, new_theme_name):
        """Dynamic theme reloading method."""
        self.themes = load_themes()  # Reload in case JSON was manually edited
        if new_theme_name in self.themes:
            self.current_theme_name = new_theme_name
            self.theme = self.themes[new_theme_name]
            self.settings["current_theme"] = new_theme_name

            # Re-apply theme to widgets
            t = self.theme
            font_main = (t["font_family"], 12, "bold")
            font_title = (t["font_family"], 18, "bold")

            self.configure(fg_color=t["bg_main"])
            self.outer_border.configure(fg_color=t["bg_main"], border_color=t["border_color"], border_width=t["border_width"], corner_radius=t["corner_radius"])
            self.gui_frame.configure(fg_color=t["container_bg"], border_color=t["slot_bg"], border_width=t["border_width"], corner_radius=t["corner_radius"])
            
            self.lbl_theme.configure(font=font_main, text_color=t["text_color"])
            self.theme_dropdown.configure(font=font_main, fg_color=t["btn_bg"], button_color=t["btn_border"], button_hover_color=t["btn_hover"], text_color=t["text_color"], dropdown_text_color=t["text_color"], dropdown_fg_color=t["container_bg"], corner_radius=t["corner_radius"])

            self.title_label.configure(font=font_title, text_color=t["title_color"])
            self.subtitle_label.configure(font=(t["font_family"], 11, "bold"), text_color=t["muted_text"])

            self.config_frame.configure(fg_color=t["card_bg"], border_color=t["slot_bg"], border_width=t["border_width"], corner_radius=t["corner_radius"])
            self.hold_label.configure(font=font_main, text_color=t["text_color"])
            self.lbl_to1.configure(font=font_main, text_color=t["muted_text"])
            self.entry_hold_min.configure(font=font_main, fg_color=t["slot_bg"], text_color=t["active_color"], border_color=t["btn_border"], corner_radius=t["corner_radius"])
            self.entry_hold_max.configure(font=font_main, fg_color=t["slot_bg"], text_color=t["active_color"], border_color=t["btn_border"], corner_radius=t["corner_radius"])

            self.wait_label.configure(font=font_main, text_color=t["text_color"])
            self.lbl_to2.configure(font=font_main, text_color=t["muted_text"])
            self.entry_wait_min.configure(font=font_main, fg_color=t["slot_bg"], text_color=t["active_color"], border_color=t["btn_border"], corner_radius=t["corner_radius"])
            self.entry_wait_max.configure(font=font_main, fg_color=t["slot_bg"], text_color=t["active_color"], border_color=t["btn_border"], corner_radius=t["corner_radius"])

            self.status_card.configure(fg_color=t["slot_bg"], border_color=t["btn_border"], border_width=t["border_width"], corner_radius=t["corner_radius"])
            self.status_label.configure(font=(t["font_family"], 14, "bold"), text_color=t["active_color"] if self.is_running else t["off_color"])

            self.toggle_btn.configure(font=(t["font_family"], 14, "bold"), fg_color="#A83232" if self.is_running else t["btn_bg"], hover_color="#C73E3E" if self.is_running else t["btn_hover"], text_color=t["text_color"], border_color=t["btn_border"], border_width=t["border_width"], corner_radius=t["corner_radius"])

            # Apply Theme to Overlay Window
            self.overlay.apply_theme()
            save_settings(self.settings)

    def get_delays_and_save_ui_state(self):
        try:
            h_min = max(10, int(self.entry_hold_min.get()))
            h_max = max(h_min, int(self.entry_hold_max.get()))
            w_min = max(10, int(self.entry_wait_min.get()))
            w_max = max(w_min, int(self.entry_wait_max.get()))

            self.settings.update({
                "current_theme": self.current_theme_name,
                "hold_min": h_min,
                "hold_max": h_max,
                "wait_min": w_min,
                "wait_max": w_max,
                "win_x": self.winfo_x(),
                "win_y": self.winfo_y(),
                "overlay_x": self.overlay.winfo_x() if hasattr(self, 'overlay') else self.settings.get("overlay_x"),
                "overlay_y": self.overlay.winfo_y() if hasattr(self, 'overlay') else self.settings.get("overlay_y")
            })
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
        self.status_label.configure(text="STATUS: ACTIVE [F6]", text_color=self.theme["active_color"])
        self.toggle_btn.configure(text="STOP [F6]", fg_color="#A83232", hover_color="#C73E3E")
        
        self.overlay.show()

        self.click_thread = threading.Thread(target=self.click_loop, daemon=True)
        self.click_thread.start()

    def stop_clicker(self):
        self.is_running = False
        self.mouse.release(Button.right)
        
        self.status_label.configure(text="STATUS: OFF", text_color=self.theme["off_color"])
        self.toggle_btn.configure(text="START [F6]", fg_color=self.theme["btn_bg"], hover_color=self.theme["btn_hover"])
        
        self.overlay.hide()

    def click_loop(self):
        while self.is_running:
            h_min_s, h_max_s, w_min_s, w_max_s = self.get_delays_and_save_ui_state()

            self.mouse.press(Button.right)
            hold_time = random.uniform(h_min_s, h_max_s)
            time.sleep(hold_time)
            
            self.mouse.release(Button.right)
            wait_time = random.uniform(w_min_s, w_max_s)
            
            elapsed = 0.0
            step = 0.02
            while self.is_running and elapsed < wait_time:
                time.sleep(step)
                elapsed += step

        self.mouse.release(Button.right)

    def on_close(self):
        self.stop_clicker()
        self.get_delays_and_save_ui_state()
        self.hotkey_listener.stop()
        self.destroy()


if __name__ == "__main__":
    app = AutoClickerApp()
    app.mainloop()