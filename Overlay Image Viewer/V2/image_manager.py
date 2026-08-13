import os
import shutil
import requests
from PySide6.QtCore import QByteArray, QObject, Signal, Qt
from PySide6.QtGui import QPixmap, QImage, QGuiApplication
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QMessageBox, QLabel, QFrame, QInputDialog
)

from config import TEMP_IMG_DIR


class ImageManager(QObject):
    image_changed = Signal(str, QPixmap)  # Emits (cached_path, pixmap)

    def __init__(self, parent=None):
        super().__init__(parent)
        os.makedirs(TEMP_IMG_DIR, exist_ok=True)
        self.managed_images = []
        self.locked_images = set()  # Tracks locked image paths
        self.current_image_path = None
        self.current_pixmap = None

    # --- Backward Compatibility Properties & Methods ---
    @property
    def recent_images(self):
        return self.managed_images

    @recent_images.setter
    def recent_images(self, value):
        self.managed_images = value

    def set_recents(self, raw_images):
        self.set_managed_images(raw_images)

    def remove_from_recents(self, path, parent_widget=None):
        return self.remove_image(path, parent_widget)

    def clear_recents(self):
        self.clear_all_unlocked()

    # --- Utility Helpers ---
    def is_valid_image(self, file_path):
        valid_exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tiff"}
        return os.path.splitext(file_path)[1].lower() in valid_exts

    # --- Lock Feature Helpers ---
    def is_locked(self, path):
        return path in self.locked_images

    def toggle_lock(self, path):
        if path in self.locked_images:
            self.locked_images.remove(path)
            return False  # Unlocked
        else:
            self.locked_images.add(path)
            return True   # Locked

    # --- Rename Feature ---
    def rename_image(self, old_path, new_name, parent_widget=None):
        if not new_name or not new_name.strip():
            return False

        ext = os.path.splitext(old_path)[1]
        new_filename = new_name.strip() if new_name.endswith(ext) else f"{new_name.strip()}{ext}"
        new_path = os.path.join(os.path.dirname(old_path), new_filename)

        if old_path == new_path:
            return True

        if os.path.exists(new_path):
            if parent_widget:
                QMessageBox.warning(parent_widget, "Rename Error", f"A file named '{new_filename}' already exists.")
            return False

        try:
            os.rename(old_path, new_path)

            if old_path in self.managed_images:
                idx = self.managed_images.index(old_path)
                self.managed_images[idx] = new_path

            if old_path in self.locked_images:
                self.locked_images.remove(old_path)
                self.locked_images.add(new_path)

            if self.current_image_path == old_path:
                self.current_image_path = new_path
                self.image_changed.emit(new_path, self.current_pixmap)

            return True
        except Exception as e:
            if parent_widget:
                QMessageBox.critical(parent_widget, "Rename Error", f"Failed to rename file:\n{e}")
            return False

    # --- Image Operations ---
    def add_to_managed(self, cached_path):
        if cached_path in self.managed_images:
            self.managed_images.remove(cached_path)
        self.managed_images.insert(0, cached_path)
        self.managed_images = self.managed_images[:30]

    def remove_image(self, path, parent_widget=None):
        """Removes the image from manager list and DELETES the file from disk if unlocked."""
        if self.is_locked(path):
            if parent_widget:
                QMessageBox.warning(
                    parent_widget,
                    "Image Locked",
                    "This image is locked. Unlock it before deleting."
                )
            return False

        if path in self.managed_images:
            self.managed_images.remove(path)

        # Delete physical file from disk
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                if parent_widget:
                    QMessageBox.warning(parent_widget, "File Error", f"Could not delete physical file:\n{e}")

        if self.current_image_path == path:
            self.clear()

        return True

    def clear_all_unlocked(self):
        """Clears all unlocked images from manager list AND deletes their actual files on disk."""
        unlocked = [p for p in self.managed_images if not self.is_locked(p)]
        for path in unlocked:
            self.managed_images.remove(path)

            # Delete physical file from disk
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

            if self.current_image_path == path:
                self.clear()

    def set_managed_images(self, raw_images):
        self.managed_images = []
        for item in raw_images:
            if isinstance(item, dict):
                path = item.get("cached", "")
                if item.get("locked", False):
                    self.locked_images.add(path)
            else:
                path = item

            if path and os.path.exists(path):
                self.managed_images.append(path)
        self.managed_images = self.managed_images[:30]

    def get_managed_data(self):
        """Helper to serialize managed list along with locked state for config saving."""
        return [
            {"cached": path, "locked": self.is_locked(path)}
            for path in self.managed_images
        ]

    # --- Loading Logic ---
    def load_image_from_path(self, cached_path):
        if not os.path.exists(cached_path):
            return False

        pixmap = QPixmap(cached_path)
        if not pixmap.isNull():
            self.current_image_path = cached_path
            self.current_pixmap = pixmap
            self.add_to_managed(cached_path)
            self.image_changed.emit(cached_path, pixmap)
            return True
        return False

    def import_and_cache_file(self, source_path, parent_widget=None):
        try:
            filename = os.path.basename(source_path)
            cached_path = os.path.join(TEMP_IMG_DIR, filename)

            if os.path.abspath(source_path) != os.path.abspath(cached_path):
                shutil.copy2(source_path, cached_path)

            return self.load_image_from_path(cached_path)
        except Exception as e:
            if parent_widget:
                QMessageBox.critical(parent_widget, "Error", f"Failed to import image:\n{e}")
            return False

    def load_from_url(self, url, parent_widget=None):
        if not url or not url.strip():
            return False
        try:
            response = requests.get(url.strip(), timeout=5)
            response.raise_for_status()
            image = QImage()
            if image.loadFromData(QByteArray(response.content)):
                filename = f"url_image_{len(self.managed_images) + 1}.png"
                cached_path = os.path.join(TEMP_IMG_DIR, filename)
                image.save(cached_path, "PNG", 100)
                return self.load_image_from_path(cached_path)
            else:
                if parent_widget:
                    QMessageBox.warning(parent_widget, "Error", "Failed to parse image from URL.")
        except Exception as e:
            if parent_widget:
                QMessageBox.critical(parent_widget, "Error", f"Failed to download image:\n{str(e)}")
        return False

    def paste_from_clipboard(self, parent_widget=None):
        clipboard = QGuiApplication.clipboard()
        mime_data = clipboard.mimeData()

        if mime_data.hasImage():
            image = clipboard.image()
            if not image.isNull():
                filename = f"pasted_{len(self.managed_images) + 1}.png"
                cached_path = os.path.join(TEMP_IMG_DIR, filename)
                image.save(cached_path, "PNG", 100)
                return self.load_image_from_path(cached_path)
        elif mime_data.hasUrls():
            urls = mime_data.urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path and self.is_valid_image(file_path):
                    return self.import_and_cache_file(file_path, parent_widget)
        else:
            if parent_widget:
                QMessageBox.information(parent_widget, "Clipboard Empty", "No valid image found on clipboard.")
        return False

    def save_pixmap_as_snip(self, pixmap):
        if pixmap and not pixmap.isNull():
            filename = f"snip_{len(self.managed_images) + 1}.png"
            cached_path = os.path.join(TEMP_IMG_DIR, filename)
            pixmap.save(cached_path, "PNG", 100)
            return self.load_image_from_path(cached_path)
        return False

    def clear(self):
        self.current_image_path = None
        self.current_pixmap = None

    def open_manager_dialog(self, parent_window=None):
        dialog = ImageManagerDialog(image_manager=self, parent=parent_window)
        return dialog.exec()


