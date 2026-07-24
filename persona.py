#!/usr/bin/env python3
"""persona.py v11 - Otak reply (GROK/Hermes), topic-aware.

Dua mode:
- UMUM: Ji Gen Z, skip kalau gak paham konteks (harga mati).
- POLITIK ID: Ji Gen Z, KRITIS + SATIRE tajam thd politik Indonesia,
  berbasis konteks & fakta di tweet (bukan template "politik emang kotor"),
  tetap skip kalau gak paham / terlalu berisiko.

Enforce "harga mati": Grok wajib JSON {reply, skip}; skip/gagal -> gak reply.
Validasi pasca-Grok: tolak frasa generic/cringe (topic-aware).
Pre-filter sampah tetap (hemat Grok call).
"""
import os
import re
import json
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROVIDER = "xai-oauth"
MODEL = "grok-4.3"

# ---------- system prompts ----------
SYSTEM_PROMPT_UMUM = """Kamu adalah Ji, user X (Twitter) Gen Z Indonesia, santai, cerdas, kadang konyol.
Tugas: balas tweet orang DENGAN pemahaman konteks yang BENAR-BENAR nyambung.

ATURAN HARGA MATI (wajib):
1. SEBELUM balas, di dalam dirimu RINGKAS dulu: tweet ini ngomongin apa, konteksnya apa.
   Kalau lo gak bisa ringkas konteks dengan yakin -> WAJIB skip.
2. BALAS cuma kalau lo paham & bisa kasih balasan yang selaras (nyambung topik, bukan basa-basi).
3. LARANG KERAS balas template kosong: "iya bgt", "serius lo", "lo tanya apa", "gw setuju sih",
   "wkwk lucu juga", "menarik", "relate banget". Itu cringe -> mending SKIP.
4. Bahasa IKUTI tweet asli (Indo->Indo, English->English).
5. Max 150 karakter. NO emoji. Typo alami (lo/gw/bgt/yg) tapi gak berlebihan.

OUTPUT WAJIB JSON saja:
{"reply": "teks balasan yg nyambung", "skip": false}
atau kalau ragu / gak paham / cuma basa-basi:
{"reply": "", "skip": true, "reason": "alasan singkat"}
"""

SYSTEM_PROMPT_POLITIK = """Kamu adalah Ji, user X (Twitter) Gen Z Indonesia, cerdas, sinis, dan suka satir.
Tugas: balas tweet soal POLITIK INDONESIA dengan cara KRITIS + SATIRE TAJAM.

ATURAN (wajib):
1. SEBELUM balas, RINGKAS konteks: tweet ini soal apa (tokoh/partai/kebijakan/isku yg dibahas).
   Kalau lo gak paham konteks politiknya -> WAJIB skip.
2. SATIRE HARUS NYAMBUNG KONTEKS & BERBASIS FAKTA di tweet. Sindir poin asli yang dibahas,
   jangan template "politik emang kotor" / "wakil rakyat ya gitu". Itu cringe, bukan satire.
3. JANGAN fitnah / bikin klaim bohong soal orang. Sindiran boleh pedas TAPI berakar di
   pernyataan/fakta yang ada di tweet atau yang umum diketahui publik. Hindari fitnah pribadi.
4. Bahasa IKUTI tweet asli (Indo->Indo, English->English).
5. Max 150 karakter. NO emoji. Typo alami (lo/gw/bgt/yg) oke.

OUTPUT WAJIB JSON saja:
{"reply": "sindiran tajam yg nyambung konteks", "skip": false}
atau kalau ragu / gak paham / terlalu berisiko:
{"reply": "", "skip": true, "reason": "alasan singkat"}
"""

# ---------- deteksi topik politik ----------
POLITIK_STRONG = [
    "jokowi", "prabowo", "gibran", "megawati", "sby", "ahy", "anies", "ganjar", "puan",
    "pdip", "gerindra", "golkar", "demokrat", "pks", "nasdem", "pkb", "pan", "ppp",
    "dpr", "mpr", "mk", "kpk", "pilpres", "pilkada", "pemilu", "cawapres", "capres",
    "menteri", "presiden", "wakil presiden", "gubernur", "bupati", "walikota",
    "korupsi", "kkn", "komisi", "fraksi", "partai", "legislatif", "eksekutif",
    "omnibus", "uu ", "uud", "regulasi", "subsidi", "bbm", "ikn", "apbd", "apbn",
    "caleg", "timses", "kampanye", "quick count", "kpu", "bawaslu", "dewannya",
    "paripurna", "reshuffle", "kabinet", "koalisi", "oposisi", "demokrasi",
]
POLITIK_CONTEXT = ["politik", "rakyat", "pemerintah", "negara", "wakil rakyat", "caleg"]

def detect_topic(text):
    t = (text or "").lower()
    for k in POLITIK_STRONG:
        if k in t:
            return "politik_id"
    # butuh konteks: "politik" atau ("indonesia" + kata konteks)
    if "politik" in t:
        return "politik_id"
    if "indonesia" in t and any(w in t for w in POLITIK_CONTEXT):
        return "politik_id"
    return "umum"

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
    return classify_tweet_type(text) == "ok"

# ---------- frasa generic/cringe (topic-aware) ----------
GENERIC_UMUM = [
    "iya bgt", "serius lo", "lo tanya apa", "gw setuju sih", "gw juga mikir gitu",
    "wkwk lucu juga", "menarik", "relate banget", "gw ngerasain bgt", "bener juga ya",
    "gw setuju", "hmm menarik", "gw penasaran juga", "ini relate", "gw juga",
]
GENERIC_POLITIK = [
    "ya udah lah", "biasa aja", "wkwk politik", "hmm menarik", "politik emang gitu",
    "ya gitu deh", "gw pasrah", "nasib", "ya begitulah", "wkwk kocak",
]

def _is_generic(reply, topic):
    r = reply.lower()
    banned = GENERIC_POLITIK if topic == "politik_id" else GENERIC_UMUM
    return any(p in r for p in banned)

# ---------- otak Grok ----------
def _extract_json(out):
    try:
        s = out.strip()
        s = re.sub(r"```(?:json)?", "", s)
        candidates = re.findall(r"\{[^{}]*\}", s)
        for c in candidates:
            try:
                return json.loads(c)
            except Exception:
                continue
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1:
            return json.loads(s[start:end + 1])
    except Exception:
        pass
    return None

def get_ai_reply(text, topic="umum"):
    """Return (reply_text, skip_bool). skip=True -> jangan reply."""
    prompt = (SYSTEM_PROMPT_POLITIK if topic == "politik_id" else SYSTEM_PROMPT_UMUM)
    prompt += f"\n\nTWEET:\n\"{text}\"\n\nJSON:"
    try:
        result = subprocess.run(
            ["hermes", "chat", "-q", prompt, "-Q", "--provider", PROVIDER, "-m", MODEL],
            capture_output=True, text=True, timeout=60, check=True,
        )
        out = result.stdout.strip()
        data = _extract_json(out)
        if data is None:
            return ("", True)
        skip = bool(data.get("skip"))
        reply = (data.get("reply") or "").strip()
        if skip or not reply:
            return ("", True)
        if _is_generic(reply, topic):
            return ("", True)
        if len(reply) > 150:
            reply = reply[:148].rsplit(" ", 1)[0]
        return (reply, False)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return ("", True)

def decide_reply(text):
    """Entry point. Return (reply, skip). Pre-filter -> detect topic -> Grok."""
    if not pre_filter(text):
        return ("", True)
    topic = detect_topic(text)
    return get_ai_reply(text, topic)
