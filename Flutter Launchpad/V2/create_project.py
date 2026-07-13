import os
import re
import subprocess
from tkinter import messagebox
import customtkinter as ctk

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