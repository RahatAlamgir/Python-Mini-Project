"""Main CustomTkinter Window layout and UI interactions."""

import json
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import requests

from app_state import DEFAULT_JSON, AppStateManager
from converter import JsonToDartConverter
from highlighter import TokenHighlighter
from ui.code_editor import CodeEditor


class MainWindow(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("JsonToDart Studio")
        self.geometry("1200x800")
        self.minsize(950, 650)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.highlighter = TokenHighlighter()

        # Build UI layout
        self._build_top_bar()
        self._build_options_bar()
        self._build_api_bar()
        self._build_workspace()

        # Setup token colors
        self.highlighter.setup_text_tags(self.json_editor.text)
        self.highlighter.setup_text_tags(self.dart_editor.text)

        # Load saved data & compute initial run
        self._load_saved_state()
        self.convert_json()

    def _build_top_bar(self):
        self.top_bar = ctk.CTkFrame(self, corner_radius=0)
        self.top_bar.pack(side="top", fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            self.top_bar,
            text="Class Name:",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left", padx=(10, 2), pady=10)

        self.class_entry = ctk.CTkEntry(self.top_bar, width=150)
        self.class_entry.insert(0, "UserModel")
        self.class_entry.pack(side="left", padx=5, pady=10)
        self.class_entry.bind("<KeyRelease>", lambda e: self.convert_json())

        ctk.CTkLabel(
            self.top_bar,
            text="Generator:",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left", padx=(15, 2), pady=10)

        self.generator_option = ctk.CTkOptionMenu(
            self.top_bar,
            values=["Standard Dart", "Freezed Package"],
            command=self.on_generator_change,
        )
        self.generator_option.pack(side="left", padx=5, pady=10)

        self.export_btn = ctk.CTkButton(
            self.top_bar,
            text="💾 Save .dart",
            fg_color="transparent",
            border_width=1,
            command=self.save_file,
        )
        self.export_btn.pack(side="right", padx=10, pady=10)

        self.copy_btn = ctk.CTkButton(
            self.top_bar,
            text="📋 Copy Code",
            fg_color="transparent",
            border_width=1,
            command=self.copy_to_clipboard,
        )
        self.copy_btn.pack(side="right", padx=5, pady=10)

    def _build_options_bar(self):
        self.options_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.options_bar.pack(side="top", fill="x", padx=10, pady=(0, 5))

        self.null_switch = ctk.CTkSwitch(
            self.options_bar,
            text="Nullable Fields (?)",
            command=self.convert_json,
        )
        self.null_switch.select()
        self.null_switch.pack(side="left", padx=10)

        self.copy_with_switch = ctk.CTkSwitch(
            self.options_bar,
            text="Generate copyWith()",
            command=self.convert_json,
        )
        self.copy_with_switch.pack(side="left", padx=10)

        self.equatable_switch = ctk.CTkSwitch(
            self.options_bar,
            text="Extend Equatable",
            command=self.convert_json,
        )
        self.equatable_switch.pack(side="left", padx=10)

    def _build_api_bar(self):
        self.api_bar = ctk.CTkFrame(self, corner_radius=6)
        self.api_bar.pack(side="top", fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(
            self.api_bar,
            text="🌐 API URL:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left", padx=(10, 5), pady=6)

        self.url_entry = ctk.CTkEntry(
            self.api_bar, placeholder_text="https://api.example.com/data"
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=5, pady=6)

        self.fetch_btn = ctk.CTkButton(
            self.api_bar,
            text="Fetch JSON",
            width=90,
            command=self.fetch_api_json,
        )
        self.fetch_btn.pack(side="right", padx=10, pady=6)

    def _build_workspace(self):
        self.workspace_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.workspace_frame.pack(
            side="top", fill="both", expand=True, padx=10, pady=5
        )

        self.workspace_frame.grid_columnconfigure(0, weight=1, uniform="group1")
        self.workspace_frame.grid_columnconfigure(1, weight=1, uniform="group1")
        self.workspace_frame.grid_rowconfigure(0, weight=1)

        # Left Panel (Input)
        self.left_frame = ctk.CTkFrame(self.workspace_frame)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.left_frame.grid_rowconfigure(1, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        self.input_tool_frame = ctk.CTkFrame(
            self.left_frame, fg_color="transparent"
        )
        self.input_tool_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(
            self.input_tool_frame,
            text="JSON Input",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left", padx=5)

        self.status_badge = ctk.CTkLabel(
            self.input_tool_frame,
            text="● Valid JSON",
            text_color="#2ecc71",
            font=ctk.CTkFont(size=11),
        )
        self.status_badge.pack(side="left", padx=10)

        ctk.CTkButton(
            self.input_tool_frame,
            text="Clear",
            width=50,
            height=24,
            fg_color="transparent",
            command=self.clear_json,
        ).pack(side="right", padx=2)

        ctk.CTkButton(
            self.input_tool_frame,
            text="Format JSON",
            width=80,
            height=24,
            command=self.format_json,
        ).pack(side="right", padx=2)

        ctk.CTkButton(
            self.input_tool_frame,
            text="📂 Load File",
            width=80,
            height=24,
            fg_color="transparent",
            border_width=1,
            command=self.load_json_file,
        ).pack(side="right", padx=2)

        self.json_editor = CodeEditor(self.left_frame, font_size=11)
        self.json_editor.grid(
            row=1, column=0, sticky="nsew", padx=10, pady=(0, 10)
        )
        self.json_editor.text.bind("<KeyRelease>", self.on_json_type)

        # Right Panel (Output)
        self.right_frame = ctk.CTkFrame(self.workspace_frame)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.right_frame,
            text="Dart Model Output",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=10, pady=5)

        self.dart_editor = CodeEditor(self.right_frame, font_size=11)
        self.dart_editor.grid(
            row=1, column=0, sticky="nsew", padx=10, pady=(0, 10)
        )

    # --- Actions and Event Handlers ---
    def fetch_api_json(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning(
                "Warning", "Please enter an API URL to fetch."
            )
            return

        self.fetch_btn.configure(state="disabled", text="Fetching...")

        def worker():
            try:
                res = requests.get(url, timeout=10)
                res.raise_for_status()
                res_data = res.json()

                if isinstance(res_data, list):
                    payload = (
                        res_data[0]
                        if len(res_data) > 0 and isinstance(res_data[0], dict)
                        else {}
                    )
                else:
                    payload = res_data

                formatted_json = json.dumps(payload, indent=2)
                self.after(0, lambda: self._update_fetched_json(formatted_json))
            except requests.exceptions.RequestException as e:
                self.after(
                    0,
                    lambda: messagebox.showerror(
                        "Fetch Error", f"Failed to fetch data:\n{str(e)}"
                    ),
                )
            finally:
                self.after(
                    0,
                    lambda: self.fetch_btn.configure(
                        state="normal", text="Fetch JSON"
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

    def _update_fetched_json(self, formatted_json: str):
        self.highlighter.apply_highlighting(
            self.json_editor.text,
            formatted_json,
            self.highlighter.json_lexer,
        )
        self.validate_json()
        self.convert_json()

    def on_json_type(self, event=None):
        raw_json = self.json_editor.get_text()
        self.highlighter.apply_highlighting(
            self.json_editor.text, raw_json, self.highlighter.json_lexer
        )
        self.validate_json()
        self.convert_json()

    def on_generator_change(self, choice):
        state = "disabled" if choice == "Freezed Package" else "normal"
        self.null_switch.configure(state=state)
        self.copy_with_switch.configure(state=state)
        self.equatable_switch.configure(state=state)
        self.convert_json()

    def validate_json(self) -> bool:
        raw_json = self.json_editor.get_text()
        if not raw_json:
            self.status_badge.configure(text="", text_color="gray")
            return False
        try:
            json.loads(raw_json)
            self.status_badge.configure(text="● Valid JSON", text_color="#2ecc71")
            return True
        except json.JSONDecodeError:
            self.status_badge.configure(
                text="● Invalid JSON", text_color="#e74c3c"
            )
            return False

    def load_json_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.highlighter.apply_highlighting(
                    self.json_editor.text, content, self.highlighter.json_lexer
                )
                self.validate_json()
                self.convert_json()

    def format_json(self):
        raw_json = self.json_editor.get_text()
        if raw_json:
            try:
                parsed = json.loads(raw_json)
                formatted = json.dumps(parsed, indent=2)
                self.highlighter.apply_highlighting(
                    self.json_editor.text,
                    formatted,
                    self.highlighter.json_lexer,
                )
                self.validate_json()
            except json.JSONDecodeError as e:
                messagebox.showerror(
                    "Invalid JSON", f"Cannot format invalid JSON:\n{str(e)}"
                )

    def clear_json(self):
        self.json_editor.set_text("")
        self.dart_editor.set_text("")
        self.validate_json()

    def convert_json(self):
        raw_json = self.json_editor.get_text()
        class_name = self.class_entry.get().strip() or "AutogeneratedClass"
        generator_mode = self.generator_option.get()

        if not raw_json:
            self.dart_editor.set_text("")
            return

        try:
            data = json.loads(raw_json)
            if isinstance(data, list):
                if len(data) > 0 and isinstance(data[0], dict):
                    data = data[0]
                else:
                    return

            if not isinstance(data, dict):
                return

            if generator_mode == "Freezed Package":
                dart_code = JsonToDartConverter.generate_freezed_class(
                    class_name, data
                )
            else:
                dart_code = JsonToDartConverter.generate_standard_class(
                    class_name,
                    data,
                    is_optional=bool(self.null_switch.get()),
                    gen_copy_with=bool(self.copy_with_switch.get()),
                    gen_equatable=bool(self.equatable_switch.get()),
                )

            self.highlighter.apply_highlighting(
                self.dart_editor.text, dart_code, self.highlighter.dart_lexer
            )
        except json.JSONDecodeError:
            pass

    def copy_to_clipboard(self):
        code = self.dart_editor.get_text()
        if code:
            self.clipboard_clear()
            self.clipboard_append(code)
            self.copy_btn.configure(text="✅ Copied!")
            self.after(
                2000, lambda: self.copy_btn.configure(text="📋 Copy Code")
            )

    def save_file(self):
        code = self.dart_editor.get_text()
        if not code:
            messagebox.showwarning("Warning", "No Dart code to save.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".dart",
            filetypes=[("Dart Files", "*.dart"), ("All Files", "*.*")],
            initialfile=f"{self.class_entry.get().strip().lower()}.dart",
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)
            messagebox.showinfo("Success", f"File saved to {file_path}")

    def _load_saved_state(self):
        state = AppStateManager.load_state()
        if state:
            self.class_entry.delete(0, tk.END)
            self.class_entry.insert(0, state.get("class_name", "UserModel"))

            generator = state.get("generator", "Standard Dart")
            self.generator_option.set(generator)

            if state.get("nullable", True):
                self.null_switch.select()
            else:
                self.null_switch.deselect()

            if state.get("copy_with", False):
                self.copy_with_switch.select()
            else:
                self.copy_with_switch.deselect()

            if state.get("equatable", False):
                self.equatable_switch.select()
            else:
                self.equatable_switch.deselect()

            url_val = state.get("url", "")
            if url_val:
                self.url_entry.insert(0, url_val)

            json_val = state.get("json_data", DEFAULT_JSON)
            self.highlighter.apply_highlighting(
                self.json_editor.text, json_val, self.highlighter.json_lexer
            )
            self.on_generator_change(generator)
            self.validate_json()
        else:
            self.highlighter.apply_highlighting(
                self.json_editor.text, DEFAULT_JSON, self.highlighter.json_lexer
            )
            self.validate_json()

    def on_close(self):
        state = {
            "class_name": self.class_entry.get().strip(),
            "generator": self.generator_option.get(),
            "nullable": bool(self.null_switch.get()),
            "copy_with": bool(self.copy_with_switch.get()),
            "equatable": bool(self.equatable_switch.get()),
            "url": self.url_entry.get().strip(),
            "json_data": self.json_editor.get_text(),
        }
        AppStateManager.save_state(state)
        self.destroy()