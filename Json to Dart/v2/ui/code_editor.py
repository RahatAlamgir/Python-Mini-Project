"""Reusable Tkinter Text component with horizontal and vertical scrollbars."""

import tkinter as tk
import customtkinter as ctk


class CodeEditor(ctk.CTkFrame):

    def __init__(self, master, font_size: int = 11, **kwargs):
        super().__init__(master, fg_color="#1E1E1E", **kwargs)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.text = tk.Text(
            self,
            bg="#1E1E1E",
            fg="#D4D4D4",
            insertbackground="#FFFFFF",
            selectbackground="#264F78",
            font=("Consolas", font_size),
            wrap="none",
            border=0,
            padx=8,
            pady=8,
        )
        self.text.grid(row=0, column=0, sticky="nsew")

        # Scrollbars
        self.v_scroll = ctk.CTkScrollbar(
            self, orientation="vertical", command=self.text.yview
        )
        self.v_scroll.grid(row=0, column=1, sticky="ns")

        self.h_scroll = ctk.CTkScrollbar(
            self, orientation="horizontal", command=self.text.xview
        )
        self.h_scroll.grid(row=1, column=0, sticky="ew")

        self.text.configure(
            yscrollcommand=self.v_scroll.set,
            xscrollcommand=self.h_scroll.set,
        )

    def get_text(self) -> str:
        return self.text.get("1.0", tk.END).strip()

    def set_text(self, content: str):
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, content)