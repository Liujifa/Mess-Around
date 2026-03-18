# styles.py

QSS = """
QMainWindow {
    background-color: #1e1e1e;
}

QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 8px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background: rgba(120, 120, 120, 0.5);
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background: none;
}

#Header {
    background-color: #323233;
    border-bottom: 2px solid #4CAF50;
    min-height: 40px;
}

#ReaderArea {
    background-color: transparent;
    border: none;
    padding: 30px;
    color: #e0e0e0;
    font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
    line-height: 1.5;
}

QPushButton {
    background-color: #3e3e3e;
    border: 1px solid #505050;
    color: #ffffff;
    padding: 5px 10px;
    border-radius: 4px;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #4CAF50;
    border: 1px solid #707070;
}

QPushButton::menu-indicator {
    image: none;
}

#TOCButton {
    text-align: left;
    min-width: 100px;
}
"""
