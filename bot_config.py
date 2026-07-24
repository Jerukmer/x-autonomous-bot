"""bot_config.py - config terpusat, ACCOUNT-AGNOSTIC.
Semua setting ada di sini. Gak hardcode handle/profile di script lain.
Override lewat env: X_HANDLE, X_PROFILE, X_CDP_PORT.
"""
import os
import time as _time

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "config")
STATE = os.path.join(BASE, "state")

# === AKUN (ganti tanpa edit kode: set env X_HANDLE) ===
ACCOUNT = os.environ.get("X_HANDLE", "penepian")        # handle akun bot (ganti ke akun baru)
PROFILE = os.environ.get("X_PROFILE", r"C:\Users\EMIS-07\bot_profile5")  # profil Chrome bot (terpisah)
CDP_PORT = int(os.environ.get("X_CDP_PORT", "9242"))     # port KHUSUS bot, jangan 9223 (punya Chrome Ji)
CDP = f"http://127.0.0.1:{CDP_PORT}"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

TG = "telegram:-1003321472507:2197"   # channel wajib lapor

# Rate: dedupe + cap per-run yang jaga. Batasi per run biar durasi run pendek
# (cegah lock staleness + kurangi risiko ban). Bukan "spam sebanyak mungkin".
RATE_MAX_PER_HOUR = 999999
COOLDOWN = 0
MAX_PER_RUN = 5                        # maks reply per 1 run (bound durasi)

def p_state(n):
    return os.path.join(STATE, n)

def p_config(n):
    return os.path.join(CONFIG, n)

REPLIED_FILE = p_state("replied.json")   # dedupe global, key = status_id
LEARN_FILE = p_state("learn_log.json")
LOCK = p_state("reply.lock")

# ---- lock file: cegah 2 run reply barengan (anti dobel/kirim ganda) ----
def acquire_lock(stale=240, run_id="x"):
    """True kalau dapet lock. Lock stale (>stale dtk) = run mati -> ambil alih."""
    try:
        if os.path.exists(LOCK):
            age = _time.time() - os.path.getmtime(LOCK)
            if age < stale:
                return False
            os.remove(LOCK)
        os.makedirs(STATE, exist_ok=True)
        with open(LOCK, "w") as f:
            f.write(f"{run_id}:{_time.time()}")
        return True
    except Exception:
        return True

def release_lock():
    try:
        os.remove(LOCK)
    except Exception:
        pass
