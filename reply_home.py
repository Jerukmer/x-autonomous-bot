#!/usr/bin/env python3
"""reply_home.py - Komen beranda @penepian dengan KURASI + otak persona (konsisten).

Pipeline:
  1. Scan beranda (pakai page yg ADA, gak goto/reload).
  2. Score kurasi (engagement + niche + FYP) -> utamakan yg berpotensi RAMAI.
  3. BACA tweet -> analisa -> reply SELARAS via persona.gen_reply (SAMA dgn pipeline lain).
  4. Max 2/run, dedupe state/replied.json. Tombol tweetButton. Tutup modal tiap selesai.
  5. Lapor channel -1003321472507.

Otak = persona.gen_reply (baca->analisa->reply selaras, Gen Z+typo+NO emoji) ->
HASIL KELUARAN KONSISTEN dg learn_timeline.
"""
import os, sys, re, json, time, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bot_config as C
import persona
from playwright.sync_api import sync_playwright
from learn_timeline import open_modal, type_and_send

BASE = os.path.dirname(os.path.abspath(__file__))
REPLIED = os.path.join(C.STATE, "replied.json")  # SATU file dedupe global (bukan replied_home) biar gak dobel antar-pipeline
MAX_REPLY = 9999  # rate limit dihapus (perintah Ji)

NICHE_KW = ["jawa","gus","santri","nu","pesantren","kiai","ustad","politik","indonesia",
            "jokowi","prabowo","ganjar","kraton","ngopi","warung","tongkrongan","receh",
            "ngakak","viral","breaking"]

def parse_engagement(article):
    rep = ret = lk = 0
    try:
        labels = article.evaluate("""() => {
            const r = [];
            document.querySelectorAll('[data-testid]').forEach(e => {
                const lbl = e.getAttribute('aria-label') || '';
                if (/Reply|Retweet|Like|Balas|Retwit|Suka/.test(lbl)) r.push(lbl);
            });
            return r;
        }""")
    except:
        labels = []
    for lbl in labels:
        m = re.search(r"(\d[\d.,kK]*)", lbl)
        if not m: continue
        num = m.group(1).lower().replace("k","000").replace(",","")
        try: val = int(float(num))
        except: val = 0
        if "Reply" in lbl or "Balas" in lbl: rep = val
        elif "Retweet" in lbl or "Retwit" in lbl: ret = val
        elif "Like" in lbl or "Suka" in lbl: lk = val
    return rep, ret, lk

def score(verified, text, eng):
    rep, ret, lk = eng
    eng_score = (rep + ret*2 + lk*1) ** 0.5
    niche = min(sum(1 for k in NICHE_KW if k in text.lower()), 3) * 3
    fyp_bonus = 5 if verified else 0
    return round(eng_score + niche + fyp_bonus, 1)

def reply_one(pg, h, reply):
    """Reply beranda via open_modal (fresh-scan article) + type_and_send.
    Modal-first = buka modal sebelum type. Return True/False."""
    if not h:
        return False
    if not open_modal(pg, h):
        return False
    return type_and_send(pg, reply)

def main():
    try:
        # tunggu max 20s kalau lock dipegang pipeline lain (biar gak kelewat run, tapi gak dobel)
        for _ in range(10):
            if C.acquire_lock():
                break
            time.sleep(2)
        else:
            print("[reply_home] lock dipegang terus -> skip (anti-dobel)")
            return
        replied = {}
        try: replied = json.load(open(REPLIED))
        except: pass
        with sync_playwright() as p:
            b = p.chromium.connect_over_cdp(C.CDP)
            ctx = b.contexts[0]
            # ATURAN BARU (Ji 2026-07-17): tiap cron bebas buka tab sendiri.
            # JANGAN tutup tab ekstra punya cron lain -> cuma pilih page home utk scan.
            pg = None
            for c in ctx.pages:
                try:
                    if "x.com/home" in (c.url or ""):
                        pg = c; break
                except: pass
            if pg is None:
                pg = ctx.pages[0] if ctx.pages else ctx.new_page()
            pg.wait_for_timeout(2500)
            # Scroll lebih dalam untuk ambil ~100 tweet
            for _ in range(15):
                pg.mouse.wheel(0, 1400); pg.wait_for_timeout(650)
            # kumpul + score (SIMPAN object article biar gak detached pas dipakai)
            cands = []
            for a in pg.query_selector_all("article"):
                try: t = a.inner_text()
                except: continue
                if "iklan" in t.lower() or t.lower().startswith("ad "): continue
                m = re.search(r"@(\w+)", t)
                h = m.group(1) if m else "?"
                if h.lower() == C.HANDLE: continue
                verified = a.query_selector("[data-testid='icon-verified']") is not None
                eng = parse_engagement(a)
                sc = score(verified, t, eng)
                cands.append((sc, h, t, verified, h))  # simpan HANDLE (gak object stale)
            # urutkan by score (tertinggi dulu)
            cands.sort(key=lambda x: -x[0])
            done = 0
            for sc, h, t, ver, hdl in cands:
                if done >= MAX_REPLY: break
                key = h + ":" + t[:40]
                if key in replied: continue
                reply = persona.gen_reply(t)  # OTAK SAMA: baca->analisa->reply selaras
                if not reply: continue
                if reply_one(pg, hdl, reply):
                    replied[key] = time.time()
                    json.dump(replied, open(REPLIED, "w"), indent=2)  # SIMPAN LANGSUNG (anti-dobel/race)
                    done += 1
                    try:
                        import subprocess
                        subprocess.run(["hermes","send","-t",C.TG,
                            f"[Beranda] Komen @{h} (score {sc}): {reply}"],
                            capture_output=True, text=True, timeout=60)
                    except: pass
            json.dump(replied, open(REPLIED, "w"), indent=2)
            print(f"[reply_home] scan={len(cands)} reply={done} (tertinggi score={cands[0][0] if cands else 0})")
    finally:
        C.release_lock()

if __name__ == "__main__":
    main()