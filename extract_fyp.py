#!/usr/bin/env python3
"""
extract_fyp.py v1 (STABIL) — STRATEGI C (@penepian request, Ji percaya otak grok):
@penepian komen di tweet akun BESAR/terkenal buat IMPRESI.

SUMBER = search 'from:@handle' per akun di fyp_accounts.json (STABIL, terbukti jalan).
For You murni (/home) GAGAL load di headless -> pakai whitelist search sbg pengganti.
Otak reply = Hermes/grok (persona Ji), dijalankan lewat cron.
"""
import json, os, time
from playwright.sync_api import sync_playwright

PROFILE = r"C:\Users\EMIS-07\AppData\Local\hermes-chrome-profile2"
OUT = r"C:\Users\EMIS-07\.hermes\penepian_fyp.json"
CONF = r"C:\Users\EMIS-07\.hermes\fyp_accounts.json"
HANDLE = "penepian"
MAX_PER_ACCOUNT = 2

def load_accounts():
    if os.path.exists(CONF):
        try:
            d = json.load(open(CONF))
            s = []
            for a in d.get("famous", []) + d.get("priority_b", []):
                s.append(a["username"].lstrip("@").lower())
            return s
        except: pass
    return []

def main():
    accounts = load_accounts()
    if not accounts:
        print("NO_FYP_ACCOUNTS (isi ~/.hermes/fyp_accounts.json dulu)")
        json.dump([], open(OUT, "w"))
        return
    out, seen = [], set()
    with sync_playwright() as p:
        # CDP: nyambung Chrome bot (profil2, port 9223) yg SDH login.
        b = p.chromium.connect_over_cdp("http://localhost:9223")
        ctx = b.contexts[0] if b.contexts else b.new_context()
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            for acc in accounts:
                try:
                    q = f"from:{acc}"
                    pg.goto(f"https://x.com/search?q={q}&src=typed_query&f=live",
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
                    if cnt >= MAX_PER_ACCOUNT:
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
                        if not tid or tid in seen or len(text) < 5:
                            continue
                        if uname.lower() == HANDLE:
                            continue
                        seen.add(tid)
                        out.append({
                            "id": tid, "username": uname, "text": text,
                            "url": f"https://x.com/{uname}/status/{tid}"
                        })
                        cnt += 1
                    except Exception:
                        continue
                print(f"  @{acc}: {cnt} tweet")
        finally:
            pass  # JANGAN pg.close() -> reuse page (hemat renderer)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=2)
    print(f"EXTRACTED {len(out)} FYP-famous tweets | accounts={len(accounts)}")

if __name__ == "__main__":
    main()
