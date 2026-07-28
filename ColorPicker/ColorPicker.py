import sys
import os
import json
import colorsys
import pyperclip
from PIL import ImageGrab

from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QColor, QCursor, QGuiApplication, QPixmap, QPainter, QImage, QIcon, QPen, QRegion
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QComboBox
)

SETTINGS_FILE = "settings.json"

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class ClickableFrame(QFrame):
    """A color swatch frame that behaves like a button on click."""
    def __init__(self, click_callback, parent=None):
        super().__init__(parent)
        self.click_callback = click_callback
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.click_callback()


class FullscreenOverlay(QWidget):
    """Takes a snapshot of the screen with a live magnifying glass on hover."""
    def __init__(self, main_picker):
        super().__init__()
        self.main_picker = main_picker
        self.mouse_pos = QPoint(-1000, -1000)

        # Magnifier Settings
        self.zoom_factor = 8     # 8x zoom level
        self.loupe_radius = 60   # Loupe radius in pixels
        
        # Capture screen once for fast pixel lookups and zoom rendering
        screen_img = ImageGrab.grab(all_screens=True)
        img_data = screen_img.tobytes("raw", "RGB")
        self.qimage = QImage(
            img_data, 
            screen_img.width, 
            screen_img.height, 
            screen_img.width * 3, 
            QImage.Format.Format_RGB888
        )
        self.pixmap = QPixmap.fromImage(self.qimage)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        geo = QApplication.primaryScreen().virtualGeometry()
        self.setGeometry(geo)

        self.setMouseTracking(True)
        QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Draw full background screenshot
        painter.drawPixmap(0, 0, self.pixmap)

        # 2. Draw Magnifying Glass Loupe at current mouse position
        x, y = self.mouse_pos.x(), self.mouse_pos.y()
        if 0 <= x < self.qimage.width() and 0 <= y < self.qimage.height():
            src_w = int((self.loupe_radius * 2) / self.zoom_factor)
            src_h = int((self.loupe_radius * 2) / self.zoom_factor)
            src_x = x - src_w // 2
            src_y = y - src_h // 2

            cropped_pixmap = self.pixmap.copy(src_x, src_y, src_w, src_h)
            zoomed_pixmap = cropped_pixmap.scaled(
                self.loupe_radius * 2, 
                self.loupe_radius * 2, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.FastTransformation
            )

            # Circular Loupe region setup using QRegion
            loupe_rect = QRect(x - self.loupe_radius, y - self.loupe_radius, self.loupe_radius * 2, self.loupe_radius * 2)
            loupe_region = QRegion(loupe_rect, QRegion.RegionType.Ellipse)
            
            painter.save()

            # Clip inside the circular region
            painter.setClipRegion(loupe_region)
            painter.drawPixmap(loupe_rect.topLeft(), zoomed_pixmap)

            # Draw Center Pixel Highlight Box
            px_size = self.zoom_factor
            center_x = x - (px_size // 2)
            center_y = y - (px_size // 2)
            painter.setPen(QPen(QColor("#FFFFFF"), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(center_x, center_y, px_size, px_size)

            painter.restore()

            # Draw Outer Ring Border for the Loupe
            painter.setPen(QPen(QColor("#007ACC"), 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(loupe_rect)

    def mouseMoveEvent(self, event):
        self.mouse_pos = event.pos()
        x, y = self.mouse_pos.x(), self.mouse_pos.y()

        if 0 <= x < self.qimage.width() and 0 <= y < self.qimage.height():
            qcolor = self.qimage.pixelColor(x, y)
            self.main_picker.update_color(qcolor)

        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.cleanup_and_close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cleanup_and_close()

    def cleanup_and_close(self):
        QGuiApplication.restoreOverrideCursor()
        self.close()


class FlutterColorPicker(QWidget):
    def __init__(self, icon):
        super().__init__()
        self.app_icon = icon
        self.current_color = QColor("#3B82F6")
        self.init_ui()
        self.load_settings()
        self.position_bottom_left()

    def position_bottom_left(self):
        """Positions window at bottom-left corner."""
        screen = QApplication.primaryScreen().geometry()
        margin = 15
        x = margin
        y = screen.height() - self.height() - margin - 40  # Taskbar clearance
        self.move(x, y)

    def init_ui(self):
        self.setWindowTitle("Color Picker")
        self.setWindowIcon(self.app_icon)

        # Ultra compact dimensions
        self.setFixedSize(280, 105)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
                color: #CCCCCC;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QPushButton.format-btn {
                background-color: #252526;
                color: #D4D4D4;
                border: 1px solid #3C3C3C;
                border-radius: 2px;
                text-align: center;
                font-family: 'Consolas', 'Cascadia Code', monospace;
                font-size: 12px;
            }
            QPushButton.format-btn:hover {
                background-color: #2A2D2E;
                border-color: #007ACC;
                color: #FFFFFF;
            }
            QPushButton.format-btn:pressed {
                background-color: #094771;
            }
            QComboBox {
                background-color: #252526;
                color: #D4D4D4;
                border: 1px solid #3C3C3C;
                border-radius: 2px;
                padding: 2px 5px;
                font-size: 11px;
                font-weight: bold;
            }
            QComboBox::drop-down {
                border-left: 1px solid #3C3C3C;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #252526;
                color: #D4D4D4;
                selection-background-color: #094771;
                border: 1px solid #3C3C3C;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        # Top Bar: Clickable Color Swatch Window
        top_bar = QHBoxLayout()
        top_bar.setSpacing(0)

        self.swatch = ClickableFrame(self.start_eyedropper)
        self.swatch.setFixedHeight(30)
        self.swatch.setToolTip("Click here to pick a color")
        top_bar.addWidget(self.swatch, stretch=1)

        layout.addLayout(top_bar)

        # Format Selection Dropdown with Proper Display Names
        self.combo_format = QComboBox()
        self.combo_format.setFixedHeight(24)
        self.combo_format.addItems([
            "HEX", 
            "ARGB Hex", 
            "fromARGB", 
            "fromRGBO", 
            "HSL"
        ])
        self.combo_format.currentIndexChanged.connect(self.on_format_changed)
        layout.addWidget(self.combo_format)

        # Click-to-copy Output Button
        self.btn_copy = QPushButton()
        self.btn_copy.setProperty("class", "format-btn")
        self.btn_copy.setFixedHeight(26)
        self.btn_copy.setToolTip("Click to copy color code")
        self.btn_copy.clicked.connect(lambda: self.copy_to_clipboard(self.btn_copy.text()))
        layout.addWidget(self.btn_copy)

        self.setLayout(layout)
        self.update_color_display()

    def start_eyedropper(self):
        self.overlay = FullscreenOverlay(self)
        self.overlay.show()

    def update_color(self, color):
        self.current_color = color
        self.update_color_display()

    def update_color_display(self):
        r, g, b, _ = self.current_color.getRgb()

        # Update visual swatch style
        self.swatch.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); border-radius: 2px; border: 1px solid #3C3C3C;"
        )

        idx = self.combo_format.currentIndex()
        text_val = ""

        if idx == 0:
            text_val = f"#{r:02X}{g:02X}{b:02X}"
        elif idx == 1:
            text_val = f"Color(0xFF{r:02X}{g:02X}{b:02X})"
        elif idx == 2:
            text_val = f"Color.fromARGB(255, {r}, {g}, {b})"
        elif idx == 3:
            text_val = f"Color.fromRGBO({r}, {g}, {b}, 1.0)"
        elif idx == 4:
            h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
            text_val = f"HSLColor.fromAHSL(1.0, {h*360:.0f}, {s:.2f}, {l:.2f})"

        self.btn_copy.setText(text_val)

    def on_format_changed(self, index):
        self.update_color_display()
        self.save_settings()

    def load_settings(self):
        """Loads last selected dropdown option from settings.json."""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    idx = data.get("selected_format_index", 0)
                    if 0 <= idx < self.combo_format.count():
                        self.combo_format.setCurrentIndex(idx)
            except Exception:
                pass

    def save_settings(self):
        """Saves current dropdown index to settings.json."""
        try:
            data = {"selected_format_index": self.combo_format.currentIndex()}
            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def copy_to_clipboard(self, text):
        pyperclip.copy(text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    icon_path = resource_path("picker.ico")
    icon = QIcon(icon_path)
    app.setWindowIcon(icon)

    picker = FlutterColorPicker(icon)
    picker.show()
    sys.exit(app.exec())