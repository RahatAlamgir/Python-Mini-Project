import os
import re
import subprocess
import threading
from tkinter import messagebox
import customtkinter as ctk

class AndroidSDKManagerWindow(ctk.CTkToplevel):
    """Component manager featuring isolated tabs for managing platforms, tools, and emulator OS images."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Android SDK Component Manager")
        self.center_window(750, 580)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        ctk.CTkLabel(self, text="Android SDK Platforms & Emulator Images", font=ctk.CTkFont(size=16, weight="bold")).pack(padx=20, pady=(15, 5), anchor="w")
        ctk.CTkLabel(self, text="Install core development platforms or choose specific emulator system images.", font=ctk.CTkFont(size=12, slant="italic"), text_color="gray").pack(padx=20, pady=(0, 10), anchor="w")

        self.tabview = ctk.CTkTabview(self, width=710, height=400)
        self.tabview.pack(padx=20, pady=5, fill="both", expand=True)
        
        self.tab_installed = self.tabview.add("Installed Components")
        self.tab_platforms = self.tabview.add("Available SDK Platforms")
        self.tab_images = self.tabview.add("Available Emulator System Images")

        self.installed_frame = ctk.CTkScrollableFrame(self.tab_installed)
        self.installed_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.platforms_frame = ctk.CTkScrollableFrame(self.tab_platforms)
        self.platforms_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.images_frame = ctk.CTkScrollableFrame(self.tab_images)
        self.images_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.pack(padx=20, pady=(5, 0), fill="x")
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, orientation="horizontal", height=10)
        self.progress_bar.pack(fill="x", side="top", pady=(2, 5))
        self.progress_bar.set(0.0)

        self.status_lbl = ctk.CTkLabel(self, text="Status: Ready", font=ctk.CTkFont(size=12, weight="bold"))
        self.status_lbl.pack(side="left", padx=20, pady=(5, 15))

        self.refresh_btn = ctk.CTkButton(self, text="🔄 Refresh List", width=120, command=self.start_sdk_scan)
        self.refresh_btn.pack(side="right", padx=20, pady=(5, 15))

        self.start_sdk_scan()

    def center_window(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def update_status(self, text):
        self.status_lbl.configure(text=f"Status: {text}")

    def update_progress(self, percentage_val):
        self.progress_bar.set(percentage_val / 100.0)

    def start_sdk_scan(self):
        self.update_status("Scanning SDK Packages...")
        self.update_progress(0)
        self.refresh_btn.configure(state="disabled")
        
        for w in self.installed_frame.winfo_children(): w.destroy()
        for w in self.platforms_frame.winfo_children(): w.destroy()
        for w in self.images_frame.winfo_children(): w.destroy()
        
        threading.Thread(target=self.fetch_sdk_packages, daemon=True).start()

    def fetch_sdk_packages(self):
        try:
            result = subprocess.run(["sdkmanager", "--list"], capture_output=True, text=True, shell=True, creationflags=0x08000000 if os.name == 'nt' else 0)
            output = result.stdout
            
            installed_packages = []
            available_platforms = []
            available_images = []
            
            sections = output.split("Available Packages:")
            
            installed_part = sections[0]
            for line in installed_part.split("\n"):
                if line.strip() and not line.startswith("---") and not line.startswith("Installed"):
                    match = re.match(r'^\s*([^\s]+)\s*\|\s*([^\s|]+)', line.strip())
                    if match and ";" in match.group(1):
                        installed_packages.append((match.group(1), match.group(2)))

            if len(sections) > 1:
                available_part = sections[1].split("Available Updates:")[0]
                for line in available_part.split("\n"):
                    if line.strip() and not line.startswith("---") and not line.startswith("Path"):
                        match = re.match(r'^\s*([^\s]+)\s*\|\s*([^\s|]+)', line.strip())
                        if match and ";" in match.group(1):
                            package_path = match.group(1)
                            package_version = match.group(2)
                            
                            if "system-images;" in package_path:
                                available_images.append((package_path, package_version))
                            elif "platforms;" in package_path or "build-tools;" in package_path or "platform-tools" in package_path:
                                available_platforms.append((package_path, package_version))

            self.after(0, lambda: self.populate_ui(installed_packages, available_platforms, available_images))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("SDK Manager Error", f"Failed to parse sdkmanager output:\n{e}", parent=self))
            self.after(0, lambda: self.update_status("Scan Failed"))
            self.after(0, lambda: self.refresh_btn.configure(state="normal"))

    def populate_ui(self, installed, platforms, images):
        if not self.winfo_exists(): return

        if not installed:
            ctk.CTkLabel(self.installed_frame, text="No packages currently active.", font=ctk.CTkFont(slant="italic")).pack(pady=20)
        for path, version in installed:
            row = ctk.CTkFrame(self.installed_frame, fg_color="transparent")
            row.pack(fill="x", padx=5, pady=4)
            ctk.CTkLabel(row, text=f"{path} (v{version})", anchor="w").pack(side="left", fill="x", expand=True)
            ctk.CTkButton(row, text="Remove", fg_color="#8b0000", hover_color="#5a0000", width=80, height=26,
                           command=lambda p=path: self.modify_package(p, action="uninstall")).pack(side="right")

        if not platforms:
            ctk.CTkLabel(self.platforms_frame, text="No baseline platform tools found.", font=ctk.CTkFont(slant="italic")).pack(pady=20)
        for path, version in platforms:
            row = ctk.CTkFrame(self.platforms_frame, fg_color="transparent")
            row.pack(fill="x", padx=5, pady=4)
            ctk.CTkLabel(row, text=f"{path} (v{version})", anchor="w").pack(side="left", fill="x", expand=True)
            ctk.CTkButton(row, text="Install", fg_color="#2e7d32", hover_color="#1b5e20", width=80, height=26,
                           command=lambda p=path: self.modify_package(p, action="install")).pack(side="right")

        if not images:
            ctk.CTkLabel(self.images_frame, text="No virtual architecture system images found.", font=ctk.CTkFont(slant="italic")).pack(pady=20)
        for path, version in images:
            row = ctk.CTkFrame(self.images_frame, fg_color="transparent")
            row.pack(fill="x", padx=5, pady=4)
            ctk.CTkLabel(row, text=f"{path} (v{version})", anchor="w").pack(side="left", fill="x", expand=True)
            ctk.CTkButton(row, text="Install", fg_color="#2e7d32", hover_color="#1b5e20", width=80, height=26,
                           command=lambda p=path: self.modify_package(p, action="install")).pack(side="right")

        self.update_status("Ready")
        self.refresh_btn.configure(state="normal")

    def modify_package(self, package_path, action="install"):
        confirm = messagebox.askyesno("Confirm Action", f"Are you sure you want to {action} component:\n\n{package_path}?", parent=self)
        if not confirm: return

        self.update_status(f"{action.capitalize()}ing component package...")
        self.update_progress(0)
        self.refresh_btn.configure(state="disabled")

        def run_modification():
            try:
                cmd = ["sdkmanager", package_path] if action == "install" else ["sdkmanager", "--uninstall", package_path]
                process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True, creationflags=0x08000000 if os.name == 'nt' else 0)
                process.stdin.write("y\ny\ny\n")
                process.stdin.flush()

                while True:
                    line = process.stdout.readline()
                    if not line: break
                    progress_match = re.search(r'(\d+)%', line)
                    if progress_match:
                        pct = int(progress_match.group(1))
                        self.after(0, lambda val=pct: self.update_progress(val))
                        self.after(0, lambda val=pct: self.update_status(f"Processing: {val}%"))
                process.wait()
                self.after(0, lambda: self.update_progress(100))
                self.after(0, lambda: messagebox.showinfo("Success", f"Component package completed successfully.", parent=self))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Execution pipeline error:\n{e}", parent=self))
            finally:
                self.after(0, self.start_sdk_scan)

        threading.Thread(target=run_modification, daemon=True).start()