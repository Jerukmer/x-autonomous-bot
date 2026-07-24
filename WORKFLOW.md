# WORKFLOW BOT X - REWRITE v2 (2026-07-24)

Sumber kebenaran: `C:\Users\EMIS-07\x_bot\`. Otak = Grok/Hermes. 1 orchestrator.

## ARSITEKTUR
- 1 Chrome VISIBLE di profil BOT TERPISAH, port **9242** (bukan 9223 = punya Chrome Ji).
- `run_bot.py` = 1 cron tunggal. Gantikan learn_timeline.py + reply_home.py (dihapus).
- `launch_bot.py` = nyalain Chrome bot, aman (cek port, gak bunuh Chrome Ji).
- `persona.py` v9 = Grok JSON-skip (harga mati di-enforce).
- `bot_config.py` = account-agnostic (env X_HANDLE / X_PROFILE / X_CDP_PORT).

## ALUR RUN_BOT (tiap 2 mnt)
1. CDP hidup? Mati -> relaunch launcher; gagal -> notif + exit.
2. Session expired? -> notif Ji login manual (rate-limited 6j) + PAUSE.
3. Scan beranda 1x -> (status_id, handle, text, verified).
4. Filter verified-only + pre-filter sampah.
5. Dedupe by status_id.
6. Lock -> per kandidat: open_modal(status_id) -> Grok -> type_and_send (clipboard paste + validasi).
7. Mention watcher (tab mentions sendiri, ditutup finally).
8. Report JUJUR (sent/failed/skip, atau "gak ada target layak").
9. Self-heal: cleanup junk + simpan learn_log.

## FIX YANG DITERAPKAN (vs v1)
- Port 9242 terisolasi -> gak tabrakan Chrome Ji.
- Kirim: clipboard paste + Ctrl+V (trigger React) + validasi typed_len>=3 + send.enabled + toast "sent".
- Persona: Grok wajib JSON {"reply","skip"}; skip/gagal -> gak reply (gak ada fallback generic).
- Dedupe by status_id (bukan text[:40]).
- 1 orchestrator (gak 2 cron bentrok).
- Lock pid+timestamp; stale 240dtk.
- Report jujur; session-expired guard gak spam.

## BLOKER
- Akun X: @penepian kemungkinan suspended. Butuh akun baru + login manual 1x.
- Setelah akun siap: set X_HANDLE, login di profil bot, cron jalan otomatis.
