from ast import pattern
import json
import os
import re
import shutil
import stat
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

CONFIG_FILE = "config.json"

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


def onerror(func, path, exc_info):
    """Helper to clear Windows Read-Only flags when deleting files (Fixes WinError 5)."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


class ProjectSettingsWindow(ctk.CTkToplevel):
    """An advanced settings dashboard for managing existing Flutter projects."""

    def __init__(self, parent, project_name, project_path):
        super().__init__(parent)
        self.parent = parent
        self.project_name = project_name
        self.project_path = project_path

        self.title(f"Manage: {project_name}")
        self.center_window(480, 560)
        
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # ---- Title Header ----
        self.header_label = ctk.CTkLabel(
            self, text=f"Project: {project_name}", font=ctk.CTkFont(size=16, weight="bold")
        )
        self.header_label.pack(padx=20, pady=(20, 10), anchor="w")

        # ---- Git Tool Section ----
        self.git_frame = ctk.CTkFrame(self)
        self.git_frame.pack(padx=20, pady=10, fill="x")

        has_git = os.path.exists(os.path.join(project_path, ".git"))
        git_status_text = "Git Repository Status: Active" if has_git else "Git Repository Status: Missing"
        
        self.git_lbl = ctk.CTkLabel(self.git_frame, text=git_status_text, font=ctk.CTkFont(size=12))
        self.git_lbl.pack(side="left", padx=15, pady=15)

        self.git_btn = ctk.CTkButton(
            self.git_frame,
            text="Init Git",
            width=90,
            state="normal" if not has_git else "disabled",
            command=self.initialize_git,
        )
        self.git_btn.pack(side="right", padx=15, pady=15)

        # ---- Dynamic Platform Management Section ----
        self.platform_frame = ctk.CTkFrame(self)
        self.platform_frame.pack(padx=20, pady=10, fill="x")

        self.platform_lbl = ctk.CTkLabel(
            self.platform_frame, text="Active Platform Folders:", font=ctk.CTkFont(size=13, weight="bold")
        )
        self.platform_lbl.pack(padx=15, pady=(10, 5), anchor="w")

        # FIX: Separate container specifically dedicated to grid elements
        self.grid_container = ctk.CTkFrame(self.platform_frame, fg_color="transparent")
        self.grid_container.pack(padx=15, pady=(0, 10), fill="x")

        # Core platforms to track
        self.supported_platforms = ["android", "ios", "web", "macos", "windows", "linux"]
        self.checkbox_vars = {}

        # Render checkboxes reflecting actual folders found on storage
        grid_coords = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]
        for i, plat in enumerate(self.supported_platforms):
            r, c = grid_coords[i]
            
            # Check if directory folder exists physically
            folder_exists = os.path.exists(os.path.join(self.project_path, plat))
            self.checkbox_vars[plat] = ctk.BooleanVar(value=folder_exists)

            cb = ctk.CTkCheckBox(
                self.grid_container,  # Target the container, not the parent frame
                text=plat.upper(), 
                variable=self.checkbox_vars[plat]
            )
            cb.grid(row=r, column=c, padx=15, pady=12, sticky="w")

        # ---- Apply Platform Sync Changes ----
        self.sync_btn = ctk.CTkButton(
            self,
            text="Sync & Update Platforms",
            font=ctk.CTkFont(weight="bold"),
            command=self.sync_platforms
        )
        self.sync_btn.pack(padx=20, pady=10, fill="x")

        # ---- Separator Row ----
        self.sep = ctk.CTkFrame(self, height=2, fg_color="gray30")
        self.sep.pack(padx=20, pady=15, fill="x")

        # ---- Danger Zone (Delete) ----
        self.delete_btn = ctk.CTkButton(
            self,
            text="⚠️ Delete Entire Project Folder",
            fg_color="#8b0000",
            hover_color="#5a0000",
            font=ctk.CTkFont(weight="bold"),
            height=40,
            command=self.delete_project,
        )
        self.delete_btn.pack(padx=20, pady=10, fill="x")

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
        except Exception as e:
            messagebox.showerror("Git Error", f"Failed to initialize Git:\n{e}", parent=self)

    def sync_platforms(self):
        """Adds unchecked missing platforms and safely wipes unchecked platform folders."""
        try:
            os.chdir(self.project_path)
            platforms_to_add = []

            for plat, var in self.checkbox_vars.items():
                folder_path = os.path.join(self.project_path, plat)
                is_checked = var.get()
                folder_exists = os.path.exists(folder_path)

                if is_checked and not folder_exists:
                    platforms_to_add.append(plat)
                elif not is_checked and folder_exists:
                    shutil.rmtree(folder_path, onerror=onerror)

            if platforms_to_add:
                self.sync_btn.configure(state="disabled", text="Injecting Platform Boilerplate...")
                self.update()
                
                platforms_str = ",".join(platforms_to_add)
                command = ["flutter", "create", f"--platforms={platforms_str}", "."]
                subprocess.run(command, capture_output=True, shell=True, check=True)

            messagebox.showinfo("Success", "Project platform directories synced successfully!", parent=self)
        except Exception as e:
            messagebox.showerror("Sync Error", f"Failed to sync layout parameters:\n{e}", parent=self)
        finally:
            self.sync_btn.configure(state="normal", text="Sync & Update Platforms")

    def delete_project(self):
        confirm = messagebox.askyesno(
            "CRITICAL WARNING",
            f"Are you absolutely sure you want to completely delete '{self.project_name}'?\n\nThis will permanently erase the folder and cannot be undone!",
            parent=self
        )
        if confirm:
            try:
                shutil.rmtree(self.project_path, onerror=onerror)
                messagebox.showinfo("Deleted", "Project directory deleted successfully.", parent=self)
                self.parent.scan_workspace()
                self.destroy()
            except Exception as e:
                messagebox.showerror("Delete Error", f"Could not clear project contents:\n{e}", parent=self)

class CreateProjectWindow(ctk.CTkToplevel):
    """The pop-up view to configure and deploy a new project framework."""
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
        if not proj_name:
            messagebox.showerror("Error", "Please enter a project name.", parent=self)
            return
        if not re.match(r'^[a-z][a-z0-9_]*$', proj_name):
            messagebox.showerror(
                "Invalid Project Name", 
                "Flutter project names must:\n"
                "• Start with a lowercase letter\n"
                "• Contain ONLY lowercase letters, numbers, and underscores\n\n"
                "Example: my_awesome_app", 
                parent=self
            )
            return

        full_path = os.path.join(self.workspace_dir, proj_name)

        if os.path.exists(full_path):
            messagebox.showerror("Error", f"A folder named '{proj_name}' already exists in this workspace!", parent=self)
            return

        selected_platforms = [p for p, var in self.platforms.items() if var.get()]
        if not selected_platforms:
            messagebox.showerror("Error", "Please select at least one platform.", parent=self)
            return

        platforms_str = ",".join(selected_platforms)
        command = ["flutter", "create", f"--platforms={platforms_str}", proj_name]

        try:
            self.create_btn.configure(state="disabled", text="Generating Boilerplate...")
            self.update()

            os.chdir(self.workspace_dir)
            subprocess.run(command, capture_output=True, text=True, check=True, shell=True)

            if self.git_var.get():
                os.chdir(full_path)
                if not os.path.exists(os.path.join(full_path, ".git")):
                    subprocess.run(["git", "init"], capture_output=True, shell=True)
                subprocess.run(["git", "add", "."], capture_output=True, shell=True)
                subprocess.run(["git", "commit", "-m", "Initial commit from Launchpad"], capture_output=True, shell=True)

            subprocess.Popen(["code", "."], shell=True, cwd=full_path)
            self.parent.destroy()

        except Exception as e:
            messagebox.showerror("Flutter Error", f"Command failed:\n\n{e}", parent=self)
            self.create_btn.configure(state="normal", text="Launch & Open in VS Code")


class FlutterLaunchpadApp(ctk.CTk):
    """The Primary App Drawer Dashboard interface view configuration."""
    def __init__(self):
        super().__init__()

        self.title("Flutter Launchpad")
        self.center_window(550, 600)
        self.resizable(False, False)

        self.loc_label = ctk.CTkLabel(self, text="Current Workspace:", font=ctk.CTkFont(size=14, weight="bold"))
        self.loc_label.pack(padx=20, pady=(20, 5), anchor="w")

        self.loc_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.loc_frame.pack(padx=20, pady=5, fill="x")

        self.loc_entry = ctk.CTkEntry(self.loc_frame, placeholder_text="Select workspace folder...", width=380)
        self.loc_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.loc_entry.bind("<FocusOut>", lambda e: self.scan_workspace())
        self.loc_entry.bind("<Return>", lambda e: self.scan_workspace())

        self.browse_btn = ctk.CTkButton(self.loc_frame, text="Change", width=90, command=self.browse_workspace)
        self.browse_btn.pack(side="right")

        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.pack(padx=20, pady=(20, 10), fill="x")

        self.list_title = ctk.CTkLabel(self.action_frame, text="Your Projects", font=ctk.CTkFont(size=16, weight="bold"))
        self.list_title.pack(side="left", anchor="w")

        self.new_proj_btn = ctk.CTkButton(self.action_frame, text="+ Create New Project", fg_color="#1f6aa5", hover_color="#144870", font=ctk.CTkFont(weight="bold"), command=self.open_creation_window)
        self.new_proj_btn.pack(side="right")

        self.projects_scroll = ctk.CTkScrollableFrame(self, width=510, height=380, label_text="Select a project to open or configure")
        self.projects_scroll.pack(padx=20, pady=10, fill="both", expand=True)

        self.load_last_location()

    def center_window(self, width, height):
        """Calculates and updates window coordinates to perfectly position in the screen center."""
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
            except Exception:
                pass

    def save_location(self, path):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"last_location": path}, f)
        except Exception:
            pass

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
            lbl = ctk.CTkLabel(self.projects_scroll, text="No valid workspace directory selected.")
            lbl.pack(pady=20)
            return

        found_projects = []
        try:
            for item in os.listdir(target_dir):
                full_item_path = os.path.join(target_dir, item)
                if os.path.isdir(full_item_path):
                    if os.path.exists(os.path.join(full_item_path, "pubspec.yaml")):
                        found_projects.append(item)
        except Exception as e:
            lbl = ctk.CTkLabel(self.projects_scroll, text=f"Error reading directory:\n{e}")
            lbl.pack(pady=20)
            return

        if not found_projects:
            lbl = ctk.CTkLabel(self.projects_scroll, text="No existing Flutter projects discovered here.", font=ctk.CTkFont(slant="italic"))
            lbl.pack(pady=30)
            return

        for project in found_projects:
            proj_path = os.path.join(target_dir, project)
            
            row_frame = ctk.CTkFrame(self.projects_scroll, fg_color="transparent")
            row_frame.pack(fill="x", padx=5, pady=4)

            btn = ctk.CTkButton(
                row_frame,
                text=f"📂  {project}",
                anchor="w",
                height=38,
                font=ctk.CTkFont(size=13),
                fg_color="gray20",
                hover_color="gray25",
                command=lambda p=proj_path: self.open_project(p),
            )
            btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

            settings_btn = ctk.CTkButton(
                row_frame,
                text="⚙",
                width=38,
                height=38,
                fg_color="gray25",
                hover_color="gray35",
                font=ctk.CTkFont(size=16),
                command=lambda name=project, path=proj_path: self.open_settings_window(name, path)
            )
            settings_btn.pack(side="right")

    def open_project(self, project_path):
        if os.path.exists(project_path):
            subprocess.Popen(["code", "."], shell=True, cwd=project_path)
            self.destroy()

    def open_creation_window(self):
        workspace_dir = self.loc_entry.get().strip()
        if not workspace_dir or not os.path.exists(workspace_dir):
            messagebox.showerror("Workspace Error", "Please provide or choose a valid Workspace directory before creating a project.")
            return
        CreateProjectWindow(self, workspace_dir)

    def open_settings_window(self, project_name, project_path):
        ProjectSettingsWindow(self, project_name, project_path)


if __name__ == "__main__":
    app = FlutterLaunchpadApp()
    app.mainloop()