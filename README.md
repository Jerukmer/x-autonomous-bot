# X Autonomous Bot (1 Orchestrator)

Bot X (Twitter) autonomous. 1 file orchestrator (`run_bot.py`) yang handle scan +
like + reply verified + mention watcher + lapor + self-heal. Account-agnostic.

Otak reply = **Hermes/grok** via `hermes chat`. Persona = Ji (Gen Z, no emoji,
skip kalau gak paham konteks = "harga mati").

## Arsitektur

```
Chrome bot (profile TERPISAH, port 9242, VISIBLE)
      |  connect_over_cdp("http://127.0.0.1:9242")  <- gak buka instance baru
      v
run_bot.py  -- 1 cron: scan + like + reply verified + mention + lapor + self-heal
      |
Laporan -> Telegram channel -1003321472507 thread 2197
```

- 1 Chrome, 1 profil bot (terpisah dari Chrome Ji @ port 9223).
- Dedupe by `status_id` (bukan text) -> gak dobel pas X re-render.
- Lock file cegah 2 run reply barengan.
- Kirim terbukti: clipboard paste + validasi, cek toast X "sent".

## Setup

1. Prasyarat: Python 3.11+, Chrome, `pip install playwright`.
2. Set akun (env, gak edit kode):
   - `X_HANDLE` = handle akun bot (misal `penepian` atau akun baru)
   - `X_PROFILE` = path profil bot (misal `C:\Users\EMIS-07\bot_profile5`)
   - `X_CDP_PORT` = 9242 (jangan 9223)
3. Nyalain Chrome bot:
   ```
   python launch_bot.py
   ```
   Lalu LOGIN manual 1x di window bot (X blokir login otomatis).
4. Test:
   ```
   python run_bot.py
   ```
5. Pasang cron (Hermes):
   ```
   hermes cron create --name "X Bot" --schedule "*/2 * * * *" \
     --prompt "JALANKAN python run_bot.py" --deliver telegram:-1003321472507:2197
   ```

## Keamanan

- Profile bot TERPISAH dari Chrome Ji. Launcher gak pernah bunuh Chrome Ji.
- Kalau session expired -> bot notif Ji login manual, lalu PAUSE (gak spin).
- Kalau kena limit X -> bot pause (gak spam klik).
- JANGAN commit cookie / session json.

## Disclaimer

Tool edukasi. Otomatisasi X melanggar ToS X - risiko akun dibanned ditanggung pengguna.
