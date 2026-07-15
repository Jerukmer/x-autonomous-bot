#!/usr/bin/env python3
"""
extract_mentions.py — baca mention @penepian via hermes-chrome-profile (headless).
Output: ~/.hermes/penepian_mentions.json  -> list[{id,username,text}]
"""
import json, os, time
from playwright.sync_api import sync_playwright

PROFILE = r"C:\Users\EMIS-07\AppData\Local\hermes-chrome-profile2"
OUT = r"C:\Users\EMIS-07\.hermes\penepian_mentions.json"
HANDLE = "penepian"
MENTIONS_URL = f"https://x.com/{HANDLE}/mentions"

def main():
    with sync_playwright() as p:
        # CDP: nyambung Chrome bot (profil2, port 9223) yg SDH login.
        b = p.chromium.connect_over_cdp("http://localhost:9223")
        ctx = b.contexts[0] if b.contexts else b.new_context()
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            pg.goto(MENTIONS_URL, wait_until="domcontentloaded", timeout=30000)
            time.sleep(5)
            try:
                pg.wait_for_selector("article", timeout=15000)
            except Exception:
                json.dump([], open(OUT, "w"))
                print("NO_MENTIONS")
                return
            arts = pg.locator("article").all()
            out = []
            seen = set()
            for tw in arts:
                try:
                    txt_el = tw.locator("div[data-testid='tweetText']").first
                    text = txt_el.inner_text() if txt_el.count() else ""
                    # Handle ASLI ada di href="/HANDLE/status/ID"
                    href = ""
                    for a in tw.locator("a[href*='/status/']").all():
                        h = a.get_attribute("href") or ""
                        if "/status/" in h and "/status/" not in h[h.find("/status/"):]:
                            href = h
                            break
                    if not href:
                        href = tw.locator("a[href*='/status/']").first.get_attribute("href") or ""
                    parts = [x for x in href.split("/") if x]
                    # cari index 'status', handle = elemen sebelumnya
                    if "status" in parts:
                        idx = parts.index("status")
                        uname = parts[idx-1].replace("@","").strip()
                        tid = parts[idx+1].split("?")[0]
                    else:
                        continue
                except Exception:
                    continue
                if not tid or tid in seen:
                    continue
                if uname.lower() == HANDLE:
                    continue
                if len(text) < 3:
                    continue
                seen.add(tid)
                out.append({"id": tid, "username": uname, "text": text})
            json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=2)
        finally:
            pass  # JANGAN pg.close() -> reuse page (hemat renderer)

if __name__ == "__main__":
    main()
