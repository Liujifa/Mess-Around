import requests
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
urls = ["https://m.bqg5.com/1_1771/", "https://m.bqg5.com/1_1771/1.html"]

for u in urls:
    print(f"\n--- {u} ---")
    try:
        res = requests.get(u, headers=headers, timeout=10)
        res.encoding = res.apparent_encoding or "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")
        for a in soup.find_all("a"):
            t = a.get_text(strip=True)
            if "页" in t or "章" in t or "目录" in t:
                print(f"[{t}] -> {a.get('href')}")
    except Exception as e:
        print("Error:", e)
