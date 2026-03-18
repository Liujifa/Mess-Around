# reader_logic.py
import re
import chardet

class ReaderLogic:
    def __init__(self):
        pass

    def load_txt(self, path):
        # Detect encoding
        with open(path, 'rb') as f:
            raw_data = f.read(10000) # Read first 10kb to detect encoding
            result = chardet.detect(raw_data)
            encoding = result['encoding'] or 'utf-8'

        try:
            with open(path, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read()
                return content, self.parse_chapters(content)
        except Exception as e:
            print(f"Error loading file: {e}")
            return "", []

    def parse_chapters(self, content):
        # Common Chinese chapter patterns: 第...章, 第...集, 第...节, 第...部分
        patterns = [
            r'^\s*第[一二三四五六七八九十百千万零0-9]+章.*$',
            r'^\s*第[一二三四五六七八九十百千万零0-9]+[章节集部卷].*$',
            r'^\s*Chapter\s+[0-9]+.*$',
            r'^\s*[0-9]+\s+.*$' # Simple numbering
        ]
        
        chapters = []
        lines = content.split('\n')
        current_pos = 0
        
        for i, line in enumerate(lines):
            # We match the first 100 chars of a line to see if it's a chapter header
            is_chapter = False
            for p in patterns:
                if re.match(p, line):
                    chapters.append({
                        "title": line.strip(),
                        "pos": current_pos,
                        "index": i
                    })
                    is_chapter = True
                    break
            current_pos += len(line) + 1 # +1 for \n
            
        return chapters
