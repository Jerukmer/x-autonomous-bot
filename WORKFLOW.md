# WORKFLOW BOT X @penepian — DOKUMENTASI LENGKAP

> Dibuat 2026-07-16, update 2026-07-17. Sumber kebenaran: `C:\Users\EMIS-07\x_bot\`.
> Otak reply = GROK/Hermes (bukan LLM luar). Persona = Ji (Gen Z, no emoji).

## 1. ARSITEKTUR (CDP-attach, 1 Chrome VISIBLE)

```
Chrome bot_profile4 (VISIBLE, --user-data-dir non-default, port 9223)
   ▲ attach via connect_over_cdp("http://127.0.0.1:9223") — gak launch instance baru
   │
   ├─ learn_timeline.py  (cron A) → scan beranda + belajar tren + FYP
   │                          + reply VERIFIED (open_modal+type_and_send)
   │                          + MENTION WATCHER (buka tab mentions sendiri, modal-first)
   └─ reply_home.py      (cron B) → komen beranda KURASI (score engagement+niche+FYP)
                                pakai open_modal+type_and_send SAMA (1 otak konsisten)
```

- 1 Chrome, 1 profile (`bot_profile4`), VISIBLE (Ji bisa lihat, gak headless).
- Tiap cron bebas buka tab sendiri, TAPI gak tutup tab cron lain (aturan XXIII).
- Dedupe: 1 file `state/replied.json` global (gak dobel antar pipeline).
- Lock file `state/reply.lock` cegah 2 pipeline reply barengan (anti-race).

## 2. FILE INTI (`x_bot/`)

| File | Fungsi |
|------|--------|
| `bot_config.py` | 1 config terpusat (CDP, PROFILE4, TG, STATE, lock, rate off) |
| `launch_bot_visible.py` | nyalain Chrome bot_profile4 VISIBLE + port 9223 (cek port dulu) |
| `learn_timeline.py` | AI agent terpusat: scan/learn/FYP/reply verified + mention watcher |
| `reply_home.py` | komen beranda kurasi (reuse open_modal+type_and_send dari learn_timeline) |
| `persona.py` v8 | Grok sebagai otak, Python filter/pengirim, Gen Z no-emoji, max 150 char |
| `config/priority_accounts.json` | 38 akun Ji ikuti (contoh di `priority_accounts.example.json`) |
| `config/fyp_accounts.json` | akun besar (contoh di `fyp_accounts.example.json`) |
| `state/*.json` | dedupe + learn_log + threads (GAK di-commit, privat) |

## 3. OTAK & PERSONA

- **Brain**: grok/Hermes via `hermes chat -q ... -Q --provider xai-oauth -m grok-4.3`.
  Bukan OpenRouter. Timeout 60dtk/call.
- **Persona Ji**: Gen Z, lonely/warm, NO emoji, on-topic, match bahasa tweet, ~150 char.
- **Rate**: DIHAPUS (RATE_MAX_PER_HOUR=999999, COOLDOWN=0, MAX_REPLY=9999).
  Dedupe tetap ON. Cron jalan tiap 2 menit (`*/2`).

## 4. LAPORAN

- Semua aktivitas → Telegram channel `-1003321472507` thread `2197`
  (format `telegram:-1003321472507:2197`).
- Learning Agent lapor progres tiap run ke channel yang sama.

## 5. AUTONOMOUS LEARNING AGENT

- `learn_timeline.py` simpan preferensi Ji + riwayat eksperimen ke `state/learn_log.json`.
- `maintenance()` jalan cleanup otomatis (hapus junk, RAM-safe).
- Aturan agen: jangan ulangi kesalahan, RAM-safe (1 Chrome), beresin sampah sendiri.
  GAK pernah kill Chrome Ji / copy cookie / paksa visible window.

## 6. ANTI-BAN & KESELAMATAN

- 1 Chrome VISIBLE (CDP-attach) → X gak logout (1 fingerprint).
- Chrome mati (ECONNREFUSED) → relaunch `launch_bot_visible.py` (cek port dulu,
  jangan buka instance ke-2 yang lock profil).
- X "temporarily limited" = cooldown HARD, gak usah retry (tunggu jam-an).
- JANGAN kill Chrome Ji (user Emis_MHM) — cuma bot_profile4.

## 7. BLOKER / STATUS

- Core reply: modal-first (open_modal → Grok → type_and_send) sudah stabil buka modal
  + masukin teks. Send button kadang ke-intercepts X mask → perlu force/Ctrl+Enter.
- Chrome bot_profile4 VISIBLE + port 9223 (jalan via launch_bot_visible.py).
- Session: login manual Ji di window bot_profile4 (X blokir login otomatis).

## 8. CRON STATUS

| Job | Schedule | Fungsi |
|-----|----------|--------|
| learn_timeline (AI Agent) | `*/2` | scan+learn+FYP+reply verified+mention |
| reply_home (Beranda Komen) | `*/2` | komen beranda kurasi |
| Auto-Login (PAUSED) | `*/15` | login_x kalau gak dibatasi |

## 9. CARA JALANKAN (manual)

```bash
cd C:\Users\EMIS-07\x_bot
export PATH="/c/Users/EMIS-07/AppData/Local/hermes/bin:$PATH"
. .venv/Scripts/activate
python launch_bot_visible.py     # nyalain Chrome bot VISIBLE (cek port 9223 dulu)
# Ji login manual @penepian di window bot_profile4
python learn_timeline.py         # test 1x
python reply_home.py             # test 1x
```
