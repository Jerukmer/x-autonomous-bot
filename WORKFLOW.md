# WORKFLOW BOT X @penepian — DOKUMENTASI LENGKAP

> Dibuat 2026-07-16. Sumber kebenaran: `C:\Users\EMIS-07\x_bot\`.
> Otak reply = GROK/Hermes (bukan LLM luar). Persona = Ji (Gen Z, no emoji).

## 1. ARSITEKTUR (CDP-attach, 1 Chrome)
```
Chrome bot_profile2 (headless, --user-data-dir non-default, port 9223)
   ▲ attach via connect_over_cdp("http://localhost:9223") — gak launch instance baru
   │
   ├─ PIPELINE A: extract_mentions.py  → x.com/notifications/mentions
   ├─ PIPELINE B: extract_priority.py  → search from:@akun (38 akun Ji ikuti, batch 8/run)
   ├─ PIPELINE C: extract_fyp.py       → search from:@akun_besar (15 akun)
   ├─ PIPELINE D: extract_home.py      → x.com/home (tweet random beranda)
   ├─ check_threads.py  → lanjutin percakapan (balas balikan)
   ├─ post_replies.py   → kirim reply/komen (CDP, 1 page reuse)
   ├─ watchdog_loop.py  → jaga Chrome + zombie-killer (>12 procs → restart)
   ├─ x_session_watchdog.py → cek session expired → lapor channel
   ├─ agent_learn.py    → 🤖 agen belajar (preferensi + eksperimen + cleanup)
   └─ cleanup.py        → buang sisa percobaan (ram-safe)
```

## 2. FILE INTI (`x_bot/`)
| File | Fungsi |
|------|--------|
| `bot_config.py` | 1 config terpusat (PROFILE2, CDP, TG, CONFIG, STATE, rate) |
| `launch_bot.py` | nyalain Chrome bot_profile2 headless + port 9223 |
| `login_x.py` | login otomatis @penepian (PATH C, berhenti kalau X limit) |
| `extract_mentions/priority/fyp/home.py` | 4 pipeline baca tweet |
| `extract_following.py` | util (X blokir /following di headless → gagal, ref aja) |
| `post_replies.py` | kirim reply (CDP, reuse 1 page) |
| `check_threads.py` | lanjutin percakapan |
| `watchdog_loop.py` | jaga Chrome + zombie-killer (PowerShell, bukan wmic) |
| `x_session_watchdog.py` | cek session expired |
| `agent_learn.py` | 🤖 agen belajar mandiri |
| `cleanup.py` | hapus sisa percobaan (aman) |
| `config/priority_accounts.json` | 38 akun Ji ikuti |
| `config/fyp_accounts.json` | 15 akun besar |
| `state/*.json` | dedupe + cursor + learn_log (gak di-commit) |

## 3. OTAK & PERSONA
- **Brain**: grok/Hermes (agent sendiri nulis reply saat cron fire). Bukan OpenRouter.
- **Persona Ji**: Gen Z, lonely/warm, NO emoji, on-topic, match bahasa tweet, ~200 char.
- **Rate**: max 2/run, 30/jam, cooldown 25s, dedupe via state/*.json.

## 4. LAPORAN
- Semua aktivitas → Telegram channel `-1003321472507` (t.me/c/3321472507/2197).
- Learning Agent lapor tiap 30 mnt ke channel yang sama.

## 5. 🤖 AUTONOMOUS LEARNING AGENT (baru, 2026-07-16)
Ji: "bot dikelola agen AI yang terus belajar, eksperimen mandiri banyak percobaan,
tapi RAM-safe & file percobaan otomatis dibuang."

- `agent_learn.py` simpan preferensi Ji + riwayat eksperimen ke `state/learn_log.json`.
  Tiap eksperimen gagal → dicatat, gak diulang (baca pitfall).
- `cleanup.py` jalan otomatis tiap 6 jam: hapus `*.bak`, `*.old`, `__pycache__`,
  `hermes-verify-*` temp, `*.log`. GAK sentuh script inti/config/state dedupe.
- Cron `b9ae4087b81e` (`*/30`) jalanin agent_learn --report → lapor channel.
- **Aturan agen (tanam di otak)**: jangan ulangi kesalahan. Eksperimen baru HARUS
  RAM-safe (1 Chrome) & beresin sampahnya sendiri. Gak pernah Kill Chrome Ji /
  copy cookie / paksa visible window.

## 6. ANTI-BAN & KESELAMATAN
- 1 Chrome headless (CDP-attach) → X gak logout (1 fingerprint).
- Zombie-killer: chrome profil bot >12 procs → kill + relaunch 1 headless.
- Jangan `Get-Process chrome | Kill` (bunuh bot + Chrome Ji).
- X "temporarily limited" = cooldown HARD, gak usah retry (tunggu jam-an).

## 7. BLOKER SAAT INI
- ❌ X blokir login @penepian (sejak ~2 jam lalu, "temporarily limited").
- ✅ Chrome bot_profile2 headless + port 9223 jalan (RAM ~884MB).
- ❌ Session expired (belum login karena blokir).
- Bot baru jalan penuh setelah blokir lewat (Ji login manual via NoPort VBS, atau
  login_x.py sekali setelah cooldown).

## 8. CRON STATUS
| Job | Schedule | Deliver |
|-----|----------|---------|
| X @penepian Learning Agent | `*/30` | channel -1003321472507 |
| (4 pipeline + watchdog) | DIHAPUS | — (Ji mau tata dari awal) |

## 9. CARA JALANKAN (manual)
```bash
cd C:\Users\EMIS-07\x_bot
export PATH="/c/Users/EMIS-07/AppData/Local/hermes/bin:$PATH"
. .venv/Scripts/activate
python launch_bot.py          # nyalain Chrome bot (sekali)
# tunggu blokir lewat, lalu:
python login_x.py              # login 1x (berhenti kalau X limit)
python extract_home.py && ...  # pipeline (cron yg dihidupkan lagi nanti)
```
