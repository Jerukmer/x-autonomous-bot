#!/usr/bin/env python3
"""run_bot.py - 1 ORCHESTRATOR tunggal bot X (ganti learn_timeline + reply_home).

Alur per run:
  1. Cek CDP (port bot). Mati -> coba relaunch launcher. Gagal -> notif + exit.
  2. Cek session: login screen? -> notif Ji login manual (rate-limited) + PAUSE.
  3. Scan beranda SEKALI -> kumpul (status_id, handle, text, verified).
  4. Filter: verified-only + pre-filter.
  5. Dedupe by status_id.
  6. Lock (anti dobel). Per kandidat: open_modal(status_id) -> Grok -> type_and_send terbukti.
  7. Mention watcher (tab mentions sendiri, ditutup di finally).
  8. Report JUJUR (bukan cuma "cron sukses").
  9. Self-heal: cleanup junk + simpan learn_log.

Bukti kirim = toast X "sent" / composer hilang, bukan cuma "udah coba".
"""
import os
import re
import sys
import json
import time
import shutil
import glob
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bot_config as C
from playwright.sync_api import sync_playwright
import persona

BASE = os.path.dirname(os.path.abspath(__file__))
LEARN = C.LEARN_FILE
REPLIED = C.REPLIED_FILE
TEMP = os.environ.get("TEMP", r"C:\Users\EMIS-07\AppData\Local\Temp")

# ---------------- helpers ----------------
def load(p, d):
    try:
        return json.load(open(p))
    except Exception:
        return d

