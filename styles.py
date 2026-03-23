READER_QSS = """
#CentralWidget {
    background-color: rgba(15, 20, 25, 0.88);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
}

QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 8px;
    margin: 12px 2px 12px 0;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.15);
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 0.25);
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}

#Header {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(20, 26, 32, 0.95),
        stop:1 rgba(30, 38, 45, 0.95));
    border-top-left-radius: 16px;
    border-top-right-radius: 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    min-height: 50px;
}

#ReaderArea {
    background-color: transparent;
    border: none;
    padding: 30px 40px 40px 40px;
    font-family: system-ui, -apple-system, 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
    line-height: 1.8;
    selection-background-color: rgba(94, 151, 246, 0.35);
    selection-color: #ffffff;
}

QPushButton {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.85);
    padding: 7px 14px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: #ffffff;
}

QPushButton:pressed {
    background-color: rgba(0, 0, 0, 0.3);
}

QPushButton::menu-indicator {
    image: none;
}

#TOCButton {
    text-align: left;
    min-width: 120px;
}
"""


LIBRARY_QSS = """
QWidget {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: system-ui, -apple-system, 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
    font-size: 13px;
}

QGroupBox {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    margin-top: 14px;
    padding: 16px 14px 14px 14px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px;
    color: #8b949e;
}

QListWidget,
QComboBox,
QTextEdit {
    background-color: #010409;
    alternate-background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    color: #e6edf3;
    padding: 8px 10px;
}

QListWidget::item {
    padding: 10px 12px;
    border-radius: 6px;
    margin: 2px 4px;
}

QListWidget::item:selected {
    background-color: rgba(56, 139, 253, 0.15);
    border: 1px solid rgba(56, 139, 253, 0.4);
    color: #ffffff;
}

QListWidget::item:hover:!selected {
    background-color: rgba(255, 255, 255, 0.05);
}

QComboBox {
    min-height: 20px;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #161b22;
    border: 1px solid #30363d;
    selection-background-color: rgba(56, 139, 253, 0.15);
    color: #e6edf3;
    border-radius: 6px;
}

QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #238636,
        stop:1 #2ea043);
    border: 1px solid rgba(240, 246, 252, 0.1);
    color: #ffffff;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #2ea043,
        stop:1 #3fb950);
}

QPushButton:pressed {
    background: #238636;
}

QLabel {
    color: #8b949e;
}

QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #30363d;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #58a6ff;
    border: 2px solid #0d1117;
    width: 14px;
    margin: -6px 0;
    border-radius: 9px;
}

QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #30363d;
    background: #010409;
}

QCheckBox::indicator:checked {
    background: #2ea043;
    border: 1px solid rgba(240, 246, 252, 0.1);
}
"""

QSS = READER_QSS
