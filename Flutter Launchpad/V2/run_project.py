import os
import json
import re
import socket
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from utils import CONFIG_FILE

class RunProjectWindow(ctk.CTkToplevel):
    def __init__(self, parent, project_name, project_path):
        super().__init__(parent)
        self.parent = parent
        self.project_name = project_name
        self.project_path = project_path

        self.title(f"Run: {project_name}")
        self.center_window(500, 320)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.header_label = ctk.CTkLabel(self, text=f"Launch Pipeline: {project_name}", font=ctk.CTkFont(size=15, weight="bold"))
        self.header_label.pack(padx=20, pady=(15, 10), anchor="w")

        self.path_row = ctk.CTkFrame(self, fg_color="transparent")
        self.path_row.pack(padx=20, pady=4, fill="x")
        
        self.path_entry = ctk.CTkEntry(self.path_row, placeholder_text="Select emulator.exe path...", width=280)
        self.path_entry.pack(side="left", padx=(0, 10))
        
        self.browse_path_btn = ctk.CTkButton(self.path_row, text="⚙ Path", width=120, fg_color="#455a64", hover_color="#37474f", command=self.browse_emulator_path)
        self.browse_path_btn.pack(side="right", fill="x", expand=True)

        self.boot_row = ctk.CTkFrame(self, fg_color="transparent")
        self.boot_row.pack(padx=20, pady=4, fill="x")
        
        self.emulator_dropdown = ctk.CTkComboBox(self.boot_row, values=["Loading Emulators..."], width=280)
        self.emulator_dropdown.pack(side="left", padx=(0, 10))
        
        self.boot_btn = ctk.CTkButton(self.boot_row, text="⚡ Boot Device", width=120, fg_color="#673ab7", hover_color="#512da8", command=self.boot_selected_emulator)
        self.boot_btn.pack(side="right", fill="x", expand=True)

        self.target_frame = ctk.CTkFrame(self)
        self.target_frame.pack(padx=20, pady=(10, 15), fill="x")

        self.run_row = ctk.CTkFrame(self.target_frame, fg_color="transparent")
        self.run_row.pack(padx=15, pady=(15, 5), fill="x")
        
        self.device_dropdown = ctk.CTkComboBox(self.run_row, values=["Scanning Target Hardware..."], width=250)
        self.device_dropdown.pack(side="left", padx=(0, 10))
        
        self.refresh_btn = ctk.CTkButton(self.run_row, text="🔄 Refresh", width=110, fg_color="#1f6aa5", hover_color="#144870", command=lambda: threading.Thread(target=self.fetch_active_devices, daemon=True).start())
        self.refresh_btn.pack(side="right", fill="x", expand=True)

        self.run_btn = ctk.CTkButton(self.target_frame, text="▶ Run Project Live", fg_color="#2e7d32", hover_color="#1b5e20", font=ctk.CTkFont(weight="bold"), command=self.run_flutter_project)
        self.run_btn.pack(padx=15, pady=(5, 15), fill="x")

        self.load_saved_emulator_path()
        threading.Thread(target=self.fetch_emulators, daemon=True).start()
        threading.Thread(target=self.fetch_active_devices, daemon=True).start()

    def center_window(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def load_saved_emulator_path(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    saved_path = config.get("emulator_path", "")
                    if saved_path and os.path.exists(saved_path):
                        self.path_entry.insert(0, saved_path)
                        return
            except Exception: pass
        
        local_appdata = os.environ.get("LOCALAPPDATA")
        default_path = os.path.join(local_appdata, "Android", "Sdk", "emulator", "emulator.exe") if local_appdata else ""
        if default_path and os.path.exists(default_path):
            self.path_entry.insert(0, default_path)
        else:
            self.path_entry.insert(0, "emulator")

    def browse_emulator_path(self):
        file_path = filedialog.askopenfilename(title="Locate Android SDK emulator.exe", filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")])
        if file_path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, file_path)
            try:
                config = {}
                if os.path.exists(CONFIG_FILE):
                    with open(CONFIG_FILE, "r") as f: config = json.load(f)
                config["emulator_path"] = file_path
                with open(CONFIG_FILE, "w") as f: json.dump(config, f)
            except Exception: pass
            threading.Thread(target=self.fetch_emulators, daemon=True).start()

    def fetch_emulators(self):
        try:
            emulator_exe = self.path_entry.get().strip()
            if not emulator_exe: emulator_exe = "emulator"
            result = subprocess.run([emulator_exe, "-list-avds"], capture_output=True, text=True, shell=True, creationflags=0x08000000 if os.name == 'nt' else 0)
            emulators = [line.strip() for line in result.stdout.split("\n") if line.strip()]
            
            def update_emu_ui():
                if not self.winfo_exists(): return
                if emulators:
                    self.emulator_dropdown.configure(values=emulators)
                    self.emulator_dropdown.set(emulators[0])
                else:
                    self.emulator_dropdown.configure(values=["No Emulators Setup"])
                    self.emulator_dropdown.set("No Emulators Setup")
            self.after(0, update_emu_ui)
        except Exception:
            if self.winfo_exists(): self.after(0, lambda: self.emulator_dropdown.configure(values=["Error Scanning"]))

    def fetch_active_devices(self):
        if not self.winfo_exists(): return
        devices = []
        seen_ids = set()

        for port in range(5554, 5585, 2):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.1)
                if s.connect_ex(('127.0.0.1', port)) == 0:
                    dev_id = f"emulator-{port}"
                    devices.append(f"Running Emulator [{dev_id}]")
                    seen_ids.add(dev_id)
                s.close()
            except Exception: pass

        try:
            result = subprocess.run(["flutter", "devices"], capture_output=True, text=True, shell=True, creationflags=0x08000000 if os.name == 'nt' else 0)
            for line in result.stdout.split("\n"):
                line_str = line.strip()
                if "•" in line_str and not line_str.startswith("---") and "available device" not in line_str:
                    parts = [p.strip() for p in line_str.split("•") if p.strip()]
                    if len(parts) >= 2:
                        name, device_id = parts[0], parts[1]
                        if device_id not in seen_ids:
                            devices.append(f"{name} [{device_id}]")
                            seen_ids.add(device_id)
        except Exception: pass

        for fallback_id, fallback_name in [("chrome", "Google Chrome"), ("edge", "Microsoft Edge"), ("windows", "Windows Desktop")]:
            if fallback_id not in seen_ids:
                devices.append(f"{fallback_name} [{fallback_id}]")

        def update_ui():
            if not self.winfo_exists(): return
            if devices:
                self.device_dropdown.configure(values=devices)
                self.device_dropdown.set(devices[0])
            else:
                self.device_dropdown.configure(values=["No Active Targets Found"])
                self.device_dropdown.set("No Active Targets Found")

        if self.winfo_exists(): self.after(0, update_ui)

    def boot_selected_emulator(self):
        emulator_id = self.emulator_dropdown.get()
        if "No Emulators" in emulator_id or "Error" in emulator_id:
            messagebox.showwarning("Execution Warning", "Please select a valid emulator configuration first.", parent=self)
            return
        
        def run_boot():
            try:
                emulator_exe = self.path_entry.get().strip()
                if not emulator_exe: emulator_exe = "emulator"
                subprocess.Popen([emulator_exe, "-avd", emulator_id], shell=False, creationflags=0x08000000 | 0x00000008)
                for delay in [4000, 8000, 12000, 16000]:
                    self.after(delay, lambda: threading.Thread(target=self.fetch_active_devices, daemon=True).start())
            except Exception: pass

        threading.Thread(target=run_boot, daemon=True).start()
        messagebox.showinfo("Boot Command Sent", f"Starting '{emulator_id}' silently in background...", parent=self)

    def run_flutter_project(self):
        choice = self.device_dropdown.get()
        if "No Active" in choice or "Scanning" in choice:
            messagebox.showwarning("Execution Warning", "No valid online target device is currently selected.", parent=self)
            return

        match = re.search(r'\[([^\]]+)\]', choice)
        device_id = match.group(1).strip() if match else choice.strip()
        run_command = f'start "Flutter Live Run: {self.project_name}" cmd /k "cd /d {self.project_path} && flutter run -d {device_id}"'
        try:
            subprocess.Popen(run_command, shell=True)
        except Exception as e:
            messagebox.showerror("Execution Error", f"Failed to open terminal interface engine:\n{e}", parent=self)