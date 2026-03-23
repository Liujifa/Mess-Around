from __future__ import annotations

import os

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

import styles
from web_novel_downloader import DownloadResult, WebDownloadError, WebNovelDownloader


TRANSLATIONS = {
    "CN": {
        "title": "\u7f51\u9875\u4e0b\u8f7d TXT",
        "url": "\u5c0f\u8bf4\u76ee\u5f55 / \u9605\u8bfb\u9875 URL",
        "name": "\u4e66\u540d\uff08\u53ef\u9009\uff09",
        "browser": "\u5bfc\u5165\u6d4f\u89c8\u5668 Cookie",
        "none": "\u4e0d\u5bfc\u5165",
        "download": "\u4e0b\u8f7d\u5e76\u5165\u5e93",
        "close": "\u5173\u95ed",
        "status_idle": "\u7b49\u5f85\u5f00\u59cb",
        "logs": "下载日志",
        "cancel": "取消下载",
        "hint": "请输入小说目录页或单章页URL。即使输入单章，下载器也会自动尝试追溯全书目录并完整下载全本。",
        "missing_url": "请先输入 URL。",
        "success": "\u4e0b\u8f7d\u5b8c\u6210\uff0c\u5df2\u81ea\u52a8\u51c6\u5907\u5165\u5e93\u3002",
        "failed": "\u4e0b\u8f7d\u5931\u8d25",
        "progress_web": "\u6b63\u5728\u4e0b\u8f7d\u7f51\u9875\u7ae0\u8282",
        "progress_fanqie": "\u6b63\u5728\u4e0b\u8f7d\u756a\u8304\u7ae0\u8282",
        "progress_format": "{label} ({current}/{total})",
    },
    "EN": {
        "title": "Download TXT From Web",
        "url": "Novel Index / Reading URL",
        "name": "Book Title (Optional)",
        "browser": "Import Browser Cookie",
        "none": "Do Not Import",
        "download": "Download And Import",
        "close": "Close",
        "status_idle": "Waiting to start",
        "logs": "Download Log",
        "cancel": "Cancel",
        "hint": "Enter a novel index or single chapter URL. The downloader will intelligently trace back to the catalog and download the entire book.",
        "missing_url": "Please enter a URL first.",
        "success": "Download completed and is ready to import into the library.",
        "failed": "Download Failed",
        "progress_web": "Downloading web chapters",
        "progress_fanqie": "Downloading Fanqie chapters",
        "progress_format": "{label} ({current}/{total})",
    },
}


class DownloadWorker(QObject):
    progress = pyqtSignal(int, int, str, str)
    log = pyqtSignal(str)
    finished = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, url: str, title: str, browser: str, download_dir: str):
        super().__init__()
        self.url = url
        self.title = title
        self.browser = browser
        self.download_dir = download_dir
        self.downloader = None

    def run(self):
        try:
            self.downloader = WebNovelDownloader(
                download_dir=self.download_dir,
                progress_callback=self.progress.emit,
                log_callback=self.log.emit,
            )
            result = self.downloader.download(self.url, self.title, self.browser)
            payload = {
                "title": result.title,
                "file_path": result.file_path,
                "chapter_count": result.chapter_count,
                "source_url": result.source_url,
            }
            self.finished.emit(payload)
        except WebDownloadError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(str(exc))

    def abort(self):
        if self.downloader:
            self.downloader.is_cancelled = True

class WebDownloadDialog(QDialog):
    def __init__(self, language: str = "CN", parent=None):
        super().__init__(parent)
        self.language = language if language in TRANSLATIONS else "CN"
        self.result_data: dict | None = None
        self.thread: QThread | None = None
        self.worker: DownloadWorker | None = None
        self.download_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "novel_downloads")
        self.init_ui()

    def t(self, key: str) -> str:
        return TRANSLATIONS[self.language].get(key, key)

    def init_ui(self):
        self.setWindowTitle(self.t("title"))
        self.setMinimumWidth(620)
        self.setStyleSheet(styles.LIBRARY_QSS)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        hint = QLabel(self.t("hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(10)

        self.url_input = QLineEdit()
        self.title_input = QLineEdit()
        self.browser_combo = QComboBox()
        self.browser_combo.addItem(self.t("none"), "none")
        self.browser_combo.addItem("Edge", "edge")
        self.browser_combo.addItem("Chrome", "chrome")
        self.browser_combo.addItem("Firefox", "firefox")

        form.addRow(self.t("url"), self.url_input)
        form.addRow(self.t("name"), self.title_input)
        form.addRow(self.t("browser"), self.browser_combo)
        layout.addLayout(form)

        self.status_label = QLabel(self.t("status_idle"))
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText(self.t("logs"))
        layout.addWidget(self.log_box)

        button_row = QHBoxLayout()
        self.btn_download = QPushButton(self.t("download"))
        self.btn_download.clicked.connect(self.start_download)
        button_row.addWidget(self.btn_download)

        self.btn_close = QPushButton(self.t("close"))
        self.btn_close.clicked.connect(self.reject)
        button_row.addWidget(self.btn_close)
        layout.addLayout(button_row)

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, self.t("title"), self.t("missing_url"))
            return

        self.result_data = None
        self.log_box.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText(self.t("status_idle"))
        self.btn_download.setEnabled(False)
        self.btn_close.setText(self.t("cancel"))
        self.url_input.setEnabled(False)
        self.title_input.setEnabled(False)
        self.browser_combo.setEnabled(False)

        self.thread = QThread(self)
        self.worker = DownloadWorker(
            url=url,
            title=self.title_input.text().strip(),
            browser=self.browser_combo.currentData(),
            download_dir=self.download_dir,
        )
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.log.connect(self.append_log)
        self.worker.finished.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def on_progress(self, current: int, total: int, message: str, chapter_title: str):
        percentage = int((current / total) * 100) if total else 0
        self.progress_bar.setValue(max(0, min(100, percentage)))
        self.status_label.setText(self.format_progress_status(message, current, total))

    def format_progress_status(self, message: str, current: int, total: int) -> str:
        label = self.t(message) if message in TRANSLATIONS[self.language] else message
        if total > 0:
            return self.t("progress_format").format(label=label, current=current, total=total)
        return label

    def append_log(self, message: str):
        self.log_box.appendPlainText(message)

    def on_finished(self, payload: dict):
        self.result_data = payload
        self.progress_bar.setValue(100)
        self.status_label.setText(self.t("success"))
        self.append_log(payload["file_path"])
        self.btn_close.setText(self.t("close"))
        QMessageBox.information(self, self.t("title"), self.t("success"))
        self.accept()

    def on_failed(self, message: str):
        self.progress_bar.setValue(0)
        self.status_label.setText(self.t("failed"))
        self.append_log(message)
        QMessageBox.critical(self, self.t("failed"), message)
        self.btn_download.setEnabled(True)
        self.btn_close.setText(self.t("close"))
        self.btn_close.setEnabled(True)
        self.url_input.setEnabled(True)
        self.title_input.setEnabled(True)
        self.browser_combo.setEnabled(True)

    def reject(self):
        if self.thread and self.thread.isRunning():
            if self.worker:
                self.worker.abort()
            self.btn_close.setEnabled(False)
            self.append_log("Canceling download...")
            return
        super().reject()
