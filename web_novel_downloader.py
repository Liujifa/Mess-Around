from __future__ import annotations

import concurrent.futures
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import parse_qs, urlencode, urldefrag, urljoin, urlparse, urlunparse

try:
    import requests
    from bs4 import BeautifulSoup
    IMPORT_ERROR = None
except ImportError as exc:
    requests = None
    BeautifulSoup = None
    IMPORT_ERROR = exc

from browser_cookie_importer import CookieImportError, import_browser_cookies


ProgressCallback = Optional[Callable[[int, int, str, str], None]]
LogCallback = Optional[Callable[[str], None]]


@dataclass
class ChapterLink:
    title: str
    url: str
    index: int


@dataclass
class DownloadResult:
    title: str
    file_path: str
    chapter_count: int
    source_url: str


class WebDownloadError(RuntimeError):
    pass


class WebNovelDownloader:
    FANQIE_DOMAIN = "fanqienovel.com"
    CODE = ((58344, 58715), (58345, 58716))
    MAX_WORKERS = 4
    MAX_CONTENT_RETRIES = 3
    MAX_CATALOG_PAGES = 200
    MAX_CHAPTER_PAGES = 24

    CHAPTER_SKIP_KEYWORDS = (
        "\u4e0a\u4e00\u7ae0",
        "\u4e0b\u4e00\u7ae0",
        "\u4e0a\u4e00\u9875",
        "\u4e0b\u4e00\u9875",
        "\u4e0a\u9875",
        "\u4e0b\u9875",
        "\u8fd4\u56de\u76ee\u5f55",
        "\u52a0\u4e66\u7b7e",
        "\u52a0\u5165\u4e66\u67b6",
        "\u76ee\u5f55",
        "\u4e66\u67b6",
        "\u767b\u5f55",
        "\u6ce8\u518c",
        "\u4e0b\u8f7d",
        "\u6392\u884c",
        "\u63a8\u8350",
        "\u8bc4\u8bba",
        "\u9996\u9875",
        "previous chapter",
        "next chapter",
        "previous page",
        "next page",
        "table of contents",
        "toc",
        "bookmark",
        "login",
        "register",
        "download",
        "comment",
        "review",
        "home",
    )

    CONTENT_SKIP_KEYWORDS = (
        "\u4e0a\u4e00\u7ae0",
        "\u4e0b\u4e00\u7ae0",
        "\u4e0a\u4e00\u9875",
        "\u4e0b\u4e00\u9875",
        "\u4e0a\u9875",
        "\u4e0b\u9875",
        "\u52a0\u4e66\u7b7e",
        "\u52a0\u5165\u4e66\u67b6",
        "\u8fd4\u56de\u76ee\u5f55",
        "\u70b9\u51fb\u4e0b\u8f7d",
        "app\u4e0b\u8f7d",
        "\u624b\u673a\u9605\u8bfb",
        "\u63a8\u8350\u9605\u8bfb",
        "\u4e3e\u62a5",
        "\u6536\u85cf",
        "\u8bc4\u8bba",
        "\u6295\u7968",
        "\u9a8c\u8bc1\u7801",
        "\u7ae0\u8282\u62a5\u9519",
        "\u7ae0\u8282\u5185\u5bb9\u7f3a\u5931",
        "\u7a0d\u540e\u91cd\u65b0\u5c1d\u8bd5",
        "\u672c\u7ae0\u672a\u5b8c",
        "\u70b9\u51fb\u4e0b\u4e00\u9875\u7ee7\u7eed\u9605\u8bfb",
        "\u7b2c\u4e00\u65f6\u95f4\u66f4\u65b0",
        "\u865e\u76ae\u5c0f\u8bf4",
        "\u5c0f\u4e3b\uff0c\u8fd9\u4e2a\u7ae0\u8282\u540e\u9762\u8fd8\u6709\u54e6",
        "ttgcaptcha",
        "previous chapter",
        "next chapter",
        "previous page",
        "next page",
        "table of contents",
        "download app",
        "comment",
        "report",
    )

    CHAPTER_PATTERNS = (
        r"^\s*\u7b2c[\d\u96f6\u3007\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e\u5343\u4e07\u4e24\u58f9\u8d30\u53c1\u8086\u4f0d\u9646\u67d2\u634c\u7396\u62fe\u4f70\u4edf]+[\u7ae0\u8282\u5377\u96c6\u90e8\u7bc7\u56de\u8bdd\u5e55]",
        r"^\s*(\u5e8f\u7ae0|\u5e8f\u5e55|\u6954\u5b50|\u524d\u8a00|\u5f15\u5b50|\u6b63\u6587|\u540e\u8bb0|\u5c3e\u58f0|\u756a\u5916)",
        r"^\s*(chapter|prologue|epilogue)\b",
        r"^\s*\d+\s*[.\-:,\u3001]",
    )

    CONTENT_SELECTORS = (
        "article",
        ".article",
        "main",
        "#content",
        "#chaptercontent",
        "#nr",
        "#ajax-loaded-content",
        ".content",
        ".chapter-content",
        ".read-content",
        ".reader-content",
        ".article-content",
        ".book-content",
        ".txt",
        ".novel-content",
        ".read",
        ".yd_text2",
    )

    CATALOG_TEXT_KEYWORDS = (
        "\u5168\u90e8\u7ae0\u8282\u76ee\u5f55",
        "\u7ae0\u8282\u76ee\u5f55",
        "\u76ee\u5f55",
        "chapter list",
        "all chapters",
    )

    NEXT_PAGE_TEXTS = (
        "\u4e0b\u4e00\u9875",
        "\u4e0b\u9875",
        "\u4e0b\u4e00\u7ae0",
        "\u4e0b\u7ae0",
        "next",
        "next page",
    )

    PLACEHOLDER_HINTS = (
        "\u7ae0\u8282\u5185\u5bb9\u7f3a\u5931",
        "\u7a0d\u540e\u91cd\u65b0\u5c1d\u8bd5",
        "\u672c\u7ae0\u672a\u5b8c",
        "\u70b9\u51fb\u4e0b\u4e00\u9875\u7ee7\u7eed\u9605\u8bfb",
        "\u7b2c\u4e00\u65f6\u95f4\u66f4\u65b0",
        "\u865e\u76ae\u5c0f\u8bf4",
    )

    def __init__(
        self,
        download_dir: str,
        progress_callback: ProgressCallback = None,
        log_callback: LogCallback = None,
    ):
        if IMPORT_ERROR is not None or requests is None or BeautifulSoup is None:
            raise WebDownloadError(
                "Missing dependencies. Install requests and beautifulsoup4 to use web downloads."
            ) from IMPORT_ERROR

        self.download_dir = download_dir
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.is_cancelled = False
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/123.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
        )
        os.makedirs(self.download_dir, exist_ok=True)
        self.charset = self._load_charset()

    def log(self, message: str):
        if self.log_callback:
            self.log_callback(message)

    def emit_progress(self, current: int, total: int, message: str, chapter_title: str = ""):
        if self.progress_callback:
            self.progress_callback(current, total, message, chapter_title)

    def download(self, url: str, title_override: str = "", browser: str = "none") -> DownloadResult:
        normalized_url = self.normalize_url(url)
        hostname = (urlparse(normalized_url).hostname or "").lower()

        if browser and browser != "none":
            self._import_browser_cookie(browser, hostname)

        if self._is_fanqie_book_url(normalized_url):
            return self._download_fanqie_book(normalized_url, title_override.strip())

        return self._download_generic_book(normalized_url, title_override.strip())

    def normalize_url(self, url: str) -> str:
        cleaned = (url or "").strip()
        if not cleaned:
            raise WebDownloadError("URL is required.")
        if not re.match(r"^https?://", cleaned, re.IGNORECASE):
            cleaned = "https://" + cleaned
        return cleaned

    def _load_charset(self):
        charset_candidates = [
            Path(__file__).with_name("charset.json"),
            Path(__file__).resolve().parent.parent / "Tomato thief" / "src" / "charset.json",
        ]
        for charset_path in charset_candidates:
            if charset_path.exists():
                try:
                    with open(charset_path, "r", encoding="utf-8") as file:
                        return json.load(file)
                except Exception:
                    continue
        return None

    def _import_browser_cookie(self, browser: str, hostname: str):
        browser = (browser or "none").strip().lower()
        last_error = None
        for domain in self._cookie_domains(hostname):
            try:
                imported = import_browser_cookies(browser, domain)
                self.session.headers["Cookie"] = imported.cookie_header
                self.log(f"Imported {imported.browser} cookies for {domain}")
                return
            except CookieImportError as exc:
                last_error = exc

        raise WebDownloadError(str(last_error or "Failed to import browser cookies."))

    def _cookie_domains(self, hostname: str) -> list[str]:
        parts = [part for part in hostname.split(".") if part]
        candidates = []
        for size in range(len(parts), 1, -1):
            candidates.append(".".join(parts[-size:]))
        if hostname:
            candidates.insert(0, hostname)

        seen = set()
        result = []
        for domain in candidates:
            if domain not in seen:
                seen.add(domain)
                result.append(domain)
        return result

    def _is_fanqie_book_url(self, url: str) -> bool:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        return self.FANQIE_DOMAIN in hostname and "/page/" in parsed.path

    def _download_fanqie_book(self, url: str, title_override: str) -> DownloadResult:
        self.log("Detected Fanqie source, switching to the Fanqie downloader.")
        soup = self.fetch_soup(url)
        book_title = title_override or self.extract_book_title(soup, url)
        chapter_links: list[ChapterLink] = []
        seen = set()

        for index, link in enumerate(soup.select("a[href]")):
            href = self.normalize_link(url, link.get("href"))
            if not href or "/reader/" not in href or href in seen:
                continue
            seen.add(href)
            title = self.clean_chapter_title(link.get_text(" ", strip=True)) or f"Chapter {len(chapter_links) + 1}"
            chapter_links.append(ChapterLink(title=title, url=href, index=index))

        if not chapter_links:
            chapter_title, content = self._download_fanqie_single_chapter(url, soup)
            return self._save_txt(book_title or chapter_title, [(chapter_title, content)], url)

        chapters = []
        total = len(chapter_links)
        for current, chapter in enumerate(chapter_links, start=1):
            if self.is_cancelled:
                raise WebDownloadError("Download canceled by user.")
            chapter_title, content = self._download_fanqie_single_chapter(chapter.url, title_hint=chapter.title)
            if content:
                chapters.append((chapter_title, content))
            self.emit_progress(current, total, "progress_fanqie", chapter_title)

        if not chapters:
            raise WebDownloadError("Could not extract readable content from Fanqie pages.")

        return self._save_txt(book_title, chapters, url)

    def _download_fanqie_single_chapter(
        self,
        url: str,
        soup: BeautifulSoup | None = None,
        title_hint: str = "",
    ) -> tuple[str, str]:
        soup = soup or self.fetch_soup(url)
        content = self.extract_fanqie_content(soup)
        if not content:
            content = self.extract_content(soup)
        if self.charset:
            content = self.decode_best_content(content)
        chapter_title = self.clean_chapter_title(title_hint or self.extract_chapter_title(soup)) or "Untitled Chapter"
        return chapter_title, content.strip()

    def _download_generic_book(self, url: str, title_override: str) -> DownloadResult:
        self.log("Using the generic web novel downloader.")
        initial_soup = self.fetch_soup(url)
        catalog_url = self.resolve_catalog_url(url, initial_soup)
        catalog_soup = initial_soup if catalog_url == url else self.fetch_soup(catalog_url, referer=url)
        chapter_links = self.extract_chapter_links(catalog_url, catalog_soup)

        if len(chapter_links) < 3:
            chapter_title, content = self.download_generic_chapter(url, title_override)
            if not content:
                raise WebDownloadError("No readable page content or chapter list was detected.")
            return self._save_txt(title_override or chapter_title, [(chapter_title, content)], url)

        book_title = title_override or self.extract_book_title(catalog_soup, catalog_url)
        chapters = self.download_chapter_batch(chapter_links)
        if not chapters:
            raise WebDownloadError("A chapter list was detected, but every chapter download failed.")
        return self._save_txt(book_title, chapters, catalog_url)

    def resolve_catalog_url(self, url: str, soup: BeautifulSoup) -> str:
        parsed = urlparse(url)
        if "/index/" in parsed.path:
            return url

        base_host = parsed.hostname or ""
        candidates = []
        for anchor in soup.select("a[href]"):
            href = self.normalize_link(url, anchor.get("href"))
            if not href or href == url:
                continue

            href_parsed = urlparse(href)
            if not self.is_same_site(base_host, href_parsed.hostname or ""):
                continue

            text = self.clean_text(anchor.get_text(" ", strip=True)).lower()
            path = href_parsed.path.lower()
            score = 0
            if any(keyword in text for keyword in self.CATALOG_TEXT_KEYWORDS):
                score += 5
            if "/index/" in path:
                score += 4
            if "chapter" in path:
                score += 1
            if score >= 4:
                candidates.append((score, len(path), href))

        if not candidates:
            return url

        return sorted(candidates, key=lambda item: (-item[0], item[1]))[0][2]

    def download_chapter_batch(self, chapter_links: list[ChapterLink]) -> list[tuple[str, str]]:
        max_workers = min(self.MAX_WORKERS, max(1, len(chapter_links)))
        downloaded: dict[int, tuple[str, str]] = {}
        total = len(chapter_links)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(self.download_generic_chapter, chapter.url, chapter.title): chapter
                for chapter in chapter_links
            }

            completed = 0
            for future in concurrent.futures.as_completed(future_map):
                if self.is_cancelled:
                    raise WebDownloadError("Download canceled by user.")
                chapter = future_map[future]
                completed += 1
                try:
                    chapter_title, content = future.result()
                    if content:
                        downloaded[chapter.index] = (chapter_title, content)
                except Exception as exc:
                    self.log(f"Failed to download chapter: {chapter.title} - {exc}")
                self.emit_progress(completed, total, "progress_web", chapter.title)

        return [downloaded[index] for index in sorted(downloaded)]

    def download_generic_chapter(self, url: str, title_hint: str = "") -> tuple[str, str]:
        chapter_title, parts = self.collect_chapter_pages(url, title_hint)
        return chapter_title, "\n\n".join(parts).strip()

    def collect_chapter_pages(self, url: str, title_hint: str = "") -> tuple[str, list[str]]:
        visited = set()
        parts = []
        chapter_title = self.clean_chapter_title(title_hint)
        current_url = self.normalize_url(url)
        referer = ""

        for _ in range(self.MAX_CHAPTER_PAGES):
            if current_url in visited:
                break
            visited.add(current_url)

            content, page_title, next_page_url = self.fetch_chapter_page_content(current_url, referer)
            if page_title and not chapter_title:
                chapter_title = page_title

            if content and (not parts or content != parts[-1]):
                parts.append(content)

            if not next_page_url or next_page_url in visited:
                break

            referer = current_url
            current_url = next_page_url

        return chapter_title or "Untitled Chapter", parts

    def fetch_chapter_page_content(self, url: str, referer: str = "") -> tuple[str, str, str]:
        last_content = ""
        last_title = ""
        last_next_page = ""

        for attempt in range(self.MAX_CONTENT_RETRIES):
            html = self.fetch_html(url, referer=referer)
            html = self.resolve_ajax_content(url, html)
            soup = BeautifulSoup(html, "html.parser")
            page_title = self.clean_chapter_title(self.extract_chapter_title(soup))
            content = self.extract_content(soup)
            next_page_url = self.find_next_chapter_page(url, soup)

            last_content = content
            last_title = page_title
            last_next_page = next_page_url

            if content and not self.is_placeholder_content(content):
                return content, page_title, next_page_url

            if next_page_url:
                return "", page_title, next_page_url

            if attempt < self.MAX_CONTENT_RETRIES - 1:
                self.log(f"Retrying chapter page: {url}")
                time.sleep(0.8 * (attempt + 1))

        if last_content and not self.is_placeholder_content(last_content):
            return last_content, last_title, last_next_page
        return "", last_title, last_next_page

    def fetch_html(self, url: str, referer: str = "") -> str:
        headers = {"Referer": referer} if referer else None
        response = self.session.get(url, timeout=20, headers=headers)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or response.encoding or "utf-8"
        return response.text

    def resolve_ajax_content(self, url: str, html: str) -> str:
        ajax_match = re.search(r'\$\.ajax\(\{\s*type\s*:\s*[\'"]post[\'"]\s*,\s*url\s*:\s*[\'"]([^\'"]+)[\'"]\s*,\s*data\s*:\s*\{(.*?)\}', html, re.IGNORECASE)
        if not ajax_match:
            return html

        api_path = ajax_match.group(1)
        if not any(kw in api_path.lower() for kw in ("reader", "chapter", "content", "api")):
            return html

        try:
            api_url = urljoin(url, api_path)
            payload = {}
            for kv in ajax_match.group(2).split(","):
                if ":" in kv:
                    k, v = kv.split(":", 1)
                    payload[k.strip(" '\"")] = v.strip(" '\"")
            
            res = self.session.post(api_url, data=payload, headers={"Referer": url}, timeout=10)
            res.raise_for_status()
            res.encoding = res.apparent_encoding or res.encoding or "utf-8"
            
            # Combine the dynamic text cleanly for the parser
            return html + f'<div id="ajax-loaded-content">{res.text}</div>'
        except Exception as exc:
            self.log(f"Failed to fetch dynamic AJAX content for {url}: {exc}")
            return html

    def fetch_soup(self, url: str, referer: str = "") -> BeautifulSoup:
        return BeautifulSoup(self.fetch_html(url, referer=referer), "html.parser")

    def extract_chapter_links(self, base_url: str, soup: BeautifulSoup) -> list[ChapterLink]:
        catalog_pages = self.collect_catalog_pages(base_url, soup)
        parsed_base = urlparse(base_url)
        base_host = parsed_base.hostname or ""
        candidates: list[ChapterLink] = []
        seen_urls = set()
        running_index = 0

        for page_url, page_soup in catalog_pages:
            for anchor in page_soup.select("a[href]"):
                href = self.normalize_link(page_url, anchor.get("href"))
                if not href or href in seen_urls:
                    continue

                parsed_href = urlparse(href)
                if not parsed_href.scheme.startswith("http"):
                    continue
                if not self.is_same_site(base_host, parsed_href.hostname or ""):
                    continue

                title = self.clean_chapter_title(anchor.get_text(" ", strip=True))
                if not self.looks_like_chapter_link(title, href):
                    continue

                seen_urls.add(href)
                candidates.append(ChapterLink(title=title, url=href, index=running_index))
                running_index += 1

        if len(candidates) < 3:
            return []

        return self.sort_chapter_links(candidates)

    def collect_catalog_pages(self, start_url: str, start_soup: BeautifulSoup) -> list[tuple[str, BeautifulSoup]]:
        pages = []
        current_url = self.normalize_url(start_url)
        current_soup = start_soup
        visited = {current_url}

        for _ in range(self.MAX_CATALOG_PAGES):
            if self.is_cancelled:
                raise WebDownloadError("Download canceled by user.")
            pages.append((current_url, current_soup))
            next_page_url = self.find_next_catalog_page(current_url, current_soup)
            if not next_page_url or next_page_url in visited:
                break
            visited.add(next_page_url)
            self.log(f"Loading catalog page: {next_page_url}")
            current_soup = self.fetch_soup(next_page_url, referer=current_url)
            current_url = next_page_url

        return pages

    def find_next_catalog_page(self, current_url: str, soup: BeautifulSoup) -> str:
        for anchor in soup.select("a[href]"):
            label = self.clean_text(anchor.get_text(" ", strip=True)).lower()
            if any(keyword in label for keyword in self.NEXT_PAGE_TEXTS):
                href = self.normalize_link(current_url, anchor.get("href"))
                if href and self.is_catalog_pagination_candidate(current_url, href):
                    return href

        guessed = self.build_next_chapter_page_url(current_url)
        if guessed and guessed != current_url:
            parsed_guessed = urlparse(guessed)
            for anchor in soup.select("a[href]"):
                href = self.normalize_link(current_url, anchor.get("href"))
                if not href:
                    continue
                parsed_href = urlparse(href)
                if parsed_href.path == parsed_guessed.path and parsed_href.query == parsed_guessed.query:
                    if self.is_catalog_pagination_candidate(current_url, href):
                        return href

        return ""

    def find_next_chapter_page(self, current_url: str, soup: BeautifulSoup) -> str:
        for anchor in soup.select("a[href]"):
            label = self.clean_text(anchor.get_text(" ", strip=True)).lower()
            if not any(keyword in label for keyword in self.NEXT_PAGE_TEXTS):
                continue

            href = self.normalize_link(current_url, anchor.get("href"))
            if href and self.is_chapter_pagination_candidate(current_url, href):
                return href

        current_title = self.clean_text(self.extract_chapter_title(soup))
        page_match = re.search(r"[(\uff08](\d+)/(\d+)[)\uff09]", current_title)
        if page_match and int(page_match.group(1)) < int(page_match.group(2)):
            guessed = self.build_next_chapter_page_url(current_url)
            if guessed and guessed != current_url:
                return guessed

        return ""

    def is_catalog_pagination_candidate(self, current_url: str, next_url: str) -> bool:
        current = urlparse(current_url)
        next_page = urlparse(next_url)
        if not self.is_same_site(current.hostname or "", next_page.hostname or ""):
            return False
        if next_url == current_url or "/chapter/" in next_page.path:
            return False

        current_base = self.base_page_identity(current.path)
        next_base = self.base_page_identity(next_page.path)
        if current_base == next_base:
            return True

        if "index" in next_page.path.lower() or "list" in next_page.path.lower():
            return True

        return False

    def is_chapter_pagination_candidate(self, current_url: str, next_url: str) -> bool:
        current = urlparse(current_url)
        next_page = urlparse(next_url)
        if not self.is_same_site(current.hostname or "", next_page.hostname or ""):
            return False
        if next_url == current_url:
            return False

        current_base = self.base_page_identity(current.path)
        next_base = self.base_page_identity(next_page.path)
        if current_base == next_base:
            return True

        if current.path == next_page.path and current.query != next_page.query:
            return True

        return False

    def build_next_chapter_page_url(self, current_url: str) -> str:
        parsed = urlparse(current_url)
        path = parsed.path

        match = re.search(r"_(\d+)\.html$", path, re.IGNORECASE)
        if match:
            next_num = int(match.group(1)) + 1
            new_path = re.sub(r"_(\d+)\.html$", f"_{next_num}.html", path, flags=re.IGNORECASE)
            return urlunparse(parsed._replace(path=new_path))

        if path.lower().endswith(".html"):
            new_path = path[:-5] + "_2.html"
            return urlunparse(parsed._replace(path=new_path))

        if path.endswith("/"):
            new_path = path + "index_2.html"
            return urlunparse(parsed._replace(path=new_path))

        query = parse_qs(parsed.query, keep_blank_values=True)
        if "page" in query:
            try:
                page_num = int(query["page"][0])
            except Exception:
                page_num = 1
            query["page"] = [str(page_num + 1)]
            return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))

        return ""

    def base_page_identity(self, path: str) -> str:
        normalized = path.rstrip("/")
        normalized = re.sub(r"_(\d+)\.html$", ".html", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"/(\d+)\.html$", ".html", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(?:/page)?/(\d+)$", "", normalized, flags=re.IGNORECASE)
        return normalized

    def is_placeholder_content(self, content: str) -> bool:
        text = self.clean_text(content).lower()
        if not text:
            return True
        if len(text) < 120 and any(marker in text for marker in self.PLACEHOLDER_HINTS):
            return True
        lines = [line for line in content.splitlines() if line.strip()]
        if len(lines) <= 3 and any(marker in text for marker in self.PLACEHOLDER_HINTS):
            return True
        return False

    def normalize_link(self, base_url: str, href: str | None) -> str:
        if not href:
            return ""
        href = href.strip()
        if href.lower().startswith(("javascript:", "mailto:", "#")):
            return ""
        return self.normalize_url(urldefrag(urljoin(base_url, href)).url)

    def is_same_site(self, base_host: str, target_host: str) -> bool:
        if not base_host or not target_host:
            return False
        if base_host == target_host:
            return True
        return target_host.endswith("." + base_host) or base_host.endswith("." + target_host)

    def looks_like_chapter_link(self, title: str, href: str) -> bool:
        if not title or len(title) > 80:
            return False

        lowered = title.lower()
        if any(keyword in lowered for keyword in self.CHAPTER_SKIP_KEYWORDS):
            return False

        if any(re.search(pattern, title, re.IGNORECASE) for pattern in self.CHAPTER_PATTERNS):
            return True

        href_lower = href.lower()
        href_patterns = ("chapter", "reader", "read", "chapterid", "view", "cid")
        if any(pattern in href_lower for pattern in href_patterns) and re.search(r"\d", href_lower):
            return True

        if re.search(r"\d", title) and len(title) <= 32:
            return True

        return False

    def sort_chapter_links(self, links: list[ChapterLink]) -> list[ChapterLink]:
        numbered = []
        for link in links:
            match = re.search(r"\d+", link.title)
            if match:
                numbered.append((int(match.group()), link.index, link))

        if len(numbered) >= max(3, len(links) // 2):
            ordered = [item[2] for item in sorted(numbered, key=lambda item: (item[0], item[1]))]
            return [ChapterLink(title=link.title, url=link.url, index=index) for index, link in enumerate(ordered)]

        ordered = sorted(links, key=lambda link: link.index)
        return [ChapterLink(title=link.title, url=link.url, index=index) for index, link in enumerate(ordered)]

    def extract_book_title(self, soup: BeautifulSoup, url: str) -> str:
        meta_candidates = [
            ("meta", {"property": "og:title"}),
            ("meta", {"property": "og:novel:book_name"}),
            ("meta", {"name": "twitter:title"}),
        ]
        for tag_name, attrs in meta_candidates:
            tag = soup.find(tag_name, attrs=attrs)
            if tag and tag.get("content"):
                title = self.clean_title(tag.get("content", ""))
                if title:
                    return title

        for selector in ("h1", ".book-name", ".novel-title", ".title"):
            tag = soup.select_one(selector)
            if tag:
                title = self.clean_title(tag.get_text(" ", strip=True))
                if title:
                    return title

        if soup.title and soup.title.string:
            title = self.clean_title(soup.title.string)
            if title:
                return title

        fallback = urlparse(url).path.strip("/").split("/")[-1]
        return self.clean_title(fallback) or "web_novel"

    def extract_chapter_title(self, soup: BeautifulSoup) -> str:
        for selector in ("h1", ".chapter-title", ".title", ".headline"):
            tag = soup.select_one(selector)
            if tag:
                title = self.clean_text(tag.get_text(" ", strip=True))
                if title:
                    return title

        if soup.title and soup.title.string:
            title = self.clean_text(soup.title.string)
            if title:
                return title
        return ""

    def extract_fanqie_content(self, soup: BeautifulSoup) -> str:
        for selector in (".muye-reader-content", "[class*='reader-content']", "article", "main"):
            tag = soup.select_one(selector)
            if tag:
                text = self.tag_to_text(tag)
                filtered = self.filter_content_lines(text)
                if filtered:
                    return filtered
        return ""

    def extract_content(self, soup: BeautifulSoup) -> str:
        candidates = []

        for selector in self.CONTENT_SELECTORS:
            for tag in soup.select(selector):
                score, text = self.score_content_tag(tag)
                if score > 0 and text:
                    candidates.append((score, text))

        if not candidates and soup.body:
            score, text = self.score_content_tag(soup.body)
            if score > 0 and text:
                candidates.append((score, text))

        if not candidates:
            return ""

        best_text = max(candidates, key=lambda item: item[0])[1]
        return self.filter_content_lines(best_text)

    def score_content_tag(self, tag) -> tuple[int, str]:
        cloned = BeautifulSoup(str(tag), "html.parser")
        for bad in cloned.select(
            "script, style, nav, header, footer, aside, form, button, noscript, iframe, .ads, .ad, .toolbar, .comment, .recommend, .share"
        ):
            bad.decompose()

        text = self.tag_to_text(cloned)
        if not text:
            return 0, ""

        paragraphs = len([line for line in text.splitlines() if line.strip()])
        links_text = " ".join(node.get_text(" ", strip=True) for node in cloned.select("a"))
        link_penalty = len(links_text)
        score = len(text) + paragraphs * 25 - link_penalty
        return score, text

    def tag_to_text(self, tag) -> str:
        for br in tag.select("br"):
            br.replace_with("\n")
        for paragraph in tag.select("p"):
            paragraph.insert_after("\n")
        text = tag.get_text("\n", strip=False)
        return re.sub(r"\n{3,}", "\n\n", text)

    def filter_content_lines(self, text: str) -> str:
        lines = []
        for raw_line in text.splitlines():
            line = self.clean_text(raw_line)
            if not line:
                continue
            lowered = line.lower()
            if any(keyword in lowered for keyword in self.CONTENT_SKIP_KEYWORDS):
                continue
            lines.append(line)

        deduplicated = []
        seen = set()
        for line in lines:
            key = line.lower()
            if key in seen and len(line) > 30:
                continue
            seen.add(key)
            deduplicated.append(line)

        return "\n".join(deduplicated).strip()

    def clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def clean_title(self, text: str) -> str:
        title = self.clean_text(text)
        title = re.split(r"\s*[-|]\s*", title)[0].strip()
        return title

    def clean_chapter_title(self, text: str) -> str:
        title = self.clean_text(text)
        title = re.sub(r"[(\uff08]\d+/\d+[)\uff09]\s*$", "", title).strip()
        title = re.sub(r"[\u002c\uff0c]\s*\d+\s*\u9875\s*$", "", title).strip()
        title = re.sub(r"\s*-\s*\d+\s*/\s*\d+\s*$", "", title).strip()
        return title

    def normalize_chapter_title(self, text: str) -> str:
        title = self.clean_text(text)
        title = re.sub(r"[(\uff08]\d+/\d+[)\uff09]\s*$", "", title).strip()
        title = re.sub(r"[,，]\s*\d+\s*\u9875\s*$", "", title).strip()
        title = re.sub(r"\s*-\s*\d+\s*/\s*\d+\s*$", "", title).strip()
        return title

    def sanitize_filename(self, filename: str) -> str:
        safe = filename or "web_novel"
        safe = re.sub(r'[<>:"/\\\\|?*]+', "_", safe)
        safe = safe.strip().rstrip(".")
        return safe[:120] or "web_novel"

    def ensure_unique_path(self, title: str) -> str:
        safe_title = self.sanitize_filename(title)
        candidate = os.path.join(self.download_dir, f"{safe_title}.txt")
        if not os.path.exists(candidate):
            return candidate

        suffix = time.strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.download_dir, f"{safe_title}_{suffix}.txt")

    def _save_txt(self, title: str, chapters: list[tuple[str, str]], source_url: str) -> DownloadResult:
        if not chapters:
            raise WebDownloadError("No chapter content available to save.")

        output_title = self.clean_title(title) or chapters[0][0] or "web_novel"
        output_path = self.ensure_unique_path(output_title)

        with open(output_path, "w", encoding="utf-8") as file:
            file.write(f"{output_title}\n")
            file.write(f"Source: {source_url}\n")
            file.write(f"Chapters: {len(chapters)}\n\n")
            for chapter_title, content in chapters:
                file.write(f"{chapter_title}\n\n")
                file.write(content.strip())
                file.write("\n\n")

        self.log(f"Saved TXT to: {output_path}")
        return DownloadResult(
            title=output_title,
            file_path=output_path,
            chapter_count=len(chapters),
            source_url=source_url,
        )

    def decode_best_content(self, content: str) -> str:
        if not self.charset or not content:
            return content

        candidates = [content]
        for mode in range(len(self.CODE)):
            try:
                candidates.append(self.decode_content(content, mode))
            except Exception:
                continue

        return max(candidates, key=self.score_decoded_text)

    def decode_content(self, content: str, mode: int = 0) -> str:
        result = []
        start, end = self.CODE[mode]
        charset = self.charset[mode]

        for char in content:
            code_point = ord(char)
            if start <= code_point <= end:
                bias = code_point - start
                if 0 <= bias < len(charset) and charset[bias] != "?":
                    result.append(charset[bias])
                else:
                    result.append(char)
            else:
                result.append(char)
        return "".join(result)

    def score_decoded_text(self, text: str) -> int:
        chinese_chars = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
        private_use_chars = sum(1 for char in text if 0xE000 <= ord(char) <= 0xF8FF)
        replacement_chars = text.count("\ufffd") + text.count("?")
        return chinese_chars * 2 - private_use_chars * 3 - replacement_chars * 5
