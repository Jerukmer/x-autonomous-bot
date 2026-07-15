#!/usr/bin/env python3
"""
watchdog_loop.py — jaga Chrome bot (profil2, port 9223) tetap nyala 24/7 HEADLESS.
- Restart Chrome bot HEADLESS kalau process mati (reboot/crash) -> session persist
  (cookies di profil2) jadi gak perlu login ulang.
- Cek session X tiap 60s, lapor Telegram kalau EXPIRED (Ji login manual).
- HEADLESS = gak ada window keliatan. Ji bebas tutup semua Chrome visible.
- JANGAN tutup Chrome lain Ji (profile beda).
Dijalankan sebagai background process / startup Windows.
"""
import time, subprocess, urllib.request, json, os

CDP = "http://localhost:9223"
PROFILE2 = r"C:\Users\EMIS-07\AppData\Local\hermes-chrome-profile2"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def alive():
    try:
        json.load(urllib.request.urlopen(CDP + "/json/version", timeout=5))
        return True
    except:
        return False

def session_ok():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.connect_over_cdp(CDP)
            pg = b.contexts[0].new_page()
            pg.goto("https://x.com/home", wait_until="domcontentloaded", timeout=15000)
            pg.wait_for_timeout(4000)
            t = pg.inner_text("body")[:300].replace("\n", " ")
            pg.close()
            return any(m in t for m in ["Untuk Anda", "Mengikuti", "postingan baru",
                                        "Apa yang sedang terjadi", "Home", "Beranda",
                                        "Following", "Timeline"])
    except:
        return False

def kill_zombie_chrome():
    """Kill Chrome bot profil2 kalau procs numpuk (>12 = ada yang gak close bersih).
    Pakai taskkill langung ke PID yg CommandLine contain profil2."""
    try:
        out = subprocess.check_output(
            'wmic process where "name=\'chrome.exe\'" get ProcessId,CommandLine /value',
            shell=True, timeout=20).decode("utf-8", "ignore")
        pids = []
        for block in out.split("\n\n"):
            if "hermes-chrome-profile2" in block:
                for line in block.split("\n"):
                    if line.strip().startswith("ProcessId="):
                        pids.append(line.strip().split("=")[1])
        if len(pids) > 12:
            # kill SEMUA, biarkan restart bikin 1 bersih
            for pid in pids:
                try: subprocess.run(f"taskkill /PID {pid} /F", shell=True, timeout=10,
                                     capture_output=True)
                except: pass
            print(f"[wd] ZOMBIE_KILLED {len(pids)}", flush=True)
    except:
        pass

def restart_chrome():
    """Nyalain Chrome bot HEADLESS (gak ada window) pakai profil2.
    Cookies @penepian persist di disk -> session kebawa, gak perlu login ulang."""
    subprocess.Popen([CHROME, "--headless=new",
                      f"--user-data-dir={PROFILE2}",
                      "--remote-debugging-port=9223", "--no-first-run",
                      "--disable-dev-shm-usage", "--disable-gpu",
                      "https://x.com/home"],
                     creationflags=0x08000000)

def notify(msg):
    try:
        tmp = r"C:\Users\EMIS-07\x_automation_src\watchdog_msg.txt"
        open(tmp, "w").write(msg)
        subprocess.run(f'hermes send -t telegram:-1003321472507 -f "{tmp}"', shell=True, timeout=30)
    except:
        pass

if __name__ == "__main__":
    print("WATCHDOG_LOOP start (HEADLESS mode)", flush=True)
    last_alert = 0
    while True:
        try:
            kill_zombie_chrome()  # bersihin chrome bot yg numpuk (biar PC gak berat)
            if not alive():
                print("[wd] chrome mati -> restart HEADLESS", flush=True)
                restart_chrome()
                notify("[X-BOT] Chrome bot restart otomatis (headless).")
            elif not session_ok():
                now = time.time()
                if now - last_alert > 1800:  # alert max 1x/30m
                    notify("[X-BOT] SESSION @penepian EXPIRED. Ji login ulang di Chrome bot (profil2).")
                    last_alert = now
                print("[wd] session expired", flush=True)
        except Exception as e:
            print("[wd] err:", repr(e)[:100], flush=True)
        time.sleep(60)
