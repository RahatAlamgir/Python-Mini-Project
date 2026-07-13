import os
import shutil
import stat
import subprocess
from tkinter import messagebox
import customtkinter as ctk
from utils import onerror

class ProjectSettingsWindow(ctk.CTkToplevel):
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

        self.header_label = ctk.CTkLabel(self, text=f"Repository Settings: {project_name}", font=ctk.CTkFont(size=15, weight="bold"))
        self.header_label.pack(padx=20, pady=(15, 5), anchor="w")

        self.git_frame = ctk.CTkFrame(self)
        self.git_frame.pack(padx=20, pady=8, fill="x")

        has_git = os.path.exists(os.path.join(project_path, ".git"))
        git_status_text = "Git Repository Status: Active" if has_git else "Git Repository Status: Missing"
        
        self.git_lbl = ctk.CTkLabel(self.git_frame, text=git_status_text, font=ctk.CTkFont(size=12))
        self.git_lbl.pack(side="left", padx=15, pady=12)

        self.git_btn = ctk.CTkButton(self.git_frame, text="Init Git", width=90, state="disabled" if has_git else "normal", command=self.initialize_git)
        self.git_btn.pack(side="right", padx=15, pady=12)

        self.git_ops_frame = ctk.CTkFrame(self)
        self.git_ops_frame.pack(padx=20, pady=8, fill="x")
        
        self.git_ops_lbl = ctk.CTkLabel(self.git_ops_frame, text="Git Operations (Commit & Push):", font=ctk.CTkFont(size=13, weight="bold"))
        self.git_ops_lbl.pack(padx=15, pady=(10, 5), anchor="w")
        
        self.commit_entry = ctk.CTkEntry(self.git_ops_frame, placeholder_text="Enter commit message...", width=440)
        self.commit_entry.pack(padx=15, pady=5, fill="x")
        
        self.push_btn = ctk.CTkButton(self.git_ops_frame, text="Commit All & Push to Remote", font=ctk.CTkFont(weight="bold"), state="normal" if has_git else "disabled", command=self.git_commit_and_push)
        self.push_btn.pack(padx=15, pady=(5, 15), fill="x")

        self.platform_frame = ctk.CTkFrame(self)
        self.platform_frame.pack(padx=20, pady=8, fill="x")

        self.platform_lbl = ctk.CTkLabel(self.platform_frame, text="Active Platform Folders:", font=ctk.CTkFont(size=13, weight="bold"))
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

            cb = ctk.CTkCheckBox(self.grid_container, text=plat.upper(), variable=self.checkbox_vars[plat])
            cb.grid(row=r, column=c, padx=15, pady=10, sticky="w")

        self.sync_btn = ctk.CTkButton(self, text="Sync & Update Platforms", font=ctk.CTkFont(weight="bold"), command=self.sync_platforms)
        self.sync_btn.pack(padx=20, pady=8, fill="x")

        self.delete_btn = ctk.CTkButton(self, text="⚠️ Delete Entire Project Folder", fg_color="#8b0000", hover_color="#5a0000", font=ctk.CTkFont(weight="bold"), height=38, command=self.delete_project)
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
                    confirm_push = messagebox.askyesno("Ownership Warning", f"Repository target URL belongs to another host structure:\n{remote_url}\n\nDo you still want to force attempt the push anyway?", parent=self)
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
        confirm = messagebox.askyesno("CRITICAL WARNING", f"Permanently erase folder '{self.project_name}'? This cannot be undone!", parent=self)
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