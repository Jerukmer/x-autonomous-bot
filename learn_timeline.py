#!/usr/bin/env python3
"""learn_timeline.py - AI Agent TERPUSAT bot X @penepian (1 file, gak subprocess).

Pipeline (cron tiap 1m): maintenance(cleanup+pref) -> scan beranda ->
belajar tren -> FYP dari beranda -> reply verified (otak = persona/Grok) ->
lapor progres Telegram.

Gabungan learn_timeline + reply_verified (dobel cron dihilangkan).
reply_home jalan terpisah (pakai lock file biar gak dobel).
File aktif: learn_timeline, reply_home, persona, bot_config, launch_bot_visible.
"""
import os, sys, re, json, time, random, shutil, glob, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bot_config as C
from playwright.sync_api import sync_playwright
import persona

BASE = os.path.dirname(os.path.abspath(__file__))
LEARN = os.path.join(BASE, "state", "learn_log.json")
FYP = os.path.join(BASE, "config", "fyp_accounts.json")
REPLIED = os.path.join(BASE, "state", "replied.json")
THREADS = os.path.join(BASE, "state", "threads.json")
TEMP = os.environ.get("TEMP", r"C:\Users\EMIS-07\AppData\Local\Temp")

MAX_REPLY = 9999
DAILY_FYP_CAP = 5
FYP_BLACKLIST = {"penepian"}
FYP_MIN_FREQ = 2

def load(p, d):
    try: return json.load(open(p))
    except: return d

