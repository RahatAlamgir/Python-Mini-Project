import json
import os
import re
import shutil
import stat
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import customtkinter as ctk
from PIL import Image
import urllib.request
import io
import getpass
import threading
import socket

CONFIG_FILE = "config.json"

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


def onerror(func, path, exc_info):
    """Aggressive permission clearing to bypass Windows WinError 5 Access Denied blocks on hidden .git packs."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        try:
            subprocess.run(["attrib", "-R", "-H", "-S", path], capture_output=True, shell=True)
            func(path)
        except Exception:
            pass


def get_git_username():
    """Retrieves the global git username configured on the system, falling back to PC Username."""
    try:
        result = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, shell=True)
        username = result.stdout.strip()
        if not username:
            result_email = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True, shell=True)
            email = result_email.stdout.strip()
            if email and "@" in email:
                return email.split("@")[0]
        return username if username else getpass.getuser()
    except Exception:
        try:
            return getpass.getuser()
        except Exception:
            return "PC User"


class RunProjectWindow(ctk.CTkToplevel):
    """A dedicated execution pop-up window to boot emulators and run on any target (Emulator, Chrome, Web, etc.)"""

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

        # ---- Title Header ----
        self.header_label = ctk.CTkLabel(
            self, text=f"Launch Pipeline: {project_name}", font=ctk.CTkFont(size=15, weight="bold")
        )
        self.header_label.pack(padx=20, pady=(15, 10), anchor="w")

        # ---- Path Settings Setup Row ----
        self.path_row = ctk.CTkFrame(self, fg_color="transparent")
        self.path_row.pack(padx=20, pady=4, fill="x")
        
        self.path_entry = ctk.CTkEntry(self.path_row, placeholder_text="Select emulator.exe path...", width=280)
        self.path_entry.pack(side="left", padx=(0, 10))
        
        self.browse_path_btn = ctk.CTkButton(
            self.path_row, text="⚙ Path", width=120, fg_color="#455a64", hover_color="#37474f", command=self.browse_emulator_path
        )
        self.browse_path_btn.pack(side="right", fill="x", expand=True)

        # ---- Cold Boot Virtual Devices Frame ----
        self.boot_row = ctk.CTkFrame(self, fg_color="transparent")
        self.boot_row.pack(padx=20, pady=4, fill="x")
        
        self.emulator_dropdown = ctk.CTkComboBox(self.boot_row, values=["Loading Emulators..."], width=280)
        self.emulator_dropdown.pack(side="left", padx=(0, 10))
        
        self.boot_btn = ctk.CTkButton(
            self.boot_row, text="⚡ Boot Device", width=120, fg_color="#673ab7", hover_color="#512da8", command=self.boot_selected_emulator
        )
        self.boot_btn.pack(side="right", fill="x", expand=True)

        # ---- Target Select & Live Run Frame (Supports Chrome, Web, Devices, Emulators) ----
        self.target_frame = ctk.CTkFrame(self)
        self.target_frame.pack(padx=20, pady=(10, 15), fill="x")

        self.run_row = ctk.CTkFrame(self.target_frame, fg_color="transparent")
        self.run_row.pack(padx=15, pady=(15, 5), fill="x")
        
        self.device_dropdown = ctk.CTkComboBox(self.run_row, values=["Scanning Target Hardware..."], width=250)
        self.device_dropdown.pack(side="left", padx=(0, 10))
        
        self.refresh_btn = ctk.CTkButton(
            self.run_row, text="🔄 Refresh", width=110, fg_color="#1f6aa5", hover_color="#144870", command=lambda: threading.Thread(target=self.fetch_active_devices, daemon=True).start()
        )
        self.refresh_btn.pack(side="right", fill="x", expand=True)

        self.run_btn = ctk.CTkButton(
            self.target_frame, text="▶ Run Project Live", fg_color="#2e7d32", hover_color="#1b5e20", font=ctk.CTkFont(weight="bold"), command=self.run_flutter_project
        )
        self.run_btn.pack(padx=15, pady=(5, 15), fill="x")

        # Load configurations and trigger non-blocking scanning thread tasks
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
            except Exception:
                pass
        
        local_appdata = os.environ.get("LOCALAPPDATA")
        default_path = os.path.join(local_appdata, "Android", "Sdk", "emulator", "emulator.exe") if local_appdata else ""
        if default_path and os.path.exists(default_path):
            self.path_entry.insert(0, default_path)
        else:
            self.path_entry.insert(0, "emulator")

    def browse_emulator_path(self):
        file_path = filedialog.askopenfilename(
            title="Locate Android SDK emulator.exe",
            filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")]
        )
        if file_path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, file_path)
            try:
                config = {}
                if os.path.exists(CONFIG_FILE):
                    with open(CONFIG_FILE, "r") as f:
                        config = json.load(f)
                config["emulator_path"] = file_path
                with open(CONFIG_FILE, "w") as f:
                    json.dump(config, f)
            except Exception:
                pass
            threading.Thread(target=self.fetch_emulators, daemon=True).start()

    def fetch_emulators(self):
        try:
            emulator_exe = self.path_entry.get().strip()
            if not emulator_exe:
                emulator_exe = "emulator"
            result = subprocess.run(
                [emulator_exe, "-list-avds"], 
                capture_output=True, 
                text=True, 
                shell=True,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )
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
            if self.winfo_exists():
                self.after(0, lambda: self.emulator_dropdown.configure(values=["Error Scanning"]))

    def fetch_active_devices(self):
        """Scans both local virtual engine sockets and standard platform channels safely."""
        if not self.winfo_exists():
            return
            
        devices = []
        seen_ids = set()

        # 1. Port scanning for booted local Android emulators (fastest local scan mechanism)
        for port in range(5554, 5585, 2):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.1)
                if s.connect_ex(('127.0.0.1', port)) == 0:
                    dev_id = f"emulator-{port}"
                    devices.append(f"Running Emulator [{dev_id}]")
                    seen_ids.add(dev_id)
                s.close()
            except Exception:
                pass

        # 2. Querying Flutter Engine natively for global active targets (Chrome, Edge, Windows Desktop, etc.)
        try:
            result = subprocess.run(
                ["flutter", "devices"], 
                capture_output=True, 
                text=True, 
                shell=True,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )
            lines = result.stdout.split("\n")
            for line in lines:
                line_str = line.strip()
                if "•" in line_str and not line_str.startswith("---") and "available device" not in line_str:
                    parts = [p.strip() for p in line_str.split("•") if p.strip()]
                    if len(parts) >= 2:
                        name = parts[0]
                        device_id = parts[1]
                        if device_id not in seen_ids:
                            devices.append(f"{name} [{device_id}]")
                            seen_ids.add(device_id)
        except Exception:
            pass

        # 3. Smart fallbacks if the standard native environment calls timed out/didn't report web layers
        for fallback_id, fallback_name in [("chrome", "Google Chrome"), ("edge", "Microsoft Edge"), ("windows", "Windows Desktop")]:
            if fallback_id not in seen_ids:
                # Add basic standard options so the user is never blocked from deployment targets
                devices.append(f"{fallback_name} [{fallback_id}]")

        def update_ui():
            if not self.winfo_exists(): return
            if devices:
                self.device_dropdown.configure(values=devices)
                self.device_dropdown.set(devices[0])
            else:
                self.device_dropdown.configure(values=["No Active Targets Found"])
                self.device_dropdown.set("No Active Targets Found")

        if self.winfo_exists():
            self.after(0, update_ui)

    def boot_selected_emulator(self):
        emulator_id = self.emulator_dropdown.get()
        if "No Emulators" in emulator_id or "Error" in emulator_id:
            messagebox.showwarning("Execution Warning", "Please select a valid emulator configuration first.", parent=self)
            return
        
        def run_boot():
            try:
                emulator_exe = self.path_entry.get().strip()
                if not emulator_exe:
                    emulator_exe = "emulator"
                
                subprocess.Popen(
                    [emulator_exe, "-avd", emulator_id],
                    shell=False,
                    creationflags=0x08000000 | 0x00000008
                )
                
                for delay in [4000, 8000, 12000, 16000]:
                    self.after(delay, lambda: threading.Thread(target=self.fetch_active_devices, daemon=True).start())
            except Exception:
                pass

        threading.Thread(target=run_boot, daemon=True).start()
        messagebox.showinfo("Boot Command Sent", f"Starting '{emulator_id}' silently in background...", parent=self)

    def run_flutter_project(self):
        choice = self.device_dropdown.get()
        if "No Active" in choice or "Scanning" in choice:
            messagebox.showwarning("Execution Warning", "No valid online target device is currently selected.", parent=self)
            return

        # Regular expression layout mapping to capture contents inside the brackets cleanly
        match = re.search(r'\[([^\]]+)\]', choice)
        if match:
            device_id = match.group(1).strip()
        else:
            device_id = choice.strip()

        run_command = f'start "Flutter Live Run: {self.project_name}" cmd /k "cd /d {self.project_path} && flutter run -d {device_id}"'
        try:
            subprocess.Popen(run_command, shell=True)
        except Exception as e:
            messagebox.showerror("Execution Error", f"Failed to open terminal interface engine:\n{e}", parent=self)


class ProjectSettingsWindow(ctk.CTkToplevel):
    """An advanced configuration panel focusing cleanly on Git Management, Synchronizations, and Platforms optimization."""

    def __init__(self, parent, project_name, project_path, developer_name):
        super().__init__(parent)
        self.parent = parent
        self.project_name = project_name
        self.project_path = project_path
        self.developer_name = developer_name

        self.title(f"Configure: {project_name}")
        self.center_window(500, 560)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # ---- Title Header ----
        self.header_label = ctk.CTkLabel(
            self, text=f"Repository Settings: {project_name}", font=ctk.CTkFont(size=15, weight="bold")
        )
        self.header_label.pack(padx=20, pady=(15, 5), anchor="w")

        # ---- Git Tool Section ----
        self.git_frame = ctk.CTkFrame(self)
        self.git_frame.pack(padx=20, pady=8, fill="x")

        has_git = os.path.exists(os.path.join(project_path, ".git"))
        git_status_text = "Git Repository Status: Active" if has_git else "Git Repository Status: Missing"
        
        self.git_lbl = ctk.CTkLabel(self.git_frame, text=git_status_text, font=ctk.CTkFont(size=12))
        self.git_lbl.pack(side="left", padx=15, pady=12)

        self.git_btn = ctk.CTkButton(
            self.git_frame,
            text="Init Git",
            width=90,
            state="disabled" if has_git else "normal",
            command=self.initialize_git,
        )
        self.git_btn.pack(side="right", padx=15, pady=12)

        # ---- Git Commit & Push Panel ----
        self.git_ops_frame = ctk.CTkFrame(self)
        self.git_ops_frame.pack(padx=20, pady=8, fill="x")
        
        self.git_ops_lbl = ctk.CTkLabel(
            self.git_ops_frame, text="Git Operations (Commit & Push):", font=ctk.CTkFont(size=13, weight="bold")
        )
        self.git_ops_lbl.pack(padx=15, pady=(10, 5), anchor="w")
        
        self.commit_entry = ctk.CTkEntry(
            self.git_ops_frame, placeholder_text="Enter commit message...", width=440
        )
        self.commit_entry.pack(padx=15, pady=5, fill="x")
        
        self.push_btn = ctk.CTkButton(
            self.git_ops_frame,
            text="Commit All & Push to Remote",
            font=ctk.CTkFont(weight="bold"),
            state="normal" if has_git else "disabled",
            command=self.git_commit_and_push
        )
        self.push_btn.pack(padx=15, pady=(5, 15), fill="x")

        # ---- Dynamic Platform Management Section ----
        self.platform_frame = ctk.CTkFrame(self)
        self.platform_frame.pack(padx=20, pady=8, fill="x")

        self.platform_lbl = ctk.CTkLabel(
            self.platform_frame, text="Active Platform Folders:", font=ctk.CTkFont(size=13, weight="bold")
        )
        self.platform_lbl.pack(padx=15, pady=(10, 5), anchor="w")

        self.grid_container = ctk.CTkFrame(self.platform_frame, fg_color="transparent")
        self.grid_container.pack(padx=15, pady=(0, 10), fill="x")

        self.supported_platforms = ["android", "ios", "web", "macos", "windows", "linux"]
        self.checkbox_vars = {}

        grid_coords = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]
        for i, plat in enumerate(self.supported_platforms):
            r, c = grid_coords[i]
            folder_exists = os.path.exists(os.path.join(self.project_path, plat))
            self.checkbox_vars[plat] = ctk.BooleanVar(value=folder_exists)

            cb = ctk.CTkCheckBox(
                self.grid_container,
                text=plat.upper(), 
                variable=self.checkbox_vars[plat]
            )
            cb.grid(row=r, column=c, padx=15, pady=10, sticky="w")

        self.sync_btn = ctk.CTkButton(
            self, text="Sync & Update Platforms", font=ctk.CTkFont(weight="bold"), command=self.sync_platforms
        )
        self.sync_btn.pack(padx=20, pady=8, fill="x")

        # ---- Danger Zone (Delete) ----
        self.delete_btn = ctk.CTkButton(
            self,
            text="⚠️ Delete Entire Project Folder",
            fg_color="#8b0000",
            hover_color="#5a0000",
            font=ctk.CTkFont(weight="bold"),
            height=38,
            command=self.delete_project,
        )
        self.delete_btn.pack(padx=20, pady=(10, 15), fill="x")

    def center_window(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def initialize_git(self):
        try:
            os.chdir(self.project_path)
            subprocess.run(["git", "init"], capture_output=True, shell=True, check=True)
            subprocess.run(["git", "add", "."], capture_output=True, shell=True, check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit from Launchpad"], capture_output=True, shell=True, check=True)
            
            messagebox.showinfo("Success", "Git repository initialized successfully!", parent=self)
            self.git_lbl.configure(text="Git Repository Status: Active")
            self.git_btn.configure(state="disabled")
            self.push_btn.configure(state="normal")
        except Exception as e:
            messagebox.showerror("Git Error", f"Failed to initialize Git:\n{e}", parent=self)

    def git_commit_and_push(self):
        msg = self.commit_entry.get().strip()
        if not msg:
            messagebox.showerror("Git Error", "Please enter a commit message before pushing.", parent=self)
            return
            
        try:
            os.chdir(self.project_path)
            remote_result = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True, shell=True)
            remote_url = remote_result.stdout.strip().lower()
            
            if remote_url:
                clean_username = self.developer_name.lower().replace(" ", "")
                if clean_username not in remote_url:
                    confirm_push = messagebox.askyesno(
                        "Ownership Warning",
                        f"Repository target URL belongs to another host structure:\n{remote_url}\n\n"
                        "Do you still want to force attempt the push anyway?",
                        parent=self
                    )
                    if not confirm_push: return

            self.push_btn.configure(state="disabled", text="Pushing updates to Remote...")
            self.update()
            
            subprocess.run(["git", "add", "."], capture_output=True, shell=True, check=True)
            subprocess.run(["git", "commit", "-m", msg], capture_output=True, shell=True, check=True)
            subprocess.run(["git", "push"], capture_output=True, text=True, shell=True, check=True)
            
            messagebox.showinfo("Git Success", "Changes committed and pushed successfully!", parent=self)
            self.commit_entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Git Push Failed", f"Operational failure:\n\n{e}", parent=self)
        finally:
            self.push_btn.configure(state="normal", text="Commit All & Push to Remote")

    def sync_platforms(self):
        try:
            os.chdir(self.project_path)
            platforms_to_add = []

            for plat, var in self.checkbox_vars.items():
                folder_path = os.path.join(self.project_path, plat)
                if var.get() and not os.path.exists(folder_path):
                    platforms_to_add.append(plat)
                elif not var.get() and os.path.exists(folder_path):
                    shutil.rmtree(folder_path, onerror=onerror)

            if platforms_to_add:
                self.sync_btn.configure(state="disabled", text="Injecting Platform Boilerplate...")
                self.update()
                platforms_str = ",".join(platforms_to_add)
                subprocess.run(["flutter", "create", f"--platforms={platforms_str}", "."], capture_output=True, shell=True, check=True)

            messagebox.showinfo("Success", "Project platform directories synced successfully!", parent=self)
        except Exception as e:
            messagebox.showerror("Sync Error", f"Sync layout parameters failed:\n{e}", parent=self)
        finally:
            self.sync_btn.configure(state="normal", text="Sync & Update Platforms")

    def delete_project(self):
        confirm = messagebox.askyesno(
            "CRITICAL WARNING",
            f"Permanently erase folder '{self.project_name}'? This cannot be undone!",
            parent=self
        )
        if confirm:
            try:
                for root, dirs, files in os.walk(self.project_path):
                    for file in files:
                        os.chmod(os.path.join(root, file), stat.S_IWRITE)
                shutil.rmtree(self.project_path, onerror=onerror)
                messagebox.showinfo("Deleted", "Project directory deleted successfully.", parent=self)
                self.parent.scan_workspace()
                self.destroy()
            except Exception as e:
                messagebox.showerror("Delete Error", f"Could not clear project contents:\n{e}", parent=self)


class CreateProjectWindow(ctk.CTkToplevel):
    def __init__(self, parent, workspace_dir):
        super().__init__(parent)
        self.parent = parent
        self.workspace_dir = workspace_dir

        self.title("Configure New Flutter Project")
        self.center_window(500, 500)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.name_label = ctk.CTkLabel(self, text="Project Name:", font=ctk.CTkFont(size=14, weight="bold"))
        self.name_label.pack(padx=20, pady=(20, 5), anchor="w")

        self.name_entry = ctk.CTkEntry(self, placeholder_text="e.g., my_awesome_app", width=460)
        self.name_entry.pack(padx=20, pady=5)

        self.platform_label = ctk.CTkLabel(self, text="Target Platforms:", font=ctk.CTkFont(size=14, weight="bold"))
        self.platform_label.pack(padx=20, pady=(15, 5), anchor="w")

        self.platform_frame = ctk.CTkFrame(self)
        self.platform_frame.pack(padx=20, pady=5, fill="x")

        self.platforms = {
            "android": ctk.BooleanVar(value=True),
            "ios": ctk.BooleanVar(value=False),
            "web": ctk.BooleanVar(value=False),
            "macos": ctk.BooleanVar(value=False),
            "windows": ctk.BooleanVar(value=False),
            "linux": ctk.BooleanVar(value=False),
        }

        coords = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]
        for i, (platform, var) in enumerate(self.platforms.items()):
            r, c = coords[i]
            cb = ctk.CTkCheckBox(self.platform_frame, text=platform.upper(), variable=var)
            cb.grid(row=r, column=c, padx=20, pady=15, sticky="w")

        self.git_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.git_frame.pack(padx=20, pady=15, fill="x")

        self.git_var = ctk.BooleanVar(value=False)
        self.git_cb = ctk.CTkCheckBox(self.git_frame, text="Initialize Git Repository & Add Initial Commit", variable=self.git_var)
        self.git_cb.pack(side="left")

        self.create_btn = ctk.CTkButton(self, text="Create Project", font=ctk.CTkFont(size=16, weight="bold"), height=45, command=self.create_project)
        self.create_btn.pack(padx=20, pady=(25, 20), fill="x")

    def center_window(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def create_project(self):
        proj_name = self.name_entry.get().strip()
        if not proj_name or not re.match(r'^[a-z][a-z0-9_]*$', proj_name):
            messagebox.showerror("Invalid Project Name", "Use lowercase alphanumeric and underscores only.", parent=self)
            return

        full_path = os.path.join(self.workspace_dir, proj_name)
        if os.path.exists(full_path):
            messagebox.showerror("Error", "Folder name already exists!", parent=self)
            return

        selected_platforms = [p for p, var in self.platforms.items() if var.get()]
        if not selected_platforms:
            messagebox.showerror("Error", "Select at least one target platform.", parent=self)
            return

        try:
            self.create_btn.configure(state="disabled", text="Generating Boilerplate...")
            self.update()

            os.chdir(self.workspace_dir)
            subprocess.run(["flutter", "create", f"--platforms={','.join(selected_platforms)}", proj_name], capture_output=True, shell=True, check=True)

            if self.git_var.get():
                os.chdir(full_path)
                subprocess.run(["git", "init"], capture_output=True, shell=True)
                subprocess.run(["git", "add", "."], capture_output=True, shell=True)
                subprocess.run(["git", "commit", "-m", "Initial commit from Launchpad"], capture_output=True, shell=True)

            subprocess.Popen(["code", "."], shell=True, cwd=full_path)
            self.parent.destroy()
        except Exception as e:
            messagebox.showerror("Flutter Error", f"Command failed:\n\n{e}", parent=self)
            self.create_btn.configure(state="normal", text="Create Project")


class FlutterLaunchpadApp(ctk.CTk):
    """The Primary App Dashboard Window Workspace Interface."""

    def __init__(self):
        super().__init__()

        self.title("Flutter Launchpad")
        self.center_window(580, 650)
        self.resizable(False, False)

        self.dev_name = get_git_username()
        
        # ---- Profile Panel Layout ----
        self.profile_frame = ctk.CTkFrame(self, fg_color="gray14", height=60, corner_radius=8)
        self.profile_frame.pack(padx=20, pady=(15, 5), fill="x")
        self.profile_frame.pack_propagate(False)

        self.avatar_image = None
        try:
            avatar_url = f"https://github.com/{self.dev_name.replace(' ', '')}.png"
            req = urllib.request.Request(avatar_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                pil_img = Image.open(io.BytesIO(response.read()))
            self.avatar_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(36, 36))
        except Exception: pass

        if self.avatar_image:
            ctk.CTkLabel(self.profile_frame, image=self.avatar_image, text="").pack(side="left", padx=(15, 10))
        else:
            ctk.CTkLabel(self.profile_frame, text="👤", font=ctk.CTkFont(size=22)).pack(side="left", padx=(15, 10))

        ctk.CTkLabel(self.profile_frame, text=f"Active Workspace Profile: {self.dev_name}", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", pady=15)

        # ---- Directory Select Tools ----
        ctk.CTkLabel(self, text="Current Workspace:", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=20, pady=(10, 5), anchor="w")

        self.loc_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.loc_frame.pack(padx=20, pady=5, fill="x")

        self.loc_entry = ctk.CTkEntry(self.loc_frame, placeholder_text="Select workspace folder...", width=400)
        self.loc_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.loc_entry.bind("<FocusOut>", lambda e: self.scan_workspace())
        self.loc_entry.bind("<Return>", lambda e: self.scan_workspace())

        ctk.CTkButton(self.loc_frame, text="Change", width=90, command=self.browse_workspace).pack(side="right")

        # ---- Action Management Operations Rows ----
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.pack(padx=20, pady=(15, 10), fill="x")

        ctk.CTkLabel(self.action_frame, text="Your Projects", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", anchor="w")

        self.new_proj_btn = ctk.CTkButton(
            self.action_frame, text="+ Create New", width=110, fg_color="#1f6aa5", hover_color="#144870", font=ctk.CTkFont(weight="bold"), command=self.open_creation_window
        )
        self.new_proj_btn.pack(side="right", padx=(5, 0))

        self.clone_btn = ctk.CTkButton(
            self.action_frame, text="📥 Clone Repo", width=110, fg_color="#2b7a78", hover_color="#175d5b", font=ctk.CTkFont(weight="bold"), command=self.clone_github_repo
        )
        self.clone_btn.pack(side="right")

        self.projects_scroll = ctk.CTkScrollableFrame(self, width=530, height=350, label_text="Project Manager - Run live deployments or open workspaces")
        self.projects_scroll.pack(padx=20, pady=10, fill="both", expand=True)

        self.load_last_location()

    def center_window(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def load_last_location(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    last_path = config.get("last_location", "")
                    if os.path.exists(last_path):
                        self.loc_entry.insert(0, last_path)
                        self.scan_workspace()
            except Exception: pass

    def save_location(self, path):
        try:
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
            config["last_location"] = path
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f)
        except Exception: pass

    def browse_workspace(self):
        directory = filedialog.askdirectory()
        if directory:
            self.loc_entry.delete(0, tk.END)
            self.loc_entry.insert(0, directory)
            self.save_location(directory)
            self.scan_workspace()

    def scan_workspace(self):
        for widget in self.projects_scroll.winfo_children():
            widget.destroy()

        target_dir = self.loc_entry.get().strip()
        if not target_dir or not os.path.exists(target_dir):
            ctk.CTkLabel(self.projects_scroll, text="No valid workspace directory selected.").pack(pady=20)
            return

        found_projects = []
        try:
            for item in os.listdir(target_dir):
                full_item_path = os.path.join(target_dir, item)
                if os.path.isdir(full_item_path) and os.path.exists(os.path.join(full_item_path, "pubspec.yaml")):
                    found_projects.append(item)
        except Exception as e:
            ctk.CTkLabel(self.projects_scroll, text=f"Error reading directory:\n{e}").pack(pady=20)
            return

        if not found_projects:
            ctk.CTkLabel(self.projects_scroll, text="No existing Flutter projects discovered here.", font=ctk.CTkFont(slant="italic")).pack(pady=30)
            return

        for project in found_projects:
            proj_path = os.path.join(target_dir, project)
            row_frame = ctk.CTkFrame(self.projects_scroll, fg_color="transparent")
            row_frame.pack(fill="x", padx=5, pady=4)

            # Direct Code Launch Button
            ctk.CTkButton(
                row_frame, text=f"📂  {project}", anchor="w", height=38, font=ctk.CTkFont(size=13),
                fg_color="gray20", hover_color="gray25", command=lambda p=proj_path: self.open_project(p)
            ).pack(side="left", fill="x", expand=True, padx=(0, 4))

            # Dedicated Pipeline Run Pop-Up Button on Main Window
            ctk.CTkButton(
                row_frame, text="▶ Run", width=65, height=38, fg_color="gray22", hover_color="gray30",
                font=ctk.CTkFont(weight="bold"), command=lambda name=project, path=proj_path: RunProjectWindow(self, name, path)
            ).pack(side="left", padx=(0, 4))

            # Repository Configuration Settings Cog Wheel Button
            ctk.CTkButton(
                row_frame, text="⚙", width=38, height=38, fg_color="gray25", hover_color="gray35",
                font=ctk.CTkFont(size=16), command=lambda name=project, path=proj_path: self.open_settings_window(name, path)
            ).pack(side="right")

    def clone_github_repo(self):
        workspace_dir = self.loc_entry.get().strip()
        if not workspace_dir or not os.path.exists(workspace_dir):
            messagebox.showerror("Workspace Error", "Select a workspace directory first.")
            return

        repo_url = simpledialog.askstring("Clone Git Repository", "Enter Repository Remote URL:")
        if not repo_url: return

        try:
            os.chdir(workspace_dir)
            self.clone_btn.configure(state="disabled", text="Cloning Repo...")
            self.update()
            subprocess.run(["git", "clone", repo_url], capture_output=True, text=True, shell=True, check=True)
            messagebox.showinfo("Success", "Repository successfully cloned!")
            self.scan_workspace()
        except Exception as e:
            messagebox.showerror("Clone Error", f"Git operation failed:\n\n{e}")
        finally:
            self.clone_btn.configure(state="normal", text="📥 Clone Repo")

    def open_project(self, project_path):
        if os.path.exists(project_path):
            subprocess.Popen(["code", "."], shell=True, cwd=project_path)
            self.destroy()

    def open_creation_window(self):
        workspace_dir = self.loc_entry.get().strip()
        if not workspace_dir or not os.path.exists(workspace_dir):
            messagebox.showerror("Workspace Error", "Choose a workspace first.")
            return
        CreateProjectWindow(self, workspace_dir)

    def open_settings_window(self, project_name, project_path):
        ProjectSettingsWindow(self, project_name, project_path, self.dev_name)


if __name__ == "__main__":
    app = FlutterLaunchpadApp()
    app.mainloop()