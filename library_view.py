# library_view.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QListWidget, QFileDialog, QLabel, QGroupBox, 
                             QSlider, QColorDialog, QCheckBox, QTextEdit)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPalette

TRANSLATIONS = {
    "CN": {
        "lib_title": "小說書庫",
        "add_novel": "添加小說 (TXT)",
        "start_reading": "開始閱讀",
        "settings": "設置",
        "font_size": "字體大小:",
        "win_opacity": "窗口不透明度:",
        "text_opacity": "文字不透明度:",
        "stealth_mode": "隱身閱讀模式",
        "change_color": "更換字體顏色",
        "preview_title": "樣式預覽 (Preview)",
        "lang_toggle": "切換語言/English",
        "preview_text": "這是一個預覽文本，用於展示你調整後的字體大小、顏色和透明度效果。\n\nThis is a preview text for testing your style settings.",
        "chapter_select": "選擇章節:"
    },
    "EN": {
        "lib_title": "Novel Library",
        "add_novel": "Add Novel (TXT)",
        "start_reading": "Start Reading",
        "settings": "Settings",
        "font_size": "Font Size:",
        "win_opacity": "Win Opacity:",
        "text_opacity": "Text Opacity:",
        "stealth_mode": "Stealth Mode",
        "change_color": "Change Color",
        "preview_title": "Style Preview",
        "lang_toggle": "Language: 中文",
        "preview_text": "This is a preview text for testing your style settings.\n\n這是一段用於測試樣式設置的預覽文本。",
        "chapter_select": "Select Chapter:"
    }
}

