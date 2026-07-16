#!/usr/bin/env python3
"""
persona.py v8 - AI-Driven Reply Engine (Grok sebagai Otak)
Versi Clean, Bug-Free, dan Robust.
"""

import os
import random
import subprocess
import json
import re

# ==========================================
# KONFIGURASI UMUM
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEARNED_PATH = os.path.join(BASE_DIR, "state", "learned_knowledge.json")

TYPOS = {
    "yang": "yg", "untuk": "buat", "dengan": "dgn", "juga": "jg",
    "sudah": "udah", "tidak": "gk", "bukan": "bkn", "karena": "krna",
    "saya": "gw", "kamu": "lo", "mereka": "mrk", "dia": "dy",
    "banget": "bgt", "bisa": "bs", "lagi": "lg", "banyak": "bnyk",
    "sangat": "bgt", "memang": "emang", "tapi": "tp", "daripada": "dr",
    "dari": "dr"
}

SYSTEM_PROMPT = """Kamu adalah user X (Twitter) bernama Ji, orangnya santai ala Gen Z Indonesia, kadang konyol tapi cerdas.
Tugas: balas tweet orang lain dengan gaya:
- Max 150 karakter.
- Pake bahasa gaul Indonesia (lo/gw/bgt/yg/dgn), tapi jangan berlebihan.
- BALAS SESUAI KONTEKS tweet (tunjukkan kamu paham APA yang dibahas, jangan template umum).
- Kalau tweet bahasa Inggris -> balas Inggris. Kalau Indo -> Indo. Ikuti bahasa asli tweet.
- JANGAN pakai emoji sama sekali.
- Typo alami biasa (kayak orang ngetik asli), tapi jangan dipaksa.
- Kalau tweet nggak penting / spam / cuma mention kosong -> balas cuma kata: SKIP (huruf kapital semua, gak usah teks lain).

Cuma keluarkan teks balasannya saja. Jangan kasih penjelasan, jangan kasih tanda kutip."""

GENERAL_FALLBACKS = [
    "ini beneran?", "serius lo?", "gw juga mikir gitu", "wkwk ini lucu juga",
    "hmm menarik", "gw setuju sih", "bener juga ya", "gw ngerasain bgt",
    "ini relate banget", "gw penasaran juga"
]


# ==========================================
# 1. UTILITAS & FILTER CEPAT
# ==========================================
def load_learned_knowledge() -> dict:
    """Memuat data pengetahuan lokal dengan aman."""
    if not os.path.exists(LEARNED_PATH):
        return {"fallback_phrases": {"neg": [], "pos": [], "general": []}}
    try:
        with open(LEARNED_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"fallback_phrases": {"neg": [], "pos": [], "general": []}}

def classify_tweet_type(text: str) -> str:
    """Mengklasifikasikan tipe tweet untuk filter awal."""
    t = text.lower().strip()

    if t.startswith("translated from") or t.startswith("translate"):
        return "translation_note"

    # Cek entitas kosong (pendek dan tanpa tanda baca)
    if len(t.split()) <= 3 and not any(c in t for c in ["?", "!", "."]):
        return "entity_only"

    if "?" in text:
        return "question"
    if any(k in t for k in ["benci", "kesel", "marah", "susah", "mahal", "kecewa"]):
        return "complaint"
    if any(k in t for k in ["bagus", "keren", "mantap", "setuju", "respect"]):
        return "positive_opinion"
    if len(t) < 20:
        return "short_reaction"

    return "general_opinion"

def calculate_context_score(text: str, tweet_type: str) -> int:
    """Menghitung skor kelayakan tweet untuk diproses AI."""
    score = 0
    words = text.lower().split()

    # Skor berdasarkan panjang kata
    if len(words) >= 8: score += 3
    elif len(words) >= 5: score += 2
    elif len(words) >= 3: score += 1

    # Skor berdasarkan tanda baca & kata ganti
    if "?" in text: score += 3
    if any(c in text for c in [".", "!", ","]): score += 1
    if any(w in text.lower() for w in ["menurut", "gw", "lo"]): score += 2

    # Modifikasi berdasarkan tipe tweet
    if tweet_type in ["question", "complaint", "positive_opinion"]:
        score += 3
    elif tweet_type == "general_opinion":
        score += 2
    elif tweet_type in ["entity_only", "translation_note", "short_reaction"]:
        score -= 4

    return max(0, min(10, score))

