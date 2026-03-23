import os
import re

import chardet


class ReaderLogic:
    def __init__(self):
        self._encoding_cache = {}
        self._chapter_cache = {}
        self.chapter_patterns = [
            re.compile("^\\s*\u7b2c[\\d\u96f6\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e\u5343\u4e07\u4e24\u3007\u25cb\u58f9\u8d30\u53c1\u8086\u4f0d\u9646\u67d2\u634c\u7396\u62fe\u4f70\u4edf]+[\u7ae0\u8282\u5377\u96c6\u90e8\u7bc7\u56de\u8bdd\u5e55].*$"),
            re.compile("^\\s*(\u5e8f\u7ae0|\u5e8f\u5e55|\u6954\u5b50|\u524d\u8a00|\u5f15\u5b50|\u6b63\u6587|\u540e\u8bb0|\u5c3e\u58f0|\u756a\u5916).*$"),
            re.compile(r"^\s*(chapter\s+[0-9ivxlcdm]+.*|prologue.*|epilogue.*)$", re.IGNORECASE),
            re.compile("^\\s*\\d+\\s*[\\u3001\\.\\uff0e]\\s*.+$"),
        ]

    def detect_encoding(self, path):
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = None

        cached = self._encoding_cache.get(path)
        if cached and cached["mtime"] == mtime:
            return cached["encoding"]

        with open(path, "rb") as f:
            raw_data = f.read(10000)
            result = chardet.detect(raw_data)
            encoding = result["encoding"] or "utf-8"

        self._encoding_cache[path] = {
            "mtime": mtime,
            "encoding": encoding,
        }
        return encoding

    def load_txt(self, path):
        try:
            encoding = self.detect_encoding(path)
            with open(path, "r", encoding=encoding, errors="ignore") as f:
                content = f.read()
            chapters = self.parse_chapters(content)
            self._update_chapter_cache(path, chapters)
            return content, chapters
        except Exception as e:
            print(f"Error loading file: {e}")
            return "", []

    def get_chapters(self, path):
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            return []

        cached = self._chapter_cache.get(path)
        if cached and cached["mtime"] == mtime:
            return cached["chapters"]

        try:
            encoding = self.detect_encoding(path)
            with open(path, "r", encoding=encoding, errors="ignore") as f:
                chapters = self._parse_chapters_from_lines(f)
            self._chapter_cache[path] = {
                "mtime": mtime,
                "chapters": chapters,
            }
            return chapters
        except Exception as e:
            print(f"Error parsing chapters: {e}")
            return []

    def _update_chapter_cache(self, path, chapters):
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            return

        self._chapter_cache[path] = {
            "mtime": mtime,
            "chapters": chapters,
        }

    def is_chapter_title(self, line):
        stripped = line.strip()
        if not stripped or len(stripped) > 80:
            return False

        return any(pattern.match(stripped) for pattern in self.chapter_patterns)

    def _parse_chapters_from_lines(self, lines):
        chapters = []
        current_pos = 0

        for i, raw_line in enumerate(lines):
            line = raw_line.rstrip("\r\n")
            if self.is_chapter_title(line):
                chapters.append({
                    "title": line.strip(),
                    "pos": current_pos,
                    "index": i,
                })
            current_pos += len(raw_line)

        return chapters

    def parse_chapters(self, content):
        return self._parse_chapters_from_lines(content.splitlines(True))
