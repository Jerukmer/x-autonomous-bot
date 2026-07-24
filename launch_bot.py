#!/usr/bin/env python3
"""launch_bot.py - Chrome bot VISIBLE di port 9242 (TERPISAH dari Chrome Ji @9223).

Keamanan:
- Cek port 9242 dulu. Kalau udah nyala -> gak buka instance baru.
- Kalau port 9242 KEBETULAN dipakai proses lain -> STOP + bilang (gak bunuh, gak nekat).
- Cari orphan chrome pakai PROFILE tanpa port -> kill itu aja (bukan Chrome Ji).
- GAK PERNAH sentuh Chrome Ji (profile default / port 9223).
"""
import subprocess
import os
import sys
import time
import urllib.request

import bot_config as C

URL = "https://x.com/home"
CDP_VER = f"http://127.0.0.1:{C.CDP_PORT}/json/version"

def port_alive():
    try:
        with urllib.request.urlopen(CDP_VER, timeout=3) as r:
            return r.status == 200
    except Exception:
        return False

def port_owner_is_ji():
    """True kalau port CDP_PORT dipakai oleh profil SELAIN bot (misal Chrome Ji)."""
    try:
        out = subprocess.run(
            ["wmic", "process", "where", "name='chrome.exe'", "get", "processid,commandline"],
            capture_output=True, text=True, timeout=15,
        ).stdout
        for line in out.splitlines():
            if f"remote-debugging-port={C.CDP_PORT}" in line:
                if C.PROFILE.lower() not in line.lower():
                    return True
    except Exception:
        pass
    return False

if __name__ == "__main__":
    if port_alive():
        print(f"[launch] port {C.CDP_PORT} SUDAH nyala -> gak buka instance baru")
        sys.exit(0)

    if port_owner_is_ji():
        print(f"[launch] PORT {C.CDP_PORT} KEBETULAN dipakai proses lain (bukan profil bot). "
              f"STOP. Ganti X_CDP_PORT atau beresin dulu. JANGAN bunuh Chrome Ji.")
        sys.exit(2)

    # bersihkan orphan chrome bot_profile tanpa port (lock profil)
    try:
        out = subprocess.run(
            ["wmic", "process", "where", "name='chrome.exe'", "get", "processid,commandline"],
            capture_output=True, text=True, timeout=15,
        ).stdout
        for line in out.splitlines():
            if C.PROFILE.lower() in line.lower() and "remote-debugging-port" not in line:
                pid = line.strip().split()[-1]
                if pid.isdigit():
                    subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True)
                    print(f"[launch] kill orphan bot-profile tanpa port (pid {pid})")
                    time.sleep(2)
    except Exception as e:
        print("[launch] cek wmic err (lanjut):", e)

    subprocess.Popen([
        C.CHROME,
        f"--remote-debugging-port={C.CDP_PORT}",
        f"--user-data-dir={C.PROFILE}",
        "--no-first-run",
        "--disable-dev-shm-usage",
        URL,
    ])
    for _ in range(15):
        if port_alive():
            print(f"Chrome bot VISIBLE + port {C.CDP_PORT} nyala (window keliatan)")
            sys.exit(0)
        time.sleep(1)
    print(f"Chrome bot nyala tapi port {C.CDP_PORT} belum respon (cek manual)")
