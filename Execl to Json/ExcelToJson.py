import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import os
import json


class ExcelToJsonGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Excel to JSON Tool")
        self.root.geometry("520x650")
        self.root.configure(bg="white")

        self.file_path = ""
        self.df = None
        self.check_vars = {}
        self.rename_entries = {}

        # ===== FILE SECTION =====
        tk.Button(root, text="Select Excel File", command=self.load_file).pack(pady=10)

        self.file_label = tk.Label(root, text="No file selected", bg="white", fg="gray")
        self.file_label.pack()

        # ===== SHEET SECTION =====
        self.sheet_frame = tk.Frame(root, bg="white")
        self.sheet_frame.pack(pady=5)

        self.sheet_var = tk.StringVar()

        # ===== HEADER CONTROL =====
        header_frame = tk.Frame(root, bg="white")
        header_frame.pack(pady=10)

        tk.Label(header_frame, text="Header Row:", bg="white").pack(side="left")

        self.header_entry = tk.Entry(header_frame, width=5)
        self.header_entry.pack(side="left", padx=5)

        tk.Button(header_frame, text="Auto Detect", command=self.auto_detect_header).pack(side="left", padx=5)
        tk.Button(header_frame, text="Reload", command=self.load_columns).pack(side="left", padx=5)

        # ===== COLUMN FRAME =====
        self.column_frame = tk.LabelFrame(root, text="Columns (Select + Rename)", bg="white")
        self.column_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ===== OUTPUT =====
        self.output_name = tk.Entry(root)

        tk.Button(root, text="Convert", command=self.convert).pack(pady=15)

    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xls")])
        if not path:
            return

        self.file_path = path
        self.file_label.config(text=os.path.basename(path), fg="black")

        try:
            xls = pd.ExcelFile(path)
            sheets = xls.sheet_names
        except:
            messagebox.showerror("Error", "Invalid Excel file")
            return

        for widget in self.sheet_frame.winfo_children():
            widget.destroy()

        if len(sheets) > 1:
            tk.Label(self.sheet_frame, text="Select Sheet:", bg="white").pack(side="left")

            self.sheet_var.set(sheets[0])
            dropdown = tk.OptionMenu(self.sheet_frame, self.sheet_var, *sheets)
            dropdown.pack(side="left")
        else:
            self.sheet_var.set(sheets[0])

        self.auto_detect_header()

    def detect_header_row(self, df_preview):
        max_count = 0
        best_row = 0

        for i in range(min(10, len(df_preview))):
            count = df_preview.iloc[i].notna().sum()
            if count > max_count:
                max_count = count
                best_row = i

        return best_row

    def auto_detect_header(self):
        if not self.file_path:
            return

        preview = pd.read_excel(self.file_path, sheet_name=self.sheet_var.get(), header=None)
        header_row = self.detect_header_row(preview)

        self.header_entry.delete(0, tk.END)
        self.header_entry.insert(0, str(header_row))

        self.load_columns()

    def load_columns(self):
        if not self.file_path:
            return

        try:
            header_row = int(self.header_entry.get())
        except:
            messagebox.showerror("Error", "Invalid header row")
            return

        self.df = pd.read_excel(
            self.file_path,
            sheet_name=self.sheet_var.get(),
            header=header_row
        )

        self.df = self.df.dropna(axis=1, how='all')

        for widget in self.column_frame.winfo_children():
            widget.destroy()

        self.check_vars.clear()
        self.rename_entries.clear()

        for col in self.df.columns:
            if str(col).strip() == "" or str(col) == "nan":
                continue

            frame = tk.Frame(self.column_frame, bg="white")
            frame.pack(fill="x", padx=5, pady=2)

            var = tk.BooleanVar(value=True)
            tk.Checkbutton(frame, variable=var, bg="white").pack(side="left")

            tk.Label(frame, text=str(col), width=18, anchor="w", bg="white").pack(side="left")

            entry = tk.Entry(frame)
            entry.insert(0, str(col))
            entry.pack(side="right", fill="x", expand=True)

            self.check_vars[col] = var
            self.rename_entries[col] = entry


    def convert(self):
        if self.df is None:
            messagebox.showerror("Error", "No data loaded")
            return

        selected_cols = []
        rename_map = {}

        for col, var in self.check_vars.items():
            if var.get():
                new_name = self.rename_entries[col].get().strip()
                if new_name:
                    selected_cols.append(col)
                    rename_map[col] = new_name

        if not selected_cols:
            messagebox.showerror("Error", "No columns selected")
            return

        df_filtered = self.df[selected_cols].rename(columns=rename_map)
        data = df_filtered.dropna(how="all").to_dict(orient="records")

        

        json_lines = ["["]

        for i, row in enumerate(data):
            obj = json.dumps(row, separators=(',', ':'))

            if i < len(data) - 1:
                json_lines.append(f"    {obj},")
            else:
                json_lines.append(f"    {obj}")

        json_lines.append("]")

        json_output = "\n".join(json_lines)

        save_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=self.output_name.get().strip() or "output.json"
        )
        if not save_path:
            return

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(json_output)

        messagebox.showinfo("Success", f"Saved:\n{save_path}")
    # def convert(self):
    #     if self.df is None:
    #         messagebox.showerror("Error", "No data loaded")
    #         return

    #     selected_cols = []
    #     rename_map = {}

    #     for col, var in self.check_vars.items():
    #         if var.get():
    #             new_name = self.rename_entries[col].get().strip()
    #             if new_name:
    #                 selected_cols.append(col)
    #                 rename_map[col] = new_name

    #     if not selected_cols:
    #         messagebox.showerror("Error", "No columns selected")
    #         return

    #     df_filtered = self.df[selected_cols].rename(columns=rename_map)
    #     data = df_filtered.dropna(how="all").to_dict(orient="records")

    #     # ✅ Clean JSON (line breaks, no extra spaces)
    #     json_output = json.dumps(data, indent=4, separators=(',', ':'))

    #     save_path = filedialog.asksaveasfilename(
    #         defaultextension=".json",
    #         filetypes=[("JSON files", "*.json")],
    #         initialfile=self.output_name.get().strip() or "output.json"
    #     )
    #     if not save_path:
    #         return

    #     with open(save_path, "w", encoding="utf-8") as f:
    #         f.write(json_output)

    #     messagebox.showinfo("Success", f"Saved:\n{save_path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ExcelToJsonGUI(root)
    root.mainloop()