def save(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(d, open(p, "w"), indent=2)

def save_replied(d):
    save(REPLIED, d)

def notify(msg):
    try:
        subprocess.run(["hermes", "send", "-t", C.TG, msg],
                       capture_output=True, text=True, timeout=60)
    except Exception:
        pass

def cdp_alive():
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{C.CDP_PORT}/json/version", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False

def launch_bot():
    try:
        subprocess.run([sys.executable, os.path.join(BASE, "launch_bot.py")],
                       capture_output=True, text=True, timeout=60)
        for _ in range(10):
            if cdp_alive():
                return True
            time.sleep(1)
    except Exception:
        pass
    return cdp_alive()

# ---------------- scan ----------------
def on_home(pg):
    u = (pg.url or "")
    return "x.com/home" in u or u.rstrip("/").endswith("x.com")

def wait_articles(pg, tries=10):
    for _ in range(tries):
        if pg.query_selector_all("article"):
            return True
        pg.wait_for_timeout(1500)
    return False

def session_expired(pg):
    try:
        body = (pg.content() or "").lower()
        return "sign in" in body or "continue with" in body
    except Exception:
        return False

def scan_home(pg):
    pg.wait_for_timeout(2000)
    for _ in range(3):
        pg.mouse.wheel(0, 1000)
        pg.wait_for_timeout(800)
    rows = []
    for a in pg.query_selector_all("article"):
        try:
            t = a.inner_text()
        except Exception:
            continue
        if "iklan" in t.lower() or t.lower().startswith("ad "):
            continue
        link = a.query_selector("a[href*='/status/']")
        href = link.get_attribute("href") if link else ""
        m = re.search(r"/status/(\d+)", href or "")
        sid = m.group(1) if m else None
        if not sid:
            continue
        mh = re.search(r"@(\w+)", t)
        h = mh.group(1) if mh else "?"
        if h.lower() == C.ACCOUNT.lower():
            continue
        verified = a.query_selector("[data-testid='icon-verified']") is not None
        rows.append({"status_id": sid, "handle": h, "text": t, "verified": verified})
    return rows

# ---------------- reply interaction ----------------
def _type_len(box):
    try:
        return box.evaluate("e => (e.textContent || e.innerText || '').length")
    except Exception:
        return -1

def _paste_text(pg, text):
    # clipboard API (https context) lalu fallback execCommand
    try:
        pg.evaluate("(t) => { try { navigator.clipboard.writeText(t); } catch(e){} }", text)
    except Exception:
        pass
    try:
        pg.evaluate("""(t) => {
            const ta = document.createElement('textarea');
            ta.value = t; ta.style.position='fixed'; ta.style.opacity='0';
            document.body.appendChild(ta); ta.focus(); ta.select();
            try { document.execCommand('copy'); } catch(e){}
            document.body.removeChild(ta);
        }""", text)
    except Exception:
        pass

def open_modal(pg, status_id):
    """Buka modal reply by STATUS_ID (bukan has-text @h yg gampang false-positive)."""
    try:
        try:
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(400)
        except Exception:
            pass
        loc = None
        for _ in range(25):
            l = pg.locator(f"article:has(a[href*='/status/{status_id}'])").first
            if l.count() and l.is_visible():
                loc = l
                break
            pg.mouse.wheel(0, 600)
            pg.wait_for_timeout(300)
        if loc is None:
            print(f"[open_modal] status {status_id} gak ada di viewport", flush=True)
            return False
        # LIKE dulu
        try:
            lb = loc.locator("[data-testid='like']").first
            if lb.count() and "liked" not in (lb.get_attribute("aria-label") or "").lower():
                lb.click()
        except Exception as e:
            print(f"[like] err {status_id}: {e}", flush=True)
        # klik reply
        btn = loc.locator("[data-testid='reply']").first
        if not btn.count():
            btn = loc.locator("[role='button'][aria-label='Reply']").first
        if not btn.count():
            print(f"[open_modal] gak ada tombol reply {status_id}", flush=True)
            return False
        try:
            btn.click(force=True, timeout=8000)
        except Exception as e:
            print(f"[open_modal] klik reply gagal {status_id}: {e}", flush=True)
            try:
                pg.keyboard.press("Escape")
            except Exception:
                pass
            return False
        box = pg.locator("[data-testid='tweetTextarea_0']").first
        try:
            box.wait_for(state="visible", timeout=8000)
        except Exception:
            try:
                pg.keyboard.press("Escape")
            except Exception:
                pass
            return False
        return True
    except Exception as e:
        print(f"[open_modal] err {status_id}: {e}", flush=True)
        try:
            pg.keyboard.press("Escape")
        except Exception:
            pass
        return False

def type_and_send(pg, reply):
    """Paste via clipboard + Ctrl+V (trigger React state). Validasi ketat.
    Return True / False / 'LIMITED'."""
    try:
        box = pg.locator("[data-testid='tweetTextarea_0']").first
        box.click(force=True)
        _paste_text(pg, reply)
        pg.wait_for_timeout(600)
        typed = _type_len(box)
        send = pg.locator("[data-testid='tweetButton']").first
        for _ in range(10):
            try:
                if send.is_enabled():
                    break
            except Exception:
                pass
            try:
                box.focus()
                pg.keyboard.type(" ", delay=20)
                pg.keyboard.press("Backspace")
            except Exception:
                pass
            pg.wait_for_timeout(300)
        if typed < 3:
            # paste gagal -> fallback ketik langsung
            try:
                box.focus()
                pg.keyboard.type(reply, delay=25)
            except Exception:
                pass
            typed = _type_len(box)
        if typed < 3:
            print(f"[type_and_send] teks gak masuk (typed={typed})", flush=True)
            return False
        try:
            send.click(force=True, timeout=5000)
        except Exception:
            try:
                send.evaluate("e => e.click()")
            except Exception:
                pass
        try:
            pg.keyboard.press("Control+Enter")
        except Exception:
            pass
        pg.wait_for_timeout(3500)
        res = _check_result(pg)
        try:
            pg.keyboard.press("Escape")
        except Exception:
            pass
        return res
    except Exception as e:
        print(f"[type_and_send] err: {e}", flush=True)
        try:
            pg.keyboard.press("Escape")
        except Exception:
            pass
        return False

def _check_result(pg):
    try:
        toasts = [e.inner_text() or "" for e in pg.locator("[data-testid='toast']").all()]
    except Exception:
        toasts = []
    joined = " ".join(toasts).lower()
    if "sent" in joined or "your post was sent" in joined:
        return True
    if any(k in joined for k in ["limit", "try again", "something went wrong", "please try"]):
        return "LIMITED"
    composer_gone = pg.locator("[data-testid='tweetTextarea_0']").count() == 0
    if composer_gone:
        return True
    return False

# ---------------- do replies ----------------
def do_replies(pg, cands, replied):
    sent = failed = skipped = 0
    limited = False
    for c in cands:
        if sent + failed >= C.MAX_PER_RUN:
            break
        if not open_modal(pg, c["status_id"]):
            failed += 1
            continue
        reply, skip = persona.decide_reply(c["text"])
        if skip or not reply:
            skipped += 1
            try:
                pg.keyboard.press("Escape")
            except Exception:
                pass
            continue
        res = type_and_send(pg, reply)
        if res == "LIMITED":
            notify("[Bot] KENA LIMIT X - pause sementara (jangan spam klik).")
            limited = True
            failed += 1
            break
        if res:
            replied[c["status_id"]] = time.time()
            save_replied(replied)
            notify(f"[Bot] Reply @{c['handle']}: {reply}")
            sent += 1
        else:
            failed += 1
    return sent, failed, skipped, limited

def do_mentions(pg, replied):
    sent = failed = skipped = 0
    mp = None
    try:
        mp = pg.context.new_page()
        mp.goto("https://x.com/notifications/mentions", wait_until="domcontentloaded", timeout=30000)
        mp.wait_for_timeout(3500)
        for _ in range(6):
            mp.mouse.wheel(0, 1200)
            mp.wait_for_timeout(500)
        for a in mp.query_selector_all("article"):
            if sent + failed >= C.MAX_PER_RUN:
                break
            try:
                t = a.inner_text()
            except Exception:
                continue
            if "iklan" in t.lower() or t.lower().startswith("ad "):
                continue
            link = a.query_selector("a[href*='/status/']")
            href = link.get_attribute("href") if link else ""
            m = re.search(r"/status/(\d+)", href or "")
            sid = m.group(1) if m else None
            if not sid:
                continue
            mh = re.search(r"@(\w+)", t)
            h = mh.group(1) if mh else "?"
            if h.lower() == C.ACCOUNT.lower():
                continue
            if sid in replied:
                continue
            if not open_modal(mp, sid):
                failed += 1
                continue
            reply, skip = persona.decide_reply(t)
            if skip or not reply:
                skipped += 1
                try:
                    mp.keyboard.press("Escape")
                except Exception:
                    pass
                continue
            res = type_and_send(mp, reply)
            if res == "LIMITED":
                notify("[Bot] KENA LIMIT X - pause (mention).")
                failed += 1
                break
            if res:
                replied[sid] = time.time()
                save_replied(replied)
                notify(f"[Bot] Reply mention @{h}: {reply}")
                sent += 1
            else:
                failed += 1
    except Exception as e:
        print(f"[mentions] err: {e}", flush=True)
    finally:
        if mp:
            try:
                mp.close()
            except Exception:
                pass
    return sent, failed, skipped

# ---------------- report ----------------
def report(scan_n, ver_n, sent, failed, skipped, limited):
    if limited:
        msg = f"[Bot] LIMIT X aktif - pause. (scan={scan_n} verified={ver_n})"
    elif sent == 0 and failed == 0:
        msg = f"[Bot] scan={scan_n} verified={ver_n} | gak ada target layak (skip/dedup). Gak kirim apa-apa."
    else:
        msg = f"[Bot] scan={scan_n} verified={ver_n} sent={sent} gagal={failed} skip={skipped}"
    notify(msg)

# ---------------- self-heal cleanup ----------------
def run_cleanup():
    removed = 0
    paths = list(glob.glob(os.path.join(TEMP, "hermes-verify-*")))
    pycf = os.path.join(BASE, "__pycache__")
    if os.path.isdir(pycf):
        paths.append(pycf)
    paths += [os.path.join(BASE, f) for f in os.listdir(BASE) if f.endswith(".log")]
    for t in paths:
        try:
            if os.path.isdir(t):
                shutil.rmtree(t)
            else:
                os.remove(t)
            removed += 1
        except Exception:
            pass
    return removed

# ---------------- main ----------------
def main():
    print("[run_bot] START", flush=True)
    d = load(LEARN, {"last_session_notify": 0, "experiments": []})
    replied = load(REPLIED, {})

    # 1. CDP hidup?
    if not cdp_alive():
        print("[run_bot] CDP mati -> relaunch", flush=True)
        if not launch_bot():
            notify("[Bot] Chrome bot mati & gagal relaunch. Jalankan launch_bot_visible.py manual.")
            return

    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(C.CDP)
        ctx = b.contexts[0]
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        if not on_home(pg):
            try:
                pg.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                print("[run_bot] goto home err:", e, flush=True)
        if not wait_articles(pg):
            if session_expired(pg):
                now = time.time()
                if now - d.get("last_session_notify", 0) > 6 * 3600:
                    notify("[Bot] SESSION EXPIRED - login manual di profil bot "
                           "(jalankan launch_bot_visible.py lalu login). Bot pause.")
                    d["last_session_notify"] = now
                    save(LEARN, d)
                print("[run_bot] SESSION EXPIRED", flush=True)
                return
        if session_expired(pg):
            now = time.time()
            if now - d.get("last_session_notify", 0) > 6 * 3600:
                notify("[Bot] SESSION EXPIRED - login manual di profil bot.")
                d["last_session_notify"] = now
                save(LEARN, d)
            return

        rows = scan_home(pg)
        print(f"[run_bot] scanned {len(rows)}", flush=True)
        cands = [r for r in rows if r["verified"]]
        cands = [c for c in cands if c["status_id"] not in replied]
        print(f"[run_bot] verified+dopen {len(cands)}", flush=True)

        sent = failed = skipped = 0
        limited = False
        if C.acquire_lock():
            try:
                s, f, sk, lim = do_replies(pg, cands, replied)
                sent, failed, skipped, limited = s, f, sk, lim
                if not limited:
                    ms, mf, msk = do_mentions(pg, replied)
                    sent += ms
                    failed += mf
                    skipped += msk
            finally:
                C.release_lock()
        else:
            print("[run_bot] lock dipegang -> skip (anti dobel)", flush=True)

        report(len(rows), len(cands), sent, failed, skipped, limited)
        # self-heal
        run_cleanup()
        save(LEARN, d)
        print(f"[run_bot] scan={len(rows)} sent={sent} failed={failed} skip={skipped} limited={limited}", flush=True)

if __name__ == "__main__":
    main()
