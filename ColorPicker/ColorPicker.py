import sys
import colorsys
import pyperclip
from PIL import ImageGrab

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QCursor, QGuiApplication, QPixmap, QPainter, QImage, QIcon
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGridLayout
)

def create_vscode_style_icon():
    """Generates a VS Code style icon programmatically for the title bar & taskbar."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setBrush(QColor("#1E1E1E"))
    painter.setPen(QColor("#0E639C"))
    painter.drawRoundedRect(0, 0, size, size, 12, 12)

    painter.setBrush(QColor("#007ACC"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(12, 12, 40, 40)

    painter.setBrush(QColor("#FFFFFF"))
    painter.drawEllipse(28, 28, 8, 8)

    painter.end()
    return QIcon(pixmap)


class FullscreenOverlay(QWidget):
    """Takes a snapshot of the screen to prevent blackouts and captures color on click."""
    def __init__(self, main_picker):
        super().__init__()
        self.main_picker = main_picker

        screen_img = ImageGrab.grab(all_screens=True)
        img_data = screen_img.tobytes("raw", "RGB")
        qimage = QImage(img_data, screen_img.width, screen_img.height, screen_img.width * 3, QImage.Format.Format_RGB888)
        self.pixmap = QPixmap.fromImage(qimage)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        geo = QApplication.primaryScreen().virtualGeometry()
        self.setGeometry(geo)

        self.setMouseTracking(True)
        QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.CrossCursor))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)

    def mouseMoveEvent(self, event):
        pos = event.pos()
        x, y = pos.x(), pos.y()
        if 0 <= x < self.pixmap.width() and 0 <= y < self.pixmap.height():
            qcolor = self.pixmap.toImage().pixelColor(x, y)
            self.main_picker.update_color(qcolor)

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
    def __init__(self):
        super().__init__()
        self.current_color = QColor("#3B82F6")
        self.init_ui()
        self.position_bottom_left()

    def position_bottom_left(self):
        """Positions window at bottom-left corner."""
        screen = QApplication.primaryScreen().geometry()
        margin = 15
        x = margin
        y = screen.height() - self.height() - margin - 40  # Taskbar clearance
        self.move(x, y)

    def init_ui(self):
        self.setWindowTitle("Flutter Color Picker")
        self.setWindowIcon(create_vscode_style_icon())

        # Super compact window dimensions (350x230 px)
        self.setFixedSize(330, 200)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
                color: #CCCCCC;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QLabel {
                font-size: 11px;
            }
            QPushButton.format-btn {
                background-color: #252526;
                color: #D4D4D4;
                border: 1px solid #3C3C3C;
                border-radius: 2px;
                text-align: left;
                padding-left: 6px;
                font-family: 'Consolas', 'Cascadia Code', monospace;
                font-size: 11px;
            }
            QPushButton.format-btn:hover {
                background-color: #2A2D2E;
                border-color: #007ACC;
                color: #FFFFFF;
            }
            QPushButton.format-btn:pressed {
                background-color: #094771;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        # Top Bar: Compact Pick Button + Swatch
        top_bar = QHBoxLayout()
        top_bar.setSpacing(6)

        self.btn_pick = QPushButton("🔍 Pick Color")
        self.btn_pick.setFixedHeight(28)
        self.btn_pick.setFixedWidth(95)
        self.btn_pick.setStyleSheet("""
            QPushButton {
                background-color: #0E639C;
                color: #FFFFFF;
                border: none;
                border-radius: 2px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
            QPushButton:pressed {
                background-color: #094771;
            }
        """)
        self.btn_pick.clicked.connect(self.start_eyedropper)
        top_bar.addWidget(self.btn_pick)

        # Color Preview Swatch
        self.swatch = QFrame()
        self.swatch.setFixedHeight(28)
        self.swatch.setStyleSheet("border-radius: 2px; border: 1px solid #3C3C3C;")
        top_bar.addWidget(self.swatch, stretch=1)

        layout.addLayout(top_bar)

        # Format Grid Layout (Reduced spacing & height)
        grid = QGridLayout()
        grid.setSpacing(4)

        self.btn_hex = self.create_format_button(grid, "HEX:", 0)
        self.btn_argb_hex = self.create_format_button(grid, "0xFF:", 1)
        self.btn_from_argb = self.create_format_button(grid, "fromARGB:", 2)
        self.btn_rgb = self.create_format_button(grid, "fromRGBO:", 3)
        self.btn_hsl = self.create_format_button(grid, "HSL:", 4)

        layout.addLayout(grid)

        self.setLayout(layout)
        self.update_color_display()

    def create_format_button(self, grid, label_text, row):
        label = QLabel(label_text)
        label.setStyleSheet("font-weight: bold; color: #569CD6; font-size: 11px;")
        grid.addWidget(label, row, 0)

        btn = QPushButton()
        btn.setProperty("class", "format-btn")
        btn.setFixedHeight(24)
        grid.addWidget(btn, row, 1)

        btn.clicked.connect(lambda: self.copy_to_clipboard(btn.text()))
        return btn

    def start_eyedropper(self):
        self.overlay = FullscreenOverlay(self)
        self.overlay.show()

    def update_color(self, color):
        self.current_color = color
        self.update_color_display()

    def update_color_display(self):
        r, g, b, _ = self.current_color.getRgb()

        self.swatch.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); border-radius: 2px; border: 1px solid #3C3C3C;"
        )

        hex_val = f"#{r:02X}{g:02X}{b:02X}"
        flutter_argb_hex = f"Color(0xFF{r:02X}{g:02X}{b:02X})"
        flutter_from_argb = f"Color.fromARGB(255, {r}, {g}, {b})"
        flutter_rgb_o = f"Color.fromRGBO({r}, {g}, {b}, 1.0)"

        h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
        flutter_hsl = f"HSLColor.fromAHSL(1.0, {h*360:.0f}, {s:.2f}, {l:.2f})"

        self.btn_hex.setText(hex_val)
        self.btn_argb_hex.setText(flutter_argb_hex)
        self.btn_from_argb.setText(flutter_from_argb)
        self.btn_rgb.setText(flutter_rgb_o)
        self.btn_hsl.setText(flutter_hsl)

    def copy_to_clipboard(self, text):
        pyperclip.copy(text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(create_vscode_style_icon())
    
    picker = FlutterColorPicker()
    picker.show()
    sys.exit(app.exec()) 