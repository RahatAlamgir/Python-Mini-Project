from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QGuiApplication, QPainter, QPen, QColor
from PySide6.QtWidgets import QWidget, QLabel


class ScreenSnipper(QWidget):
    """Overlay window for dragging and capturing a high-resolution rectangular screen area."""
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.is_selecting = False

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.CrossCursor)

        primary_screen = QGuiApplication.primaryScreen()
        self.dpr = primary_screen.devicePixelRatio() if primary_screen else 1.0

        screen_rect = QRect()
        for screen in QGuiApplication.screens():
            screen_rect = screen_rect.united(screen.geometry())
        self.setGeometry(screen_rect)

        self.full_screen_pixmap = primary_screen.grabWindow(0, screen_rect.x(), screen_rect.y(), screen_rect.width(), screen_rect.height())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.is_selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False
            rect = QRect(self.start_point, self.end_point).normalized()
            self.hide()

            if rect.width() > 10 and rect.height() > 10:
                scaled_rect = QRect(
                    int(rect.x() * self.dpr),
                    int(rect.y() * self.dpr),
                    int(rect.width() * self.dpr),
                    int(rect.height() * self.dpr)
                )
                cropped = self.full_screen_pixmap.copy(scaled_rect)
                self.callback(cropped)
            else:
                self.callback(None)
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
            self.callback(None)
            self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self.is_selecting:
            rect = QRect(self.start_point, self.end_point).normalized()
            scaled_rect = QRect(
                int(rect.x() * self.dpr),
                int(rect.y() * self.dpr),
                int(rect.width() * self.dpr),
                int(rect.height() * self.dpr)
            )
            painter.drawPixmap(rect, self.full_screen_pixmap, scaled_rect)
            
            pen = QPen(QColor(59, 130, 246), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(rect)


class ImageDisplayWidget(QLabel):
    """Custom label that draws crosshair mark and configurable grid overlays."""
    GRID_COLORS = {
        "white": QColor(255, 255, 255, 180),
        "black": QColor(0, 0, 0, 180),
        "red": QColor(239, 68, 68, 200),
        "blue": QColor(59, 130, 246, 200),
        "yellow": QColor(234, 179, 8, 200),
        "cyan": QColor(6, 182, 212, 200)
    }

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.show_mark = True
        self.mark_color = QColor(239, 68, 68)

        # Grid settings
        self.show_grid = False
        self.grid_cols = 3
        self.grid_rows = 3
        self.grid_color_key = "white"

        self.apply_empty_style(True)

    def apply_empty_style(self, is_empty):
        if is_empty:
            self.setStyleSheet("""
                QLabel {
                    background-color: #121214;
                    border: 2px dashed #3F3F46;
                    border-radius: 8px;
                    color: #A1A1AA;
                    font-size: 13px;
                    font-weight: 500;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    border: none;
                }
            """)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Draw Grid Overlay
        if self.show_grid and self.grid_cols > 0 and self.grid_rows > 0:
            color = self.GRID_COLORS.get(self.grid_color_key, self.GRID_COLORS["white"])
            grid_pen = QPen(color, 1, Qt.DashLine)
            painter.setPen(grid_pen)

            col_step = w / self.grid_cols
            for col in range(1, self.grid_cols):
                x = int(col * col_step)
                painter.drawLine(x, 0, x, h)

            row_step = h / self.grid_rows
            for row in range(1, self.grid_rows):
                y = int(row * row_step)
                painter.drawLine(0, y, w, y)

        # Draw Center Crosshair Mark
        if self.show_mark:
            center = self.rect().center()
            size = 12
            
            pen_outer = QPen(QColor(0, 0, 0, 200), 3.5)
            painter.setPen(pen_outer)
            painter.drawLine(center.x() - size, center.y(), center.x() + size, center.y())
            painter.drawLine(center.x(), center.y() - size, center.x(), center.y() + size)
            
            pen_inner = QPen(self.mark_color, 2)
            painter.setPen(pen_inner)
            painter.drawLine(center.x() - size, center.y(), center.x() + size, center.y())
            painter.drawLine(center.x(), center.y() - size, center.x(), center.y() + size)