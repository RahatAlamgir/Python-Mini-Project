import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageOps
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import (
    RoundedModuleDrawer, CircleModuleDrawer, SquareModuleDrawer, GappedSquareModuleDrawer
)
from qrcode.image.styles.colormasks import SolidFillColorMask
import barcode
from barcode.writer import ImageWriter
import cv2

CONFIG_FILE = "config.json"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class CodeStudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Pro QR & Barcode Studio")
        self.geometry("920x720")
        self.minsize(880, 650)
        self.resizable(True, True)

        self.logo_path = None
        self.qr_image_pil = None
        self.barcode_image_pil = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")

        self.tab_qr = self.tabview.add("Generate QR Code")
        self.tab_barcode = self.tabview.add("Generate Barcode")
        self.tab_reader = self.tabview.add("Read / Scan Code")

        self.build_qr_tab()
        self.build_barcode_tab()
        self.build_reader_tab()

        self.load_settings()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ==========================================
    # TAB 1: ADVANCED QR CODE GENERATOR
    # ==========================================
    def build_qr_tab(self):
        self.tab_qr.columnconfigure(0, weight=3)
        self.tab_qr.columnconfigure(1, weight=2)
        self.tab_qr.rowconfigure(0, weight=1)

        # Fixed layout panel
        controls_frame = ctk.CTkFrame(self.tab_qr)
        controls_frame.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")

        ctk.CTkLabel(controls_frame, text="QR Code Studio Settings", font=("Helvetica", 13, "bold")).pack(pady=(2, 2), fill="x")

        # 1. Content Input
        self.qr_data_entry = ctk.CTkEntry(controls_frame, placeholder_text="Enter URL or Text...", height=26)
        self.qr_data_entry.pack(pady=2, padx=6, fill="x")

        def make_row(parent, label_text, widget_type, widget_kwargs):
            row_frame = ctk.CTkFrame(parent, fg_color="transparent")
            row_frame.pack(fill="x", padx=4, pady=1)
            lbl = ctk.CTkLabel(row_frame, text=label_text, anchor="w", font=("Helvetica", 11))
            lbl.pack(side="left", fill="x", expand=True)
            widget = widget_type(row_frame, **widget_kwargs)
            widget.pack(side="right")
            return widget

        # 2. Colors Section
        colors_sec = ctk.CTkFrame(controls_frame)
        colors_sec.pack(fill="x", padx=4, pady=2)

        ctk.CTkLabel(colors_sec, text="Color Palette", font=("Helvetica", 11, "bold"), anchor="w").pack(fill="x", padx=6, pady=(1, 0))

        self.qr_fg_entry = make_row(colors_sec, "Pattern Color:", ctk.CTkEntry, {"width": 90, "height": 22})
        self.qr_fg_entry.insert(0, "#000000")

        self.qr_eye_entry = make_row(colors_sec, "Corner Eyes Color:", ctk.CTkEntry, {"width": 90, "height": 22})
        self.qr_eye_entry.insert(0, "#000000")

        self.qr_bg_entry = make_row(colors_sec, "Background Color:", ctk.CTkEntry, {"width": 90, "height": 22})
        self.qr_bg_entry.insert(0, "#FFFFFF")

        self.transparent_bg_var = tk.BooleanVar(value=False)
        self.transparent_bg_chk = ctk.CTkCheckBox(
            colors_sec, text="Transparent Background (.png)", variable=self.transparent_bg_var,
            command=self.toggle_bg_entry, font=("Helvetica", 10), checkbox_width=16, checkbox_height=16
        )
        self.transparent_bg_chk.pack(anchor="w", padx=6, pady=(1, 2))

        # 3. Pattern Section
        shape_sec = ctk.CTkFrame(controls_frame)
        shape_sec.pack(fill="x", padx=4, pady=2)

        ctk.CTkLabel(shape_sec, text="Pattern & Module Customization", font=("Helvetica", 11, "bold"), anchor="w").pack(fill="x", padx=6, pady=(1, 0))

        self.qr_style_option = make_row(
            shape_sec, "Module Shape:", ctk.CTkOptionMenu, 
            {"values": ["Square", "Rounded", "Circle", "Gapped"], "width": 110, "height": 22}
        )
        self.qr_eye_style_option = make_row(
            shape_sec, "Corner Eyes Shape:", ctk.CTkOptionMenu, 
            {"values": ["Square", "Rounded", "Ring / Circle", "Blob / Oval"], "width": 110, "height": 22}
        )

        # 4. Center Overlay & Text Customization
        overlay_sec = ctk.CTkFrame(controls_frame)
        overlay_sec.pack(fill="x", padx=4, pady=2)

        ctk.CTkLabel(overlay_sec, text="Center Overlay (Multi-line Text & Logo)", font=("Helvetica", 11, "bold"), anchor="w").pack(fill="x", padx=6, pady=(1, 0))

        txt_row = ctk.CTkFrame(overlay_sec, fg_color="transparent")
        txt_row.pack(fill="x", padx=4, pady=1)
        ctk.CTkLabel(txt_row, text="Center Text:", font=("Helvetica", 11), anchor="w").pack(side="left")
        self.center_text_entry = ctk.CTkTextbox(txt_row, width=140, height=38)
        self.center_text_entry.pack(side="right")

        self.center_text_fg = make_row(overlay_sec, "Center Text Color:", ctk.CTkEntry, {"width": 90, "height": 22})
        self.center_text_fg.insert(0, "#000000")

        self.center_text_bg = make_row(overlay_sec, "Center Text BG:", ctk.CTkEntry, {"width": 90, "height": 22})
        self.center_text_bg.insert(0, "#FFFFFF")

        self.center_border_fg = make_row(overlay_sec, "Center Border Color:", ctk.CTkEntry, {"width": 90, "height": 22})
        self.center_border_fg.insert(0, "#000000")

        self.center_border_width = make_row(overlay_sec, "Center Border Width:", ctk.CTkEntry, {"width": 90, "height": 22})
        self.center_border_width.insert(0, "2")

        # Logo Controls
        lg_1 = ctk.CTkFrame(overlay_sec, fg_color="transparent")
        lg_1.pack(fill="x", padx=4, pady=2)
        
        self.logo_btn = ctk.CTkButton(lg_1, text="Select Logo", width=75, height=20, command=self.upload_logo)
        self.logo_btn.pack(side="left")
        
        self.clear_logo_btn = ctk.CTkButton(lg_1, text="Clear Logo", width=65, height=20, fg_color="#c92a2a", hover_color="#a81f1f", command=self.remove_logo)
        self.clear_logo_btn.pack(side="left", padx=3)

        self.logo_label = ctk.CTkLabel(lg_1, text="No logo selected", font=("Helvetica", 9), text_color="gray")
        self.logo_label.pack(side="left", padx=3)

        # 5. Outer Frame Options
        frame_sec = ctk.CTkFrame(controls_frame)
        frame_sec.pack(fill="x", padx=4, pady=2)

        ctk.CTkLabel(frame_sec, text="Outer Border & Card Style", font=("Helvetica", 11, "bold"), anchor="w").pack(fill="x", padx=6, pady=(1, 0))

        self.enable_frame_var = tk.BooleanVar(value=True)
        self.frame_chk = ctk.CTkCheckBox(
            frame_sec, text="Enable Outer Card Frame", variable=self.enable_frame_var, 
            font=("Helvetica", 10), checkbox_width=16, checkbox_height=16
        )
        self.frame_chk.pack(anchor="w", padx=6, pady=2)

        self.frame_style_option = make_row(
            frame_sec, "Card Corner Style:", ctk.CTkOptionMenu,
            {"values": ["Rounded Image", "Square Image"], "width": 110, "height": 22}
        )

        self.frame_thickness_option = make_row(
            frame_sec, "Border Thickness:", ctk.CTkOptionMenu, 
            {"values": ["Thin (6px)", "Medium (12px)", "Thick (20px)"], "width": 110, "height": 22}
        )
        self.frame_thickness_option.set("Medium (12px)")

        self.banner_text_entry = make_row(frame_sec, "Bottom Banner Text:", ctk.CTkEntry, {"width": 110, "height": 22})
        self.banner_text_entry.insert(0, "SCAN ME")

        # Action Buttons
        btn_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=4, pady=3)

        ctk.CTkButton(
            btn_frame, text="Generate QR Code", fg_color="#1f6aa5", height=26, 
            font=("Helvetica", 11, "bold"), command=self.generate_qr
        ).pack(fill="x", pady=1)

        ctk.CTkButton(
            btn_frame, text="Save Image", fg_color="#2b8a3e", height=24, 
            command=self.save_qr
        ).pack(fill="x", pady=1)

        # Preview Frame
        preview_frame = ctk.CTkFrame(self.tab_qr)
        preview_frame.grid(row=0, column=1, padx=4, pady=4, sticky="nsew")

        ctk.CTkLabel(preview_frame, text="Live Preview", font=("Helvetica", 14, "bold")).pack(pady=8)
        self.qr_preview_label = ctk.CTkLabel(preview_frame, text="Your custom QR Code\nwill appear here", width=200, height=200)
        self.qr_preview_label.pack(expand=True, pady=8)

    def toggle_bg_entry(self):
        if self.transparent_bg_var.get():
            self.qr_bg_entry.configure(state="disabled")
        else:
            self.qr_bg_entry.configure(state="normal")

    def parse_rgb(self, color_str, default=(0, 0, 0)):
        if not color_str:
            return default
        try:
            return ImageColor.getcolor(color_str.strip(), "RGB")
        except Exception:
            return default

    def parse_rgba(self, color_str, default=(0, 0, 0, 255)):
        if not color_str:
            return default
        try:
            return ImageColor.getcolor(color_str.strip(), "RGBA")
        except Exception:
            return default

    def upload_logo(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")])
        if file_path:
            self.logo_path = file_path
            filename = os.path.basename(file_path)
            self.logo_label.configure(text=f"{filename[:10]}...", text_color="#4dabf7")

    def remove_logo(self):
        self.logo_path = None
        self.logo_label.configure(text="No logo selected", text_color="gray")

    def generate_qr(self):
        data = self.qr_data_entry.get().strip()
        if not data:
            messagebox.showwarning("Input Error", "Please enter text or a URL.")
            return

        fg_rgb = self.parse_rgb(self.qr_fg_entry.get(), (0, 0, 0))
        eye_rgb = self.parse_rgb(self.qr_eye_entry.get(), fg_rgb)
        
        is_transparent = self.transparent_bg_var.get()
        bg_rgb = (255, 255, 255) if is_transparent else self.parse_rgb(self.qr_bg_entry.get(), (255, 255, 255))

        style = self.qr_style_option.get()
        eye_style = self.qr_eye_style_option.get()
        
        center_text = self.center_text_entry.get("1.0", tk.END).strip()
        banner_text = self.banner_text_entry.get().strip()

        try:
            drawer_map = {
                "Square": SquareModuleDrawer(),
                "Rounded": RoundedModuleDrawer(),
                "Circle": CircleModuleDrawer(),
                "Gapped": GappedSquareModuleDrawer()
            }
            drawer = drawer_map.get(style, SquareModuleDrawer())

            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=12,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=drawer,
                color_mask=SolidFillColorMask(back_color=bg_rgb, front_color=fg_rgb)
            ).convert("RGBA")

            img = self.apply_eye_customization(qr, img, eye_style, eye_rgb, bg_rgb, 4, 12)

            if is_transparent:
                img = self.make_transparent(img, bg_rgb)

            if center_text:
                text_fg = self.parse_rgba(self.center_text_fg.get(), (0, 0, 0, 255))
                text_bg = self.parse_rgba(self.center_text_bg.get(), (255, 255, 255, 255))
                border_fg = self.parse_rgba(self.center_border_fg.get(), (0, 0, 0, 255))
                try:
                    border_w = int(self.center_border_width.get().strip())
                except ValueError:
                    border_w = 2

                img = self.embed_text(img, center_text, text_fg, text_bg, border_fg, border_w)
            elif self.logo_path and os.path.exists(self.logo_path):
                img = self.embed_logo(img, self.logo_path)

            if self.enable_frame_var.get():
                thickness_str = self.frame_thickness_option.get()
                border_px = 6 if "Thin" in thickness_str else (20 if "Thick" in thickness_str else 12)
                is_round = self.frame_style_option.get() == "Rounded Image"
                img = self.apply_outer_frame(img, banner_text, fg_rgb, bg_rgb, border_px, is_round)

            self.qr_image_pil = img

            preview_img = ctk.CTkImage(light_image=img, dark_image=img, size=(240, 265 if self.enable_frame_var.get() else 240))
            self.qr_preview_label.configure(image=preview_img, text="")

            self.save_settings()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate QR Code:\n{str(e)}")

    def embed_logo(self, qr_img, logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        qr_w, qr_h = qr_img.size
        
        logo_size = int(qr_w * 0.22)
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)

        # Create Circular Mask for the Logo
        mask = Image.new("L", (logo_size, logo_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, logo_size, logo_size), fill=255)

        # Round white background circle behind the logo
        bg_circle_size = logo_size + 6
        bg_circle = Image.new("RGBA", (bg_circle_size, bg_circle_size), (0, 0, 0, 0))
        bg_draw = ImageDraw.Draw(bg_circle)
        bg_draw.ellipse((0, 0, bg_circle_size, bg_circle_size), fill="white")

        pos_bg = ((qr_w - bg_circle_size) // 2, (qr_h - bg_circle_size) // 2)
        qr_img.paste(bg_circle, pos_bg, bg_circle)

        pos = ((qr_w - logo_size) // 2, (qr_h - logo_size) // 2)
        qr_img.paste(logo, pos, mask=mask)

        return qr_img

    def apply_outer_frame(self, qr_img, banner_text, fg_color, bg_color, border_px, is_round=True):
        w, h = qr_img.size
        padding = 24
        bottom_banner_h = 80 if banner_text else 20
        
        card_w = w + (padding * 2)
        card_h = h + padding + bottom_banner_h

        card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(card)

        corner_radius = 30 if is_round else 0
        draw.rounded_rectangle([0, 0, card_w, card_h], radius=corner_radius, fill=fg_color)
        
        inner_radius = max(0, corner_radius - border_px) if is_round else 0
        inner_rect = [border_px, border_px, card_w - border_px, card_h - bottom_banner_h + 8]
        draw.rounded_rectangle(inner_rect, radius=inner_radius, fill=bg_color)

        card.paste(qr_img, (padding, padding), qr_img)

        if banner_text:
            font_size = int(bottom_banner_h * 0.45)
            try:
                font = ImageFont.truetype("arialbd.ttf", font_size)
            except OSError:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), banner_text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            text_x = (card_w - text_w) // 2
            text_y = card_h - (bottom_banner_h // 2) - (text_h // 2) - 6

            draw.text((text_x, text_y), banner_text, fill=bg_color, font=font)

        return card

    def apply_eye_customization(self, qr, img, eye_style, eye_rgb, bg_rgb, border, box_size):
        matrix_size = len(qr.get_matrix())
        eyes_coords = [
            (border, border),
            (matrix_size - 7 - border, border),
            (border, matrix_size - 7 - border)
        ]

        eye_rgba = eye_rgb + (255,)
        bg_rgba = bg_rgb + (255,)

        for col, row in eyes_coords:
            x0 = col * box_size
            y0 = row * box_size
            x1 = (col + 7) * box_size
            y1 = (row + 7) * box_size
            w = x1 - x0

            eye_tile = Image.new("RGBA", (w, w), bg_rgba)
            draw = ImageDraw.Draw(eye_tile)

            if eye_style == "Square":
                draw.rectangle([0, 0, w, w], fill=eye_rgba)
                draw.rectangle([box_size, box_size, w - box_size, w - box_size], fill=bg_rgba)
                draw.rectangle([box_size * 2, box_size * 2, w - box_size * 2, w - box_size * 2], fill=eye_rgba)

            elif eye_style == "Rounded":
                r_out = int(box_size * 1.5)
                r_in = int(box_size * 0.8)
                draw.rounded_rectangle([0, 0, w, w], radius=r_out, fill=eye_rgba)
                draw.rounded_rectangle([box_size, box_size, w - box_size, w - box_size], radius=r_in, fill=bg_rgba)
                draw.rounded_rectangle([box_size * 2, box_size * 2, w - box_size * 2, w - box_size * 2], radius=r_in, fill=eye_rgba)

            elif eye_style == "Ring / Circle":
                draw.ellipse([0, 0, w, w], fill=eye_rgba)
                draw.ellipse([box_size, box_size, w - box_size, w - box_size], fill=bg_rgba)
                draw.ellipse([box_size * 2, box_size * 2, w - box_size * 2, w - box_size * 2], fill=eye_rgba)

            elif eye_style == "Blob / Oval":
                draw.rounded_rectangle([0, 0, w, w], radius=w // 2, fill=eye_rgba)
                draw.rounded_rectangle([box_size, box_size, w - box_size, w - box_size], radius=(w - box_size * 2) // 2, fill=bg_rgba)
                draw.ellipse([box_size * 2, box_size * 2, w - box_size * 2, w - box_size * 2], fill=eye_rgba)

            img.paste(eye_tile, (x0, y0))
        return img

    def make_transparent(self, img, bg_rgb):
        r, g, b, a = img.split()
        r_mask = r.point(lambda p: 255 if p == bg_rgb[0] else 0)
        alpha = Image.eval(r_mask, lambda p: 0 if p == 255 else 255)
        img.putalpha(alpha)
        return img

    def embed_text(self, qr_img, text, fg_rgba, bg_rgba, border_rgba, border_width):
        qr_w, qr_h = qr_img.size
        scale = 4
        canvas_w = qr_w * scale
        canvas_h = qr_h * scale
        
        overlay = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return qr_img

        font_size = int(canvas_w * 0.05)
        try:
            font = ImageFont.truetype("arialbd.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

        line_heights = []
        line_widths = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_widths.append(bbox[2] - bbox[0])
            line_heights.append(bbox[3] - bbox[1])

        max_w = max(line_widths)
        line_spacing = int(font_size * 0.2)
        total_h = sum(line_heights) + (len(lines) - 1) * line_spacing

        pad_x = int(font_size * 0.6)
        pad_y = int(font_size * 0.4)
        center_x, center_y = canvas_w // 2, canvas_h // 2
        
        bg_rect = [
            center_x - (max_w // 2) - pad_x,
            center_y - (total_h // 2) - pad_y,
            center_x + (max_w // 2) + pad_x,
            center_y + (total_h // 2) + pad_y
        ]
        
        scaled_border_w = border_width * scale

        if scaled_border_w > 0:
            draw.rounded_rectangle(
                bg_rect, 
                radius=int(font_size * 0.35), 
                fill=bg_rgba, 
                outline=border_rgba, 
                width=scaled_border_w
            )
        else:
            draw.rounded_rectangle(
                bg_rect, 
                radius=int(font_size * 0.35), 
                fill=bg_rgba
            )

        current_y = center_y - (total_h // 2)
        for i, line in enumerate(lines):
            l_w = line_widths[i]
            draw.text((center_x - (l_w // 2), current_y), line, font=font, fill=fg_rgba)
            current_y += line_heights[i] + line_spacing

        overlay = overlay.resize((qr_w, qr_h), Image.Resampling.LANCZOS)
        qr_img.paste(overlay, (0, 0), overlay)
        return qr_img

    def save_qr(self):
        if not self.qr_image_pil:
            messagebox.showwarning("Save Error", "No QR Code generated yet.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Image", "*.png")])
        if file_path:
            self.qr_image_pil.save(file_path)
            messagebox.showinfo("Success", f"QR Code saved to:\n{file_path}")

    # ==========================================
    # PERSISTENT SETTINGS
    # ==========================================
    def save_settings(self):
        settings = {
            "qr_data": self.qr_data_entry.get(),
            "qr_fg": self.qr_fg_entry.get(),
            "qr_eye": self.qr_eye_entry.get(),
            "qr_bg": self.qr_bg_entry.get(),
            "transparent_bg": self.transparent_bg_var.get(),
            "qr_style": self.qr_style_option.get(),
            "qr_eye_style": self.qr_eye_style_option.get(),
            "center_text": self.center_text_entry.get("1.0", tk.END).strip(),
            "center_text_fg": self.center_text_fg.get(),
            "center_text_bg": self.center_text_bg.get(),
            "center_border_fg": self.center_border_fg.get(),
            "center_border_width": self.center_border_width.get(),
            "enable_frame": self.enable_frame_var.get(),
            "frame_style": self.frame_style_option.get(),
            "frame_thickness": self.frame_thickness_option.get(),
            "banner_text": self.banner_text_entry.get(),
            "bc_data": self.bc_data_entry.get(),
            "bc_type": self.bc_type_option.get(),
            "bc_fg": self.bc_fg_entry.get(),
            "bc_bg": self.bc_bg_entry.get()
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(settings, f, indent=4)
        except Exception:
            pass

    def load_settings(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r") as f:
                s = json.load(f)

            if "qr_data" in s: self.qr_data_entry.insert(0, s["qr_data"])
            if "qr_fg" in s: self.qr_fg_entry.delete(0, tk.END); self.qr_fg_entry.insert(0, s["qr_fg"])
            if "qr_eye" in s: self.qr_eye_entry.delete(0, tk.END); self.qr_eye_entry.insert(0, s["qr_eye"])
            if "qr_bg" in s: self.qr_bg_entry.delete(0, tk.END); self.qr_bg_entry.insert(0, s["qr_bg"])
            if "transparent_bg" in s: self.transparent_bg_var.set(s["transparent_bg"]); self.toggle_bg_entry()
            if "qr_style" in s: self.qr_style_option.set(s["qr_style"])
            if "qr_eye_style" in s: self.qr_eye_style_option.set(s["qr_eye_style"])
            if "center_text" in s: self.center_text_entry.insert("1.0", s["center_text"])
            if "center_text_fg" in s: self.center_text_fg.delete(0, tk.END); self.center_text_fg.insert(0, s["center_text_fg"])
            if "center_text_bg" in s: self.center_text_bg.delete(0, tk.END); self.center_text_bg.insert(0, s["center_text_bg"])
            if "center_border_fg" in s: self.center_border_fg.delete(0, tk.END); self.center_border_fg.insert(0, s["center_border_fg"])
            if "center_border_width" in s: self.center_border_width.delete(0, tk.END); self.center_border_width.insert(0, s["center_border_width"])
            if "enable_frame" in s: self.enable_frame_var.set(s["enable_frame"])
            if "frame_style" in s: self.frame_style_option.set(s["frame_style"])
            if "frame_thickness" in s: self.frame_thickness_option.set(s["frame_thickness"])
            if "banner_text" in s: self.banner_text_entry.delete(0, tk.END); self.banner_text_entry.insert(0, s["banner_text"])
            if "bc_data" in s: self.bc_data_entry.insert(0, s["bc_data"])
            if "bc_type" in s: self.bc_type_option.set(s["bc_type"])
            if "bc_fg" in s: self.bc_fg_entry.delete(0, tk.END); self.bc_fg_entry.insert(0, s["bc_fg"])
            if "bc_bg" in s: self.bc_bg_entry.delete(0, tk.END); self.bc_bg_entry.insert(0, s["bc_bg"])
        except Exception:
            pass

    def on_close(self):
        self.save_settings()
        self.destroy()

    # ==========================================
    # TAB 2 & 3: BARCODE & READER
    # ==========================================
    def build_barcode_tab(self):
        self.tab_barcode.columnconfigure(0, weight=2)
        self.tab_barcode.columnconfigure(1, weight=1)

        controls_frame = ctk.CTkFrame(self.tab_barcode)
        controls_frame.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")

        ctk.CTkLabel(controls_frame, text="Barcode Settings", font=("Helvetica", 13, "bold")).pack(pady=6)

        self.bc_data_entry = ctk.CTkEntry(controls_frame, placeholder_text="Enter text/digits...", width=240, height=26)
        self.bc_data_entry.pack(pady=4)

        type_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        type_frame.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(type_frame, text="Barcode Type:").pack(side="left")
        self.bc_type_option = ctk.CTkOptionMenu(type_frame, values=["code128", "ean13", "code39"], width=110, height=22)
        self.bc_type_option.pack(side="right")

        fg_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        fg_frame.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(fg_frame, text="Bar Color (Hex):").pack(side="left")
        self.bc_fg_entry = ctk.CTkEntry(fg_frame, width=90, height=22)
        self.bc_fg_entry.insert(0, "#000000")
        self.bc_fg_entry.pack(side="right")

        bg_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        bg_frame.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(bg_frame, text="Background (Hex):").pack(side="left")
        self.bc_bg_entry = ctk.CTkEntry(bg_frame, width=90, height=22)
        self.bc_bg_entry.insert(0, "#FFFFFF")
        self.bc_bg_entry.pack(side="right")

        ctk.CTkButton(controls_frame, text="Generate Barcode", fg_color="#1f6aa5", height=28, command=self.generate_barcode).pack(pady=10)
        ctk.CTkButton(controls_frame, text="Save Barcode", fg_color="#2b8a3e", height=26, command=self.save_barcode).pack(pady=2)

        preview_frame = ctk.CTkFrame(self.tab_barcode)
        preview_frame.grid(row=0, column=1, padx=8, pady=8, sticky="nsew")

        ctk.CTkLabel(preview_frame, text="Preview", font=("Helvetica", 13, "bold")).pack(pady=8)
        self.bc_preview_label = ctk.CTkLabel(preview_frame, text="Your Barcode will appear here", width=220, height=140)
        self.bc_preview_label.pack(expand=True, pady=8)

    def generate_barcode(self):
        data = self.bc_data_entry.get().strip()
        bc_type = self.bc_type_option.get()
        fg = self.bc_fg_entry.get().strip() or "#000000"
        bg = self.bc_bg_entry.get().strip() or "#FFFFFF"

        if not data:
            messagebox.showwarning("Input Error", "Please enter data for the barcode.")
            return

        try:
            barcode_cls = barcode.get_barcode_class(bc_type)
            writer_options = {
                "module_width": 0.3,
                "module_height": 15.0,
                "font_size": 10,
                "text_distance": 5.0,
                "foreground": fg,
                "background": bg,
            }
            
            bc_instance = barcode_cls(data, writer=ImageWriter())
            img = bc_instance.render(writer_options)

            self.barcode_image_pil = img

            w, h = img.size
            aspect = h / w
            preview_w = 240
            preview_h = int(preview_w * aspect)

            preview_img = ctk.CTkImage(light_image=img, dark_image=img, size=(preview_w, preview_h))
            self.bc_preview_label.configure(image=preview_img, text="")

            self.save_settings()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate Barcode:\n{str(e)}")

    def save_barcode(self):
        if not self.barcode_image_pil:
            messagebox.showwarning("Save Error", "No Barcode generated yet.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Image", "*.png")])
        if file_path:
            self.barcode_image_pil.save(file_path)
            messagebox.showinfo("Success", f"Barcode saved to:\n{file_path}")

    def build_reader_tab(self):
        self.tab_reader.columnconfigure(0, weight=1)
        self.tab_reader.rowconfigure(0, weight=1)

        frame = ctk.CTkFrame(self.tab_reader)
        frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(frame, text="Upload Image to Decode QR / Barcode", font=("Helvetica", 14, "bold")).pack(pady=8)

        ctk.CTkButton(frame, text="Select File to Scan", fg_color="#1f6aa5", height=28, command=self.decode_image).pack(pady=6)

        self.scan_preview_label = ctk.CTkLabel(frame, text="No image loaded", width=180, height=180)
        self.scan_preview_label.pack(pady=6)

        ctk.CTkLabel(frame, text="Decoded Content:", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=20, pady=(4, 0))
        self.decoded_text = ctk.CTkTextbox(frame, width=400, height=70)
        self.decoded_text.pack(pady=4)

    def decode_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")])
        if not file_path:
            return

        img_pil = Image.open(file_path)
        preview_img = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=(180, 180))
        self.scan_preview_label.configure(image=preview_img, text="")

        cv_img = cv2.imread(file_path)
        decoded_results = []

        qr_detector = cv2.QRCodeDetector()
        val, pts, _ = qr_detector.detectAndDecode(cv_img)
        if val:
            decoded_results.append(f"[QR Code Detected]\n{val}")

        try:
            bc_detector = cv2.barcode.BarcodeDetector()
            ok, vals, _, _ = bc_detector.detectAndDecode(cv_img)
            if ok:
                for v in vals:
                    if v:
                        decoded_results.append(f"[Barcode Detected]\n{v}")
        except Exception:
            pass

        self.decoded_text.delete("1.0", tk.END)
        if decoded_results:
            self.decoded_text.insert(tk.END, "\n\n".join(decoded_results))
        else:
            self.decoded_text.insert(tk.END, "No valid QR or Barcode could be detected in this image.")


if __name__ == "__main__":
    app = CodeStudioApp()
    app.mainloop()