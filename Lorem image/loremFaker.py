import io
import json
import os
import random
import threading
import time
import customtkinter as ctk
from PIL import Image, ImageOps
import requests

# App Setup
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

SETTINGS_FILE = "app_settings.json"


class SettingsManager:
    """Manages local settings persistence."""

    DEFAULT_SETTINGS = {
        "theme": "Dark",
        "category": "Male Avatar",
        "preset_res": "500 x 500 (Square Avatar)",
        "width": 500,
        "height": 500,
        "count": 10,
        "search_term": "",
    }

    @classmethod
    def load(cls):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    for k, v in cls.DEFAULT_SETTINGS.items():
                        if k not in data:
                            data[k] = v
                    return data
            except Exception:
                pass
        return cls.DEFAULT_SETTINGS.copy()

    @classmethod
    def save(cls, settings):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)


class ImageStudioApp(ctk.CTk):

    PRESET_RESOLUTIONS = {
        "500 x 500 (Square Avatar)": (500, 500),
        "1080 x 1080 (Square Post)": (1080, 1080),
        "1920 x 1080 (Full HD Landscape)": (1920, 1080),
        "1280 x 720 (HD Landscape)": (1280, 720),
        "800 x 600 (Standard)": (800, 600),
        "Custom": (500, 500),
    }

    CATEGORIES = [
        "Male Avatar",
        "Female Avatar",
        "Nature",
        "Architecture",
        "Technology",
        "Abstract",
        "Food",
        "Animals",
        "City & Urban",
    ]

    # Pre-sorted Pravatar IDs for Male vs Female portrait generation
    MALE_AVATAR_IDS = [1, 3, 7, 8, 11, 12, 13, 14, 15, 18, 33, 51, 52, 53, 55, 56, 57, 59, 60, 64, 65, 67, 68, 69]
    FEMALE_AVATAR_IDS = [2, 5, 9, 10, 16, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 34, 35, 36, 47, 49]

    def __init__(self):
        super().__init__()

        self.title("Image Studio Pro - Fixed Duplicates")
        self.geometry("1200 x 800")
        self.minsize(1030, 650)

        self.settings = SettingsManager.load()
        self.image_records = []
        self.favorites = []
        self.selected_image_data = None
        
        # Track served URLs/IDs across sessions to prevent duplicates
        self.used_pravatar_ids = set()

        ctk.set_appearance_mode(self.settings.get("theme", "Dark"))
        self._build_ui()

        self.bind("<Configure>", self._on_window_resize)
        self._resize_timer = None

    def _build_ui(self):
        # --- LEFT SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=270, corner_radius=0)
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)

        ctk.CTkLabel(
            self.sidebar,
            text="🖼 Image Studio Pro",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(padx=20, pady=(20, 15))

        # 1. Search Keywords Bar
        ctk.CTkLabel(
            self.sidebar, text="Search Keywords:", font=ctk.CTkFont(weight="bold")
        ).pack(padx=20, pady=(5, 0), anchor="w")

        self.search_entry = ctk.CTkEntry(
            self.sidebar, placeholder_text="e.g. businessman, fashion, portrait..."
        )
        if self.settings.get("search_term"):
            self.search_entry.insert(0, self.settings.get("search_term"))
        self.search_entry.pack(padx=20, pady=(5, 12), fill="x")

        # 2. Preset Category
        ctk.CTkLabel(
            self.sidebar, text="Category Filter:", font=ctk.CTkFont(weight="bold")
        ).pack(padx=20, pady=(5, 0), anchor="w")

        self.category_dropdown = ctk.CTkOptionMenu(
            self.sidebar,
            values=self.CATEGORIES,
            command=self._on_category_changed,
        )
        self.category_dropdown.set(self.settings.get("category", "Male Avatar"))
        self.category_dropdown.pack(padx=20, pady=(5, 12), fill="x")

        # 3. Quantity Option
        ctk.CTkLabel(
            self.sidebar, text="Quantity to Show:", font=ctk.CTkFont(weight="bold")
        ).pack(padx=20, pady=(5, 0), anchor="w")

        self.count_dropdown = ctk.CTkOptionMenu(
            self.sidebar,
            values=["4", "6", "8", "10", "12", "16", "20"],
            command=self._on_settings_change,
        )
        self.count_dropdown.set(str(self.settings.get("count", 10)))
        self.count_dropdown.pack(padx=20, pady=(5, 12), fill="x")

        # 4. Predefined Resolution Dropdown
        ctk.CTkLabel(
            self.sidebar, text="Resolution Preset:", font=ctk.CTkFont(weight="bold")
        ).pack(padx=20, pady=(5, 0), anchor="w")

        self.res_preset_dropdown = ctk.CTkOptionMenu(
            self.sidebar,
            values=list(self.PRESET_RESOLUTIONS.keys()),
            command=self._on_preset_selected,
        )
        self.res_preset_dropdown.set(
            self.settings.get("preset_res", "500 x 500 (Square Avatar)")
        )
        self.res_preset_dropdown.pack(padx=20, pady=(5, 10), fill="x")

        # Custom Width / Height Inputs
        res_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        res_frame.pack(padx=20, pady=(0, 15), fill="x")

        self.width_entry = ctk.CTkEntry(res_frame, placeholder_text="Width", width=85)
        self.width_entry.insert(0, str(self.settings.get("width", 500)))
        self.width_entry.pack(side="left", padx=(0, 5))

        ctk.CTkLabel(res_frame, text="x").pack(side="left")

        self.height_entry = ctk.CTkEntry(
            res_frame, placeholder_text="Height", width=85
        )
        self.height_entry.insert(0, str(self.settings.get("height", 500)))
        self.height_entry.pack(side="right", padx=(5, 0))

        # Fetch Button
        self.btn_generate = ctk.CTkButton(
            self.sidebar,
            text="Fetch Images",
            command=self.start_generation,
            height=38,
            font=ctk.CTkFont(weight="bold"),
        )
        self.btn_generate.pack(padx=20, pady=(10, 10), fill="x")

        # Theme Switcher
        ctk.CTkLabel(self.sidebar, text="Theme Mode:").pack(
            padx=20, pady=(15, 2), anchor="w"
        )
        self.theme_dropdown = ctk.CTkOptionMenu(
            self.sidebar,
            values=["Dark", "Light", "System"],
            command=self.change_theme,
        )
        self.theme_dropdown.set(self.settings.get("theme", "Dark"))
        self.theme_dropdown.pack(padx=20, pady=(0, 20), fill="x")

        # --- RIGHT MAIN PANEL ---
        self.main_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.main_panel.pack(side="right", fill="both", expand=True, padx=15, pady=15)

        self.status_label = ctk.CTkLabel(
            self.main_panel,
            text="Ready. Click 'Fetch Images' to load unique results.",
            text_color="gray60",
            anchor="w",
        )
        self.status_label.pack(anchor="w", pady=(0, 5))

        self.progress_bar = ctk.CTkProgressBar(self.main_panel)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(0, 10))

        # Selected Action Bar
        self.selection_bar = ctk.CTkFrame(self.main_panel, height=45)
        self.selection_bar.pack(fill="x", pady=(0, 10))

        self.selected_url_entry = ctk.CTkEntry(
            self.selection_bar, placeholder_text="Click any image below to select..."
        )
        self.selected_url_entry.pack(
            side="left", fill="x", expand=True, padx=10, pady=8
        )

        self.btn_copy_url = ctk.CTkButton(
            self.selection_bar,
            text="Copy Link",
            width=85,
            command=self.copy_selected_url,
            state="disabled",
        )
        self.btn_copy_url.pack(side="right", padx=(0, 5), pady=8)

        self.btn_copy_image = ctk.CTkButton(
            self.selection_bar,
            text="📋 Copy Image",
            width=120,
            command=self.copy_selected_image,
            state="disabled",
        )
        self.btn_copy_image.pack(side="right", padx=5, pady=8)

        self.btn_download_selected = ctk.CTkButton(
            self.selection_bar,
            text="Save File",
            width=85,
            command=self.save_selected_file,
            state="disabled",
        )
        self.btn_download_selected.pack(side="right", padx=(5, 10), pady=8)

        # Tabview
        self.tabview = ctk.CTkTabview(self.main_panel)
        self.tabview.pack(fill="both", expand=True)

        self.tab_grid = self.tabview.add("🔍 Search Grid")
        self.tab_favorites = self.tabview.add("❤️ Shortlist")

        self.grid_scroll_frame = ctk.CTkScrollableFrame(self.tab_grid)
        self.grid_scroll_frame.pack(fill="both", expand=True)

        self.fav_top_bar = ctk.CTkFrame(self.tab_favorites, height=40)
        self.fav_top_bar.pack(fill="x", padx=5, pady=5)

        self.fav_count_lbl = ctk.CTkLabel(
            self.fav_top_bar,
            text="No items in shortlist.",
            font=ctk.CTkFont(weight="bold"),
        )
        self.fav_count_lbl.pack(side="left", padx=10)

        self.btn_download_all_favs = ctk.CTkButton(
            self.fav_top_bar,
            text="📦 Batch Download All Shortlisted",
            command=self.batch_download_favorites,
            state="disabled",
        )
        self.btn_download_all_favs.pack(side="right", padx=10, pady=5)

        self.fav_scroll_frame = ctk.CTkScrollableFrame(self.tab_favorites)
        self.fav_scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.rendered_cards = []

    def _on_category_changed(self, category_name):
        if "Avatar" in category_name:
            self.res_preset_dropdown.set("500 x 500 (Square Avatar)")
            self._on_preset_selected("500 x 500 (Square Avatar)")
        self._save_settings()

    def _on_preset_selected(self, preset_name):
        if preset_name in self.PRESET_RESOLUTIONS and preset_name != "Custom":
            w, h = self.PRESET_RESOLUTIONS[preset_name]
            self.width_entry.delete(0, "end")
            self.width_entry.insert(0, str(w))
            self.height_entry.delete(0, "end")
            self.height_entry.insert(0, str(h))
        self._save_settings()

    def _save_settings(self):
        try:
            w = int(self.width_entry.get())
            h = int(self.height_entry.get())
            count = int(self.count_dropdown.get())
        except ValueError:
            w, h, count = 500, 500, 10

        self.settings["width"] = w
        self.settings["height"] = h
        self.settings["count"] = count
        self.settings["preset_res"] = self.res_preset_dropdown.get()
        self.settings["category"] = self.category_dropdown.get()
        self.settings["search_term"] = self.search_entry.get().strip()
        self.settings["theme"] = self.theme_dropdown.get()
        SettingsManager.save(self.settings)

    def _on_settings_change(self, *args):
        self._save_settings()

    def change_theme(self, new_theme):
        ctk.set_appearance_mode(new_theme)
        self._save_settings()

    def start_generation(self):
        self._save_settings()
        w = self.settings["width"]
        h = self.settings["height"]
        count = self.settings["count"]
        category = self.settings["category"]
        keyword = self.settings["search_term"]

        self.btn_generate.configure(state="disabled")
        query_desc = f"'{keyword}'" if keyword else f"Category: {category}"
        self.status_label.configure(
            text=f"Fetching {count} unique images ({query_desc}, {w}x{h})...",
            text_color="#007ACC",
        )
        self.progress_bar.set(0.2)

        threading.Thread(
            target=self._fetch_images_thread,
            args=(category, keyword, w, h, count),
            daemon=True,
        ).start()

    def _fetch_images_thread(self, category, keyword, w, h, count):
        images_data = []
        
        # Determine available Avatar ID pool based on gender
        if category == "Male Avatar":
            available_pool = [i for i in self.MALE_AVATAR_IDS if i not in self.used_pravatar_ids]
            if len(available_pool) < count:
                self.used_pravatar_ids.clear()
                available_pool = list(self.MALE_AVATAR_IDS)
            selected_ids = random.sample(available_pool, min(count, len(available_pool)))
        elif category == "Female Avatar":
            available_pool = [i for i in self.FEMALE_AVATAR_IDS if i not in self.used_pravatar_ids]
            if len(available_pool) < count:
                self.used_pravatar_ids.clear()
                available_pool = list(self.FEMALE_AVATAR_IDS)
            selected_ids = random.sample(available_pool, min(count, len(available_pool)))
        else:
            selected_ids = []

        # Unique seeds set for LoremFlickr queries
        used_seeds = set()

        for i in range(count):
            base_timestamp = int(time.time() * 1000)

            if category in ["Male Avatar", "Female Avatar"] and not keyword:
                img_id = selected_ids[i] if i < len(selected_ids) else random.randint(1, 70)
                self.used_pravatar_ids.add(img_id)
                url = f"https://i.pravatar.cc/{w}?img={img_id}"
            elif keyword:
                tag = keyword.strip().replace(" ", ",")
                gender_prefix = "man," if category == "Male Avatar" else ("woman," if category == "Female Avatar" else "")
                
                # Ensure unique seed per image in loop
                seed = random.randint(100000, 999999)
                while seed in used_seeds:
                    seed = random.randint(100000, 999999)
                used_seeds.add(seed)

                url = f"https://loremflickr.com/{w}/{h}/{gender_prefix}{tag}?lock={seed}&time={base_timestamp + i}"
            else:
                cat_tag = category.split()[-1].lower()
                
                seed = random.randint(100000, 999999)
                while seed in used_seeds:
                    seed = random.randint(100000, 999999)
                used_seeds.add(seed)

                url = f"https://loremflickr.com/{w}/{h}/{cat_tag}?lock={seed}&time={base_timestamp + i}"

            images_data.append(
                {
                    "id": f"{i}_{base_timestamp}_{random.randint(100,999)}",
                    "index": i + 1,
                    "url": url,
                    "width": w,
                    "height": h,
                    "tag": keyword or category,
                }
            )

        self.image_records = images_data

        thumbnails = []
        for item in images_data:
            try:
                r = requests.get(
                    item["url"], timeout=8, headers={"User-Agent": "Mozilla/5.0"}
                )
                pil_img = Image.open(io.BytesIO(r.content)).convert("RGBA")
                thumb_pil = ImageOps.fit(
                    pil_img, (180, 120), method=Image.Resampling.LANCZOS
                )
                thumb_ctk = ctk.CTkImage(thumb_pil, size=(180, 120))
                thumbnails.append((thumb_ctk, r.content, pil_img))
            except Exception:
                thumbnails.append((None, None, None))

        self.after(0, lambda: self._render_grid(images_data, thumbnails))

    def _render_grid(self, records, thumbnails):
        self.progress_bar.set(1.0)
        self.status_label.configure(
            text=f"✔ Displayed {len(records)} unique images!",
            text_color="#2CC985",
        )
        self.btn_generate.configure(state="normal")

        for child in self.grid_scroll_frame.winfo_children():
            child.destroy()

        self.rendered_cards = []

        for idx, (item, (thumb_ctk, raw_bytes, pil_img)) in enumerate(
            zip(records, thumbnails)
        ):
            card_frame = ctk.CTkFrame(self.grid_scroll_frame, corner_radius=8)

            if thumb_ctk:
                btn_img = ctk.CTkButton(
                    card_frame,
                    image=thumb_ctk,
                    text="",
                    fg_color="transparent",
                    hover_color="#007ACC",
                    command=lambda it=item, b=raw_bytes, p=pil_img: self.select_image(
                        it, b, p
                    ),
                )
                btn_img.pack(padx=5, pady=(5, 2))
            else:
                lbl_err = ctk.CTkLabel(
                    card_frame, text="Failed to load", text_color="red"
                )
                lbl_err.pack(padx=10, pady=20)

            lbl_title = ctk.CTkLabel(
                card_frame,
                text=f"Option #{item['index']}",
                font=ctk.CTkFont(weight="bold"),
            )
            lbl_title.pack(pady=(0, 2))

            actions_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
            actions_frame.pack(fill="x", padx=5, pady=(2, 8))

            btn_fav = ctk.CTkButton(
                actions_frame,
                text="❤️ Fav",
                width=55,
                height=24,
                fg_color="#E63946",
                hover_color="#C1121F",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda it=item, b=raw_bytes, p=pil_img: self.add_to_favorites(
                    it, b, p
                ),
            )
            btn_fav.pack(side="left", padx=2)

            btn_pick = ctk.CTkButton(
                actions_frame,
                text="Pick",
                height=24,
                font=ctk.CTkFont(size=11),
                command=lambda it=item, b=raw_bytes, p=pil_img: self.select_image(
                    it, b, p
                ),
            )
            btn_pick.pack(side="right", fill="x", expand=True, padx=2)

            self.rendered_cards.append(card_frame)

        self.rearrange_grid()

    def rearrange_grid(self):
        if not self.rendered_cards:
            return

        frame_width = self.grid_scroll_frame.winfo_width()
        cols = max(1, frame_width // 210)

        for idx, card in enumerate(self.rendered_cards):
            r = idx // cols
            c = idx % cols
            card.grid(row=r, column=c, padx=8, pady=8, sticky="n")

    def _on_window_resize(self, event):
        if self._resize_timer:
            self.after_cancel(self._resize_timer)
        self._resize_timer = self.after(100, self.rearrange_grid)

    def select_image(self, item_data, raw_bytes, pil_img):
        self.selected_image_data = {
            "meta": item_data,
            "bytes": raw_bytes,
            "pil": pil_img,
        }

        self.selected_url_entry.delete(0, "end")
        self.selected_url_entry.insert(0, item_data["url"])

        self.btn_copy_url.configure(state="normal")
        self.btn_copy_image.configure(state="normal")
        self.btn_download_selected.configure(state="normal")

        self.status_label.configure(
            text=f"Selected Option #{item_data['index']} ({item_data['width']}x{item_data['height']} px)",
            text_color="#007ACC",
        )

    def add_to_favorites(self, item, raw_bytes, pil_img):
        if any(f["meta"]["id"] == item["id"] for f in self.favorites):
            self.status_label.configure(
                text=f"Option #{item['index']} is already in Shortlist!",
                text_color="orange",
            )
            return

        if pil_img:
            thumb_pil = ImageOps.fit(
                pil_img, (160, 110), method=Image.Resampling.LANCZOS
            )
            thumb_ctk = ctk.CTkImage(thumb_pil, size=(160, 110))
        else:
            thumb_ctk = None

        fav_entry = {
            "meta": item,
            "bytes": raw_bytes,
            "thumb": thumb_ctk,
            "pil": pil_img,
        }
        self.favorites.append(fav_entry)
        self._render_favorites_tray()
        self.status_label.configure(
            text=f"Added Option #{item['index']} to Shortlist!", text_color="#2CC985"
        )

    def _render_favorites_tray(self):
        count = len(self.favorites)
        self.fav_count_lbl.configure(text=f"Total Shortlisted Images: {count}")
        self.btn_download_all_favs.configure(
            state="normal" if count > 0 else "disabled"
        )

        for child in self.fav_scroll_frame.winfo_children():
            child.destroy()

        for idx, fav in enumerate(self.favorites):
            card = ctk.CTkFrame(self.fav_scroll_frame, corner_radius=8)
            card.pack(side="left", padx=8, pady=8)

            if fav["thumb"]:
                lbl = ctk.CTkLabel(card, image=fav["thumb"], text="")
                lbl.pack(padx=5, pady=5)

            ctk.CTkLabel(
                card,
                text=f"Fav #{idx+1} ({fav['meta']['width']}x{fav['meta']['height']})",
                font=ctk.CTkFont(weight="bold", size=11),
            ).pack(pady=(0, 2))

            btn_remove = ctk.CTkButton(
                card,
                text="Remove",
                height=22,
                fg_color="gray30",
                hover_color="#E63946",
                command=lambda f=fav: self.remove_favorite(f),
            )
            btn_remove.pack(padx=5, pady=(2, 6))

    def remove_favorite(self, fav):
        if fav in self.favorites:
            self.favorites.remove(fav)
            self._render_favorites_tray()

    def batch_download_favorites(self):
        if not self.favorites:
            return

        folder_path = ctk.filedialog.askdirectory(
            title="Select Folder to Save Shortlisted Images"
        )
        if folder_path:
            saved_count = 0
            for idx, fav in enumerate(self.favorites):
                if fav["bytes"]:
                    file_path = os.path.join(
                        folder_path, f"shortlist_avatar_{idx+1}.jpg"
                    )
                    with open(file_path, "wb") as f:
                        f.write(fav["bytes"])
                    saved_count += 1

            self.status_label.configure(
                text=f"Saved {saved_count} shortlisted images!",
                text_color="#2CC985",
            )

    def copy_selected_url(self):
        if self.selected_image_data:
            url = self.selected_image_data["meta"]["url"]
            self.clipboard_clear()
            self.clipboard_append(url)
            self.update()

            self.btn_copy_url.configure(text="Copied! ✔", fg_color="#2CC985")
            self.after(
                1200,
                lambda: self.btn_copy_url.configure(
                    text="Copy Link",
                    fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
                ),
            )

    def copy_selected_image(self):
        if not self.selected_image_data or not self.selected_image_data["pil"]:
            return

        pil_img = self.selected_image_data["pil"]

        try:
            import win32clipboard

            output = io.BytesIO()
            pil_img.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]
            output.close()

            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()

            self.btn_copy_image.configure(text="Copied! ✔", fg_color="#2CC985")
            self.after(
                1200,
                lambda: self.btn_copy_image.configure(
                    text="📋 Copy Image",
                    fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
                ),
            )
        except Exception:
            self.copy_selected_url()

    def save_selected_file(self):
        if self.selected_image_data and self.selected_image_data["bytes"]:
            file_path = ctk.filedialog.asksaveasfilename(
                defaultextension=".jpg",
                filetypes=[("JPEG Image", "*.jpg"), ("PNG Image", "*.png")],
            )
            if file_path:
                with open(file_path, "wb") as f:
                    f.write(self.selected_image_data["bytes"])
                self.status_label.configure(
                    text=f"Saved image to: {os.path.basename(file_path)}",
                    text_color="#2CC985",
                )


if __name__ == "__main__":
    app = ImageStudioApp()
    app.mainloop()