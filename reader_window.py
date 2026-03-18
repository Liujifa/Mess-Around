# reader_window.py
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTextEdit, QLabel, QPushButton, QSlider, QColorDialog, 
                             QListWidget, QDockWidget, QFrame, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QPoint, QTimer
from PyQt6.QtGui import QColor, QFont, QPalette, QAction, QCursor
import styles

TRANSLATIONS = {
    "CN": {
        "toc": "目錄 ☰",
        "font_plus": "A+",
        "font_minus": "A-",
        "mode_stealth": "模式 ✨",
        "mode_normal": "模式 🌙",
        "close": "✕"
    },
    "EN": {
        "toc": "TOC ☰",
        "font_plus": "A+",
        "font_minus": "A-",
        "mode_stealth": "Stealth ✨",
        "mode_normal": "Normal 🌙",
        "close": "✕"
    }
}

class CustomReader(QTextEdit):
    pass


class ReaderWindow(QMainWindow):
    def __init__(self, manager, logic):
        super().__init__()
        self.manager = manager
        self.logic = logic
        self.settings = self.manager.get_settings()
        self.chapters = []
        
        self.setWindowTitle("MoYu Reader")
        self.setMinimumSize(400, 600)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # VERY IMPORTANT: Keep window tracking mouse
        self.setMouseTracking(True)
        
        self.init_ui()
        self.apply_settings()
        
        self._dragging = False
        self._drag_pos = QPoint()
        
        # Hover tracking using QTimer for robust true transparency
        self.hover_timer = QTimer(self)
        self.hover_timer.timeout.connect(self.check_hover_state)
        self.hover_timer.start(100)
        self._is_hovering = True

    def init_ui(self):
        self.central_widget = QWidget()
        self.central_widget.setObjectName("CentralWidget")
        self.central_widget.setMouseTracking(True)
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.header_frame = QFrame()
        self.header_frame.setObjectName("Header")
        self.header_frame.setMouseTracking(True)
        self.header_layout = QHBoxLayout(self.header_frame)
        self.header_layout.setContentsMargins(10, 5, 10, 5)

        self.btn_toc = QPushButton()
        self.btn_toc.setObjectName("TOCButton")
        self.toc_menu = QMenu(self)
        self.btn_toc.setMenu(self.toc_menu)
        self.header_layout.addWidget(self.btn_toc)

        self.btn_font_plus = QPushButton()
        self.btn_font_plus.clicked.connect(lambda: self.change_font_size(1))
        self.header_layout.addWidget(self.btn_font_plus)

        self.btn_font_minus = QPushButton()
        self.btn_font_minus.clicked.connect(lambda: self.change_font_size(-1))
        self.header_layout.addWidget(self.btn_font_minus)

        self.header_layout.addStretch()

        self.btn_mode = QPushButton()
        self.btn_mode.clicked.connect(self.toggle_stealth_mode)
        self.header_layout.addWidget(self.btn_mode)

        self.btn_close = QPushButton()
        self.btn_close.setFixedSize(25, 25)
        self.btn_close.clicked.connect(self.hide)
        self.header_layout.addWidget(self.btn_close)

        self.layout.addWidget(self.header_frame)

        self.reader_area = CustomReader()
        self.reader_area.setObjectName("ReaderArea")
        self.reader_area.setReadOnly(True)
        self.reader_area.setMouseTracking(True)
        self.reader_area.setFrameStyle(0) # Ensure no border/frame is drawn
        self.reader_area.setStyleSheet("background-color: transparent;")
        self.layout.addWidget(self.reader_area)

        self.setStyleSheet(styles.QSS)
        self.retranslate_ui()

    def t(self, key):
        lang = self.settings.get("language", "CN")
        return TRANSLATIONS[lang].get(key, key)

    def retranslate_ui(self):
        self.btn_toc.setText(self.t("toc"))
        self.btn_font_plus.setText(self.t("font_plus"))
        self.btn_font_minus.setText(self.t("font_minus"))
        self.btn_close.setText(self.t("close"))
        if self.settings.get("reading_mode"):
            self.btn_mode.setText(self.t("mode_stealth"))
        else:
            self.btn_mode.setText(self.t("mode_normal"))

    def apply_settings(self):
        s = self.settings
        self.retranslate_ui()
        
        font = QFont()
        font.setPointSize(s["font_size"])
        self.reader_area.setFont(font)
        
        if s.get("reading_mode"):
            self.header_frame.hide()
        else:
            self.header_frame.show()
            
        # Apply color layout and transparency via our custom function
        self.update_text_visibility(True)

    def update_text_visibility(self, visible):
        s = self.settings
        color = QColor(s["font_color"])
        r, g, b = color.red(), color.green(), color.blue()
        
        if s.get("reading_mode"):
            self.reader_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            if not visible:
                # Hover out: text is totally invisible
                a = 0.0
            else:
                # Hover in: use setting's text opacity
                a = s.get("text_opacity", 1.0)
                
            self.setWindowOpacity(s.get("window_opacity", 1.0))
            # 1% opacity background to catch mouse scroll events, virtually invisible
            self.central_widget.setStyleSheet("QWidget#CentralWidget { background-color: rgba(0, 0, 0, 0.01); }")
        else:
            # Normal mode
            self.reader_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            a = s.get("text_opacity", 1.0)
            self.setWindowOpacity(s.get("window_opacity", 1.0))
            self.central_widget.setStyleSheet("")
            self.setStyleSheet(styles.QSS)
            
        # Update text color using style sheet for reliability
        self.reader_area.setStyleSheet(f"#ReaderArea {{ color: rgba({r}, {g}, {b}, {a}); background-color: transparent; border: none; }}")

    def toggle_stealth_mode(self):
        self.settings["reading_mode"] = not self.settings["reading_mode"]
        self.manager.update_settings(self.settings)
        self.apply_settings()

    def change_font_size(self, delta):
        self.settings["font_size"] = max(10, min(50, self.settings["font_size"] + delta))
        self.manager.update_settings(self.settings)
        self.apply_settings()

    def load_novel(self, novel_data):
        self.current_novel = novel_data
        content, chapters = self.logic.load_txt(novel_data["path"])
        self.chapters = chapters
        self.reader_area.setPlainText(content)
        
        self.toc_menu.clear()
        for idx, ch in enumerate(chapters):
            action = QAction(ch["title"], self)
            action.triggered.connect(lambda checked=False, i=idx: self.jump_to_chapter(i))
            self.toc_menu.addAction(action)
            
        cursor = self.reader_area.textCursor()
        # Safeguard the position
        pos = min(novel_data.get("last_pos", 0), len(content))
        cursor.setPosition(pos)
        self.reader_area.setTextCursor(cursor)
        
        # Use QTimer to ensure the text layout is finished before scrolling
        QTimer.singleShot(100, self.reader_area.ensureCursorVisible)

    def jump_to_chapter(self, index):
        if 0 <= index < len(self.chapters):
            pos = self.chapters[index]["pos"]
            cursor = self.reader_area.textCursor()
            cursor.setPosition(pos)
            self.reader_area.setTextCursor(cursor)
            self.reader_area.ensureCursorVisible()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._dragging:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def check_hover_state(self):
        if not self.settings.get("reading_mode"):
            return
            
        cursor_pos = self.mapFromGlobal(QCursor.pos())
        is_hovering = self.rect().contains(cursor_pos)
        
        if is_hovering != self._is_hovering:
            self._is_hovering = is_hovering
            self.update_text_visibility(is_hovering)

    def hideEvent(self, event):
        if hasattr(self, 'current_novel'):
            cursor = self.reader_area.textCursor()
            self.manager.update_pos(self.current_novel["path"], cursor.position())
        super().hideEvent(event)
