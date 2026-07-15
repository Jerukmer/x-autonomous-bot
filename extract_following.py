#!/usr/bin/env python3
"""
extract_following.py — ambil daftar akun yang @penepian IKUTI (x.com/penepian/following)
lalu tulis ke priority_accounts.json (priority_a) sebagai sumber Priority Watcher.
X lazy-load -> butuh scroll. Cap MAX untuk jaga rate + speed.
"""
import json, os, re, time
from playwright.sync_api import sync_playwright

PROFILE = r"C:\Users\EMIS-07\AppData\Local\hermes-chrome-profile2"
OUT = r"C:\Users\EMIS-07\.hermes\priority_accounts.json"
HANDLE = "penepian"
MAX = 60          # cap jumlah akun yang diambil (jaga rate)
SCROLL = 25       # jumlah scroll

def main():
    handles = []
    seen = set()
    with sync_playwright() as p:
        b = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        pg = b.new_page()
        try:
            pg.goto(f"https://x.com/{HANDLE}/following", wait_until="domcontentloaded", timeout=45000)
            # X butuh scroll + waktu buat render list following
            for pre in range(4):
                try: pg.mouse.wheel(0, 1500)
                except: pass
                time.sleep(2)
            try:
                pg.wait_for_selector("article", timeout=30000)
            except Exception as e:
                print("WARN no article, body snip:", pg.inner_text("body")[:80].replace("\n"," "))
            for _ in range(SCROLL):
                # ambil handle dari cell user di following list
                for a in pg.locator("a[href^='/']").all():
                    try:
                        h = a.get_attribute("href").strip("/")
                    except:
                        continue
                    if not h or h.count("/") != 0:
                        continue
                    # filter: hanya handle valid (huruf/angka/_), bukan path khusus
                    if h.lower() in (HANDLE, "home", "explore", "notifications",
                                      "messages", "i", "settings", "compose",
                                      "search", "logout", "login", "signup",
                                      "hashtag", "following", "followers"):
                        continue
                    if re.fullmatch(r"[A-Za-z0-9_]{1,15}", h) and h.lower() not in seen:
                        seen.add(h.lower())
                        handles.append(h)
                if len(handles) >= MAX:
                    break
                try: pg.mouse.wheel(0, 2000)
                except: pass
                time.sleep(1.0)
        finally:
            b.close()

    handles = handles[:MAX]
    data = {"priority_a": [{"username": h, "note": "auto: following @penepian",
                             "added_at": "2026-07-15"} for h in handles]}
    json.dump(data, open(OUT, "w"), ensure_ascii=False, indent=2)
    print(f"SCRAPED_FOLLOWING {len(handles)} akun -> {OUT}")
    for h in handles[:10]:
        print("  @" + h)

if __name__ == "__main__":
    main()
