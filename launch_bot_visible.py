#!/usr/bin/env python3
"""launch_bot_visible.py - Chrome bot VISIBLE + port 9223 (Ji bisa lihat).
JANGAN pakai creationflags DETACHED (0x08000000) -> itu bikin invisible.
Pakai subprocess biasa (inherits Ji's desktop) -> window KELIATAN.

AMAN: cek port 9223 dulu. Kalau udah nyala (instance lama), JANGAN buka
instance ke-2 (bikin profil ke-lock + port gak kedenger -> ECONNREFUSED).
"""
import subprocess, os, sys, time, urllib.request

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFILE = r"C:\Users\EMIS-07\bot_profile4"
URL = "https://x.com/home"
CDP = "http://127.0.0.1:9223/json/version"

def port_alive():
    try:
        with urllib.request.urlopen(CDP, timeout=3) as r:
            return r.status == 200
    except Exception:
        return False

if port_alive():
    print("[launch] port 9223 SUDAH nyala -> gak buka instance baru (hindari lock profil)")
    sys.exit(0)

# pastiin gak ada chrome profile4 nyangkut tanpa port
try:
    out = subprocess.run(
        ["wmic", "process", "where", "name='chrome.exe'", "get", "processid,commandline"],
        capture_output=True, text=True, timeout=15
    ).stdout
    for line in out.splitlines():
        if "bot_profile4" in line and "remote-debugging-port" not in line:
            # ada chrome pakai bot_profile4 tapi gak buka port -> lock. Kill itu aja.
            pid = line.strip().split()[-1]
            if pid.isdigit():
                subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True)
                print(f"[launch] kill chrome bot_profile4 tanpa port (pid {pid})")
                time.sleep(2)
except Exception as e:
    print("[launch] cek wmic err (lanjut):", e)

subprocess.Popen([
    CHROME,
    "--remote-debugging-port=9223",
    "--user-data-dir=" + PROFILE,
    "--no-first-run",
    "--disable-dev-shm-usage",
    URL,
])
# tunggu port nyala
for _ in range(10):
    if port_alive():
        print("Chrome bot VISIBLE + port 9223 nyala (window keliatan)")
        sys.exit(0)
    time.sleep(1)
print("Chrome bot nyala tapi port 9223 belum respon (cek manual)")
