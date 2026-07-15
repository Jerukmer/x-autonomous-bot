#!/usr/bin/env python3
"""cdp_helper.py — koneksi CDP ke Chrome bot (profil2, port 9223).
Semua script X automation pakai ini supaya TIDAK buka instance headless baru
-> session X tdk expire berulang (fix logout berulang).
Gunakan: from cdp_helper import get_browser, close_browser
"""
from playwright.sync_api import sync_playwright

CDP_URL = "http://localhost:9223"

def get_browser():
    """Return (playwright_obj, browser_cdp, context, page). Page siap dipakai."""
    p = sync_playwright().start()
    b = p.chromium.connect_over_cdp(CDP_URL)
    ctx = b.contexts[0] if b.contexts else b.new_context()
    pg = ctx.new_page()
    return p, b, ctx, pg

def close_browser(p, b, pg=None):
    """TUTUP page aja, JANGAN browser (biar session tetap hidup di Chrome bot)."""
    try:
        if pg: pg.close()
    except: pass
    # JANGAN b.close() / p.stop() — biarkan Chrome bot tetap nyala
