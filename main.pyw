# main.py
import sys
import os
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from library_manager import LibraryManager
from reader_logic import ReaderLogic
from reader_window import ReaderWindow
from library_view import LibraryView

class MoYuApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        self.manager = LibraryManager()
        self.logic = ReaderLogic()
        
        # Initialize Windows
        self.reader_win = ReaderWindow(self.manager, self.logic)
        self.library_win = LibraryView(self.manager)
        
        # Main Window (Library container)
        from PyQt6.QtWidgets import QMainWindow
        self.main_win = QMainWindow()
        self.main_win.setCentralWidget(self.library_win)
        self.main_win.setWindowTitle("MoYu Library")
        self.main_win.resize(400, 500)
        
        self.setup_tray()
        self.setup_connections()
        
        # Start hidden or show library? User said "Startup hidden in tray"
        # self.main_win.show() 
        self.tray_icon.showMessage("MoYu Reader", "Running in background", QSystemTrayIcon.MessageIcon.Information)

    def setup_connections(self):
        self.library_win.novel_selected.connect(self.open_novel)
        self.library_win.settings_changed.connect(self.reader_win.apply_settings)

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self.app)
        
        # Try to find a suitable icon
        icon = QIcon.fromTheme("document-open")
        if icon.isNull():
            # Create a simple colored pixmap if no icon found
            from PyQt6.QtGui import QPixmap, QPainter, QColor
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(QColor("#4CAF50"))
            painter.drawEllipse(4, 4, 24, 24)
            painter.end()
            icon = QIcon(pixmap)
            
        self.tray_icon.setIcon(icon)
        
        menu = QMenu()
        show_lib_action = QAction("Library", self.app)
        show_lib_action.triggered.connect(self.main_win.show)
        
        show_reader_action = QAction("Reader", self.app)
        show_reader_action.triggered.connect(self.reader_win.show)
        
        quit_action = QAction("Quit", self.app)
        quit_action.triggered.connect(self.quit_app)
        
        menu.addAction(show_lib_action)
        menu.addAction(show_reader_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()
        
        # Double click to show library
        self.tray_icon.activated.connect(self.on_tray_activated)

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.main_win.show()

    def open_novel(self, novel_data):
        self.reader_win.load_novel(novel_data)
        self.reader_win.show()
        self.main_win.hide()

    def quit_app(self):
        # Save progress if reading
        if hasattr(self.reader_win, 'current_novel'):
            cursor = self.reader_win.reader_area.textCursor()
            self.manager.update_pos(self.reader_win.current_novel["path"], cursor.position())
        
        self.app.quit()

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = MoYuApp()
    app.run()
