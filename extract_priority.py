#!/usr/bin/env python3
"""
extract_priority.py v2 — baca tweet akun PRIORITY (akun yg Ji ikuti) via profil2 headless.
Output: ~/.hermes/penepian_priority.json -> list[{id,username,text,url}]
Sumber = search 'from:@handle' per akun (STABIL, terbukti jalan spt extract_fyp).
Batch round-robin: 8 akun/run, cursor muter biar 38 akun ke-cover ~5 run.
"""
import json, os, time
from playwright.sync_api import sync_playwright

PROFILE = r"C:\Users\EMIS-07\AppData\Local\hermes-chrome-profile2"
OUT = r"C:\Users\EMIS-07\.hermes\penepian_priority.json"
CONF = r"C:\Users\EMIS-07\.hermes\priority_accounts.json"
CURSOR = r"C:\Users\EMIS-07\.hermes\penepian_priority_cursor.json"
HANDLE = "penepian"
MAX_PER_ACCOUNT = 2
BATCH = 8
MAX_TOTAL = 12

def load_accounts():
    if os.path.exists(CONF):
        try:
            d = json.load(open(CONF))
            return [a["username"].lstrip("@").lower() for a in d.get("priority_a", [])]
        except: pass
    return []

def load_cursor():
    if os.path.exists(CURSOR):
        try: return json.load(open(CURSOR)).get("idx", 0)
        except: pass
    return 0

def save_cursor(i):
    json.dump({"idx": i}, open(CURSOR, "w"))

def main():
    accounts = load_accounts()
    if not accounts:
        print("NO_PRIORITY_ACCOUNTS")
        json.dump([], open(OUT, "w")); return
    n = len(accounts)
    start = load_cursor()
    batch, i = [], start
    for _ in range(BATCH):
        batch.append(accounts[i % n]); i += 1
    save_cursor(i % n)

    out, seen = [], set()
    with sync_playwright() as p:
        # CDP: nyambung ke Chrome bot (profil2, port 9223) yg SDH login.
        # Tdk buka instance baru -> session X tdk expire (fix logout berulang).
        b = p.chromium.connect_over_cdp("http://localhost:9223")
        ctx = b.contexts[0] if b.contexts else b.new_context()
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            for acc in batch:
                if len(out) >= MAX_TOTAL:
                    break
                try:
                    pg.goto(f"https://x.com/search?q=from:{acc}&src=typed_query&f=live",
                             wait_until="domcontentloaded", timeout=25000)
                    time.sleep(4)
                    pg.wait_for_selector("article", timeout=12000)
                except Exception as e:
                    print(f"  skip @{acc}: {e}")
                    continue
                for _ in range(3):
                    try: pg.mouse.wheel(0, 2500)
                    except: pass
                    time.sleep(1.2)
                arts = pg.locator("article").all()
                cnt = 0
                for tw in arts:
                    if cnt >= MAX_PER_ACCOUNT or len(out) >= MAX_TOTAL:
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
                    except Exception:
                        continue
                print(f"  @{acc}: {cnt} tweet")
        finally:
            pass  # JANGAN pg.close() -> reuse page (hemat renderer)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=2)
    print(f"EXTRACTED {len(out)} priority tweets (batch {start}->{start+len(batch)}, cursor={i%n})")

if __name__ == "__main__":
    main()