def analyze(tweet_text: str) -> dict:
    """Menganalisis teks dan mengekstrak metadata penting."""
    t = tweet_text or ""
    tt = classify_tweet_type(t)

    # PERBAIKAN BUG: Menambahkan 'sentiment_post' agar fallback tidak crash
    sentiment = "neutral"
    if tt == "complaint":
        sentiment = "neg"
    elif tt == "positive_opinion":
        sentiment = "pos"

    return {
        "tweet_type": tt,
        "context_score": calculate_context_score(t, tt),
        "sentiment_post": sentiment
    }


# ==========================================
# 2. OTAK AI (GROK via CLI)
# ==========================================
def get_ai_reply(tweet_text: str) -> str:
    """Memanggil Grok via CLI Hermes dengan aman."""
    prompt = f"{SYSTEM_PROMPT}\n\nTWEET: \"{tweet_text}\"\n\nBalasan:"

    try:
        result = subprocess.run(
            ["hermes", "chat", "-q", prompt, "-Q", "--provider", "xai-oauth", "-m", "grok-4.3"],
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )
        out = result.stdout.strip()

        # Bersihkan metadata session dari CLI
        lines = [ln for ln in out.splitlines() if not ln.startswith("session_id:")]
        reply = " ".join(lines).strip().strip('"').strip("'")

        if "SKIP" in reply.upper():
            return ""
        return reply

    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return ""


# ==========================================
# 3. HUMANIZE & FALLBACK
# ==========================================
def _typo(text: str) -> str:
    """Memberikan typo natural tanpa merusak tanda baca (Menggunakan Regex)."""
    out = []
    for word in text.split():
        match = re.match(r"^(\W*)([\w\-]+)(\W*)$", word)
        if match:
            prefix, core, suffix = match.groups()
            core_lower = core.lower()

            if core_lower in TYPOS and random.random() < 0.30:
                out.append(f"{prefix}{TYPOS[core_lower]}{suffix}")
            else:
                out.append(word)
        else:
            out.append(word)

    return " ".join(out)

def _build_fallback(tweet_text: str, analysis: dict) -> str:
    """Logika aman jika AI gagal merespons."""
    if analysis["sentiment_post"] == "neg" or analysis["tweet_type"] == "complaint":
        return random.choice(["gw ngerasain bgt itu", "iya sih, susah juga ya", "wkwk relate banget"])

    if analysis["tweet_type"] == "question":
        return random.choice(["serius lo tanya itu?", "gw juga penasaran sih"])

    return random.choice(GENERAL_FALLBACKS)


# ==========================================
# 4. FUNGSI UTAMA (ENTRY POINT)
# ==========================================
def gen_reply(tweet_text: str) -> str:
    """Fungsi orkestrator untuk memproses tweet dan mengembalikan balasan."""
    t = (tweet_text or "").strip()
    if not t:
        return ""

    analysis = analyze(t)

    # 1. Filter Cepat (Tolak sampah)
    if analysis["tweet_type"] in ["translation_note", "entity_only"]:
        return ""
    if analysis["context_score"] < 5:
        return ""

    # 2. Otak AI
    reply = get_ai_reply(t)

    # 3. Fallback jika AI error
    if not reply:
        reply = _build_fallback(t, analysis)

    if not reply:
        return ""

    # 4. Humanize (Sentuhan Personal & Pemotongan aman)
    final_reply = _typo(reply)

    if len(final_reply) > 150:
        final_reply = final_reply[:148].rsplit(" ", 1)[0]

    return final_reply
