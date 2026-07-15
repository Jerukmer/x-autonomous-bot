#!/usr/bin/env python3
"""
post_replies.py v3 — kirim reply/komen dari JSON via CDP port 9223 (Chrome bot profil2).
Input (env INPUT): penepian_replies.json / penepian_priority_replies.json / penepian_fyp_replies.json
Dedupe (env MEM): penepian_replied.json / penepian_priority_replied.json / penepian_fyp_replied.json
Fields tiap item: {id, username, reply}

FIX v3 (2026-07-15):
- Pakai connect_over_cdp("http://localhost:9223") -> session X tdk expire.
- Setiap action pakai timeout eksplisit -> gak gantung.
- Print di setiap step -> cron bisa lihat progress.
- Thread tracking: simpan ke penepian_threads.json (check_threads.py yg lanjutin).
"""
import json, os, time
from datetime import datetime
from playwright.sync_api import sync_playwright

_HERMES = r"C:\Users\EMIS-07\.hermes"
IN  = os.environ.get("INPUT", os.path.join(_HERMES, "penepian_replies.json"))
MEM = os.environ.get("MEM",   os.path.join(_HERMES, "penepian_replied.json"))
OUT_THREADS = os.path.join(_HERMES, "penepian_threads.json")
CDP = "http://localhost:9223"
COOLDOWN = 25
MAX = 2
RATE_FILE = os.path.join(_HERMES, "penepian_rate.json")
RATE_MAX_PER_HOUR = 30

def check_rate():
    key = datetime.now().strftime("%Y-%m-%d-%H")
    data = {"hour": key, "count": 0}
    if os.path.exists(RATE_FILE):
        try: data = json.load(open(RATE_FILE))
        except: pass
    if data.get("hour") != key:
        data = {"hour": key, "count": 0}
    return data.get("count", 0) < RATE_MAX_PER_HOUR

def bump_rate():
    key = datetime.now().strftime("%Y-%m-%d-%H")
    data = {"hour": key, "count": 0}
    if os.path.exists(RATE_FILE):
        try: data = json.load(open(RATE_FILE))
        except: pass
    if data.get("hour") != key:
        data = {"hour": key, "count": 0}
    data["count"] = data.get("count", 0) + 1
    json.dump(data, open(RATE_FILE, "w"))

def load_replied():
    if os.path.exists(MEM):
        try: return set(json.load(open(MEM)))
        except: pass
    return set()

def save_replied(s):
    json.dump(list(s)[-300:], open(MEM, "w"))

def load_threads():
    if os.path.exists(OUT_THREADS):
        try: return json.load(open(OUT_THREADS))
        except: pass
    return {}

def save_threads(d):
    json.dump(d, open(OUT_THREADS, "w"), ensure_ascii=False, indent=2)

def send_one(pg, item, replied, threads):
    tid = item.get("id", "")
    if not tid or tid in replied:
        return False
    url = f"https://x.com/{item['username']}/status/{tid}"
    try:
        pg.goto(url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(3)
        pg.locator("button[data-testid='reply']").first.click(timeout=10000)
        time.sleep(1.5)
        box = pg.locator("div[data-testid='tweetTextarea_0']").first
        box.fill(item["reply"])
        time.sleep(1)
        pg.locator("button[data-testid='tweetButton']").first.click(timeout=10000)
        print(f"SENT @{item['username']}: {item['reply'][:60]}")
        replied.add(tid)
        threads[tid] = {"username": item["username"], "done": False, "no_reply_streak": 0}
        bump_rate()
        time.sleep(COOLDOWN)
        return True
    except Exception as e:
        print(f"FAIL {tid}: {repr(e)[:120]}")
        return False

def main():
    if not check_rate():
        print("RATE_LIMIT jam ini penuh (30/jam). skip.")
        return
    if not os.path.exists(IN):
        print("NO_REPLIES_FILE"); return
    replies = json.load(open(IN))
    if not replies:
        print("EMPTY"); return
    replied = load_replied()
    threads = load_threads()
    sent = 0
    p = sync_playwright().start()
    try:
        b = p.chromium.connect_over_cdp(CDP)
        ctx = b.contexts[0] if b.contexts else b.new_context()
        pg = ctx.new_page()
        try:
            for item in replies[:MAX]:
                if not check_rate():
                    print("RATE_LIMIT tercapai, stop run ini.")
                    break
                if send_one(pg, item, replied, threads):
                    sent += 1
        finally:
            pg.close()
    except Exception as e:
        print(f"CDP_ERROR: {repr(e)[:150]}")
    finally:
        p.stop()  # stop playwright, TAPI Chrome bot tetap nyala (CDP client diputus aja)
    save_replied(replied)
    save_threads(threads)
    print(f"DONE sent={sent}")

if __name__ == "__main__":
    main()
