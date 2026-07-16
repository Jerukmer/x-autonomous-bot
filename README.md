# X Autonomous Bot — @penepian

Bot X (Twitter) autonomous untuk akun **@penepian**. Berjalan 24/7 di background
dengan Chrome **VISIBLE** (Ji bisa lihat), login via browser profile persisten,
dan melaporkan semua aktivitas ke channel Telegram.

Otak reply = **Hermes/grok** (LLM lokal di gateway, via `hermes chat`), bukan API X resmi.
Akun X diakses via **Playwright + Chrome DevTools Protocol (CDP)** pada profile
yang sudah login (`bot_profile4`).

## Fitur

| Pipeline | Jadwal | Fungsi |
|----------|--------|--------|
| **AI Agent (learn_timeline)** | tiap 2 mnt | Scan beranda + belajar tren + FYP + reply VERIFIED + MENTION watcher |
| **Beranda Komen (reply_home)** | tiap 2 mnt | Komen beranda KURASI (score engagement + niche + FYP) |

Persona reply = gaya Gen Z Indonesia (no emoji, pendek ~150 char, kontekstual,
match bahasa asli tweet). Semua pipeline pakai 1 otak (`persona.gen_reply`)
biar output konsisten.

## Arsitektur

```
Chrome VISIBLE (profile bot_profile4, port 9223)
      |  CDP connect_over_cdp("http://127.0.0.1:9223")  <- bot NYAMBUNG, gak buka instance baru
      |                                                   (session X gak expire berulang)
      v
learn_timeline.py  -- AI agent: scan + learn + FYP + reply verified + mention
reply_home.py      -- komen beranda kurasi (reuse open_modal+type_and_send)
      |
Laporan -> Telegram channel -1003321472507 thread 2197
```

- 1 Chrome, 1 profile (`bot_profile4`), VISIBLE.
- Dedupe: 1 file `state/replied.json` global (anti-dobel antar pipeline).
- Lock file cegah 2 pipeline reply barengan (anti-race).
- Tiap cron bebas buka tab sendiri, TAPI gak tutup tab cron lain.

## Setup

### 1. Prasyarat
- Python 3.11+
- Chrome (sudah terinstall)
- `pip install playwright` lalu `playwright install chromium`
- Akun X sudah login di profile `bot_profile4`

### 2. Siapkan profile bot (sekali)
```bat
chrome.exe --user-data-dir="C:\Users\EMIS-07\bot_profile4" ^
  --remote-debugging-port=9223 ^
  --no-first-run --disable-dev-shm-usage ^
  "https://x.com/home"
```
Login @penepian sekali. Cookies persist di disk. (Atau pakai `launch_bot_visible.py`.)

### 3. Konfigurasi
Edit `CDP`, `PROFILE2`, `CHROME` path di `bot_config.py` sesuai environment.

Edit `priority_accounts.json` (akun yang diikuti) & `fyp_accounts.json`
(akun besar) — lihat contoh `*.example.json` di folder ini.

Set chat_id Telegram di `bot_config.TG` (`telegram:-1003321472507:2197`).

### 4. Jalankan
```bat
python launch_bot_visible.py   # nyalain Chrome bot VISIBLE (cek port 9223 dulu)
python learn_timeline.py       # test 1x
python reply_home.py           # test 1x
```

### 5. Jadwalkan cron (Hermes Gateway)
```bat
hermes cron create --name "X AI Agent" --schedule "*/2 * * * *" ^
  --prompt "JALANKAN python learn_timeline.py" --deliver telegram:-1003321472507:2197
hermes cron create --name "X Beranda" --schedule "*/2 * * * *" ^
  --prompt "JALANKAN python reply_home.py" --deliver telegram:-1003321472507:2197
```

## File

| File | Fungsi |
|------|--------|
| `bot_config.py` | 1 config terpusat (CDP, profile, TG, lock, rate) |
| `launch_bot_visible.py` | Chrome bot VISIBLE + port 9223 (cek port dulu) |
| `learn_timeline.py` | AI agent: scan/learn/FYP/reply verified + mention watcher |
| `reply_home.py` | Komen beranda kurasi (reuse open_modal+type_and_send) |
| `persona.py` | Grok otak + filter + humanize (Gen Z, no emoji) |

## Keamanan

- **JANGAN** commit cookie / `Cookies` file / `*.json` berisi session.
- Profile Chrome bot harus terpisah dari Chrome harian (aturan "never disturb").
- Dedupe via `state/replied.json` (1 file global).

## Disclaimer

Tool ini untuk edukasi. Penggunaan otomatis X melanggar ToS X — risiko akun
dibanned ditanggung pengguna. Gunakan dengan bijak (rate lambat, persona natural).

## Lisensi

MIT — bebas dipakai & dimodifikasi.
