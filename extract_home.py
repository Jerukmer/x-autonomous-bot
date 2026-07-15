#!/usr/bin/env python3
"""
extract_home.py — scrape tweet RANDOM dari BERANDA @penepian (x.com/home).
Output: ~/.hermes/penepian_home.json -> list[{id,username,text,url}]
Strategi: baca beranda, ambil N tweet pertama (acak/beragam dari siapa aja).
Batch round-robin cursor biar tiap run beda² tweet (gak numpuk di 1 orang).
Pakai CDP port 9223 (headless, session gak expire).
"""
import json, os, time
from playwright.sync_api import sync_playwright

CDP = "http://localhost:9223"
OUT = r"C:\Users\EMIS-07\.hermes\penepian_home.json"
CURSOR = r"C:\Users\EMIS-07\.hermes\penepian_home_cursor.json"
HANDLE = "penepian"

def load_cursor():
    if os.path.exists(CURSOR):
        try: return json.load(open(CURSOR)).get("skip", 0)
        except: pass
    return 0

def save_cursor(i):
    json.dump({"skip": i}, open(CURSOR, "w"))

def main():
    out, seen = [], set()
    skip = load_cursor()
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP)
        ctx = b.contexts[0]
        # REUSE page yg ada (jgn new_page tiap run -> renderer numpuk)
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            pg.goto("https://x.com/home", wait_until="domcontentloaded", timeout=25000)
            time.sleep(5)
            pg.wait_for_selector("article", timeout=15000)
            for _ in range(5):
                try: pg.mouse.wheel(0, 2000)
                except: pass
                time.sleep(1.5)
            arts = pg.locator("article").all()
            # skip beberapa tweet pertama biar tiap run beda (round-robin)
            # tapi kalau arts dikit, jangan skip lebay
            max_skip = max(0, len(arts) - 6)
            sk = min(skip, max_skip) if max_skip > 0 else 0
            arts = arts[sk: sk+10]
            cnt = 0
            for tw in arts:
                if cnt >= 6:
                    break
                try:
                    txt_el = tw.locator("div[data-testid='tweetText']").first
                    text = txt_el.inner_text() if txt_el.count() else ""
                    href = ""
                    for a in tw.locator("a[href*='/status/']").all():
                        h = a.get_attribute("href") or ""
                        if "/status/" in h:
                            href = h; break
                    parts = [x for x in href.split("/") if x]
                    if "status" not in parts:
                        continue
                    idx = parts.index("status")
                    uname = parts[idx-1].replace("@","").strip()
                    tid = parts[idx+1].split("?")[0]
                    if not tid or tid in seen or len(text) < 3:
                        continue
                    if uname.lower() == HANDLE:
                        continue
                    seen.add(tid)
                    out.append({"id": tid, "username": uname, "text": text,
                                "url": f"https://x.com/{uname}/status/{tid}"})
                    cnt += 1
                except: pass
            # geser cursor biar run berikutnya mulai dari tweet beda
            save_cursor((skip + 10) % 50)
            print(f"  home: {cnt} tweet (skip={skip})")
        finally:
            pass  # JANGAN pg.close() -> page dipakai ulang (hemat renderer)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=2)
    print(f"EXTRACTED {len(out)} home tweets")

if __name__ == "__main__":
    main()
