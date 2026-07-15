#!/usr/bin/env python3
"""
check_threads.py — Priority Watcher CONVERSATION MODE.
Cek tiap thread di penepian_threads.json: kalau pemilik tweet ASLI sudah
membalas reply kita (dan thread belum done), tulis ke penepian_thread_check.json
supaya cron (otak grok) bisa nulis balasan lanjutan.

Percakapan berakhir (done=True) kalau pemilik tweet TIDAK membalas
dalam 2 cek berturut-turut.

NOTE: script ini HANYA ekstrak status + konteks. Otak grok (cron) yg nulis balasan.
"""
import json, os, time
from playwright.sync_api import sync_playwright

PROFILE = r"C:\Users\EMIS-07\AppData\Local\hermes-chrome-profile2"
_HERMES = r"C:\Users\EMIS-07\.hermes"
THREADS = os.path.join(_HERMES, "penepian_threads.json")
OUT = os.path.join(_HERMES, "penepian_thread_check.json")
HANDLE = "penepian"

def extract_replies(pg, url):
    pg.goto(url, wait_until="domcontentloaded", timeout=20000)
    time.sleep(3)
    for _ in range(3):
        try: pg.mouse.wheel(0, 1500)
        except: pass
        time.sleep(1)
    out = []
    for tw in pg.locator("article").all():
        try:
            uname = None
            for a in tw.locator("a[href*='/status/']").all():
                h = a.get_attribute("href") or ""
                if "/status/" in h:
                    uname = h.split("/status/")[0].replace("@","").strip("/").lower()
                    break
            txt_el = tw.locator("div[data-testid='tweetText']").first
            txt = txt_el.inner_text() if txt_el.count() else ""
            if uname:
                out.append((uname, txt))
        except: pass
    return out

def main():
    if not os.path.exists(THREADS):
        json.dump([], open(OUT, "w")); print("NO_THREADS"); return
    threads = json.load(open(THREADS))
    if not threads:
        json.dump([], open(OUT, "w")); print("EMPTY_THREADS"); return

    need = []
    with sync_playwright() as p:
        # CDP: nyambung Chrome bot (profil2, port 9223) yg SDH login.
        b = p.chromium.connect_over_cdp("http://localhost:9223")
        ctx = b.contexts[0] if b.contexts else b.new_context()
        pg = ctx.new_page()
        try:
            for tid, meta in list(threads.items()):
                if meta.get("done"):
                    continue
                url = f"https://x.com/{meta['username']}/status/{tid}"
                replies = extract_replies(pg, url)
                owner_replies = [t for (u, t) in replies if u == meta["username"].lower() and t]
                if owner_replies:
                    need.append({
                        "tweet_id": tid,
                        "username": meta["username"],
                        "last_owner_reply": owner_replies[-1],
                        "need_reply": True,
                    })
                    meta["no_reply_streak"] = 0
                else:
                    meta["no_reply_streak"] = meta.get("no_reply_streak", 0) + 1
                    if meta["no_reply_streak"] >= 2:
                        meta["done"] = True
        finally:
            pg.close()  # JANGAN b.close()

    json.dump(threads, open(THREADS, "w"), ensure_ascii=False, indent=2)
    json.dump(need, open(OUT, "w"), ensure_ascii=False, indent=2)
    print(f"THREAD_CHECK: {len(need)} perlu dibalas, threads={len(threads)}")

if __name__ == "__main__":
    main()