class ImageManagerDialog(QDialog):
    def __init__(self, image_manager: ImageManager, parent=None):
        super().__init__(parent)
        self.image_manager = image_manager
        self.setWindowTitle("Image Manager")
        self.resize(800, 450)

        main_layout = QHBoxLayout(self)

        # Left Container
        left_layout = QVBoxLayout()

        self.list_widget = QListWidget(self)
        self.list_widget.itemDoubleClicked.connect(self.load_selected_image)
        self.list_widget.currentItemChanged.connect(self.on_item_changed)
        left_layout.addWidget(self.list_widget)

        # Action Buttons
        btn_layout = QHBoxLayout()

        self.load_btn = QPushButton("Load Selected", self)
        self.load_btn.clicked.connect(self.load_selected_image)

        self.rename_btn = QPushButton("✏️ Rename", self)
        self.rename_btn.clicked.connect(self.rename_selected_image)

        self.lock_btn = QPushButton("🔒 Lock / Unlock", self)
        self.lock_btn.clicked.connect(self.toggle_lock_selected)

        self.remove_btn = QPushButton("Remove", self)
        self.remove_btn.clicked.connect(self.remove_selected_image)

        self.clear_all_btn = QPushButton("Clear All", self)
        self.clear_all_btn.clicked.connect(self.clear_all_images)

        btn_layout.addWidget(self.load_btn)
        btn_layout.addWidget(self.rename_btn)
        btn_layout.addWidget(self.lock_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.clear_all_btn)

        left_layout.addLayout(btn_layout)
        main_layout.addLayout(left_layout, stretch=3)

        # Right Container (Preview Area)
        preview_container = QVBoxLayout()

        self.preview_label = QLabel("No Selection", self)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFrameShape(QFrame.StyledPanel)
        self.preview_label.setMinimumSize(300, 300)
        self.preview_label.setStyleSheet("background-color: #1e1e1e; color: #888888; border-radius: 4px;")

        self.info_label = QLabel("", self)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #aaaaaa; font-size: 11px;")

        preview_container.addWidget(self.preview_label, stretch=1)
        preview_container.addWidget(self.info_label)

        main_layout.addLayout(preview_container, stretch=2)

        self.populate_list()

    def populate_list(self):
        selected_path = None
        if self.list_widget.currentItem():
            selected_path = self.list_widget.currentItem().data(Qt.UserRole)

        self.list_widget.clear()
        if not self.image_manager:
            return

        images = self.image_manager.managed_images
        current_path = self.image_manager.current_image_path

        item_to_reselect = None
        for cached_path in images:
            if os.path.exists(cached_path):
                filename = os.path.basename(cached_path)

                is_locked = self.image_manager.is_locked(cached_path)
                lock_prefix = "🔒 " if is_locked else ""
                current_suffix = " (Current)" if cached_path == current_path else ""

                display_text = f"{lock_prefix}{filename}{current_suffix}"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, cached_path)

                if cached_path == selected_path:
                    item_to_reselect = item

                self.list_widget.addItem(item)

        if item_to_reselect:
            self.list_widget.setCurrentItem(item_to_reselect)
        elif self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
        else:
            self.clear_preview()

    def on_item_changed(self, current_item, previous_item=None):
        self.update_preview(current_item)
        if current_item:
            path = current_item.data(Qt.UserRole)
            is_locked = self.image_manager.is_locked(path)
            self.remove_btn.setEnabled(not is_locked)
            self.lock_btn.setText("🔓 Unlock" if is_locked else "🔒 Lock")

    def rename_selected_image(self):
        current_item = self.list_widget.currentItem()
        if not current_item:
            return

        old_path = current_item.data(Qt.UserRole)
        current_filename, _ = os.path.splitext(os.path.basename(old_path))

        new_name, ok = QInputDialog.getText(
            self,
            "Rename Image",
            "Enter new image name:",
            text=current_filename
        )

        if ok and new_name.strip():
            if self.image_manager.rename_image(old_path, new_name.strip(), parent_widget=self):
                self.populate_list()

    def toggle_lock_selected(self):
        current_item = self.list_widget.currentItem()
        if not current_item:
            return

        path = current_item.data(Qt.UserRole)
        self.image_manager.toggle_lock(path)
        self.populate_list()

    def update_preview(self, current_item):
        if not current_item:
            self.clear_preview()
            return

        path = current_item.data(Qt.UserRole)
        if path and os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    self.preview_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled_pixmap)

                file_size_kb = os.path.getsize(path) / 1024
                is_locked_str = " | Locked 🔒" if self.image_manager.is_locked(path) else ""
                self.info_label.setText(
                    f"{pixmap.width()} x {pixmap.height()} | {file_size_kb:.1f} KB{is_locked_str}"
                )
                return

        self.clear_preview()

    def clear_preview(self):
        self.preview_label.clear()
        self.preview_label.setText("No Image Selected")
        self.info_label.setText("")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_preview(self.list_widget.currentItem())

    def load_selected_image(self):
        current_item = self.list_widget.currentItem()
        if not current_item:
            return

        path = current_item.data(Qt.UserRole)
        if path and os.path.exists(path):
            self.image_manager.load_image_from_path(path)
            self.accept()

    def remove_selected_image(self):
        current_item = self.list_widget.currentItem()
        if not current_item:
            return

        path = current_item.data(Qt.UserRole)
        if self.image_manager.remove_image(path, parent_widget=self):
            if not self.image_manager.current_image_path and self.parent():
                self.parent().clear_image()

        self.populate_list()

    def clear_all_images(self):
        reply = QMessageBox.question(
            self,
            "Clear All",
            "Are you sure you want to clear and delete all unlocked images?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.image_manager.clear_all_unlocked()
            if not self.image_manager.current_image_path and self.parent():
                self.parent().clear_image()
            self.populate_list()