# X Autonomous Bot — @penepian

Bot X (Twitter) autonomous untuk akun **@penepian**. Berjalan 24/7 di background
tanpa window Chrome terlihat (headless), login via browser profile persisten,
dan melaporkan semua aktivitas ke channel Telegram.

Otak reply = **Hermes/grok** (LLM lokal di gateway), bukan API X resmi.
Akun X diakses via **Playwright + Chrome DevTools Protocol (CDP)** pada profile
yang sudah login.

## Fitur

| Pipeline | Jadwal | Fungsi |
|----------|--------|--------|
| **Mention Watcher** | tiap 30 mnt | Auto-reply mention ke @penepian |
| **Priority Watcher** | tiap 30 mnt | Komen di tweet akun yang diikuti @penepian + lanjutkan percakapan |
| **FYP-Famous Komen** | tiap 30 mnt | Komen di tweet akun besar/terkenal (visibility) |
| **Beranda Komen** | tiap 5 mnt | Komen di tweet random di beranda @penepian |
| **Session Watchdog** | tiap 15 mnt | Cek session, lapor & restart kalau mati |

Persona reply = gaya Gen Z Indonesia (no emoji, pendek, kontekstual).

## Arsitektur (tanpa pengecualian)

```
Chrome HEADLESS (profile hermes-chrome-profile2, port 9223)
      |  CDP connect_over_cdp  <- bot NYAMBUNG, gak buka instance baru
      |                          (session X gak expire berulang)
      v
watchdog_loop.py  -- restart otomatis kalau Chrome crash/reboot
                  -- session persist di disk (cookies profile), gak perlu login ulang
      |
Cron A/B/C (30 mnt) + Beranda (5 mnt) + Watchdog (15 mnt)
      |
Laporan -> Telegram channel (deliver=telegram:<chat_id>)
```

Keunggulan: **Chrome terlihat tertutup** (headless), tapi bot tetap jalan.
Kalau Chrome mati/crash, watchdog otomatis nyalakan balik. Reboot PC →
startup VBS nyalakan Chrome headless + watchdog sendiri.

## Setup

### 1. Prasyarat
- Python 3.11+
- Chrome (sudah terinstall)
- `pip install playwright` lalu `playwright install chromium`
- Akun X sudah login di profile Chrome terpisah

### 2. Siapkan profile bot
```bat
chrome.exe --headless=new ^
  --user-data-dir="C:\path\to\hermes-chrome-profile2" ^
  --remote-debugging-port=9223 ^
  --no-first-run --disable-dev-shm-usage --disable-gpu ^
  "https://x.com/home"
```
Login @penepian sekali. Cookies persist di disk.

### 3. Konfigurasi
Edit `CDP`, `PROFILE2`, `CHROME` path di tiap script sesuai environment.

Edit `priority_accounts.json` (akun yang diikuti) & `fyp_accounts.json`
(akun besar) — lihat contoh di folder ini.

Set chat_id Telegram di `deliver` cron / `notify()` watchdog_loop.py.

### 4. Jalankan watchdog
```bat
python watchdog_loop.py
```
Watchdog menjaga Chrome headless tetap hidup + cek session tiap 60 detik.

### 5. Jadwalkan cron (Hermes Gateway)
```bat
hermes cron create --name "X Beranda" --schedule "*/5 * * * *" \
  --prompt "JALANKAN pipeline beranda..." --deliver telegram:-100xxxx
```
Lihat `CRON_PROMPTS.md` untuk prompt lengkap tiap pipeline.

## File

| File | Fungsi |
|------|--------|
| `cdp_helper.py` | Koneksi CDP ke Chrome bot |
| `extract_mentions.py` | Scrape mention @penepian |
| `extract_priority.py` | Scrape tweet akun diikuti (batch round-robin) |
| `extract_fyp.py` | Scrape tweet akun besar |
| `extract_home.py` | Scrape tweet random beranda |
| `extract_following.py` | Scrape daftar Following -> priority_accounts.json |
| `post_replies.py` | Kirim reply/komen via CDP (rate-limit, dedupe, thread) |
| `check_threads.py` | Lanjutkan percakapan (cek balasan pemilik tweet) |
| `watchdog_loop.py` | Jaga Chrome headless + cek session |
| `x_session_watchdog.py` | Cek session (dipanggil cron) |

## Keamanan

- **JANGAN** commit cookie / `Cookies` file / `*.json` berisi session.
- Profile Chrome bot harus terpisah dari Chrome harian (aturan "never disturb").
- Rate-limit: max 2 reply/run, 30/jam, cooldown 25 detik, dedupe via replied.json.

## Disclaimer

Tool ini untuk edukasi. Penggunaan otomatis X melanggar ToS X — risiko akun
dibanned ditanggung pengguna. Gunakan dengan bijak (rate lambat, persona natural).

## Lisensi

MIT — bebas dipakai & dimodifikasi.
