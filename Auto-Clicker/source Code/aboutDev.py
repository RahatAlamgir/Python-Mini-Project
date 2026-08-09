import tkinter as tk
import webbrowser


def show_about(parent):
    about_win = tk.Toplevel(parent)
    about_win.title("About")
    about_win.geometry("320x250")
    about_win.configure(bg="#1a1a1a")

    tk.Label(
        about_win,
        text="AUTO CLICKER PRO",
        fg="#00ff88",
        bg="#1a1a1a",
        font=("Segoe UI", 14, "bold")
    ).pack(pady=20)

    tk.Label(
        about_win,
        text="Created by:\nMd Rahat Alamgir",
        fg="white",
        bg="#1a1a1a",
        font=("Segoe UI", 11)
    ).pack()

    tk.Button(
        about_win,
        text="GitHub",
        fg="#3498db",
        bg="#1a1a1a",
        relief="flat",
        cursor="hand2",
        command=lambda: webbrowser.open("https://github.com/RahatAlamgir")
    ).pack(pady=15)