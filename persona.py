#!/usr/bin/env python3
"""persona.py v9 - Otak reply (GROK/Hermes) dengan ENFORCE "harga mati".

Perubahan penting dari v8:
- Grok WAJIB balik JSON: {"reply": "...", "skip": true/false}
- Kalau skip / reply kosong -> bot TIDAK reply (harga mati dijalankan sbg mekanisme).
- Grok error total -> SKIP (gak ada fallback generic yg dipaksa kirim).
- Pre-filter hemat Grok: tweet sampah (terlalu pendek / translation note / entity-only)
  gak usah panggil Grok.
"""
import os
import re
import json
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SYSTEM_PROMPT = """Kamu adalah Ji, user X (Twitter) Gen Z Indonesia, santai, cerdas, kadang konyol.
Tugas: balas tweet orang DENGAN pemahaman konteks yang benar.

ATURAN HARGA MATI:
- BALAS HANYA kalau kamu BENAR-BENAR paham konteks tweet & bisa kasih balasan yang selaras, bukan template.
- Kalau tweet spam, terlalu pendek tanpa konteks, cuma mention kosong, atau kamu ragu konteksnya -> WAJIB skip.
- JANGAN pernah balas teks generic/cringe ("gw setuju sih", "serius lo?", dll) yang gak nyambung.
- Bahasa IKUTI tweet asli (Indo -> Indo, English -> English).
- Max 150 karakter. NO emoji. Typo alami (lo/gw/bgt/yg) tapi gak berlebihan.

OUTPUT WAJIB JSON saja, tanpa penjelasan:
{"reply": "teks balasan", "skip": false}
atau kalau kamu skip:
{"reply": "", "skip": true, "reason": "alasan singkat"}
"""

PROVIDER = "xai-oauth"
MODEL = "grok-4.3"

# ---------- pre-filter (hemat Grok call) ----------
def classify_tweet_type(text):
    t = text.lower().strip()
    if t.startswith("translated from") or t.startswith("translate"):
        return "translation_note"
    if len(t.split()) <= 3 and not any(c in t for c in ["?", "!", "."]):
        return "entity_only"
    if len(t) < 15:
        return "too_short"
    return "ok"

def pre_filter(text):
    """True kalau layak diproses Grok. False -> skip tanpa panggil Grok."""
    return classify_tweet_type(text) == "ok"

# ---------- otak Grok ----------
def _extract_json(out):
    try:
        s = out.strip()
        # buang markdown fence kalau ada
        if "```" in s:
            s = re.sub(r"```(?:json)?", "", s)
        start = s.find("{")
        end = s.rfind("}")
        if start == -1 or end == -1:
            return None
        return json.loads(s[start:end + 1])
    except Exception:
        return None

def get_ai_reply(text):
    """Return (reply_text, skip_bool). skip=True -> jangan reply."""
    prompt = f"{SYSTEM_PROMPT}\n\nTWEET:\n\"{text}\"\n\nJSON:"
    try:
        result = subprocess.run(
            ["hermes", "chat", "-q", prompt, "-Q", "--provider", PROVIDER, "-m", MODEL],
            capture_output=True, text=True, timeout=60, check=True,
        )
        out = result.stdout.strip()
        data = _extract_json(out)
        if data is None:
            return ("", True)   # parse gagal -> skip (harga mati)
        skip = bool(data.get("skip"))
        reply = (data.get("reply") or "").strip()
        if skip or not reply:
            return ("", True)
        # potong aman di batas kata
        if len(reply) > 150:
            reply = reply[:148].rsplit(" ", 1)[0]
        return (reply, False)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return ("", True)   # Grok error -> SKIP, gak ada fallback generic dipaksa

def decide_reply(text):
    """Entry point. Return (reply, skip). Pre-filter dl, baru Grok."""
    if not pre_filter(text):
        return ("", True)
    return get_ai_reply(text)
