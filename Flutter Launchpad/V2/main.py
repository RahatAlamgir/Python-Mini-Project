import os
import json
import io
import urllib.request
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image

# Import decoupled window classes
from utils import get_git_username, CONFIG_FILE
from sdk_manager import AndroidSDKManagerWindow
from device_manager import AndroidDeviceManagerWindow
from run_project import RunProjectWindow
from project_settings import ProjectSettingsWindow
from create_project import CreateProjectWindow

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class CustomCloneDialog(ctk.CTkToplevel):
    """A modern, styled modal window for capturing Git repository URL inputs."""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.result = None

        self.title("Clone Git Repository")
        self.center_window(460, 200)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Input Prompt Header
        ctk.CTkLabel(
            self, 
            text="Enter Remote Repository URL:", 
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(padx=20, pady=(20, 10), anchor="w")

        # URL Input Field
        self.url_entry = ctk.CTkEntry(
            self, 
            placeholder_text="e.g., https://github.com/username/repository.git", 
            width=420
        ).pack(padx=20, pady=5)
        
        # Focus input and bind Enter key to submit
        self.after(100, lambda: self.focus_entry())

        # Buttons Panel
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(20, 15), fill="x")

        self.cancel_btn = ctk.CTkButton(
            btn_frame, 
            text="Cancel", 
            fg_color="gray25", 
            hover_color="gray35", 
            width=100, 
            command=self.on_cancel
        ).pack(side="right", padx=(10, 0))

        self.clone_btn = ctk.CTkButton(
            btn_frame, 
            text="📥 Clone Repo", 
            fg_color="#2b7a78", 
            hover_color="#175d5b", 
            font=ctk.CTkFont(weight="bold"), 
            width=130, 
            command=self.on_submit
        ).pack(side="right")

    def focus_entry(self):
        # Access entry since pack() returns None if chained inline
        for widget in self.winfo_children():
            if isinstance(widget, ctk.CTkEntry):
                widget.focus_set()
                widget.bind("<Return>", lambda e: self.on_submit())
                self._entry_widget = widget

    def center_window(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def on_submit(self):
        self.result = self._entry_widget.get().strip()
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()


class FlutterLaunchpadApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Flutter Launchpad")
        self.center_window(610, 650)
        self.resizable(False, False)

        self.dev_name = get_git_username()
        
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

        ctk.CTkLabel(self, text="Current Workspace:", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=20, pady=(10, 5), anchor="w")

        self.loc_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.loc_frame.pack(padx=20, pady=5, fill="x")

        self.loc_entry = ctk.CTkEntry(self.loc_frame, placeholder_text="Select workspace folder...", width=400)
        self.loc_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.loc_entry.bind("<FocusOut>", lambda e: self.scan_workspace())
        self.loc_entry.bind("<Return>", lambda e: self.scan_workspace())

        ctk.CTkButton(self.loc_frame, text="Change", width=90, command=self.browse_workspace).pack(side="right")

        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.pack(padx=20, pady=(15, 10), fill="x")

        ctk.CTkLabel(self.action_frame, text="Your Projects", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", anchor="w")

        self.sdk_mgr_btn = ctk.CTkButton(self.action_frame, text="🤖 SDK Manager", width=110, fg_color="#5d4037", hover_color="#4e342e", font=ctk.CTkFont(weight="bold"), command=self.open_sdk_manager)
        self.sdk_mgr_btn.pack(side="right", padx=(5, 0))

        self.avd_mgr_btn = ctk.CTkButton(self.action_frame, text="📱 AVD Manager", width=110, fg_color="#37474f", hover_color="#263238", font=ctk.CTkFont(weight="bold"), command=self.open_device_manager)
        self.avd_mgr_btn.pack(side="right", padx=(5, 0))

        self.new_proj_btn = ctk.CTkButton(self.action_frame, text="+ Create", width=75, fg_color="#1f6aa5", hover_color="#144870", font=ctk.CTkFont(weight="bold"), command=self.open_creation_window)
        self.new_proj_btn.pack(side="right", padx=(5, 0))

        self.clone_btn = ctk.CTkButton(self.action_frame, text="📥 Clone", width=75, fg_color="#2b7a78", hover_color="#175d5b", font=ctk.CTkFont(weight="bold"), command=self.clone_github_repo)
        self.clone_btn.pack(side="right")

        self.projects_scroll = ctk.CTkScrollableFrame(self, width=560, height=350, label_text="Project Manager - Run live deployments or open workspaces")
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
                with open(CONFIG_FILE, "r") as f: config = json.load(f)
            config["last_location"] = path
            with open(CONFIG_FILE, "w") as f: json.dump(config, f)
        except Exception: pass

    def browse_workspace(self):
        directory = filedialog.askdirectory()
        if directory:
            self.loc_entry.delete(0, tk.END)
            self.loc_entry.insert(0, directory)
            self.save_location(directory)
            self.scan_workspace()

    def scan_workspace(self):
        for widget in self.projects_scroll.winfo_children(): widget.destroy()
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

            ctk.CTkButton(row_frame, text=f"📂  {project}", anchor="w", height=38, font=ctk.CTkFont(size=13), fg_color="gray20", hover_color="gray25", command=lambda p=proj_path: self.open_project(p)).pack(side="left", fill="x", expand=True, padx=(0, 4))
            ctk.CTkButton(row_frame, text="▶ Run", width=65, height=38, fg_color="#2e7d32", hover_color="#1b5e20", font=ctk.CTkFont(weight="bold"), command=lambda name=project, path=proj_path: RunProjectWindow(self, name, path)).pack(side="left", padx=(0, 4))
            ctk.CTkButton(row_frame, text="⚙", width=38, height=38, fg_color="gray25", hover_color="gray35", font=ctk.CTkFont(size=16), command=lambda name=project, path=proj_path: self.open_settings_window(name, path)).pack(side="right")

    def clone_github_repo(self):
        workspace_dir = self.loc_entry.get().strip()
        if not workspace_dir or not os.path.exists(workspace_dir):
            messagebox.showerror("Workspace Error", "Select a workspace directory first.")
            return

        # Open the modern Custom Window instead of simpledialog
        dialog = CustomCloneDialog(self)
        self.wait_window(dialog)
        repo_url = dialog.result

        if not repo_url: return
        try:
            os.chdir(workspace_dir)
            self.clone_btn.configure(state="disabled", text="Cloning...")
            self.update()
            subprocess.run(["git", "clone", repo_url], capture_output=True, text=True, shell=True, check=True)
            messagebox.showinfo("Success", "Repository successfully cloned!")
            self.scan_workspace()
        except Exception as e: messagebox.showerror("Clone Error", f"Git operation failed:\n\n{e}")
        finally: self.clone_btn.configure(state="normal", text="📥 Clone")

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

    def open_sdk_manager(self):
        AndroidSDKManagerWindow(self)

    def open_device_manager(self):
        AndroidDeviceManagerWindow(self)

if __name__ == "__main__":
    app = FlutterLaunchpadApp()
    app.mainloop()