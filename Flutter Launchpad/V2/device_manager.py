import os
import re
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk

# Application-wide UI configurations
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# ==============================================================================
# SAFE PATCH: Prevents CustomTkinter from crashing when scrolling native widgets
# ==============================================================================
orig_check_scroll = ctk.CTkScrollableFrame._check_if_valid_scroll
def patched_check_scroll(self, widget):
    if isinstance(widget, str):
        try:
            widget = self.nametowidget(widget)
        except Exception:
            return False
    try:
        return orig_check_scroll(self, widget)
    except Exception:
        return False
ctk.CTkScrollableFrame._check_if_valid_scroll = patched_check_scroll
# ==============================================================================


class AndroidDeviceManagerWindow(ctk.CTkToplevel):
    """AVD Manager interface to view, create via 'avdmanager list device', and delete emulators."""

    def __init__(self, parent=None):
        if parent:
            super().__init__(parent)
            self.transient(parent)
            self.grab_set()
        else:
            super().__init__()

        self.title("Android Virtual Device (AVD) Manager")
        self.center_window(750, 600)
        self.resizable(False, False)

        # 1. Style the internal dropdown listbox popup to look dark and modern
        self.option_add("*TCombobox*Listbox.background", "#2b2b2b")
        self.option_add("*TCombobox*Listbox.foreground", "#E1E1E1")
        self.option_add("*TCombobox*Listbox.selectBackground", "#1f538d")
        self.option_add("*TCombobox*Listbox.selectForeground", "white")
        self.option_add("*TCombobox*Listbox.font", ("Segoe UI", 10))
        self.option_add("*TCombobox*Listbox.borderwidth", 0)
        self.option_add("*TCombobox*Listbox.relief", "flat")

        # 2. Modernize the closed Combobox field element
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.style.configure("TCombobox",
                             fieldbackground="#343638",
                             background="#434547",
                             foreground="white",
                             bordercolor="#565b5e",
                             darkcolor="#343638",
                             lightcolor="#343638",
                             arrowcolor="#E1E1E1",
                             arrowsize=12,
                             font=("Segoe UI", 10))
        
        self.style.map("TCombobox", 
                       fieldbackground=[('readonly', '#343638'), ('focus', '#343638')],
                       foreground=[('readonly', 'white')],
                       bordercolor=[('focus', '#1f538d')])

        ctk.CTkLabel(self, text="Android Virtual Device (AVD) Manager", font=ctk.CTkFont(size=16, weight="bold")).pack(padx=20, pady=(15, 5), anchor="w")
        ctk.CTkLabel(self, text="Manage, boot, or provision hardware profiles into virtual devices.", font=ctk.CTkFont(size=12, slant="italic"), text_color="gray").pack(padx=20, pady=(0, 10), anchor="w")

        self.tabview = ctk.CTkTabview(self, width=710, height=420)
        self.tabview.pack(padx=20, pady=5, fill="both", expand=True)
        
        self.tab_installed = self.tabview.add("Your Virtual Devices")
        self.tab_create = self.tabview.add("➕ Create New AVD")

        self.installed_frame = ctk.CTkScrollableFrame(self.tab_installed)
        self.installed_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.setup_create_tab()

        self.status_lbl = ctk.CTkLabel(self, text="Status: Ready", font=ctk.CTkFont(size=12, weight="bold"))
        self.status_lbl.pack(side="left", padx=20, pady=(5, 15))

        self.refresh_btn = ctk.CTkButton(self, text="🔄 Refresh AVDs", width=120, command=self.refresh_installed_avds)
        self.refresh_btn.pack(side="right", padx=20, pady=(5, 15))

        self.refresh_installed_avds()
        threading.Thread(target=self.fetch_hardware_devices, daemon=True).start()

    def center_window(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def update_status(self, text):
        self.status_lbl.configure(text=f"Status: {text}")

    def refresh_installed_avds(self):
        self.update_status("Scanning installed AVDs...")
        for w in self.installed_frame.winfo_children(): w.destroy()

        def scan():
            try:
                result = subprocess.run(["emulator", "-list-avds"], capture_output=True, text=True, shell=True)
                avds = [line.strip() for line in result.stdout.split("\n") if line.strip()]
                self.after(0, lambda: self.populate_installed_ui(avds))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("AVD Scan Error", f"Failed to execute 'emulator -list-avds':\n{e}", parent=self))

        threading.Thread(target=scan, daemon=True).start()

    def populate_installed_ui(self, avds):
        if not self.winfo_exists(): return
        if not avds:
            ctk.CTkLabel(self.installed_frame, text="No Virtual Devices configured yet.", font=ctk.CTkFont(slant="italic")).pack(pady=30)
            self.update_status("Ready")
            return

        for avd in avds:
            row = ctk.CTkFrame(self.installed_frame, fg_color="gray18", corner_radius=6)
            row.pack(fill="x", padx=5, pady=6, ipady=4)
            ctk.CTkLabel(row, text=f"📱 {avd}", font=ctk.CTkFont(weight="bold"), anchor="w").pack(side="left", padx=15, fill="x", expand=True)
            ctk.CTkButton(row, text="⚡ Boot", fg_color="#2e7d32", hover_color="#1b5e20", width=70, height=28, command=lambda name=avd: self.boot_avd(name)).pack(side="right", padx=(0, 10))
            ctk.CTkButton(row, text="Delete", fg_color="#8b0000", hover_color="#5a0000", width=70, height=28, command=lambda name=avd: self.delete_avd(name)).pack(side="right", padx=(0, 15))
        self.update_status("Ready")

    def boot_avd(self, name):
        try:
            subprocess.Popen(["emulator", "-avd", name], shell=False, creationflags=0x08000000 | 0x00000008 if os.name == 'nt' else 0)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to boot emulator:\n{e}", parent=self)

    def delete_avd(self, name):
        if messagebox.askyesno("Confirm Deletion", f"Permanently remove virtual device '{name}'?", parent=self):
            try:
                result = subprocess.run(["avdmanager", "delete", "avd", "-n", name], capture_output=True, text=True, shell=True)
                if result.returncode == 0:
                    messagebox.showinfo("Success", f"Successfully deleted AVD: {name}", parent=self)
                else:
                    messagebox.showerror("Error", f"Could not remove AVD:\n{result.stderr}", parent=self)
            except Exception as e:
                messagebox.showerror("Error", f"Execution error:\n{e}", parent=self)
            self.refresh_installed_avds()

    def setup_create_tab(self):
        container = ctk.CTkFrame(self.tab_create, fg_color="transparent")
        container.pack(padx=30, pady=15, fill="both", expand=True)

        ctk.CTkLabel(container, text="AVD Device Name:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", pady=10)
        self.new_avd_name = ctk.CTkEntry(container, placeholder_text="e.g., Pixel4_API35", width=350)
        self.new_avd_name.grid(row=0, column=1, padx=20, pady=10, sticky="w")

        ctk.CTkLabel(container, text="Hardware Profile (-d):", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", pady=10)
        
        # FIXED: Increased width to 47 to line up exactly with the Entry field size
        self.hardware_dropdown = ttk.Combobox(container, values=["Scanning hardware profiles..."], width=55, state="readonly", height=10)
        self.hardware_dropdown.grid(row=1, column=1, padx=20, pady=10, sticky="w")

        ctk.CTkLabel(container, text="Target System Image (-k):", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky="w", pady=10)
        self.system_image_dropdown = ttk.Combobox(container, values=["Scanning downloaded frameworks..."], width=55, state="readonly", height=10)
        self.system_image_dropdown.grid(row=2, column=1, padx=20, pady=10, sticky="w")

        self.exec_create_btn = ctk.CTkButton(container, text="🚀 Execute AVD Creation Pipeline", font=ctk.CTkFont(weight="bold"), height=40, command=self.create_new_avd_action)
        self.exec_create_btn.grid(row=3, column=0, columnspan=2, pady=30, sticky="ew")

    def fetch_hardware_devices(self):
        try:
            result = subprocess.run(["avdmanager", "list", "device"], capture_output=True, text=True, shell=True)
            output = result.stdout
            raw_device_ids = []
            for line in output.split("\n"):
                if "id:" in line or "Id:" in line:
                    match = re.search(r'id:\s*(\d+|\S+)\s*or\s*"([^"]+)"', line)
                    if match: 
                        raw_device_ids.append(match.group(2))
                    else:
                        parts = line.split(":")
                        if len(parts) > 1 and '"' in parts[1]:
                            name_match = re.search(r'"([^"]+)"', parts[1])
                            if name_match: raw_device_ids.append(name_match.group(1))

            filtered_devices = []
            for d in raw_device_ids:
                d_lower = d.lower()
                if any(x in d_lower for x in ["wear", "tv", "auto", "glass", "watch", "round", "square", "small_phone", "qvga", "wqvga", "nexus"]):
                    continue
                filtered_devices.append(d)

            filtered_devices = sorted(list(set(filtered_devices)))

            if not filtered_devices: 
                filtered_devices = ["pixel_6", "pixel_7", "pixel_8", "medium_phone"]

            self.after(0, lambda: [
                self.hardware_dropdown.configure(values=filtered_devices), 
                self.hardware_dropdown.current(0) if filtered_devices else None
            ])
        except Exception:
            fallback = ["pixel_6", "pixel_7", "pixel_8", "medium_phone"]
            self.after(0, lambda: [
                self.hardware_dropdown.configure(values=fallback), 
                self.hardware_dropdown.current(0)
            ])

        try:
            img_result = subprocess.run(
                ["sdkmanager", "--list_installed"], 
                capture_output=True, text=True, shell=True,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )
            installed_images = []
            for line in img_result.stdout.split("\n"):
                if not line.strip(): continue
                parts = line.strip().split()
                if parts and parts[0].startswith("system-images;"):
                    installed_images.append(parts[0])
                    
            if installed_images:
                self.after(0, lambda: [
                    self.system_image_dropdown.configure(values=installed_images), 
                    self.system_image_dropdown.current(0)
                ])
            else:
                warning_str = ["No installed targets found. Run SDK Manager!"]
                self.after(0, lambda: [
                    self.system_image_dropdown.configure(values=warning_str), 
                    self.system_image_dropdown.current(0)
                ])
        except Exception:
            emergency_fallback = ["system-images;android-35;google_apis;x86_64"]
            self.after(0, lambda: [
                self.system_image_dropdown.configure(values=emergency_fallback), 
                self.system_image_dropdown.current(0)
            ])

    def create_new_avd_action(self):
        name = self.new_avd_name.get().strip().replace(" ", "_")
        hw_profile = self.hardware_dropdown.get().strip()
        sys_img = self.system_image_dropdown.get().strip()

        if not name or not sys_img or "No installed" in sys_img or "Scanning" in sys_img:
            messagebox.showerror("Validation Failure", "All setup fields must contain valid parameter inputs.", parent=self)
            return

        self.update_status("Provisioning AVD Device Layout...")
        self.exec_create_btn.configure(state="disabled")

        def execute():
            try:
                cmd = ["avdmanager", "create", "avd", "-n", name, "-k", sys_img, "-d", hw_profile]
                process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
                stdout, stderr = process.communicate(input="no\n")
                
                if process.returncode == 0:
                    self.after(0, lambda: messagebox.showinfo("Success", f"Successfully created your custom device '{name}'!", parent=self))
                    self.after(0, lambda: self.new_avd_name.delete(0, tk.END))
                    self.after(0, lambda: self.tabview.set("Your Virtual Devices"))
                    self.after(0, self.refresh_installed_avds)
                else:
                    self.after(0, lambda: messagebox.showerror("AVD Pipeline Error", f"Failed to deploy device parameters:\n\n{stderr if stderr else stdout}", parent=self))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("System Error", f"Unexpected error:\n{e}", parent=self))
            finally:
                self.after(0, lambda: self.exec_create_btn.configure(state="normal"))
                self.after(0, lambda: self.update_status("Ready"))

        threading.Thread(target=execute, daemon=True).start()


if __name__ == "__main__":
    app = AndroidDeviceManagerWindow()
    app.mainloop()