#!/usr/bin/env python3
"""reply_back.py - balas mention BARU untuk @penepian (thread continuity).

RULE Ji: cuma balas mention yg MASUK BARU (setelah cron terakhir jalan).
Mention lama gak diapa2in. Cara: cursor = key mention teratas dari run sebelumnya.
Tiap run, baca mentions (terbaru di ATAS), proses dari atas sampai ketemu cursor
(= udah masuk wilayah lama) -> stop. Update cursor ke teratas yg baru.

Teks: persona.gen_reply (Gen Z, typo, bahasa asli, kontekstual, NO emoji).
Max 2/run. Tombol tweetButton. Tutup modal tiap selesai. Lapor channel.
"""
import re, json, time, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bot_config as C
import persona
from playwright.sync_api import sync_playwright

CURSOR_FILE = os.path.join(C.STATE, "reply_back_cursor.json")
REPLIED = os.path.join(C.STATE, "replied_back.json")
MAX_REPLY = 9999  # rate limit dihapus (perintah Ji)

def load_json(p, d):
    try: return json.load(open(p))
    except: return d

def save_json(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(d, open(p, "w"))

def notify(msg):
    try:
        import subprocess
        subprocess.run(["hermes","send","-t",C.TG,msg],
                       capture_output=True, text=True, timeout=60)
    except: pass

def reply_to_tweet(pg, article, reply):
    """Reply dari TIMELINE langsung. tweetButton beneran. Return True/False."""
    btn = article.query_selector("[data-testid='reply']")
    if not btn:
        btn = article.query_selector("div[role='button'][aria-label='Reply']")
    if not btn:
        return False
    btn.scroll_into_view_if_needed(); pg.wait_for_timeout(600)
    try: btn.click(timeout=6000)
    except:
        try: btn.evaluate("e=>e.click()")
        except: pass
    pg.wait_for_timeout(2500)
    tas = pg.query_selector_all("[data-testid='tweetTextarea_0']")
    box = None
    for t in tas:
        try:
            if t.evaluate("e=>!!e.closest(\"[role='dialog']\")"): box = t; break
        except: pass
    if not box and tas: box = tas[-1]
    if not box:
        return False
    box.click(); box.type(reply, delay=30); pg.wait_for_timeout(1200)
    sends = pg.query_selector_all("[data-testid='tweetButton']")
    send = None
    for s in sends:
        try:
            if s.evaluate("e=>!!e.closest(\"[role='dialog']\")"): send = s; break
        except: pass
    if not send and sends: send = sends[-1]
    if not send:
        return False
    try: send.click(timeout=9000)
    except:
        try: send.evaluate("e=>e.click()")
        except: pass
    pg.wait_for_timeout(4000)
    sent = False
    for e in pg.query_selector_all("[data-testid='toast']"):
        if "sent" in (e.inner_text() or "").lower(): sent = True
    try: pg.keyboard.press("Escape"); pg.wait_for_timeout(700)
    except: pass
    return sent or (pg.query_selector("[data-testid='tweetTextarea_0']") is None)

def parse_xtime(tweet_text, now=None):
    """Parse waktu X dari teks mention: '5m', '2h', '1d', 'Jul 15', 'Jul 15, 2026'.
    Kembalikan epoch detik (perkiraan). None kalau gak bisa parse."""
    import calendar
    if now is None: now = time.time()
    low = tweet_text.lower()
    # relatif: 5m, 2h, 1d, 30s
    m = re.search(r"(\d+)\s*(s|m|h|d|w)\b", low)
    if m:
        n = int(m.group(1)); unit = m.group(2)
        mult = {"s":1,"m":60,"h":3600,"d":86400,"w":604800}[unit]
        return now - n*mult
    # absolut: Jul 15 / Jul 15, 2026
    m = re.search(r"([a-z]{3})\s+(\d{1,2})(?:,\s*(\d{4}))?", low)
    if m:
        mon = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,
               "sep":9,"oct":10,"nov":11,"dec":12}.get(m.group(1))
        if mon:
            day = int(m.group(2))
            yr = int(m.group(3)) if m.group(3) else time.gmtime(now).tm_year
            try:
                return calendar.timegm((yr, mon, day, 0, 0, 0, 0, 0, 0))
            except: pass
    return None

def main():
    cursor = load_json(CURSOR_FILE, {})
    replied = load_json(REPLIED, {})
    now = time.time()
    last_run = cursor.get("last_run", 0)  # epoch cron terakhir jalan
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(C.CDP)
        ctx = b.contexts[0]
        for pg in ctx.pages[1:]:
            try: pg.close()
            except: pass
        pg = ctx.pages[0]
        if "mentions" not in pg.url:
            pg.goto("https://x.com/notifications/mentions", wait_until="domcontentloaded", timeout=20000)
            pg.wait_for_timeout(3500)
        for _ in range(2):
            pg.mouse.wheel(0, 1000); pg.wait_for_timeout(900)
        arts = pg.query_selector_all("article")
        cands = []
        for a in arts:
            try: t = a.inner_text()
            except: continue
            if "@penepian" not in t.lower():
                continue
            m = re.search(r"@(\w+)", t)
            h = m.group(1) if m else "?"
            xt = parse_xtime(t, now)
            cands.append((h, t, a, xt))
        if not cands:
            print("GAK ADA mention"); return
        # cuma yg LEBIH BARU dari last_run (acuan waktu X)
        new_ones = [c for c in cands if (c[3] is None or c[3] > last_run) and (h_ := c[0]) and (c[0]+":"+c[1][:40]) not in replied]
        if not new_ones:
            print("GAK ADA mention BARU dlm kurun 4m (acuan waktu) -> skip"); 
            cursor["last_run"] = now; save_json(CURSOR_FILE, cursor); return
        done = 0
        for h, t, article, xt in new_ones[:MAX_REPLY]:
            key = h + ":" + t[:40]
            if key in replied: continue
            reply = persona.gen_reply(t)
            if reply_to_tweet(pg, article, reply):
                replied[key] = now
                done += 1
                print(f"BALAS KE @{h} (BARU): {reply}")
                notify(f"[Balik] Balas mention BARU @{h}: {reply}")
        save_json(REPLIED, replied)
        cursor["last_run"] = now
        save_json(CURSOR_FILE, cursor)
        print(f"SELESAI: {done} balasan BARU (acuan waktu X)")

if __name__ == "__main__":
    main()
