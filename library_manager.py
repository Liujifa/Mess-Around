# library_manager.py
import json
import os

class LibraryManager:
    def __init__(self, data_file='library.json'):
        self.data_file = data_file
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    settings = data.setdefault("settings", {})
                    defaults = self.default_settings()

                    for key, value in defaults.items():
                        settings.setdefault(key, value)

                    # Legacy setting, no longer exposed in the UI.
                    settings.pop("window_opacity", None)

                    return data
            except:
                return {"library": [], "settings": self.default_settings()}
        return {"library": [], "settings": self.default_settings()}

    def default_settings(self):
        return {
            "font_size": 18,
            "font_color": "#e0e0e0",
            "text_opacity": 1.0,
            "reading_mode": False,
            "language": "CN",
            "first_run": True
        }

    def save(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def add_novel(self, title, path):
        for item in self.data["library"]:
            if item["path"] == path:
                return item
        new_item = {"title": title, "path": path, "last_pos": 0, "chapters": []}
        self.data["library"].append(new_item)
        self.save()
        return new_item

    def update_pos(self, path, pos):
        self.update_progress(path, pos)

    def update_progress(self, path, pos, scroll_value=0, scroll_max=0):
        scroll_ratio = (scroll_value / scroll_max) if scroll_max else 0.0
        for item in self.data["library"]:
            if item["path"] == path:
                current_pos = item.get("last_pos", 0)
                current_ratio = item.get("last_scroll_ratio", 0.0)
                if current_pos == pos and abs(current_ratio - scroll_ratio) < 0.0005:
                    return False
                item["last_pos"] = pos
                item["last_scroll_ratio"] = scroll_ratio
                break
        else:
            return False

        self.save()
        return True

    def get_settings(self):
        return self.data.get("settings", self.default_settings())

    def update_settings(self, settings):
        self.data["settings"] = settings
        self.save()