class LibraryView(QWidget):
    novel_selected = pyqtSignal(dict, int) # dict: novel_data, int: start_pos
    settings_changed = pyqtSignal()

    def __init__(self, manager, logic):
        super().__init__()
        self.manager = manager
        self.logic = logic
        self.settings = self.manager.get_settings()
        self.current_chapters = []
        self.init_ui()

    def init_ui(self):
        self.main_layout = QHBoxLayout(self)
        
        # Left side: Library List
        self.left_layout = QVBoxLayout()
        self.lib_group = QGroupBox(self.t("lib_title"))
        self.lib_layout = QVBoxLayout(self.lib_group)
        
        self.novel_list = QListWidget()
        self.lib_layout.addWidget(self.novel_list)
        
        self.btn_layout = QHBoxLayout()
        self.btn_add = QPushButton(self.t("add_novel"))
        self.btn_add.clicked.connect(self.on_add_novel)
        self.btn_layout.addWidget(self.btn_add)
        
        self.btn_read = QPushButton(self.t("start_reading"))
        self.btn_read.clicked.connect(self.on_read_selected)
        self.btn_layout.addWidget(self.btn_read)
        
        self.lib_layout.addLayout(self.btn_layout)
        
        self.left_layout.addWidget(self.lib_group)
        self.main_layout.addLayout(self.left_layout, 1)

        # Right side: Settings, Chapter & Preview
        self.right_layout = QVBoxLayout()
        
        # Chapter Selection
        self.chapter_group = QGroupBox(self.t("chapter_select"))
        self.chapter_layout = QVBoxLayout(self.chapter_group)
        from PyQt6.QtWidgets import QComboBox
        self.chapter_combo = QComboBox()
        self.chapter_layout.addWidget(self.chapter_combo)
        self.right_layout.addWidget(self.chapter_group)
        
        self.settings_group = QGroupBox(self.t("settings"))
        self.settings_layout = QVBoxLayout(self.settings_group)
        
        # Font Size

        self.fs_label = QLabel(self.t("font_size"))
        self.settings_layout.addWidget(self.fs_label)
        self.fs_slider = QSlider(Qt.Orientation.Horizontal)
        self.fs_slider.setRange(10, 50)
        self.fs_slider.setValue(self.settings["font_size"])
        self.fs_slider.valueChanged.connect(self.update_settings)
        self.settings_layout.addWidget(self.fs_slider)
        
        # Text Opacity
        self.to_label = QLabel(self.t("text_opacity"))
        self.settings_layout.addWidget(self.to_label)
        self.to_slider = QSlider(Qt.Orientation.Horizontal)
        self.to_slider.setRange(10, 100)
        self.to_slider.setValue(int(self.settings["text_opacity"] * 100))
        self.to_slider.valueChanged.connect(self.update_settings)
        self.settings_layout.addWidget(self.to_slider)

        # Window Opacity
        self.wo_label = QLabel(self.t("win_opacity"))
        self.settings_layout.addWidget(self.wo_label)
        self.wo_slider = QSlider(Qt.Orientation.Horizontal)
        self.wo_slider.setRange(10, 100)
        self.wo_slider.setValue(int(self.settings["window_opacity"] * 100))
        self.wo_slider.valueChanged.connect(self.update_settings)
        self.settings_layout.addWidget(self.wo_slider)

        self.btn_color = QPushButton(self.t("change_color"))
        self.btn_color.clicked.connect(self.on_change_color)
        self.settings_layout.addWidget(self.btn_color)

        self.rm_check = QCheckBox(self.t("stealth_mode"))
        self.rm_check.setChecked(self.settings.get("reading_mode", False))
        self.rm_check.stateChanged.connect(self.update_settings)
        self.settings_layout.addWidget(self.rm_check)
        
        # Language Toggle
        self.btn_lang = QPushButton(self.t("lang_toggle"))
        self.btn_lang.clicked.connect(self.toggle_language)
        self.settings_layout.addWidget(self.btn_lang)
        
        self.right_layout.addWidget(self.settings_group)
        
        # Preview Window
        self.preview_group = QGroupBox(self.t("preview_title"))
        self.preview_layout = QVBoxLayout(self.preview_group)
        self.preview_box = QTextEdit()
        self.preview_box.setReadOnly(True)
        self.preview_box.setPlainText(self.t("preview_text"))
        self.preview_layout.addWidget(self.preview_box)
        self.right_layout.addWidget(self.preview_group)
        
        self.main_layout.addLayout(self.right_layout, 1)
        
        self.refresh_library()
        self.apply_preview_settings()

    def t(self, key):
        lang = self.settings.get("language", "CN")
        return TRANSLATIONS[lang].get(key, key)

    def toggle_language(self):
        new_lang = "EN" if self.settings.get("language", "CN") == "CN" else "CN"
        self.settings["language"] = new_lang
        self.manager.update_settings(self.settings)
        self.retranslate_ui()
        self.settings_changed.emit()

    def retranslate_ui(self):
        self.lib_group.setTitle(self.t("lib_title"))
        self.btn_add.setText(self.t("add_novel"))
        self.btn_read.setText(self.t("start_reading"))
        self.chapter_group.setTitle(self.t("chapter_select"))
        self.settings_group.setTitle(self.t("settings"))
        self.fs_label.setText(self.t("font_size"))
        self.to_label.setText(self.t("text_opacity"))
        self.wo_label.setText(self.t("win_opacity"))
        self.btn_color.setText(self.t("change_color"))
        self.rm_check.setText(self.t("stealth_mode"))
        self.btn_lang.setText(self.t("lang_toggle"))
        self.preview_group.setTitle(self.t("preview_title"))
        self.preview_box.setPlainText(self.t("preview_text"))

    def refresh_library(self):
        self.novel_list.clear()
        # Re-connect selection change to auto-update chapters
        try:
            self.novel_list.itemSelectionChanged.disconnect(self.on_novel_selection_changed)
        except:
            pass
        for item in self.manager.data["library"]:
            self.novel_list.addItem(item["title"])
        self.novel_list.itemSelectionChanged.connect(self.on_novel_selection_changed)

    def on_novel_selection_changed(self):
        selected = self.novel_list.selectedItems()
        if not selected:
            return
        title = selected[0].text()
        for n in self.manager.data["library"]:
            if n["title"] == title:
                # Load chapters to populate combo box
                _, chapters = self.logic.load_txt(n["path"])
                self.current_chapters = chapters
                self.chapter_combo.clear()
                
                # Find current chapter based on last_pos
                last_pos = n.get("last_pos", 0)
                current_idx = 0
                for i, ch in enumerate(chapters):
                    self.chapter_combo.addItem(ch["title"])
                    if ch["pos"] <= last_pos:
                        current_idx = i
                
                if chapters:
                    self.chapter_combo.setCurrentIndex(current_idx)
                break

    def on_add_novel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open TXT", "", "TXT Files (*.txt)")
        if path:
            title = path.split('/')[-1].replace('.txt', '')
            self.manager.add_novel(title, path)
            self.refresh_library()

    def on_read_selected(self):
        selected = self.novel_list.selectedItems()
        if selected:
            title = selected[0].text()
            for n in self.manager.data["library"]:
                if n["title"] == title:
                    start_pos = n.get("last_pos", 0)
                    # Override start_pos if chapter selected
                    if self.current_chapters and self.chapter_combo.currentIndex() >= 0:
                        start_pos = self.current_chapters[self.chapter_combo.currentIndex()]["pos"]
                    
                    self.novel_selected.emit(n, start_pos)
                    break


    def on_change_color(self):
        color = QColorDialog.getColor(QColor(self.settings["font_color"]), self)
        if color.isValid():
            self.settings["font_color"] = color.name()
            self.update_settings()

    def update_settings(self):
        self.settings["font_size"] = self.fs_slider.value()
        self.settings["text_opacity"] = self.to_slider.value() / 100.0
        self.settings["window_opacity"] = self.wo_slider.value() / 100.0
        self.settings["reading_mode"] = self.rm_check.isChecked()
        self.manager.update_settings(self.settings)
        self.apply_preview_settings()
        self.settings_changed.emit()

    def apply_preview_settings(self):
        s = self.settings
        font = QFont()
        font.setPointSize(s["font_size"])
        self.preview_box.setFont(font)
        
        color = QColor(s["font_color"])
        r, g, b = color.red(), color.green(), color.blue()
        a = s["text_opacity"]
        
        self.preview_box.setStyleSheet(f"""
            QTextEdit {{
                color: rgba({r}, {g}, {b}, {a});
                background-color: rgba(30, 30, 30, {s['window_opacity']});
                border: 1px solid #4CAF50;
            }}
        """)
