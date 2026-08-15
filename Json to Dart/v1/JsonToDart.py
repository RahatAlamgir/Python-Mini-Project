import json
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import requests
from pygments import lex
from pygments.lexers import DartLexer, JsonLexer
from pygments.token import Token

# Enforce Dark Mode globally
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

SETTINGS_FILE = "app_settings.json"

# --- Dark Theme Color Palette for Syntax Highlighting ---
TOKEN_COLORS = {
    Token.Keyword: "#569CD6",          # Blue (class, final, return, import)
    Token.Keyword.Type: "#4EC9B0",     # Teal (String, int, double, bool)
    Token.Name.Class: "#4EC9B0",       # Teal class names
    Token.Name.Function: "#DCDCAA",    # Yellow functions (fromJson, toJson)
    Token.String: "#CE9178",           # Orange/Brown strings
    Token.Number: "#B5CEA8",           # Light green numbers
    Token.Comment: "#6A9955",          # Green comments
    Token.Operator: "#D4D4D4",         # Operators (+, =, ?, :)
    Token.Punctuation: "#808080",       # Brackets and commas
    Token.Name.Variable: "#9CDCFE",     # Blue variables/fields
    Token.Name.Tag: "#569CD6",          # JSON Keys
}


class JsonToDartConverter:

    @staticmethod
    def _capitalize(s: str) -> str:
        return s[0].upper() + s[1:] if s else ""

    @staticmethod
    def _camel_case(s: str) -> str:
        parts = s.replace("-", "_").replace(".", "_").split("_")
        return parts[0] + "".join(p.capitalize() for p in parts[1:])

    @classmethod
    def generate_freezed_class(cls, class_name: str, data: dict) -> str:
        sub_classes = []
        fields = []

        for key, val in data.items():
            field_name = cls._camel_case(key)
            if isinstance(val, bool):
                dart_type = "bool?"
            elif isinstance(val, int):
                dart_type = "int?"
            elif isinstance(val, float):
                dart_type = "double?"
            elif isinstance(val, str):
                dart_type = "String?"
            elif isinstance(val, list):
                if len(val) > 0 and isinstance(val[0], dict):
                    item_class_name = cls._capitalize(field_name) + "Item"
                    dart_type = f"List<{item_class_name}>?"
                    sub_classes.append(
                        cls.generate_freezed_class(item_class_name, val[0])
                    )
                else:
                    item_type = (
                        type(val[0]).__name__ if len(val) > 0 else "dynamic"
                    )
                    item_type = {
                        "str": "String",
                        "int": "int",
                        "float": "double",
                        "bool": "bool",
                    }.get(item_type, "dynamic")
                    dart_type = f"List<{item_type}>?"
            elif isinstance(val, dict):
                nested_class_name = cls._capitalize(field_name)
                dart_type = f"{nested_class_name}?"
                sub_classes.append(
                    cls.generate_freezed_class(nested_class_name, val)
                )
            else:
                dart_type = "dynamic"

            fields.append(f"    {dart_type} {field_name},")

        fields_str = "\n".join(fields)
        file_snake_case = class_name.lower()

        code = f"""import 'package:freezed_annotation/freezed_annotation.dart';

part '{file_snake_case}.freezed.dart';
part '{file_snake_case}.g.dart';

@freezed
class {class_name} with _${class_name} {{
  const factory {class_name}({{
{fields_str}
  }}) = _{class_name};

  factory {class_name}.fromJson(Map<String, dynamic> json) => _${class_name}FromJson(json);
}}"""
        if sub_classes:
            code += "\n\n" + "\n\n".join(sub_classes)
        return code

    @classmethod
    def generate_standard_class(
        cls,
        class_name: str,
        data: dict,
        is_optional: bool = True,
        gen_copy_with: bool = False,
        gen_equatable: bool = False,
    ) -> str:
        sub_classes = []
        fields = []
        constructor_args = []
        from_json_fields = []
        to_json_fields = []
        copy_with_args = []
        copy_with_assignments = []
        equatable_props = []

        nullable = "?" if is_optional else ""

        for key, val in data.items():
            field_name = cls._camel_case(key)
            equatable_props.append(field_name)

            if isinstance(val, bool):
                dart_type = "bool"
                from_json = (
                    f"json['{key}'] as bool?"
                    if is_optional
                    else f"json['{key}'] as bool"
                )
            elif isinstance(val, int):
                dart_type = "int"
                from_json = (
                    f"json['{key}'] as int?"
                    if is_optional
                    else f"json['{key}'] as int"
                )
            elif isinstance(val, float):
                dart_type = "double"
                from_json = (
                    f"(json['{key}'] as num?)?.toDouble()"
                    if is_optional
                    else f"(json['{key}'] as num).toDouble()"
                )
            elif isinstance(val, str):
                dart_type = "String"
                from_json = (
                    f"json['{key}'] as String?"
                    if is_optional
                    else f"json['{key}'] as String"
                )
            elif isinstance(val, list):
                if len(val) > 0 and isinstance(val[0], dict):
                    item_class_name = cls._capitalize(field_name) + "Item"
                    dart_type = f"List<{item_class_name}>"
                    sub_classes.append(
                        cls.generate_standard_class(
                            item_class_name,
                            val[0],
                            is_optional,
                            gen_copy_with,
                            gen_equatable,
                        )
                    )
                    from_json = (
                        f"(json['{key}'] as List<dynamic>?)?.map((e) => "
                        f"{item_class_name}.fromJson(e as Map<String, dynamic>)).toList()"
                    )
                else:
                    item_type = (
                        type(val[0]).__name__ if len(val) > 0 else "dynamic"
                    )
                    item_type = {
                        "str": "String",
                        "int": "int",
                        "float": "double",
                        "bool": "bool",
                    }.get(item_type, "dynamic")
                    dart_type = f"List<{item_type}>"
                    from_json = f"(json['{key}'] as List<dynamic>?)?.map((e) => e as {item_type}).toList()"
            elif isinstance(val, dict):
                nested_class_name = cls._capitalize(field_name)
                dart_type = nested_class_name
                sub_classes.append(
                    cls.generate_standard_class(
                        nested_class_name,
                        val,
                        is_optional,
                        gen_copy_with,
                        gen_equatable,
                    )
                )
                from_json = f"json['{key}'] != null ? {nested_class_name}.fromJson(json['{key}'] as Map<String, dynamic>) : null"
            else:
                dart_type = "dynamic"
                from_json = f"json['{key}']"

            fields.append(f"  final {dart_type}{nullable} {field_name};")

            if is_optional:
                constructor_args.append(f"    this.{field_name},")
            else:
                constructor_args.append(f"    required this.{field_name},")

            from_json_fields.append(f"      {field_name}: {from_json},")
            to_json = (
                f"'{key}': {field_name}?.toJson(),"
                if isinstance(val, dict)
                else (
                    f"'{key}': {field_name}?.map((e) => e.toJson()).toList(),"
                    if isinstance(val, list)
                    and len(val) > 0
                    and isinstance(val[0], dict)
                    else f"'{key}': {field_name},"
                )
            )
            to_json_fields.append(f"      {to_json}")

            copy_with_args.append(f"    {dart_type}? {field_name},")
            copy_with_assignments.append(
                f"      {field_name}: {field_name} ?? this.{field_name},"
            )

        fields_str = "\n".join(fields)
        args_str = "\n".join(constructor_args)
        from_json_str = "\n".join(from_json_fields)
        to_json_str = "\n".join(to_json_fields)

        copy_with_str = ""
        if gen_copy_with:
            cw_args = "\n".join(copy_with_args)
            cw_assign = "\n".join(copy_with_assignments)
            copy_with_str = f"""\n\n  {class_name} copyWith({{\n{cw_args}\n  }}) {{\n    return {class_name}(\n{cw_assign}\n    );\n  }}"""

        extends_clause = " extends Equatable" if gen_equatable else ""
        equatable_override = ""
        imports = (
            "import 'package:equatable/equatable.dart';\n\n"
            if gen_equatable
            else ""
        )
        if gen_equatable:
            props = ", ".join(equatable_props)
            equatable_override = f"""\n\n  @override\n  List<Object?> get props => [{props}];"""

        dart_code = f"""{imports}class {class_name}{extends_clause} {{
{fields_str}

  {class_name}({{
{args_str}
  }});

  factory {class_name}.fromJson(Map<String, dynamic> json) {{
    return {class_name}(
{from_json_str}
    );
  }}

  Map<String, dynamic> toJson() {{
    return {{
{to_json_str}
    }};
  }}{copy_with_str}{equatable_override}
}}"""
        if sub_classes:
            dart_code += "\n\n" + "\n\n".join(sub_classes)

        return dart_code


class ProApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("JsonToDart Studio")
        self.geometry("1200 x 800")
        self.minsize(950, 650)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Lexers for Pygments
        self.json_lexer = JsonLexer()
        self.dart_lexer = DartLexer()

        # --- Top Control Bar ---
        self.top_bar = ctk.CTkFrame(self, corner_radius=0)
        self.top_bar.pack(side="top", fill="x", padx=10, pady=(10, 5))

        self.class_label = ctk.CTkLabel(
            self.top_bar,
            text="Class Name:",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.class_label.pack(side="left", padx=(10, 2), pady=10)

        self.class_entry = ctk.CTkEntry(self.top_bar, width=150)
        self.class_entry.insert(0, "UserModel")
        self.class_entry.pack(side="left", padx=5, pady=10)
        self.class_entry.bind("<KeyRelease>", lambda e: self.convert_json())

        self.style_label = ctk.CTkLabel(
            self.top_bar,
            text="Generator:",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.style_label.pack(side="left", padx=(15, 2), pady=10)

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

        # --- Features Options Bar ---
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

        # --- Live API Fetcher Bar ---
        self.api_bar = ctk.CTkFrame(self, corner_radius=6)
        self.api_bar.pack(side="top", fill="x", padx=10, pady=(0, 5))

        self.api_label = ctk.CTkLabel(
            self.api_bar,
            text="🌐 API URL:",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.api_label.pack(side="left", padx=(10, 5), pady=6)

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

        # --- 50/50 Split Main Workspace Frame ---
        self.workspace_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.workspace_frame.pack(
            side="top", fill="both", expand=True, padx=10, pady=5
        )

        self.workspace_frame.grid_columnconfigure(0, weight=1, uniform="group1")
        self.workspace_frame.grid_columnconfigure(1, weight=1, uniform="group1")
        self.workspace_frame.grid_rowconfigure(0, weight=1)

        # --- Left Panel (Input JSON Editor) ---
        self.left_frame = ctk.CTkFrame(self.workspace_frame)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)
        self.left_frame.grid_rowconfigure(1, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        self.input_tool_frame = ctk.CTkFrame(
            self.left_frame, fg_color="transparent"
        )
        self.input_tool_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        self.json_label = ctk.CTkLabel(
            self.input_tool_frame,
            text="JSON Input",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.json_label.pack(side="left", padx=5)

        self.status_badge = ctk.CTkLabel(
            self.input_tool_frame,
            text="● Valid JSON",
            text_color="#2ecc71",
            font=ctk.CTkFont(size=11),
        )
        self.status_badge.pack(side="left", padx=10)

        self.clear_btn = ctk.CTkButton(
            self.input_tool_frame,
            text="Clear",
            width=50,
            height=24,
            fg_color="transparent",
            command=self.clear_json,
        )
        self.clear_btn.pack(side="right", padx=2)

        self.format_btn = ctk.CTkButton(
            self.input_tool_frame,
            text="Format JSON",
            width=80,
            height=24,
            command=self.format_json,
        )
        self.format_btn.pack(side="right", padx=2)

        self.load_btn = ctk.CTkButton(
            self.input_tool_frame,
            text="📂 Load File",
            width=80,
            height=24,
            fg_color="transparent",
            border_width=1,
            command=self.load_json_file,
        )
        self.load_btn.pack(side="right", padx=2)

        # Wrapper Frame for JSON Editor + Scrollbars
        self.json_editor_container = ctk.CTkFrame(
            self.left_frame, fg_color="#1E1E1E"
        )
        self.json_editor_container.grid(
            row=1, column=0, sticky="nsew", padx=10, pady=(0, 10)
        )
        self.json_editor_container.grid_rowconfigure(0, weight=1)
        self.json_editor_container.grid_columnconfigure(0, weight=1)

        # JSON Tkinter Text Editor (Reduced Font: 11pt)
        self.json_text = tk.Text(
            self.json_editor_container,
            bg="#1E1E1E",
            fg="#D4D4D4",
            insertbackground="#FFFFFF",
            selectbackground="#264F78",
            font=("Consolas", 11),
            wrap="none",
            border=0,
            padx=8,
            pady=8,
        )
        self.json_text.grid(row=0, column=0, sticky="nsew")

        # Scrollbars for Left Editor
        self.json_v_scroll = ctk.CTkScrollbar(
            self.json_editor_container,
            orientation="vertical",
            command=self.json_text.yview,
        )
        self.json_v_scroll.grid(row=0, column=1, sticky="ns")

        self.json_h_scroll = ctk.CTkScrollbar(
            self.json_editor_container,
            orientation="horizontal",
            command=self.json_text.xview,
        )
        self.json_h_scroll.grid(row=1, column=0, sticky="ew")

        self.json_text.configure(
            yscrollcommand=self.json_v_scroll.set,
            xscrollcommand=self.json_h_scroll.set,
        )
        self.json_text.bind("<KeyRelease>", self.on_json_type)

        # --- Right Panel (Output Dart Editor) ---
        self.right_frame = ctk.CTkFrame(self.workspace_frame)
        self.right_frame.grid(
            row=0, column=1, sticky="nsew", padx=(5, 0), pady=0
        )
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.dart_label = ctk.CTkLabel(
            self.right_frame,
            text="Dart Model Output",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.dart_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)

        # Wrapper Frame for Dart Editor + Scrollbars
        self.dart_editor_container = ctk.CTkFrame(
            self.right_frame, fg_color="#1E1E1E"
        )
        self.dart_editor_container.grid(
            row=1, column=0, sticky="nsew", padx=10, pady=(0, 10)
        )
        self.dart_editor_container.grid_rowconfigure(0, weight=1)
        self.dart_editor_container.grid_columnconfigure(0, weight=1)

        # Dart Tkinter Text Editor (Reduced Font: 11pt)
        self.dart_text = tk.Text(
            self.dart_editor_container,
            bg="#1E1E1E",
            fg="#D4D4D4",
            insertbackground="#FFFFFF",
            selectbackground="#264F78",
            font=("Consolas", 11),
            wrap="none",
            border=0,
            padx=8,
            pady=8,
        )
        self.dart_text.grid(row=0, column=0, sticky="nsew")

        # Scrollbars for Right Editor
        self.dart_v_scroll = ctk.CTkScrollbar(
            self.dart_editor_container,
            orientation="vertical",
            command=self.dart_text.yview,
        )
        self.dart_v_scroll.grid(row=0, column=1, sticky="ns")

        self.dart_h_scroll = ctk.CTkScrollbar(
            self.dart_editor_container,
            orientation="horizontal",
            command=self.dart_text.xview,
        )
        self.dart_h_scroll.grid(row=1, column=0, sticky="ew")

        self.dart_text.configure(
            yscrollcommand=self.dart_v_scroll.set,
            xscrollcommand=self.dart_h_scroll.set,
        )

        # Configure Color Tags for both Text Widgets
        self.setup_text_tags(self.json_text)
        self.setup_text_tags(self.dart_text)

        self.load_saved_state()
        self.convert_json()

    # --- Syntax Highlighting Core Engine ---
    def setup_text_tags(self, text_widget: tk.Text):
        """Configure color tags in the Tkinter Text widget based on Pygments Tokens."""
        for token, color in TOKEN_COLORS.items():
            text_widget.tag_config(str(token), foreground=color)

    def apply_highlighting(self, text_widget: tk.Text, code: str, lexer):
        """Parse code using Pygments and apply color tags dynamically."""
        y_scroll = text_widget.yview()
        x_scroll = text_widget.xview()

        text_widget.delete("1.0", tk.END)

        for token_type, value in lex(code, lexer):
            tag_name = None
            curr = token_type
            while curr:
                if curr in TOKEN_COLORS:
                    tag_name = str(curr)
                    break
                curr = curr.parent

            if tag_name:
                text_widget.insert(tk.END, value, tag_name)
            else:
                text_widget.insert(tk.END, value)

        text_widget.yview_moveto(y_scroll[0])
        text_widget.xview_moveto(x_scroll[0])

    # --- API Fetcher Threading Logic ---
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
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                res_data = response.json()

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
        self.apply_highlighting(self.json_text, formatted_json, self.json_lexer)
        self.validate_json()
        self.convert_json()

    def on_json_type(self, event=None):
        raw_json = self.json_text.get("1.0", tk.END).strip()
        self.apply_highlighting(self.json_text, raw_json, self.json_lexer)
        self.validate_json()
        self.convert_json()

    def on_generator_change(self, choice):
        if choice == "Freezed Package":
            self.null_switch.configure(state="disabled")
            self.copy_with_switch.configure(state="disabled")
            self.equatable_switch.configure(state="disabled")
        else:
            self.null_switch.configure(state="normal")
            self.copy_with_switch.configure(state="normal")
            self.equatable_switch.configure(state="normal")
        self.convert_json()

    def validate_json(self):
        raw_json = self.json_text.get("1.0", tk.END).strip()
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
                self.apply_highlighting(self.json_text, content, self.json_lexer)
                self.validate_json()
                self.convert_json()

    def format_json(self):
        raw_json = self.json_text.get("1.0", tk.END).strip()
        if raw_json:
            try:
                parsed = json.loads(raw_json)
                formatted = json.dumps(parsed, indent=2)
                self.apply_highlighting(self.json_text, formatted, self.json_lexer)
                self.validate_json()
            except json.JSONDecodeError as e:
                messagebox.showerror(
                    "Invalid JSON", f"Cannot format invalid JSON:\n{str(e)}"
                )

    def clear_json(self):
        self.json_text.delete("1.0", tk.END)
        self.dart_text.delete("1.0", tk.END)
        self.validate_json()

    def convert_json(self):
        raw_json = self.json_text.get("1.0", tk.END).strip()
        class_name = self.class_entry.get().strip() or "AutogeneratedClass"
        generator_mode = self.generator_option.get()

        if not raw_json:
            self.dart_text.delete("1.0", tk.END)
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
                is_optional = bool(self.null_switch.get())
                gen_copy_with = bool(self.copy_with_switch.get())
                gen_equatable = bool(self.equatable_switch.get())
                dart_code = JsonToDartConverter.generate_standard_class(
                    class_name,
                    data,
                    is_optional,
                    gen_copy_with,
                    gen_equatable,
                )

            self.apply_highlighting(self.dart_text, dart_code, self.dart_lexer)

        except json.JSONDecodeError:
            pass

    def copy_to_clipboard(self):
        code = self.dart_text.get("1.0", tk.END).strip()
        if code:
            self.clipboard_clear()
            self.clipboard_append(code)
            self.copy_btn.configure(text="✅ Copied!")
            self.after(
                2000, lambda: self.copy_btn.configure(text="📋 Copy Code")
            )

    def save_file(self):
        code = self.dart_text.get("1.0", tk.END).strip()
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

    # --- State Persistence ---
    def save_current_state(self):
        state = {
            "class_name": self.class_entry.get().strip(),
            "generator": self.generator_option.get(),
            "nullable": bool(self.null_switch.get()),
            "copy_with": bool(self.copy_with_switch.get()),
            "equatable": bool(self.equatable_switch.get()),
            "url": self.url_entry.get().strip(),
            "json_data": self.json_text.get("1.0", tk.END).strip(),
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass

    def load_saved_state(self):
        default_json = '{\n  "id": 1,\n  "name": "Alex Smith",\n  "is_admin": true,\n  "scores": [95.5, 88.0],\n  "profile": {\n    "bio": "Flutter Developer",\n    "github": "alexsmith"\n  }\n}'

        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)

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

                json_val = state.get("json_data", default_json)
                self.apply_highlighting(self.json_text, json_val, self.json_lexer)
                self.on_generator_change(generator)
                self.validate_json()
                return
            except Exception:
                pass

        self.apply_highlighting(self.json_text, default_json, self.json_lexer)
        self.validate_json()

    def on_close(self):
        self.save_current_state()
        self.destroy()


if __name__ == "__main__":
    app = ProApp()
    app.mainloop()