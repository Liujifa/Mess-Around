# main.py
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow, QMenu, QMessageBox, QSystemTrayIcon

from library_manager import LibraryManager
from library_view import LibraryView
from reader_logic import ReaderLogic
from reader_window import ReaderWindow


class MoYuApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.manager = LibraryManager()
        self.logic = ReaderLogic()

        self.reader_win = ReaderWindow(self.manager, self.logic)
        self.library_win = LibraryView(self.manager, self.logic)

        self.main_win = QMainWindow()
        self.main_win.setCentralWidget(self.library_win)
        self.main_win.setWindowTitle("MoYu Library")
        self.main_win.resize(460, 560)

        self.setup_tray()
        self.setup_connections()
        self.show_first_run_message()

        self.tray_icon.showMessage(
            "MoYu Reader",
            "Running in background",
            QSystemTrayIcon.MessageIcon.Information,
        )

    def show_first_run_message(self):
        settings = self.manager.get_settings()
        if not settings.get("first_run", True):
            return

        message = QMessageBox(self.main_win)
        message.setIcon(QMessageBox.Icon.Information)
        message.setWindowTitle("\u6b22\u8fce / Welcome")
        message.setText(
            "MoYu \u652f\u6301\u672c\u5730 TXT \u9605\u8bfb\uff0c"
            "\u4e5f\u652f\u6301\u4ece\u7f51\u9875\u4e0b\u8f7d\u5c0f\u8bf4\u5e76\u81ea\u52a8\u5165\u5e93\u3002"
        )
        message.exec()

        settings["first_run"] = False
        self.manager.update_settings(settings)

    def setup_connections(self):
        self.library_win.novel_selected.connect(self.open_novel)
        self.library_win.settings_changed.connect(self.reader_win.apply_settings)
        self.reader_win.progress_changed.connect(self.library_win.sync_progress)

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self.app)

        icon = QIcon.fromTheme("document-open")
        if icon.isNull():
            from PyQt6.QtGui import QColor, QPainter, QPixmap

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
        self.tray_icon.activated.connect(self.on_tray_activated)

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.main_win.show()

    def open_novel(self, novel_data, start_pos=0):
        novel_data["_restore_saved_scroll"] = start_pos == novel_data.get("last_pos", 0)
        novel_data["last_pos"] = start_pos
        self.reader_win.load_novel(novel_data)
        self.reader_win.show()
        self.main_win.hide()

    def quit_app(self):
        self.reader_win.persist_progress()
        self.app.quit()

    def run(self):
        sys.exit(self.app.exec())


if __name__ == "__main__":
    app = MoYuApp()
    app.run()
