#!/usr/bin/env python3
"""
x_session_watchdog.py — cek session X @penepian tiap run (lewat CDP port 9223).
Kalau session EXPIRED (redirect login), LAPOR Telegram + restart Chrome bot.
Ini jawaban atas keluhan Ji: "gampang logout berulang" -> sekarang ke-detect
& dilaporkan otomatis, plus watchdog restart bot chrome.
"""
import urllib.request, json, time, subprocess, os

CDP = "http://localhost:9223"
PROFILE2 = r"C:\Users\EMIS-07\AppData\Local\hermes-chrome-profile2"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def chrome_alive():
    try:
        json.load(urllib.request.urlopen(f"{CDP}/json/version", timeout=5))
        return True
    except:
        return False

def session_ok():
    """Cek apakah @penepian msh login (buka x.com/home, cari teks khas beranda yg SUDAH login)."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.connect_over_cdp(CDP)
            pg = b.contexts[0].new_page()
            pg.goto("https://x.com/home", wait_until="domcontentloaded", timeout=15000)
            pg.wait_for_timeout(4000)
            t = pg.inner_text("body")[:300].replace("\n", " ")
            pg.close()
            # teks khas beranda YG SUDAH LOGIN
            live_markers = ["Untuk Anda", "Mengikuti", "postingan baru",
                            "Apa yang sedang terjadi", "Home", "Beranda",
                            "Following", "Timeline"]
            return any(m in t for m in live_markers)
    except:
        return False

def restart_chrome_bot():
    subprocess.Popen(
        [CHROME, f"--user-data-dir={PROFILE2}", "--remote-debugging-port=9223",
         "--no-first-run", "--disable-dev-shm-usage", "https://x.com/login"],
        creationflags=0x08000000)  # detached, minimized-ish

def send_telegram(msg):
    try:
        import subprocess
        # tulis ke file dulu, lalu kirim via -f (heredoc gak stabil di cron)
        tmp = r"C:\Users\EMIS-07\x_automation_src\watchdog_msg.txt"
        open(tmp, "w").write(msg)
        subprocess.run(f'hermes send -t telegram -f "{tmp}"', shell=True, timeout=30)
    except:
        pass

if __name__ == "__main__":
    if not chrome_alive():
        send_telegram("[X-BOT] Chrome bot mati. Restart otomatis...")
        restart_chrome_bot()
        print("CHROME_RESTARTED")
    elif not session_ok():
        send_telegram("[X-BOT] SESSION @penepian EXPIRED. Ji harus login ulang di Chrome bot (profil2).")
        print("SESSION_EXPIRED_ALERT")
    else:
        print("SESSION_OK")
