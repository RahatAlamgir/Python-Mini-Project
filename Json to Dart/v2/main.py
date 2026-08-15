"""Entry point for JsonToDart Studio Application."""

import customtkinter as ctk
from ui.main_window import MainWindow

# Global CustomTkinter Setup
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()