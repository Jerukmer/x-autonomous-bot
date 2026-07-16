#!/usr/bin/env python3
"""launch_bot_visible.py - Chrome bot VISIBLE + port 9223 (Ji bisa lihat).
JANGAN pakai creationflags DETACHED (0x08000000) -> itu bikin invisible.
Pakai subprocess biasa (inherits Ji's desktop) -> window KELIATAN.
"""
import subprocess, os, time
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFILE = r"C:\Users\EMIS-07\bot_profile4"
URL = "https://x.com/home"
subprocess.Popen([
    CHROME,
    "--remote-debugging-port=9223",
    "--user-data-dir=" + PROFILE,
    "--no-first-run",
    "--disable-dev-shm-usage",
    URL,
])
print("Chrome bot VISIBLE + port 9223 nyala (window harusnya keliatan)")
