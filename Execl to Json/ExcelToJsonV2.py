import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import pandas as pd
import os
import json
import numpy as np

class ExcelToJsonGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Excel To Json")
        self.root.geometry("1100x850")
        self.root.configure(bg="#f0f2f5")

        # --- Custom Styling ---
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TNotebook", background="#f0f2f5", borderwidth=0)
        self.style.configure("TNotebook.Tab", padding=[20, 10], font=('Segoe UI', 10))
        self.style.map("TNotebook.Tab", background=[("selected", "#ffffff")], foreground=[("selected", "#2196F3")])

        self.file_path = ""
        self.tables_data = [] 

        # --- Header Bar ---
        header = tk.Frame(root, bg="#232429", height=70)
        header.pack(fill="x", side="top")

        btn_load = tk.Button(header, text="📂 Load Excel", command=self.load_file, bg="#474850", fg="white", 
                             relief="flat", padx=15, font=("Segoe UI", 9, "bold"), cursor="hand2")
        btn_load.pack(side="left", padx=10)

        self.file_label = tk.Label(header, text="No file active", bg="#232429", fg="#c5cae9", font=("Segoe UI", 9))
        self.file_label.pack(side="left", padx=10)

        self.sheet_var = tk.StringVar()
        self.sheet_dropdown = ttk.Combobox(header, textvariable=self.sheet_var, state="readonly", width=20)
        self.sheet_dropdown.pack(side="right", padx=20)
        self.sheet_dropdown.bind("<<ComboboxSelected>>", lambda e: self.detect_tables())

        # --- Main Container ---
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=(10, 0))

        # --- Footer Export ---
        footer = tk.Frame(root, bg="#f0f2f5", pady=15)
        footer.pack(fill="x", side="bottom")

        btn_export = tk.Button(footer, text="EXPORT JSON", command=self.export_json, 
                               bg="#2e7d32", fg="white", font=("Segoe UI", 10, "bold"), 
                               relief="flat", padx=30, pady=10, cursor="hand2")
        btn_export.pack()

    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xls")])
        if not path: return
        self.file_path = path
        self.file_label.config(text=os.path.basename(path))
        
        xls = pd.ExcelFile(path)
        self.sheet_dropdown['values'] = xls.sheet_names
        self.sheet_var.set(xls.sheet_names[0])
        self.detect_tables()

    def find_table_islands(self, df):
        mask = df.notna().values
        rows, cols = mask.shape
        visited = np.zeros_like(mask, dtype=bool)
        tables = []
        for r in range(rows):
            for c in range(cols):
                if mask[r, c] and not visited[r, c]:
                    cluster = []
                    queue = [(r, c)]
                    visited[r, c] = True
                    while queue:
                        curr_r, curr_c = queue.pop(0)
                        cluster.append((curr_r, curr_c))
                        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1), (-1,-1), (1,1), (-1,1), (1,-1)]:
                            nr, nc = curr_r + dr, curr_c + dc
                            if 0 <= nr < rows and 0 <= nc < cols and mask[nr, nc] and not visited[nr, nc]:
                                visited[nr, nc] = True
                                queue.append((nr, nc))
                    r_c, c_c = zip(*cluster)
                    t_df = df.iloc[min(r_c):max(r_c)+1, min(c_c):max(c_c)+1].reset_index(drop=True)
                    t_df.columns = t_df.iloc[0].astype(str)
                    tables.append(t_df[1:].reset_index(drop=True))
        return tables

    def detect_tables(self):
        if not self.file_path: return
        for tab in self.notebook.tabs(): self.notebook.forget(tab)
        self.tables_data = []

        try:
            full_df = pd.read_excel(self.file_path, sheet_name=self.sheet_var.get(), header=None)
            dfs = self.find_table_islands(full_df)
            for i, df in enumerate(dfs):
                self.tables_data.append(self.create_table_tab(df, i))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load sheet: {e}")

    def create_table_tab(self, df, index):
        main_tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(main_tab, text=f" Table {index+1} ")

        # --- Sidebar Config ---
        side_panel = tk.Frame(main_tab, bg="#f8f9fa", width=250, borderwidth=1, relief="solid")
        side_panel.pack(side="left", fill="y")
        
        tk.Label(side_panel, text="CONFIG", font=("Segoe UI", 10, "bold"), bg="#f8f9fa", pady=10).pack()
        
        tk.Label(side_panel, text="JSON Root Key:", bg="#f8f9fa").pack(pady=(10,0))
        name_var = tk.StringVar(value=f"Table_{index+1}")
        tk.Entry(side_panel, textvariable=name_var, font=("Segoe UI", 10), justify="center").pack(padx=10, pady=5)

        tk.Frame(side_panel, height=2, bg="#dee2e6").pack(fill="x", pady=15)

        # Row Selection Helpers
        tk.Label(side_panel, text="Row Selection:", bg="#f8f9fa").pack()
        row_vars = []
        def toggle_rows(val): 
            for v in row_vars: v.set(val)

        tk.Button(side_panel, text="Select All Rows", command=lambda: toggle_rows(True), bg="white").pack(fill="x", padx=20, pady=2)
        tk.Button(side_panel, text="Clear All Rows", command=lambda: toggle_rows(False), bg="white").pack(fill="x", padx=20, pady=2)

        # --- Table View Area ---
        view_area = tk.Frame(main_tab, bg="white")
        view_area.pack(side="right", fill="both", expand=True)

        canvas = tk.Canvas(view_area, bg="white", highlightthickness=0)
        v_scroll = ttk.Scrollbar(view_area, orient="vertical", command=canvas.yview)
        h_scroll = ttk.Scrollbar(view_area, orient="horizontal", command=canvas.xview)
        scroll_frame = tk.Frame(canvas, bg="white")

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")
        canvas.pack(side="left", fill="both", expand=True)

        # Build Table Grid
        col_configs = {}
        # Header Row
        tk.Label(scroll_frame, text="✅", font=("Arial", 10), bg="#e3f2fd").grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        
        for c, col_name in enumerate(df.columns):
            if "Unnamed" in col_name or col_name == "nan": continue
            c_idx = c + 1
            h_cell = tk.Frame(scroll_frame, bg="#e3f2fd", borderwidth=1, relief="flat")
            h_cell.grid(row=0, column=c_idx, sticky="nsew", padx=1, pady=1)
            
            c_var = tk.BooleanVar(value=True)
            tk.Checkbutton(h_cell, variable=c_var, bg="#e3f2fd", activebackground="#e3f2fd").pack()
            
            r_ent = tk.Entry(h_cell, width=18, font=("Segoe UI", 9, "bold"), relief="flat", justify="center")
            r_ent.insert(0, col_name)
            r_ent.pack(padx=5, pady=5)
            col_configs[col_name] = {"use": c_var, "rename": r_ent}

        # Data Rows
        for r_idx, row in df.iterrows():
            grid_r = r_idx + 1
            r_var = tk.BooleanVar(value=True)
            row_vars.append(r_var)
            
            cb_bg = "#ffffff" if r_idx % 2 == 0 else "#f8f9fa"
            cb_frame = tk.Frame(scroll_frame, bg=cb_bg)
            cb_frame.grid(row=grid_r, column=0, sticky="nsew")
            tk.Checkbutton(cb_frame, variable=r_var, bg=cb_bg, activebackground=cb_bg).pack(expand=True)

            for c_idx, value in enumerate(row):
                bg_color = "#ffffff" if r_idx % 2 == 0 else "#f8f9fa"
                lbl = tk.Label(scroll_frame, text=str(value), font=("Segoe UI", 9),
                               bg=bg_color, padx=10, pady=4, anchor="w", borderwidth=1, relief="flat")
                lbl.grid(row=grid_r, column=c_idx+1, sticky="nsew", padx=1, pady=1)

        return {"df": df, "name_var": name_var, "col_configs": col_configs, "row_vars": row_vars}

    def export_json(self):
        if not self.tables_data: return
        
        final_dict = {}
        for table in self.tables_data:
            key = table["name_var"].get().strip()
            df = table["df"]
            col_cfg = table["col_configs"]
            row_vars = table["row_vars"]

            active_cols = [c for c in df.columns if c in col_cfg and col_cfg[c]["use"].get()]
            rename_map = {c: col_cfg[c]["rename"].get() for c in active_cols}

            rows_list = []
            for r_idx, row in df.iterrows():
                if row_vars[r_idx].get():
                    row_data = row[active_cols].rename(rename_map).fillna("").to_dict()
                    rows_list.append(row_data)
            
            if rows_list: final_dict[key] = rows_list

        if not final_dict:
            messagebox.showwarning("Empty", "No data selected for export.")
            return

        save_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not save_path: return

        # Pretty Formatter
        output = "{\n"
        keys = list(final_dict.keys())
        for i, k in enumerate(keys):
            output += f'  "{k}": [\n'
            for j, row in enumerate(final_dict[k]):
                line = json.dumps(row, ensure_ascii=False)
                comma = "," if j < len(final_dict[k]) - 1 else ""
                output += f'    {line}{comma}\n'
            output += "  ]" + ("," if i < len(keys)-1 else "") + "\n"
        output += "}"

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(output)
        messagebox.showinfo("Success", f"Exported {len(final_dict)} table(s) successfully!")

if __name__ == "__main__":
    root = tk.Tk()
    app = ExcelToJsonGUI(root)
    root.mainloop()