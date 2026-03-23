import sys
import os

# Put src in path so imports work
sys.path.insert(0, os.path.abspath('.'))

from web_novel_downloader import WebNovelDownloader
import logging

def log_cb(msg):
    print(f"LOG: {msg}")

downloader = WebNovelDownloader("./temp_dl", log_callback=log_cb)

# only fetch catalog
url = "https://m.bqg5.com/1_1771/"
print(f"Fetching: {url}")
soup = downloader.fetch_soup(url)
pages = downloader.collect_catalog_pages(url, soup)

print(f"Collected {len(pages)} pages.")

# count links in those pages
total_links = 0
for idx, (p_url, p_soup) in enumerate(pages):
    links = downloader.extract_chapter_links(p_url, p_soup)
    print(f"Page {idx} ({p_url}): {len(links)} chapter links found.")
    total_links += len(links)
    
print(f"Total: {total_links}")

