"""bot_config.py - config terpusat buat semua script bot X @penepian.
Semua path & setting ada di sini. Script lain import ini, gak hardcode.
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "config")
STATE  = os.path.join(BASE, "state")

CDP    = "http://127.0.0.1:9223"
PROFILE2 = r"C:\Users\EMIS-07\bot_profile4"
CHROME   = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TG     = "telegram:-1003321472507:2197"
HANDLE = "penepian"

RATE_MAX_PER_HOUR = 999999  # rate limit dihapus (perintah Ji)
COOLDOWN = 0

def p_state(name):
    return os.path.join(STATE, name)

# ---- lock file bersama: cegah 2 pipeline reply jalan barengan (anti-dobel/race) ----
import time as _time
LOCK = os.path.join(STATE, "reply.lock")

def acquire_lock(stale=180):
    """True kalau dapet lock. Lock stale (>stale detik, lihat mtime file) dianggap mati -> ambil alih."""
    try:
        if os.path.exists(LOCK):
            age = _time.time() - os.path.getmtime(LOCK)
            if age < stale:
                return False          # masih dipegang pipeline lain
            os.remove(LOCK)           # stale -> buang, ambil alih
        os.makedirs(STATE, exist_ok=True)
        open(LOCK, "w").write(str(_time.time()))
        return True
    except Exception:
        return True

def release_lock():
    try: os.remove(LOCK)
    except Exception: pass

def p_config(name):
    return os.path.join(CONFIG, name)

# path json state (dedupe)
REPLIED = {
    "mention":  p_state("penepian_replied.json"),
    "priority": p_state("penepian_priority_replied.json"),
    "fyp":      p_state("penepian_fyp_replied.json"),
    "home":     p_state("penepian_home_replied.json"),
}
CURSOR = {
    "priority": p_state("penepian_priority_cursor.json"),
    "fyp":      p_state("penepian_fyp_cursor.json"),
    "home":     p_state("penepian_home_cursor.json"),
}
CONFIG_FILES = {
    "priority": p_config("priority_accounts.json"),
    "fyp":      p_config("fyp_accounts.json"),
}
