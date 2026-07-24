#!/usr/bin/env python3
"""persona.py v10 - Otak reply (GROK/Hermes) dengan ENFORCE "harga mati" ketat.

Perubahan v10 (dari v9):
- Parse JSON robust: cari objek JSON valid pertama, tahan kurung dlm teks balasan.
- System prompt diperketat: Grok wajib ringkas konteks -> balas selaras, LARANG
  template kosong ("iya bgt", "serius lo", "lo tanya apa", dll).
- Validasi pasca-Grok: kalau reply mengandung frasa generic/cringe -> PAKSA skip.
- Pre-filter sampah tetap (hemat Grok call).
- Grok error total -> SKIP (gak ada fallback generic dipaksa kirim).
"""
import os
import re
import json
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SYSTEM_PROMPT = """Kamu adalah Ji, user X (Twitter) Gen Z Indonesia, santai, cerdas, kadang konyol.
Tugas: balas tweet orang DENGAN pemahaman konteks yang BENAR-BENAR nyambung.

ATURAN HARGA MATI (wajib, gak boleh dilanggar):
1. SEBELUM balas, di dalam dirimu RINGKAS dulu: tweet ini ngomongin apa, konteksnya apa.
   Kalau lo gak bisa ringkas konteks dengan yakin -> WAJIB skip.
2. BALAS cuma kalau lo paham & bisa kasih balasan yang selaras (nyambung topik, bukan basa-basi).
3. LARANG KERAS balas pakai template kosong: "iya bgt", "serius lo", "lo tanya apa",
   "gw setuju sih", "gw juga mikir gitu", "wkwk lucu juga", "menarik", "relate banget".
   Itu cringe & gak nyambung -> mending SKIP.
4. Bahasa IKUTI tweet asli (Indo->Indo, English->English).
5. Max 150 karakter. NO emoji. Typo alami (lo/gw/bgt/yg) tapi gak berlebihan.

OUTPUT WAJIB JSON saja, tanpa penjelasan:
{"reply": "teks balasan yg nyambung", "skip": false}
atau kalau lo ragu / gak paham / cuma basa-basi:
{"reply": "", "skip": true, "reason": "alasan singkat"}
"""

PROVIDER = "xai-oauth"
MODEL = "grok-4.3"

# frasa generic/cringe yang dilarang (harga mati: skip kalau muncul)
GENERIC_PHRASES = [
    "iya bgt", "serius lo", "lo tanya apa", "gw setuju sih", "gw juga mikir gitu",
    "wkwk lucu juga", "menarik", "relate banget", "gw ngerasain bgt", "bener juga ya",
    "gw setuju", "hmm menarik", "gw penasaran juga", "ini relate", "gw juga",
]

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
    """Cari objek JSON valid pertama. Tahan kurung dlm teks balasan."""
    try:
        s = out.strip()
        # buang markdown fence
        s = re.sub(r"```(?:json)?", "", s)
        # cari semua kandidat { ... } terpendek dulu (lebih aman dari kurung dlm teks)
        candidates = re.findall(r"\{[^{}]*\}", s)
        for c in candidates:
            try:
                return json.loads(c)
            except Exception:
                continue
        # fallback: first { to last }
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1:
            return json.loads(s[start:end + 1])
    except Exception:
        pass
    return None

def _is_generic(reply):
    r = reply.lower()
    return any(p in r for p in GENERIC_PHRASES)

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
        # validasi harga mati: tolak frasa generic/cringe
        if _is_generic(reply):
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