def save(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(d, open(p, "w"), indent=2)

def notify(msg):
    try: subprocess.run(["hermes","send","-t",C.TG,msg],
                        capture_output=True, text=True, timeout=60)
    except: pass

# ---------- maintenance (gabungan cleanup + learning agent) ----------
PROFILE_JUNK = [
    r"C:\Users\EMIS-07\bot_profile.bak",
    r"C:\Users\EMIS-07\bot_profile2.bak",
    r"C:\Users\EMIS-07\hermes-chrome-profile*.old",
]

def _cleanup_collect():
    paths = []
    for p in PROFILE_JUNK:
        paths += glob.glob(p)
    pycf = os.path.join(BASE, "__pycache__")
    if os.path.isdir(pycf):
        paths.append(pycf)
    paths += glob.glob(os.path.join(TEMP, "hermes-verify-*"))
    paths += [os.path.join(BASE, f) for f in os.listdir(BASE) if f.endswith(".log")]
    return paths

def run_cleanup():
    removed = 0
    for t in _cleanup_collect():
        try:
            if os.path.isdir(t): shutil.rmtree(t)
            else: os.remove(t)
            removed += 1
        except: pass
    return removed

def maintenance(d):
    now = int(time.time())
    if now - d.get("last_cleanup", 0) > 6 * 3600:
        run_cleanup()
        d["last_cleanup"] = now
    prefs = d.setdefault("preferences", {})
    for k, v in {
        "persona": "Ji (Gen Z, santai, kadang typo, NO emoji, on-topic, bahasa asli, ~150 char)",
        "brain": "persona.gen_reply (Grok via hermes chat)",
        "ram_safe": True, "auto_cleanup": True, "report_channel": C.TG,
    }.items():
        prefs.setdefault(k, v)

def log_exp(d, name, result, note=""):
    exps = d.setdefault("experiments", [])
    exps.append({"name": name, "result": result, "note": note, "ts": int(time.time())})
    d["experiments"] = exps[-50:]

# ---------- scan beranda ----------
def _scan_once(pg):
    pg.wait_for_timeout(2500)
    for _ in range(3):
        pg.mouse.wheel(0, 1000); pg.wait_for_timeout(900)
    rows = []
    for a in pg.query_selector_all("article"):
        try: t = a.inner_text()
        except: continue
        if "iklan" in t.lower() or t.lower().startswith("ad "): continue
        m = re.search(r"@(\w+)", t)
        h = m.group(1) if m else "?"
        verified = a.query_selector("[data-testid='icon-verified']") is not None
        rows.append((h, t, a, verified))
    return rows

def scan_home(pg):
    return _scan_once(pg)

# ---------- belajar tren ----------
TOPIC_KW = {
    "bola": ["piala dunia","world cup","final","yamal","messi","argentina","brasil","inggris",
             "england","fifa","sepak","barca","madrid","remontada","timnas","euro","copa",
             "liverpool","city","ronaldo","mbappe","gol","bola","football","premier"],
    "crypto": ["btc","eth","solana","crypto","bitcoin","nft","airdrop","token","defi","wallet"],
    "ai": ["ai","gpt","llm","grok","chatbot","neural","openai","model"],
    "politik": ["jokowi","prabowo","politik","pilpres","dpr","gibran","santri","pesantren",
                "ngaji","ustad","indonesia","rakyat","presiden"],
    "musik": ["lagu","musik","album","konser","concert","spotify","artis","penyanyi","band"],
    "game": ["game","gaming","ps5","xbox","steam","mlbb","pubg","valorant","esport","moba"],
}

def learn_trends(d, rows):
    counts = {k: 0 for k in TOPIC_KW}
    for _, t, _, _ in rows:
        low = t.lower()
        for topic, kws in TOPIC_KW.items():
            if any(k in low for k in kws):
                counts[topic] += 1
    top = sorted(counts.items(), key=lambda x: -x[1])
    trends = d.setdefault("trends", {})
    today = time.strftime("%Y-%m-%d")
    trends[today] = {"topics": top, "sampled": len(rows)}
    for k in list(trends.keys()):
        if k < today:
            del trends[k]
    fav = d.setdefault("favorite_topics", {})
    for topic, n in top:
        if n > 0:
            fav[topic] = fav.get(topic, 0) + n
    return top

# ---------- FYP dari beranda ----------
def find_fyp(rows, d):
    freq = {}
    for h, t, a, ver in rows:
        if ver and h != C.HANDLE and re.match(r"^\w{1,15}$", h):
            freq[h] = freq.get(h, 0) + 1
    today = time.strftime("%Y-%m-%d")
    added_today = d.get("fyp_added_today", {}).get(today, 0)
    cur = load(FYP, {"famous": []})
    famous = set(x["username"] if isinstance(x, dict) else x for x in cur.get("famous", []))
    new_accs = []
    for h, n in sorted(freq.items(), key=lambda x: -x[1]):
        if added_today >= DAILY_FYP_CAP: break
        if n >= 2 and h not in famous:
            famous.add(h); new_accs.append(h); added_today += 1
    if new_accs:
        cur["famous"] = [{"username": x} for x in sorted(famous)]
        save(FYP, cur)
        d.setdefault("fyp_added_today", {})[today] = added_today
        notify("[Agen FYP] +%d akun potensi FYP: %s" % (len(new_accs), ", ".join("@"+x for x in new_accs)))
    return new_accs

# ---------- discover_fyp (internal, bekas script terpisah) ----------
def discover_fyp(pg, d):
    """Deteksi akun FYP dari beranda (pakai page yg ADA). Handle muncul >= MIN_FREQ
    + gak di blacklist -> famous list (max DAILY_FYP_CAP/hari). Gak verify via fetch
    (X blokir CORS) -> handle dari beranda udah valid."""
    today = time.strftime("%Y-%m-%d")
    if d.get("last_fyp_discovery") == today:
        return 0
    try:
        handles = pg.evaluate("""() => {
            const out = [];
            document.querySelectorAll('article').forEach(a => {
                const links = a.querySelectorAll('a[href*="/status/"]');
                for (const l of links) {
                    const h = (l.getAttribute('href')||'').split('/');
                    const i = h.indexOf('status');
                    if (i > 0) { out.push(h[i-1]); break; }
                }
            });
            return out;
        }""")
    except:
        handles = []
    freq = {}
    for h in handles:
        h = h.strip().lstrip("@")
        if not re.match(r"^[A-Za-z0-9_]{1,15}$", h): continue
        if h.lower() in FYP_BLACKLIST: continue
        freq[h] = freq.get(h, 0) + 1
    cur = load(FYP, {"famous": []})
    famous = set(x["username"] if isinstance(x, dict) else x for x in cur.get("famous", []))
    cands = sorted([(h, n) for h, n in freq.items()
                    if n >= FYP_MIN_FREQ and h not in famous], key=lambda x: -x[1])
    added = 0
    for h, n in cands[:DAILY_FYP_CAP]:
        famous.add(h); added += 1
    if added:
        cur["famous"] = [{"username": x} for x in sorted(famous)]
        save(FYP, cur)
        notify("[Agen FYP] +%d akun FYP: %s" % (added, ", ".join("@"+x for x in sorted(famous)[-added:])))
    d["last_fyp_discovery"] = today
    return added

# ---------- reply (BERANDA-DIRECT, terbukti jalan, anti-stale) ----------

def open_modal(pg, h):
    """Buka modal reply by HANDLE pakai LOCATOR (re-resolve tiap aksi -> gak
    detached pas X re-render). Scroll-find: balik top, turun cari article yg
    contains @h sampai ketemu di loaded DOM, lalu like+reply synchronous.
    Escape dulu buat tutup modal nangklu (biang mask intercept)."""
    try:
        # tutup modal/overlay nangklu biar gak nutupin tombol reply
        try: pg.keyboard.press("Escape"); pg.wait_for_timeout(500)
        except: pass
        pg.evaluate("window.scrollTo(0,0)")
        pg.wait_for_timeout(400)
        loc = None
        for _ in range(20):
            l = pg.locator("article:has-text('@%s')" % h).first
            if l.count() and l.is_visible():
                loc = l
                break
            pg.mouse.wheel(0, 700)
            pg.wait_for_timeout(350)
        if loc is None:
            print("[reply] @%s article gak ada di viewport (locator)" % h, flush=True)
            return False
        # LIKE dulu via locator
        try:
            lb = loc.locator("[data-testid='like']").first
            if lb.count() and "liked" not in (lb.get_attribute("aria-label") or "").lower():
                lb.click()
        except Exception as e:
            print("[like] err @%s: %s" % (h, e), flush=True)
        # klik reply via locator (force=True: hindari mask intercept dari overlay nangklu)
        btn = loc.locator("[data-testid='reply']").first
        if not btn.count():
            btn = loc.locator("[role='button'][aria-label='Reply']").first
        if not btn.count():
            print("[reply] @%s gak ada tombol reply" % h, flush=True)
            return False
        try:
            btn.click(force=True, timeout=8000)
        except Exception as e:
            print("[reply] @%s klik reply gagal: %s" % (h, e), flush=True)
            try: pg.keyboard.press("Escape")
            except: pass
            return False
        # tunggu composer (modal)
        box = pg.locator("[data-testid='tweetTextarea_0']").first
        try:
            box.wait_for(state="visible", timeout=8000)
        except Exception:
            print("[reply] @%s composer gak muncul" % h, flush=True)
            try: pg.keyboard.press("Escape")
            except: pass
            return False
        return True
    except Exception as e:
        print("[reply] open err @%s: %s" % (h, e), flush=True)
        try: pg.keyboard.press("Escape")
        except: pass
        return False

def type_and_send(pg, reply):
    """Type + klik send di modal composer yg SUDAH terbuka. Return True/False.
    Cara TERBUKTI (XXII/XXIV): box.type() -> React ke-trigger, send.click() biasa.
    Mask cuma blokir .click() visual check, tapi .type() nargetin element fokus."""
    try:
        box = pg.locator("[data-testid='tweetTextarea_0']").first
        box.click(force=True)  # fokus composer (force: hindari mask)
        box.type(reply, delay=30)
        pg.wait_for_timeout(800)
        typed = -1
        try:
            typed = box.evaluate("e => (e.value || e.textContent || '').length")
        except Exception:
            pass
        send = pg.locator("[data-testid='tweetButton']").first
        for _ in range(8):
            try:
                if send.is_enabled():
                    break
            except Exception:
                pass
            try:
                box.type(" ", delay=20)
                pg.keyboard.press("Backspace")
            except Exception:
                pass
            pg.wait_for_timeout(300)
        try:
            # force=True: hindari mask intercept. Ctrl+Enter juga submit di X.
            send.click(force=True, timeout=5000)
        except Exception:
            try:
                send.evaluate("e => e.click()")
            except Exception:
                pass
        # backup: Ctrl+Enter submit (lewati mask, keyboard-level)
        try:
            pg.keyboard.press("Control+Enter")
        except Exception:
            pass
        pg.wait_for_timeout(4000)
        sent = False
        try:
            for e in pg.locator("[data-testid='toast']").all():
                if "sent" in (e.inner_text() or "").lower():
                    sent = True
        except Exception:
            pass
        succ = sent or (pg.locator("[data-testid='tweetTextarea_0']").count() == 0)
        if not succ:
            print("[reply] type/send: sent=%s composer_gone=%s typed_len=%s" % (
                sent, pg.locator("[data-testid='tweetTextarea_0']").count() == 0, typed), flush=True)
        try:
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(600)
        except Exception:
            pass
        return succ
    except Exception as e:
        print("[reply] type/send err (lanjut): %s" % e, flush=True)
        try: pg.keyboard.press("Escape")
        except: pass
        return False

def do_replies(pg, rows, replied, threads):
    done = 0
    for h, t, a, ver in rows:
        if done >= MAX_REPLY: break
        if not ver: continue
        key = h + ":" + t[:40]
        if key in replied: continue
        # FRESH-SCAN modal-first: buka modal SEBELUM Grok (anti-detach)
        if not open_modal(pg, h):
            print("[do_replies] GAGAL buka modal @%s" % h, flush=True)
            continue
        print("[do_replies] Grok call @%s..." % h, flush=True)
        reply = persona.gen_reply(t)
        if not reply:
            print("[do_replies] @%s SKIP (Grok kosong)" % h, flush=True)
            try: pg.keyboard.press("Escape")
            except: pass
            continue
        print("[do_replies] Grok ok @%s: %s" % (h, reply[:40]), flush=True)
        if type_and_send(pg, reply):
            replied[key] = time.time()
            save(REPLIED, replied)
            threads[h] = threads.get(h, []) + [{"our_reply": reply, "orig": t[:80], "ts": time.time()}]
            save(THREADS, threads)
            done += 1
            notify("[Agen] Reply @%s: %s" % (h, reply))
            print("[do_replies] REPLY SENT @%s" % h, flush=True)
        else:
            print("[do_replies] GAGAL reply @%s" % h, flush=True)
    return done

# ---------- mention watcher (kerja DI DALAM tab mentions, bukan home) ----------

def do_mentions(pg, replied, threads):
    """Balas mention BARU yg belum dibalas.
    PENTING: article mention ada di tab mentions, BUKAN di home. Jadi buka tab
    mentions sendiri (mp) dan kerjakan modal di mp, bukan di pg(home).
    Modal-first: buka modal SEBELUM Grok (anti-detach)."""
    done = 0
    mp = None
    try:
        mp = pg.context.new_page()
        mp.goto("https://x.com/notifications/mentions", wait_until="domcontentloaded", timeout=30000)
        mp.wait_for_timeout(3500)
        # scroll biar X load lebih banyak mention
        for _ in range(6):
            mp.mouse.wheel(0, 1200); mp.wait_for_timeout(500)
        rows = []
        for a in mp.query_selector_all("article"):
            try: t = a.inner_text()
            except: continue
            if "iklan" in t.lower() or t.lower().startswith("ad "): continue
            m = re.search(r"@(\w+)", t)
            h = m.group(1) if m else "?"
            if h.lower() == C.HANDLE: continue
            rows.append((h, t))
        print("[mentions] scan %d mention" % len(rows), flush=True)
        for h, t in rows:
            if done >= MAX_REPLY: break
            key = h + ":" + t[:40]
            if key in replied: continue
            if not open_modal(mp, h):
                print("[mentions] GAGAL buka modal @%s" % h, flush=True)
                continue
            print("[mentions] Grok call @%s..." % h, flush=True)
            reply = persona.gen_reply(t)
            if not reply:
                print("[mentions] @%s SKIP (Grok kosong)" % h, flush=True)
                try: mp.keyboard.press("Escape")
                except: pass
                continue
            print("[mentions] Grok ok @%s: %s" % (h, reply[:40]), flush=True)
            if type_and_send(mp, reply):
                replied[key] = time.time()
                save(REPLIED, replied)
                threads[h] = threads.get(h, []) + [{"our_reply": reply, "orig": t[:80], "ts": time.time()}]
                save(THREADS, threads)
                done += 1
                notify("[Agen Mention] Reply @%s: %s" % (h, reply))
                print("[mentions] REPLY SENT @%s" % h, flush=True)
            else:
                print("[mentions] GAGAL reply @%s" % h, flush=True)
    except Exception as e:
        print("[mentions] err:", e, flush=True)
    finally:
        if mp:
            try: mp.close()
            except: pass
    return done
# ---------- report ----------
def report_learning(d, rows, top, new_fyp, done):
    now = time.strftime("%H:%M")
    trend_now = ", ".join(f"{k}:{v}" for k, v in top if v > 0) or "sepi"
    fav = sorted(d.get("favorite_topics", {}).items(), key=lambda x: -x[1])[:3]
    fav_str = ", ".join(f"{k}({v})" for k, v in fav) or "-"
    try: fyp_total = len(load(FYP, {}).get("famous", []))
    except: fyp_total = 0
    n_exp = len(d.get("experiments", []))
    cleaned = "ya" if (int(time.time()) - d.get("last_cleanup", 0)) < 300 else "-"
    msg = (
        f"[Progres Belajar {now}]\n"
        f"Scan beranda: {len(rows)} tweet\n"
        f"Tren skrg: {trend_now}\n"
        f"Topik favorit (kumulatif): {fav_str}\n"
        f"FYP: +{len(new_fyp)} baru | total {fyp_total} akun\n"
        f"Reply terkirim: {done}\n"
        f"Eksperimen tercatat: {n_exp} | cleanup barusan: {cleaned}"
    )
    notify(msg)

# ---------- main ----------
def main():
    print("[learn_timeline] START", flush=True)
    try:
        d = load(LEARN, {"preferences": {}, "experiments": [], "trends": {},
                         "favorite_topics": {}, "fyp_added_today": {}})
        maintenance(d)
        replied = load(REPLIED, {})
        threads = load(THREADS, {})
        with sync_playwright() as p:
            b = p.chromium.connect_over_cdp(C.CDP)
            ctx = b.contexts[0]
            # ATURAN (XXIII): jangan goto/reload page yg lagi dipakai cron lain.
            # TAPI kalau page bukan home / feed kosong, kita HARUS pastiin loaded.
            pg = ctx.pages[0] if ctx.pages else ctx.new_page()
            if "x.com/home" not in (pg.url or "") and "x.com/" != (pg.url or "").rstrip("/"):
                try:
                    pg.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
                except Exception as e:
                    print("[learn_timeline] goto home err (lanjut):", e, flush=True)
            # pastiin feed loaded: tunggu sampai ada article (max ~15dtk)
            for _ in range(10):
                if pg.query_selector_all("article"):
                    break
                pg.wait_for_timeout(1500)
            try:
                body = (pg.content() or "").lower()
                if "sign in" in body or "continue with" in body:
                    notify("[Agen] SESSION EXPIRED - login manual di bot_profile4")
                    print("[learn_timeline] SESSION EXPIRED", flush=True)
                    return
            except Exception as e:
                print("[learn_timeline] session-check err:", e, flush=True)
            rows = scan_home(pg)
            print("[learn_timeline] scanned %d" % len(rows), flush=True)
            top = learn_trends(d, rows)
            print("[learn_timeline] trends done", flush=True)
            new_fyp = find_fyp(rows, d)
            print("[learn_timeline] find_fyp done +%d" % len(new_fyp), flush=True)
            # REPLY verified di sini (learn_timeline + reply_verified udah digabung jadi 1).
            # Lock cegah dobel dg reply_home yg jalan terpisah.
            done = 0
            if C.acquire_lock():
                try:
                    done = do_replies(pg, rows, replied, threads)
                    m_done = do_mentions(pg, replied, threads)  # BALAS MENTION BARU
                    done += m_done
                finally:
                    C.release_lock()
                print("[learn_timeline] do_replies done reply=%d (mention=%d)" % (done, m_done), flush=True)
            else:
                print("[learn_timeline] lock dipegang reply_home -> skip reply (anti-dobel)", flush=True)
        log_exp(d, "cycle", "ok", "scan=%d reply=%d fyp+%d" % (len(rows), done, len(new_fyp)))
        save(LEARN, d); save(REPLIED, replied); save(THREADS, threads)
        top_str = ", ".join(f"{k}:{v}" for k, v in top if v > 0) or "random"
        print(f"[learn_timeline] scan={len(rows)} trend=[{top_str}] +FYP={len(new_fyp)} reply={done}", flush=True)
        report_learning(d, rows, top, new_fyp, done)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("[learn_timeline] CRASH:", e, flush=True)

if __name__ == "__main__":
    main()
