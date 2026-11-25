"""Tier 2: Boundary Value Analysis (BVA) & corner-case E2E tests covering E1–E8 (>= 5 per feature)."""
import http.server
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from harness import (
    KOK,
    assert_clean_diag,
    assert_clean_nav,
    e2e_test,
    ensure_akis_rows,
    load_json,
)


# ============================================================================
# E1: Navigation & Route Boundaries (5 tests)
# ============================================================================

@e2e_test('E1_T2_01', 2, 'E1', 'Unknown hash route #/olmayan-sayfa falls back cleanly to Bugun')
def test_e1_bva_unknown_route(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/olmayan-sayfa')
    assert_clean_nav(nav)
    st = b.eval("""(() => ({
      h1: document.querySelector('#ana h1')?.textContent.trim() || '',
      hasBugunCur: Boolean(document.querySelector('#anaNav a[href="#/bugun"][aria-current="page"]')),
      rows: document.querySelectorAll('#ana [data-id]').length,
    }))()""")
    assert st['hasBugunCur'], f'Unknown route did not fall back to #/bugun active nav: {st}'
    assert st['h1'] and st['rows'] > 0, f'Unknown route fallback rendered empty Bugün: {st}'


@e2e_test('E1_T2_02', 2, 'E1', 'Turkish-folded and uppercase #/PIRIL and #/p%C4%B1r%C4%B1l resolve to Piril')
def test_e1_bva_piril_turkish_folding(ctx):
    b = ctx.browser
    b.set_desktop()
    for h in ('#/PIRIL', '#/p%C4%B1r%C4%B1l'):
        nav = b.navigate(h)
        assert_clean_nav(nav)
        h1 = b.eval("document.querySelector('#ana h1')?.textContent || ''")
        assert 'Pırıl' in h1, f'Route {h} failed to resolve to Pırıl desk: {h1!r}'


@e2e_test('E1_T2_03', 2, 'E1', 'Deep link #/akis/yz?dil=en pre-applies English filter')
def test_e1_bva_deep_link_dil(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/akis/yz?dil=en')
    assert_clean_nav(nav)
    st = b.eval("""(() => ({
      enPressed: document.querySelector('[data-act="trf"][data-v="en"]')?.getAttribute('aria-pressed'),
      rows: document.querySelectorAll('#ana [data-id]').length,
      empty: Boolean(document.querySelector('#ana .bosluk')),
    }))()""")
    assert st['enPressed'] == 'true', f'Deep link ?dil=en did not activate EN chip: {st}'
    assert st['rows'] > 0 or st['empty'], f'Deep link ?dil=en rendered nothing: {st}'


@e2e_test('E1_T2_04', 2, 'E1', 'Deep link with invalid ?k= shows graceful missing-topic notice in #panel')
def test_e1_bva_invalid_k_deeplink(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/akis/gundem?k=nonexistent_id_999999')
    assert_clean_nav(nav)
    b.wait_for("document.getElementById('panel')?.open")
    b.wait_for("/artık listede yok|bulunamadı|süresi doldu/i.test(document.getElementById('panel')?.textContent || '')", timeout_ms=8000)
    txt = b.eval("document.getElementById('panel')?.textContent || ''")
    assert 'artık listede yok' in txt or 'süresi doldu' in txt, f'Unexpected panel fallback text: {txt}'


@e2e_test('E1_T2_05', 2, 'E1', 'Empty or 404 area data (#/akis/savunma when missing) degrades gracefully')
def test_e1_bva_empty_or_404_area(ctx):
    b = ctx.browser
    b.set_desktop()
    sav_exists = os.path.isfile(os.path.join(KOK, 'site', 'data', 'kume-savunma.json'))
    nav = b.navigate('#/akis/savunma')
    assert_clean_nav(nav, allowed_http_404_suffixes=() if sav_exists else ('/data/kume-savunma.json',))
    st = b.eval("""(() => ({
      rows: document.querySelectorAll('#ana [data-id]').length,
      empty: (document.querySelector('#ana .bosluk')?.textContent || '').trim(),
    }))()""")
    assert st['rows'] > 0 or st['empty'], f'Savunma route crashed or stayed blank: {st}'


# ============================================================================
# E2: Breakpoints, Panel Modality, RTL & Reduced Motion (5 tests)
# ============================================================================

@e2e_test('E2_T2_01', 2, 'E2', 'Breakpoint widths 390, 860, 1100, 1440 have zero horizontal overflow')
def test_e2_bva_breakpoints(ctx):
    b = ctx.browser
    for w, h, mob in ((390, 844, True), (860, 900, False), (1100, 900, False), (1440, 1000, False)):
        b.set_viewport(w, h, mobile=mob)
        for route in ('#/bugun', '#/akis/gundem'):
            nav = b.navigate(route)
            assert_clean_nav(nav)
            lay = b.inspect_layout()
            assert not lay['horizontalOverflow'], f'Overflow at {w}x{h} on {route}: {lay}'


@e2e_test('E2_T2_02', 2, 'E2', 'Panel modality boundary: < 1100px opens modal, >= 1100px opens non-modal side pane')
def test_e2_bva_panel_modality_threshold(ctx):
    b = ctx.browser
    # Just below 1100px (860px) -> modal
    b.set_viewport(860, 900, mobile=False)
    nav = b.navigate('#/akis/gundem')
    assert_clean_nav(nav)
    ensure_akis_rows(b)
    b.click('#ana [data-id] h3 a, #ana [data-id] h2 a')
    b.wait_for("document.getElementById('panel')?.open")
    assert b.eval("document.getElementById('panel').matches(':modal')") is True, 'Expected modal #panel at 860px'

    # At 1100px -> non-modal side pane
    b.set_viewport(1100, 900, mobile=False)
    nav2 = b.navigate('#/akis/gundem')
    assert_clean_nav(nav2)
    ensure_akis_rows(b)
    b.click('#ana [data-id] h3 a, #ana [data-id] h2 a')
    b.wait_for("document.getElementById('panel')?.open")
    assert b.eval("document.getElementById('panel').matches(':modal')") is False, 'Expected non-modal #panel at 1100px'


@e2e_test('E2_T2_03', 2, 'E2', 'RTL Arabic/Hebrew/Persian items enforce dir="auto" or unicode-bidi: isolate without overflow', gate='M3_F12')
def test_e2_bva_rtl_hygiene(ctx):
    b = ctx.browser
    b.set_mobile()
    nav = b.navigate('#/dunya/ar')
    assert_clean_nav(nav)
    lay = b.inspect_layout()
    assert not lay['horizontalOverflow'], f'Horizontal overflow on RTL #/dunya/ar: {lay}'
    rtl = b.inspect_rtl()
    assert rtl['rtlCount'] > 0, 'Expected Arabic/RTL headlines on #/dunya/ar'
    assert rtl['unprotectedCount'] == 0, (
        f"RTL text missing dir='auto' or unicode-bidi:isolate: {rtl['unprotected'][:5]}"
    )


@e2e_test('E2_T2_04', 2, 'E2', 'prefers-reduced-motion: reduce works cleanly across modal/drawer transitions')
def test_e2_bva_reduced_motion(ctx):
    b = ctx.browser
    b.set_mobile()
    nav = b.navigate('#/akis/gundem', reduced_motion=True)
    assert_clean_nav(nav)
    ensure_akis_rows(b)
    assert b.eval("matchMedia('(prefers-reduced-motion: reduce)').matches") is True
    b.click('#ana [data-id] h3 a, #ana [data-id] h2 a')
    b.wait_for("document.getElementById('panel')?.open")
    assert_clean_diag(b)


@e2e_test('E2_T2_05', 2, 'E2', 'Narrow desktop 1200x900 uc-acik reflow keeps #panel non-overlapping without overflow')
def test_e2_bva_narrow_desktop_uc_acik(ctx):
    b = ctx.browser
    b.set_viewport(1200, 900, mobile=False)
    nav = b.navigate('#/akis/gundem')
    assert_clean_nav(nav)
    ensure_akis_rows(b)
    b.click('#ana [data-id] h3 a, #ana [data-id] h2 a')
    b.wait_for("document.getElementById('panel')?.open")
    lay = b.inspect_layout()
    assert not lay['horizontalOverflow'], f'Overflow at 1200px with #panel open: {lay}'
    assert lay['panelOverlapCount'] == 0, f'Panel overlaps #ana at 1200px: {lay["panelOverlaps"]}'


# ============================================================================
# E3: Empty-State Recovery, Search, Storage & XSS Boundaries (6 tests)
# ============================================================================

@e2e_test('E3_T2_01', 2, 'E3', 'Empty filter state provides inline recovery CTAs that restore items', gate='M3_F10')
def test_e3_bva_empty_state_recovery_ctas(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/akis/adana')
    assert_clean_nav(nav)
    # Trigger empty state by selecting 1 saat + En az 3 kaynak (or hiding remaining rows if needed)
    b.eval("""(() => {
      const suz = document.querySelector('[data-act="suzAc"][aria-expanded="false"]');
      if (suz) suz.click();
      const z1 = document.querySelector('[data-act="zaman"][data-v="1"]');
      if (z1) z1.click();
      const cok = document.querySelector('[data-act="cok"]');
      if (cok && cok.getAttribute('aria-pressed') !== 'true') cok.click();
    })()""")
    # If still has items (rare high-volume breaking news), switch to narrowest language or hide visible items
    rows_left = b.eval("document.querySelectorAll('#ana [data-id]').length")
    if rows_left > 0:
        b.eval("""(() => {
          document.querySelectorAll('#ana [data-id]').forEach(el => {
            const btn = el.querySelector('[data-act="gizle"]');
            if (btn) btn.click();
          });
        })()""")
        b.wait_for("document.querySelectorAll('#ana [data-id]').length === 0")

    empty_info = b.eval("""(() => {
      const box = document.querySelector('#ana .bosluk, #ana [role="alert"]');
      const btns = box ? Array.from(box.querySelectorAll('button')) : [];
      return {
        text: box ? box.textContent.trim() : '',
        btnTexts: btns.map(x => x.textContent.trim()),
      };
    })()""")
    assert empty_info['text'], 'Empty state container missing'
    assert empty_info['btnTexts'], (
        f"Empty state dead-end has no inline recovery CTA buttons: {empty_info}"
    )
    # Click recovery CTA (e.g. Tüm zamanlar / 3 gün / Süzgeçleri sıfırla) and ensure items return
    b.click('#ana .bosluk button, #ana [role="alert"] button')
    b.wait_for("document.querySelectorAll('#ana [data-id]').length > 0", timeout_ms=4000)


@e2e_test('E3_T2_02', 2, 'E3', 'Search length boundary: 1 char prompts, 2 chars search, impossible query shows empty')
def test_e3_bva_search_boundaries(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/bugun')
    assert_clean_nav(nav)
    b.click('#araAc')
    b.wait_for("document.getElementById('arama')?.open")
    # 1 char
    b.eval("""(() => {
      const k = document.getElementById('araK');
      k.value = 'a';
      k.dispatchEvent(new Event('input', { bubbles: true }));
    })()""")
    txt1 = b.eval("document.getElementById('araS')?.textContent || ''")
    assert 'En az 2 harf yazın' in txt1, f'Expected 2-char prompt, got: {txt1!r}'

    # 2 chars
    b.eval("""(() => {
      const k = document.getElementById('araK');
      k.value = 'ai';
      k.dispatchEvent(new Event('input', { bubbles: true }));
    })()""")
    b.wait_for("document.querySelectorAll('#araS [data-act=\"araSec\"]').length > 0", timeout_ms=7000)

    # Impossible query
    b.eval("""(() => {
      const k = document.getElementById('araK');
      k.value = 'zzzznonexistent999xyz';
      k.dispatchEvent(new Event('input', { bubbles: true }));
    })()""")
    txt_none = b.eval("document.getElementById('araS')?.textContent || ''")
    assert 'Sonuç yok' in txt_none, f'Expected "Sonuç yok", got: {txt_none!r}'


@e2e_test('E3_T2_03', 2, 'E3', 'Corrupt JSON in localStorage akis2-ayar does not crash startup')
def test_e3_bva_corrupt_localstorage(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/bugun', reset_storage=True, pre_storage={'akis2-ayar': '{bad-json!!'})
    assert_clean_nav(nav)
    rows = b.eval("document.querySelectorAll('#ana [data-id]').length")
    assert rows > 0, 'App failed to boot with corrupt akis2-ayar JSON'


@e2e_test('E3_T2_04', 2, 'E3', 'Daha fazla goster pagination appends items without clearing existing rows')
def test_e3_bva_pagination_appends(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/akis/gundem')
    assert_clean_nav(nav)
    b.click('[data-act="zaman"][data-v="0"]')
    before = b.eval("document.querySelectorAll('#ana [data-id]').length")
    has_more = b.eval("Boolean(document.querySelector('#ana [data-act=\"daha\"]'))")
    if has_more:
        b.click('#ana [data-act="daha"]')
        after = b.eval("document.querySelectorAll('#ana [data-id]').length")
        assert after > before, f'Expected pagination to increase rows ({before} -> {after})'


@e2e_test('E3_T2_05', 2, 'E3', 'takip keyword highlighting escapes XSS payloads and regex metacharacters safely')
def test_e3_bva_takip_xss_and_regex_safe(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate(
        '#/bugun',
        reset_storage=True,
        pre_storage={'akis2-ayar': json.dumps({'takip': ['<script>window.__xss=1</script>', '[bad', 'Türkiye']})},
    )
    assert_clean_nav(nav)
    st = b.eval("({ xss: Boolean(window.__xss), scripts: document.querySelectorAll('#ana script').length })")
    assert not st['xss'] and st['scripts'] == 0, f'XSS executed via takip: {st}'


@e2e_test('E3_T2_06', 2, 'E3', 'Bugun time-window toggle (1h/6h/24h) handles empty 1h window cleanly')
def test_e3_bva_bugun_window_switch(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/bugun')
    assert_clean_nav(nav)
    for w in ('1', '6', '24'):
        b.click(f'[data-act="pen"][data-v="{w}"]')
        lay = b.inspect_layout()
        assert not lay['horizontalOverflow'], f'Overflow on Bugün {w}h window'
    assert_clean_diag(b)


# ============================================================================
# E4: #/kaynak Boundary Cases (5 tests)
# ============================================================================

@e2e_test('E4_T2_01', 2, 'E4', '#/kaynak zero-match search renders empty state with reset CTA restoring list')
def test_e4_bva_kaynak_zero_match_reset(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/kaynak')
    assert_clean_nav(nav)
    b.eval("""(() => {
      const inp = document.getElementById('kq');
      inp.value = 'zzzznonexistent999';
      inp.dispatchEvent(new Event('input', { bubbles: true }));
    })()""")
    b.wait_for("Boolean(document.querySelector('#kSonuc [data-act=\"kSifirla\"]'))")
    b.click('#kSonuc [data-act="kSifirla"]')
    b.wait_for("document.querySelectorAll('#kSonuc .k-item, #kSonuc table tbody tr').length > 0")


@e2e_test('E4_T2_02', 2, 'E4', 'Yeni kaynak oner form rejects invalid URL and outputs valid JSON for https://')
def test_e4_bva_kaynak_suggest_form_validation(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/kaynak')
    assert_clean_nav(nav)
    b.click('#ana details summary')
    b.eval("""(() => {
      document.getElementById('n-ad').value = 'Test Kaynak';
      document.getElementById('n-url').value = 'not-a-valid-url';
    })()""")
    b.click('[data-act="n-uret"]')
    hidden_bad = b.eval("document.getElementById('n-cikti').hidden")
    assert hidden_bad is True, 'Invalid URL produced snippet instead of rejecting'

    b.eval("document.getElementById('n-url').value = 'https://example.com/rss.xml'")
    b.click('[data-act="n-uret"]')
    out = b.eval("({ hidden: document.getElementById('n-cikti').hidden, text: document.getElementById('n-cikti').textContent })")
    assert out['hidden'] is False, 'Valid URL failed to reveal JSON snippet'
    json_part = out['text'].split('\n\n#')[0]
    parsed = json.loads(json_part)
    assert parsed['url'] == 'https://example.com/rss.xml' and parsed['dogrulama']['durum'] == 'bekliyor'


@e2e_test('E4_T2_03', 2, 'E4', '#/kaynak boundary filter combo (P3 + sinyal + diger) renders cleanly')
def test_e4_bva_kaynak_boundary_combo(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/kaynak')
    assert_clean_nav(nav)
    b.click('[data-act="konc"][data-v="3"]')
    b.click('[data-act="ktip"][data-v="sinyal"]')
    b.click('[data-act="kdil"][data-v="diger"]')
    lay = b.inspect_layout()
    assert not lay['horizontalOverflow'] and lay['clippedCount'] == 0
    assert_clean_diag(b)


@e2e_test('E4_T2_04', 2, 'E4', '#/kaynak Daha fazla goster pagination preserves active filters')
def test_e4_bva_kaynak_pagination_preserves_filter(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/kaynak')
    assert_clean_nav(nav)
    b.click('[data-act="kgor"][data-v="tablo"]')
    b.click('[data-act="kdur"][data-v="aktif"]')
    has_more = b.eval("Boolean(document.querySelector('#kSonuc [data-act=\"kdaha\"]'))")
    assert has_more, 'Expected [data-act="kdaha"] pagination button in #/kaynak tablo + aktif view'
    before = b.eval("document.querySelectorAll('#kSonuc tbody tr').length")
    b.click('#kSonuc [data-act="kdaha"]')
    after = b.eval("document.querySelectorAll('#kSonuc tbody tr').length")
    pressed = b.eval("document.querySelector('[data-act=\"kdur\"][data-v=\"aktif\"]').getAttribute('aria-pressed')")
    assert after > before and pressed == 'true', f'Filter lost or pagination failed ({before} -> {after}, pressed={pressed})'


@e2e_test('E4_T2_05', 2, 'E4', 'Mobile 390px #/kaynak Tablo mode hides .mob-yok columns without overflow')
def test_e4_bva_kaynak_mobile_table(ctx):
    b = ctx.browser
    b.set_mobile()
    nav = b.navigate('#/kaynak')
    assert_clean_nav(nav)
    b.click('[data-act="kgor"][data-v="tablo"]')
    st = b.eval("""(() => {
      const mobYok = document.querySelector('#ana .tbl .mob-yok');
      return {
        rows: document.querySelectorAll('#ana .tbl tbody tr').length,
        mobYokDisplay: mobYok ? getComputedStyle(mobYok).display : 'none',
      };
    })()""")
    assert st['rows'] > 0 and st['mobYokDisplay'] == 'none', f'Mobile table column hiding failed: {st}'
    lay = b.inspect_layout()
    assert not lay['horizontalOverflow'], f'Mobile table horizontal overflow: {lay}'


# ============================================================================
# E5: Legacy Migration, okxDenetle, 50-Draft Cap & Backup Boundaries (5 tests)
# ============================================================================

@e2e_test('E5_T2_01', 2, 'E5', 'Legacy akis2-ayar migration (tema:gece, vurgu:gul, gorunum:izgara) works on load')
def test_e5_bva_legacy_ayar_migration(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate(
        '#/akis/gundem',
        reset_storage=True,
        pre_storage={'akis2-ayar': json.dumps({'tema': 'gece', 'vurgu': 'gul', 'gorunum': 'izgara'})},
    )
    assert_clean_nav(nav)
    st = b.eval("""(() => ({
      tema: document.documentElement.dataset.tema || '',
      vurgu: document.documentElement.dataset.vurgu || '',
      hasKartlar: document.body.classList.contains('g-kartlar'),
    }))()""")
    assert st['tema'] == 'koyu', f"gece did not migrate to koyu: {st}"
    assert st['vurgu'] == '', f"gul did not migrate to default vurgu: {st}"
    assert st['hasKartlar'], f"izgara did not migrate to g-kartlar: {st}"


@e2e_test('E5_T2_02', 2, 'E5', 'akis2-ayar never persists okx property even after Okan mode & settings changes')
def test_e5_bva_ayar_never_contains_okx(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/bugun', reset_storage=True, pre_storage={'akis2-okx': '1'})
    assert_clean_nav(nav)
    b.click('#ayarAc')
    b.click('[data-act="tema"][data-v="acik"]')
    b.click('[data-act="ayarKapat"]')
    ayar_keys = b.eval("Object.keys(JSON.parse(localStorage.getItem('akis2-ayar') || '{}'))")
    assert 'okx' not in ayar_keys, f'Forbidden okx key persisted in akis2-ayar: {ayar_keys}'


@e2e_test('E5_T2_03', 2, 'E5', 'okxDenetle blocks X/FB open on empty, [placeholder], {unfilled}, and [Çevir:] in en')
def test_e5_bva_okx_denetle_error_boundaries(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/akis/gundem', reset_storage=True, pre_storage={'akis2-okx': '1'}, intercept_window_open=True)
    assert_clean_nav(nav)
    ensure_akis_rows(b)
    b.click('#ana [data-id] h3 a, #ana [data-id] h2 a')
    b.wait_for("document.getElementById('panel')?.open")
    b.click('#panel [data-act="okxAc"]')
    b.wait_for("document.getElementById('okxD')?.open")

    for bad_text in ('', 'Deneme [yer tutucu]', 'Deneme {baslik}'):
        b.eval("""((txt) => {
          const ta = document.getElementById('okxM');
          ta.value = txt;
          ta.dispatchEvent(new Event('input', { bubbles: true }));
        })(%s)""" % json.dumps(bad_text))
        b.click('#okxD [data-act="okxGit"]')
        res = b.eval("""({
          opened: (window.__openedUrls || []).length,
          hasErr: Boolean(document.querySelector('#okxL .hata')),
        })""")
        assert res['opened'] == 0 and res['hasErr'], f'Expected red error & blocked window.open for {bad_text!r}: {res}'

    # Switch to X (English) tab and confirm [Çevir: ...] placeholder blocks open
    b.eval("document.getElementById('okxM').value = 'Temiz metin'; document.getElementById('okxM').dispatchEvent(new Event('input', {bubbles:true}));")
    # Reset m0 by using tab change cleanly via clear draft
    b.eval("if(window.confirm) window.confirm = () => true;")
    b.click('#okxD [data-act="okxPl"][data-v="en"]')
    en_val = b.eval("document.getElementById('okxM').value")
    if '[Çevir:' in en_val:
        b.click('#okxD [data-act="okxGit"]')
        res_en = b.eval("""({
          opened: (window.__openedUrls || []).length,
          hasErr: Boolean(document.querySelector('#okxL .hata')),
        })""")
        assert res_en['opened'] == 0 and res_en['hasErr'], f'Expected [Çevir:] error block: {res_en}'


@e2e_test('E5_T2_04', 2, 'E5', 'akis2-okx-taslak enforces 50-draft cap (51st draft trims oldest)')
def test_e5_bva_okx_draft_50_cap(ctx):
    seed = [
        {'z': 1000 + i, 'm': f'Draft {i}', 'h': '', 'c': {'id': f'seed-{i}', 't': f'Title {i}'}}
        for i in range(50)
    ]
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate(
        '#/akis/gundem',
        reset_storage=True,
        pre_storage={'akis2-okx': '1', 'akis2-okx-taslak': json.dumps(seed)},
    )
    assert_clean_nav(nav)
    ensure_akis_rows(b)
    b.click('#ana [data-id] h3 a, #ana [data-id] h2 a')
    b.wait_for("document.getElementById('panel')?.open")
    b.click('#panel [data-act="okxAc"]')
    b.wait_for("document.getElementById('okxD')?.open")
    b.click('#okxD [data-act="okxPl"][data-v="x"]')
    b.click('#okxD [data-act="okxKaydet"]')
    cnt = b.eval("JSON.parse(localStorage.getItem('akis2-okx-taslak') || '[]').length")
    assert cnt == 50, f'Expected akis2-okx-taslak capped at 50, got {cnt}'


@e2e_test('E5_T2_05', 2, 'E5', 'Backup import rejects malformed JSON cleanly and restores valid backup')
def test_e5_bva_backup_import(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/kayit')
    assert_clean_nav(nav)
    # Trigger malformed JSON via FileReader on .ice-d input
    b.eval("""(() => {
      const inp = document.querySelector('.ice-d');
      const dt = new DataTransfer();
      dt.items.add(new File(['{not valid json'], 'bad.json', { type: 'application/json' }));
      inp.files = dt.files;
      inp.dispatchEvent(new Event('change', { bubbles: true }));
    })()""")
    b.wait_for("/Geçersiz yedek dosyası/.test(document.getElementById('toast')?.textContent || '')")

    valid = json.dumps({
        'surum': 3,
        'kayit': {'test-bak-1': {'id': 'test-bak-1', 't': 'Yedek Test Haberi', 'l': 'https://example.com/1', 'son': 1700000000}},
        'okundu': {},
        'gizli': {},
        'notlar': {},
        'durum': {},
    })
    b.eval("""((payload) => {
      const inp = document.querySelector('.ice-d');
      const dt = new DataTransfer();
      dt.items.add(new File([payload], 'ok.json', { type: 'application/json' }));
      inp.files = dt.files;
      inp.dispatchEvent(new Event('change', { bubbles: true }));
    })(%s)""" % json.dumps(valid))
    b.wait_for("Boolean(document.querySelector('#ana [data-id=\"test-bak-1\"]'))")
    assert_clean_diag(b)


# ============================================================================
# E6: sources.json BVA & tools/kaynak_test.py Contract (5 tests)
# ============================================================================

@e2e_test('E6_T2_01', 2, 'E6', 'Every inactive source (aktif=False) carries non-empty pasif_neden')
def test_e6_bva_inactive_reason(ctx):
    src = load_json('sources.json')
    missing = [s['id'] for s in src if s.get('aktif') is False and not str(s.get('pasif_neden', '')).strip()]
    assert not missing, f'Inactive sources missing pasif_neden: {missing}'


@e2e_test('E6_T2_02', 2, 'E6', 'Zero active developer/coding feeds in sources.json')
def test_e6_bva_no_active_dev_feeds(ctx):
    src = load_json('sources.json')
    dev_rx = re.compile(
        r'github\.com|stackoverflow\.com|dev\.to|lobste\.rs|python\.org|rust-lang\.org|golang\.org|kubernetes\.io|docker\.com|hackernews.*dev|smashingmagazine|css-tricks',
        re.I,
    )
    bad = [
        (s['id'], s['url'])
        for s in src
        if s.get('aktif', True) and dev_rx.search(s['id'] + ' ' + s['name'] + ' ' + s['url'])
    ]
    assert not bad, f'Active developer/coding feeds found in sources.json: {bad}'


@e2e_test('E6_T2_03', 2, 'E6', 'sources.json taxonomy (CALISMA/TIPLER/oncelik) and paywall/reddit tags valid')
def test_e6_bva_taxonomy_and_tags(ctx):
    calisma = {
        'gundem', 'adana', 'tekno', 'yz', 'siyaset', 'spor', 'ekonomi',
        'bilim', 'siber', 'oto', 'oyun', 'eglence', 'savunma',
    }
    tipler = {
        'ajans', 'ana akim', 'dogrulama', 'resmi kurum', 'uluslararasi kurum',
        'uzman teknoloji', 'bilimsel', 'spor', 'topluluk/trend',
        'sirket duyurusu', 'toplayici', 'video (YouTube)',
    }
    src = load_json('sources.json')
    for s in src:
        assert s.get('calisma') in calisma, f"Invalid calisma on {s['id']}: {s.get('calisma')}"
        assert s.get('tip') in tipler, f"Invalid tip on {s['id']}: {s.get('tip')}"
        assert s.get('oncelik') in (1, 2, 3), f"Invalid oncelik on {s['id']}: {s.get('oncelik')}"
        assert isinstance(s.get('nitelik'), list) and isinstance(s.get('aktif'), bool), s['id']
        if s['id'] in ('nyt', 'wapo', 'ft', 'economist', 'bloomberg'):
            assert 'ucretli-duvar' in s['nitelik'], f"Missing ucretli-duvar on {s['id']}"
        if s.get('plat') == 'reddit':
            assert 'erken-sinyal' in s['nitelik'], f"Missing erken-sinyal on reddit source {s['id']}"


@e2e_test('E6_T2_04', 2, 'E6', 'tools/kaynak_test.py enforces <3 items, >45d age, >=60% overlap, >=3 recent pass')
def test_e6_bva_kaynak_test_contract(ctx):
    if os.path.join(KOK, 'tools') not in sys.path:
        sys.path.insert(0, os.path.join(KOK, 'tools'))
    import kaynak_test as KT

    now = datetime.now(timezone.utc)
    recent_rfc = (now - timedelta(days=1)).strftime('%a, %d %b %Y %H:%M:%S +0000')
    old_rfc = (now - timedelta(days=60)).strftime('%a, %d %b %Y %H:%M:%S +0000')

    def rss(items):
        body = ''.join(
            f'<item><title>{t}</title><link>{l}</link><pubDate>{d}</pubDate></item>'
            for t, l, d in items
        )
        return ('<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>' + body + '</channel></rss>').encode('utf-8')

    routes = {
        '/two.xml': rss([('A', 'https://mock.test/1', recent_rfc), ('B', 'https://mock.test/2', recent_rfc)]),
        '/old.xml': rss([(f'O{i}', f'https://mock.test/old/{i}', old_rfc) for i in range(4)]),
        '/dup.xml': rss([(f'D{i}', f'https://dup.test/{i}', recent_rfc) for i in range(4)]),
        '/ok.xml': rss([(f'K{i}', f'https://ok.test/{i}', recent_rfc) for i in range(4)]),
    }

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            payload = routes.get(self.path)
            if payload is None:
                self.send_response(404); self.end_headers(); return
            self.send_response(200)
            self.send_header('Content-Type', 'application/rss+xml; charset=utf-8')
            self.end_headers()
            self.wfile.write(payload)

    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        known_urls = set()
        known_links = {f'https://dup.test/{i}' for i in range(4)}
        mk = lambda path: ('mock', 'Mock', 'tr', 'TR', 'tech', 'tekno', 'uzman teknoloji', f'http://127.0.0.1:{port}{path}', [])
        r_two = KT.dene(mk('/two.xml'), known_urls, known_links)
        r_old = KT.dene(mk('/old.xml'), known_urls, known_links)
        r_dup = KT.dene(mk('/dup.xml'), known_urls, known_links)
        r_ok = KT.dene(mk('/ok.xml'), known_urls, known_links)
        assert r_two['ok'] is False and '3' in r_two.get('neden', ''), f'Expected <3 fail: {r_two}'
        assert r_old['ok'] is False and '45' in r_old.get('neden', ''), f'Expected >45d fail: {r_old}'
        assert r_dup['ok'] is False and 'kopya' in r_dup.get('neden', ''), f'Expected overlap fail: {r_dup}'
        assert r_ok['ok'] is True and r_ok['n'] == 4, f'Expected pass: {r_ok}'
    finally:
        srv.shutdown()
        srv.server_close()


@e2e_test('E6_T2_05', 2, 'E6', 'kaynaklar.json consistent and baseline dead/403 active sources resolved', gate='M1_F1')
def test_e6_bva_dead_sources_resolved(ctx):
    kj = load_json('site/data/kaynaklar.json')
    assert sum(kj['durum_say'].values()) == len(kj['kaynaklar'])
    src_by_id = {s['id']: s for s in load_json('sources.json')}
    kj_by_id = {s['id']: s for s in kj['kaynaklar']}
    dead_baseline = ('espn', 'navalnews', 'teknoseyir-yz-ara', 'cisa-haber', 'science', 'gn-resmi-tcmb', 'googleblog-pixel')
    still_broken = []
    for sid in dead_baseline:
        s = src_by_id.get(sid)
        k = kj_by_id.get(sid)
        if not s:
            continue
        if s.get('aktif') is False:
            continue
        if k and k.get('durum') in ('hata', 'erisim-engelli', 'guncellenmiyor'):
            still_broken.append((sid, k.get('durum')))
    assert not still_broken, f'Baseline failing/stale active sources still unaddressed: {still_broken}'


# ============================================================================
# E7: Generated Data Boundary Contracts (5 tests)
# ============================================================================

@e2e_test('E7_T2_01', 2, 'E7', 'kume-*.json items preserve required keys and omit all stripped internal keys')
def test_e7_bva_kume_stripped_keys(ctx):
    stripped = {
        'cat', 'h1', 'h6', 'h24', 'h6o', 'h24o', 'k6', 'k24', 'sicak1', 'sicak6',
        'sicak24', 'yog', 'yog24', 'resmi', 'reels_alt', 'yuk', 'r', 'elen',
        'kategoriler', 'plat_topluluk', 'sadece_yabanci', 'n_tr', 'ulkeler', 'liderler', 'markalar',
    }
    req = {'t', 'kb', 'son', 'og', 'alanlar', 'alt', 'kaynaklar', 'gundem_alt'}
    for fn in sorted(os.listdir(os.path.join(KOK, 'site', 'data'))):
        if not (fn.startswith('kume-') and fn.endswith('.json')):
            continue
        d = load_json(f'site/data/{fn}')
        for c in d['kumeler'][:50]:
            assert req <= set(c.keys()), f'{fn} missing keys: {req - set(c.keys())}'
            leaked = stripped & set(c.keys())
            assert not leaked, f'{fn} leaked stripped keys: {leaked}'


@e2e_test('E7_T2_02', 2, 'E7', 'ozet.json sicak/yukselen require kb>=2, son<=40, indeks<=2600 without cat')
def test_e7_bva_ozet_and_indeks_caps(ctx):
    o = load_json('site/data/ozet.json')
    for win, items in o['sicak'].items():
        for c in items:
            assert c['kb'] >= 2, f"ozet.sicak[{win}] item has kb < 2: {c['t']}"
    for c in o['yukselen']:
        assert c['kb'] >= 2, f"ozet.yukselen item has kb < 2: {c['t']}"
    assert len(o['son']) <= 40, f"ozet.son exceeds 40: {len(o['son'])}"

    ix = load_json('site/data/indeks.json')
    assert len(ix['kayitlar']) <= 2600, f"indeks.json exceeds 2600 records: {len(ix['kayitlar'])}"
    for r in ix['kayitlar'][:100]:
        assert 'cat' not in r, 'indeks.json record contains stripped cat key'


@e2e_test('E7_T2_03', 2, 'E7', 'diller.json matches ozet.json diller and DIL_AYRILAN preserves non-TR/EN per area')
def test_e7_bva_diller_and_dil_ayrilan(ctx):
    o = load_json('site/data/ozet.json')
    dl = load_json('site/data/diller.json')['diller']
    assert [x['k'] for x in o['diller']] == [x['k'] for x in dl], 'ozet.diller != diller.json'

    alan_files = {
        a['k']: load_json(f"site/data/kume-{a['k']}.json")['kumeler']
        for a in o['alanlar']
        if os.path.isfile(os.path.join(KOK, 'site', 'data', f"kume-{a['k']}.json"))
    }
    for x in dl:
        if x['k'] in ('tr', 'en'):
            continue
        f = load_json(f"site/data/dil-{x['k']}.json")['kumeler']
        for a, kumeler in alan_files.items():
            m = sum(1 for c in f if a in c['alanlar'])
            got = sum(1 for c in kumeler if c['dil'] == x['k'])
            assert got >= min(6, m), f"DIL_AYRILAN violated for ({x['k']}, {a}): {got} < {min(6, m)}"


@e2e_test('E7_T2_04', 2, 'E7', 'trendler.json order/firsat and guncellemeler.json tur taxonomy valid')
def test_e7_bva_trendler_and_guncellemeler(ctx):
    t = load_json('site/data/trendler.json')
    assert t['sira'] and t['sira'][0] == 'TR', f"Expected TR first in trendler.sira: {t['sira']}"
    for geo in t['sira']:
        for item in t['ulkeler'][geo]['trendler']:
            assert item.get('t')
            if geo in ('TR', 'US', 'GB'):
                assert item.get('firsat') in (True, False)
            else:
                assert item.get('firsat') is None

    g = load_json('site/data/guncellemeler.json')
    turler = {k['k'] for k in g['turler']}
    for u in g['urunler']:
        assert u['ogeler']
        for item in u['ogeler']:
            assert item['tur'] in turler, f"Unknown update tur {item['tur']!r}"


@e2e_test('E7_T2_05', 2, 'E7', 'kume-*.json and indeks.json exclude lottery, tax-office, mid-SEO, and dev leaks', gate='M2_F6')
def test_e7_bva_junk_exclusion(ctx):
    junk_rx = re.compile(
        r'süper loto|sayısal loto|şans topu|on numara|vergi dairesi müdürlüğü|kimdir,\s*kaç yaşında',
        re.I,
    )
    dev_rx = re.compile(
        r'\b(github|gitlab|stack\s?overflow|npm|pypi|kubernetes|docker|ci/cd|pull request|source code|'
        r'open[- ]source (?:library|framework)|vs\s?code|xcode|android studio|typescript|javascript|'
        r'rustlang|golang|python \d|compiler|programming language|developer (?:tool|conference|kit))\b',
        re.I,
    )
    cons_rx = re.compile(
        r'chatgpt|\bgpt-\d|gemini (?:app|uygulama)|iphone|ipad|galaxy|xiaomi|pixel \d|'
        r'playstation|xbox|nintendo|\bgta\b|whatsapp|instagram',
        re.I,
    )

    def _is_leak(title):
        return bool(junk_rx.search(title) or (dev_rx.search(title) and not cons_rx.search(title)))

    ix = load_json('site/data/indeks.json')['kayitlar']
    hits = [r['t'] for r in ix if _is_leak(r.get('t', ''))]
    for fn in sorted(os.listdir(os.path.join(KOK, 'site', 'data'))):
        if fn.startswith('kume-') and fn.endswith('.json'):
            for c in load_json(f'site/data/{fn}')['kumeler']:
                if _is_leak(c.get('t', '')):
                    hits.append(f"{fn}:{c['t']}")
    assert not hits, f'Junk lottery/tax/SEO/dev titles leaked into data: {hits[:5]}'


# ============================================================================
# E8: Reels Hook, Scoring, Angle & UI Boundaries (5 tests)
# ============================================================================

@e2e_test('E8_T2_01', 2, 'E8', 'akis2.py CLI extracts lira/yuzde numeric openings into reels.json without fallback', gate='M2_F4')
def test_e8_bva_lira_yuzde_hook_regex(ctx):
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    pub_iso = (now_dt - timedelta(minutes=15)).isoformat()

    sources = [
        {
            'id': f'tr-eko-{i}',
            'name': name,
            'lang': 'tr',
            'cat': 'eco',
            'url': f'https://example{i}.com/rss',
            'plat': 'web',
            'calisma': 'ekonomi',
            'tip': 'ana akim',
            'ulke': 'TR',
            'oncelik': 1,
            'nitelik': ['resmi'] if i == 1 else [],
            'aktif': True,
        }
        for i, name in enumerate(['Anadolu Ajansı', 'TRT Haber', 'NTV', 'Bloomberg HT'], start=1)
    ]

    headlines = [
        ("50,62", "Dolar/TL'den bir rekor daha geldi: 50,62 lirayı gördü"),
        ("yüzde 25", "Elektriğe yüzde 25 zam geldi: yeni tarife açıklandı"),
    ]

    feeds = {}
    for i, s in enumerate(sources, start=1):
        feeds[s['id']] = {
            'name': s['name'],
            'cat': s['cat'],
            'lang': s['lang'],
            'plat': s['plat'],
            'items': [
                {
                    't': title,
                    'l': f'https://example{i}.com/haber-{idx}',
                    'd': pub_iso,
                    'p': s['name'],
                    's': f'{title}. Türkiye piyasalarında güncel tüketici rakamları ve ayrıntılar açıklandı.',
                }
                for idx, (_, title) in enumerate(headlines, start=1)
            ],
        }

    with tempfile.TemporaryDirectory(prefix='akis_e8_sub_') as tmp_dir:
        os.makedirs(os.path.join(tmp_dir, 'site'), exist_ok=True)
        with open(os.path.join(tmp_dir, 'sources.json'), 'w', encoding='utf-8') as f:
            json.dump(sources, f, ensure_ascii=False)
        with open(os.path.join(tmp_dir, 'site', 'feeds.json'), 'w', encoding='utf-8') as f:
            json.dump({'generated': now_iso, 'feeds': feeds}, f, ensure_ascii=False)
        with open(os.path.join(tmp_dir, 'site', 'kaynak-durum.json'), 'w', encoding='utf-8') as f:
            json.dump({}, f)

        proc = subprocess.run(
            [sys.executable, os.path.join(KOK, 'akis2.py')],
            cwd=tmp_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0, f'Isolated akis2.py failed ({proc.returncode}): {proc.stderr}'

        reels_path = os.path.join(tmp_dir, 'site', 'data', 'reels.json')
        assert os.path.isfile(reels_path), 'Isolated akis2.py did not produce site/data/reels.json'
        with open(reels_path, encoding='utf-8') as f:
            reels = json.load(f)

    adaylar = reels.get('adaylar', [])
    assert len(adaylar) >= 2, f'Expected both consumer headlines in isolated reels.json, got {len(adaylar)}'
    for num_tok, title in headlines:
        card = next((c for c in adaylar if num_tok in c.get('t', '').lower() or c.get('t') == title), None)
        assert card is not None, f'Missing generated Reels card for {title!r} in {[c.get("t") for c in adaylar]}'
        hooks = card.get('hooklar', [])
        assert hooks and not hooks[0].lower().startswith('3 saniyede özet'), (
            f'akis2.py fell back on lira/yüzde title {title!r}: {hooks}'
        )
        assert num_tok in hooks[0].lower(), (
            f'Expected extracted consumer number {num_tok!r} in hooklar[0] for {title!r}, got: {hooks}'
        )
        assert not any('?' in h for h in hooks), f'Question hook generated for {title!r}: {hooks}'


@e2e_test('E8_T2_02', 2, 'E8', 'Reels hooklar[0] opening obeys spoken-Turkish conciseness discipline')
def test_e8_bva_hook_conciseness(ctx):
    r = load_json('site/data/reels.json')
    too_long = []
    for c in r['adaylar']:
        h0 = c['hooklar'][0].strip()
        first_sent = re.split(r'[.!?]\s+', h0, maxsplit=1)[0]
        if len(first_sent.split()) > 16 or len(h0) > 150:
            too_long.append((c['id'], len(first_sent.split()), h0))
    assert not too_long, f'Verbose hooklar[0] detected: {too_long[:3]}'


@e2e_test('E8_T2_03', 2, 'E8', 'Foreign-only items flag yabanci=True and kb<2 carries verification/risk warnings')
def test_e8_bva_foreign_and_single_source_warnings(ctx):
    r = load_json('site/data/reels.json')
    for c in r['adaylar']:
        if c.get('yabanci'):
            assert c.get('dil') != 'tr' or c.get('turk_onemi'), f'Inconsistent yabanci flag on {c["id"]}'
        if c.get('kb', 0) < 2:
            dog = c.get('dogrulama', '').lower()
            risk_blob = ' '.join(c.get('risk', [])).lower()
            assert ('doğrulanmadı' in dog or 'resmî' in dog) and ('tek kaynak' in risk_blob or 'ikinci kaynak' in risk_blob), (
                f"kb<2 card missing warning on {c['id']}: dog={c.get('dogrulama')!r} risk={c.get('risk')}"
            )


@e2e_test('E8_T2_04', 2, 'E8', 'Reels aci <= 90 chars, starts with aci_etiket, no orphan units, no fake TR translation')
def test_e8_bva_aci_discipline(ctx):
    r = load_json('site/data/reels.json')
    orphan_rx = re.compile(r'\b(\d[\d.,]*|yüzde|bin|milyon|milyar)…$')
    for c in r['adaylar']:
        aci = c['aci']
        assert len(aci) <= 90, f'aci > 90 chars ({len(aci)}): {aci!r}'
        assert aci.startswith(c['aci_etiket'] + ': '), f"aci does not start with aci_etiket: {aci!r}"
        assert not orphan_rx.search(aci), f'Orphan trailing number/unit in aci: {aci!r}'


@e2e_test('E8_T2_05', 2, 'E8', '#/reels UI renders angle/hooks/copy/disclaimer and hides reels-sablonu in default/Piril')
def test_e8_bva_reels_ui_cards(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/reels')
    assert_clean_nav(nav)
    ui = b.eval("""(() => {
      const cards = document.querySelectorAll('#ana [data-id]');
      const kop = document.querySelectorAll('#ana [data-act="kop"]').length;
      const sablon = document.querySelectorAll('#ana a[href*="reels-sablonu"]').length;
      const txt = document.getElementById('ana')?.textContent || '';
      return {
        cards: cards.length,
        kop,
        sablon,
        hasDisclaimer: /viral garantisi değildir/i.test(txt),
      };
    })()""")
    assert ui['cards'] > 0 and ui['kop'] > 0, f'Reels UI missing cards or Hook kopyala button: {ui}'
    assert ui['sablon'] == 0, f'Okan reels-sablonu link leaked into default #/reels: {ui}'
    assert ui['hasDisclaimer'], 'Reels UI missing viral garantisi değildir disclaimer'
