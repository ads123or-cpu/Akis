"""Tier 1: Core feature E2E tests covering E1–E8 (public contracts, >= 5 per feature)."""
import json
import os
import re
from harness import (
    KOK,
    assert_clean_diag,
    assert_clean_nav,
    e2e_test,
    ensure_akis_rows,
    file_size,
    git_cmd,
    load_json,
    parse_snap,
    visible_okx_count,
)

SAYFALAR_CANON = [
    'bugun', 'akis', 'reels', 'trend', 'guncelleme',
    'dunya', 'videolar', 'kayit', 'kaynak',
]
ALANLAR_CANON = [
    'gundem', 'adana', 'tekno', 'yz', 'siyaset', 'spor', 'ekonomi',
    'bilim', 'siber', 'oto', 'oyun', 'eglence', 'savunma',
]
CAT_CANON = {
    'auto', 'cool', 'eco', 'ent', 'ios', 'mac', 'samsung',
    'sci', 'sport', 'tech', 'tr', 'viral', 'win', 'world',
}


# ============================================================================
# E1: Navigation & Views (6 tests)
# ============================================================================

@e2e_test('E1_T1_01', 1, 'E1', 'Default root #/bugun loads greeting h1, items, and zero errors')
def test_e1_default_bugun(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/bugun')
    assert_clean_nav(nav)
    info = b.eval("""(() => {
      const h1 = document.querySelector('#ana h1');
      const items = document.querySelectorAll('#ana [data-id]').length;
      return { h1: h1 ? h1.textContent.trim() : '', items, hash: location.hash };
    })()""")
    assert info['h1'], 'Expected non-empty greeting h1 on #/bugun'
    assert info['items'] >= 5, f"Expected >=5 feed items on #/bugun, got {info['items']}"


@e2e_test('E1_T1_02', 1, 'E1', 'All 9 canonical SAYFALAR routes render distinct views with active nav')
def test_e1_all_canonical_routes(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/bugun')
    assert_clean_nav(nav)
    seen_headings = {}
    for s in SAYFALAR_CANON:
        b.clear_diagnostics()
        res = b.set_hash(f'#/{s}')
        assert_clean_nav(res)
        st = b.eval("""(() => {
          const h1 = document.querySelector('#ana h1');
          const cur = Array.from(document.querySelectorAll('nav [aria-current="page"], #digerM [aria-current="page"], #ana [aria-current="page"]'))
            .map(el => el.getAttribute('href') || el.textContent.trim());
          return {
            h1: h1 ? h1.textContent.trim() : '',
            textLen: (document.getElementById('ana')?.textContent || '').trim().length,
            cur,
          };
        })()""")
        assert st['textLen'] > 20, f'Route #/{s} rendered empty content'
        if s != 'akis':
            assert st['h1'], f'Route #/{s} missing h1 heading'
            seen_headings[s] = st['h1']
        assert st['cur'], f'Route #/{s} missing aria-current="page" indicator'
    assert len(set(seen_headings.values())) >= 7, f'Expected distinct headings across routes: {seen_headings}'


@e2e_test('E1_T1_03', 1, 'E1', 'All 13 ALAN sub-routes load cleanly without uncaught/HTTP errors')
def test_e1_all_13_areas(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/akis/gundem')
    assert_clean_nav(nav)
    for a in ALANLAR_CANON:
        b.clear_diagnostics()
        res = b.set_hash(f'#/akis/{a}')
        assert_clean_nav(res)
        st = b.eval("""(() => {
          const rows = document.querySelectorAll('#ana [data-id]').length;
          const empty = document.querySelector('#ana .bosluk, #ana [role="alert"]');
          return {
            rows,
            hasEmpty: Boolean(empty && empty.textContent.trim()),
            cur: Array.from(document.querySelectorAll('#ana [aria-current="page"], nav [aria-current="page"]')).length,
          };
        })()""")
        assert st['rows'] > 0 or st['hasEmpty'], f'Area #/akis/{a} rendered neither items nor empty state'
        assert st['cur'] >= 1, f'Area #/akis/{a} missing aria-current="page" indicator'


@e2e_test('E1_T1_04', 1, 'E1', 'View mode switching (Akis/Kartlar/Basliklar) updates layout and persists')
def test_e1_view_modes(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/akis/gundem')
    assert_clean_nav(nav)
    for mode in ('kartlar', 'basliklar', 'akis'):
        b.click('#gorAc')
        b.click(f'[data-act="gorSec"][data-v="{mode}"]')
        st = b.eval("""(() => {
          const ayar = JSON.parse(localStorage.getItem('akis2-ayar') || '{}');
          const cls = Array.from(document.body.classList);
          return { gorunum: ayar.gorunum, cls };
        })()""")
        assert st['gorunum'] == mode, f"Expected ayar.gorunum={mode}, got {st['gorunum']}"
        assert f'g-{mode}' in st['cls'], f"Expected body class g-{mode}, got {st['cls']}"
    # Persist kartlar across reload
    b.click('#gorAc')
    b.click('[data-act="gorSec"][data-v="kartlar"]')
    rel = b.reload()
    assert_clean_nav(rel)
    persisted = b.eval("JSON.parse(localStorage.getItem('akis2-ayar') || '{}').gorunum")
    assert persisted == 'kartlar', f'View mode did not persist after reload: {persisted}'


@e2e_test('E1_T1_05', 1, 'E1', 'Mobile bottom nav and Daha dialog expose all pages and Ayarlar')
def test_e1_mobile_nav_and_daha(ctx):
    b = ctx.browser
    b.set_mobile()
    nav = b.navigate('#/bugun')
    assert_clean_nav(nav)
    b.click('[data-act="dahaAc"]')
    daha = b.eval("""(() => {
      const dlg = document.getElementById('dahaSayfa');
      if (!dlg || !dlg.open) return null;
      const hrefs = Array.from(dlg.querySelectorAll('a[href]')).map(a => a.getAttribute('href'));
      const hasAyar = Boolean(dlg.querySelector('[data-act="ayar"]'));
      return { hrefs, hasAyar };
    })()""")
    assert daha is not None, '#dahaSayfa dialog did not open on mobile'
    assert daha['hasAyar'], 'Ayarlar button missing in #dahaSayfa'
    for s in SAYFALAR_CANON:
        assert f'#/{s}' in daha['hrefs'], f'#/{s} missing from mobile #dahaSayfa links: {daha["hrefs"]}'
    b.click('[data-act="dahaKapat"]')


@e2e_test('E1_T1_06', 1, 'E1', 'Personal desk #/piril loads non-TR clusters and is excluded from SAYFALAR')
def test_e1_piril_route_and_nav_exclusion(ctx):
    b = ctx.browser
    b.set_desktop()
    nav0 = b.navigate('#/bugun')
    assert_clean_nav(nav0)
    default_nav_hrefs = b.eval("""Array.from(document.querySelectorAll('#anaNav a, #altBar a, #digerM a'))
      .map(a => a.getAttribute('href'))""")
    assert '#/piril' not in default_nav_hrefs, f"#/piril must not appear in default main nav: {default_nav_hrefs}"

    nav = b.set_hash('#/piril')
    assert_clean_nav(nav)
    st = b.eval("""(() => {
      const h1 = document.querySelector('#ana h1')?.textContent || '';
      const rows = document.querySelectorAll('#ana [data-id]').length;
      return { h1, rows };
    })()""")
    assert 'Pırıl' in st['h1'], f"Expected Pırıl heading, got {st['h1']!r}"
    assert st['rows'] >= 10, f"Expected non-TR clusters on #/piril, got {st['rows']}"


# ============================================================================
# E2: Theme & Viewport Responsiveness (6 tests)
# ============================================================================

@e2e_test('E2_T1_01', 1, 'E2', 'Light and dark themes update dataset.tema, luminance, and persist')
def test_e2_themes_and_luminance(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/bugun')
    assert_clean_nav(nav)

    b.click('#ayarAc')
    b.click('[data-act="tema"][data-v="acik"]')
    light = b.inspect_theme()
    assert light['tema'] == 'acik', f"Expected tema=acik, got {light}"
    assert light['bgLum'] > 0.5, f"Light theme bg luminance too dark: {light}"
    assert light['contrast'] >= 4.5, f"Light theme contrast too low: {light}"

    b.click('[data-act="tema"][data-v="koyu"]')
    dark = b.inspect_theme()
    assert dark['tema'] == 'koyu', f"Expected tema=koyu, got {dark}"
    assert dark['bgLum'] < 0.2, f"Dark theme bg luminance too bright: {dark}"
    assert dark['contrast'] >= 4.5, f"Dark theme contrast too low: {dark}"

    b.click('[data-act="ayarKapat"]')
    rel = b.reload()
    assert_clean_nav(rel)
    after = b.inspect_theme()
    assert after['tema'] == 'koyu' and after['bgLum'] < 0.2, f'Dark theme did not persist: {after}'


@e2e_test('E2_T1_02', 1, 'E2', 'Mobile 390x844 has zero horizontal overflow across all main routes + piril')
def test_e2_mobile_zero_overflow(ctx):
    b = ctx.browser
    b.set_mobile()
    nav = b.navigate('#/bugun')
    assert_clean_nav(nav)
    for route in SAYFALAR_CANON + ['piril']:
        res = b.set_hash(f'#/{route}')
        assert_clean_nav(res)
        lay = b.inspect_layout()
        assert not lay['horizontalOverflow'], (
            f"Mobile 390px horizontal overflow on #/{route}: "
            f"doc={lay['docScrollWidth']} body={lay['bodyScrollWidth']} inner={lay['innerWidth']}"
        )


@e2e_test('E2_T1_03', 1, 'E2', 'Desktop 1440x1000 has zero horizontal overflow across all main routes + piril')
def test_e2_desktop_zero_overflow(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/bugun')
    assert_clean_nav(nav)
    for route in SAYFALAR_CANON + ['piril']:
        res = b.set_hash(f'#/{route}')
        assert_clean_nav(res)
        lay = b.inspect_layout()
        assert not lay['horizontalOverflow'], (
            f"Desktop 1440px horizontal overflow on #/{route}: "
            f"doc={lay['docScrollWidth']} body={lay['bodyScrollWidth']} inner={lay['innerWidth']}"
        )


@e2e_test('E2_T1_04', 1, 'E2', 'Zero clipped or overlapping interactive controls on 390px and 1440px')
def test_e2_no_clipped_or_overlapping_controls(ctx):
    b = ctx.browser
    for mode, setup in (('mobile390', b.set_mobile), ('desktop1440', b.set_desktop)):
        setup()
        nav = b.navigate('#/bugun')
        assert_clean_nav(nav)
        for route in ('bugun', 'akis/gundem', 'reels', 'kaynak'):
            res = b.set_hash(f'#/{route}')
            assert_clean_nav(res)
            lay = b.inspect_layout()
            assert lay['clippedCount'] == 0, f"{mode} #/{route} clipped controls: {lay['clipped']}"
            assert lay['overlapCount'] == 0, f"{mode} #/{route} overlapping controls: {lay['overlaps']}"


@e2e_test('E2_T1_05', 1, 'E2', 'Mobile 390px interactive controls meet >= 44px touch target', gate='M3_F8')
def test_e2_mobile_touch_targets(ctx):
    b = ctx.browser
    b.set_mobile()
    for route in ('#/bugun', '#/akis/gundem', '#/reels', '#/kaynak'):
        nav = b.navigate(route)
        assert_clean_nav(nav)
        tt = b.inspect_touch_targets(44)
        assert tt['undersizedCount'] == 0, (
            f"Mobile touch targets <44px on {route}: {tt['undersized'][:8]}"
        )


@e2e_test('E2_T1_06', 1, 'E2', 'Mobile #/akis consolidates navigation bars without stacking redundant bars', gate='M3_F7')
def test_e2_mobile_nav_consolidation(ctx):
    b = ctx.browser
    b.set_mobile()
    nav = b.navigate('#/akis/gundem')
    assert_clean_nav(nav)
    ensure_akis_rows(b)
    metrics = b.eval("""(() => {
      const hdr = document.querySelector('header');
      const hb = hdr ? hdr.getBoundingClientRect().bottom : 0;
      const katBar = document.getElementById('katBar');
      const katVis = !!(katBar && !katBar.hidden && getComputedStyle(katBar).display !== 'none' && katBar.getBoundingClientRect().height > 0);
      const navStrips = Array.from(document.querySelectorAll('nav, #ana [role="navigation"]'))
        .filter(el => {
          if (el.id === 'altBar') return false;
          if (el.closest('[hidden]')) return false;
          const st = getComputedStyle(el);
          if (st.display === 'none' || st.visibility === 'hidden') return false;
          const r = el.getBoundingClientRect();
          return r.height > 0 && r.width > 0 && r.top < 400;
        });
      const firstStory = document.querySelector('#ana [data-id]');
      const firstTop = firstStory ? firstStory.getBoundingClientRect().top : 9999;
      const areaLinks = new Set(
        Array.from(document.querySelectorAll('a[href^="#/akis/"]'))
          .map(a => (a.getAttribute('href') || '').replace('#/akis/', '').split('?')[0])
      );
      return {
        headerBottom: Math.round(hb),
        katBarVisibleOnAkis: katVis,
        topNavStripCount: navStrips.length,
        firstStoryTop: Math.round(firstTop),
        areaCount: areaLinks.size,
      };
    })()""")
    assert not metrics['katBarVisibleOnAkis'], (
        f"Redundant #katBar should not stack on top of #/akis nav: {metrics}"
    )
    assert metrics['topNavStripCount'] <= 2 and metrics['firstStoryTop'] <= 250, (
        f"Stacked top chrome pushes first story too far down on 390px ({metrics['firstStoryTop']}px): {metrics}"
    )
    assert metrics['areaCount'] >= 7, f"Expected main/sub area navigation links, got {metrics['areaCount']}"


# ============================================================================
# E3: Bugün, Detail Drawer, Search, Save/Read/Hide & Empty-State (6 tests)
# ============================================================================

@e2e_test('E3_T1_01', 1, 'E3', 'Detail drawer opens (modal on mobile, side on desktop), marks read, closes cleanly')
def test_e3_detail_drawer_lifecycle(ctx):
    b = ctx.browser
    for mode, setup, expect_modal in (('mobile', b.set_mobile, True), ('desktop', b.set_desktop, False)):
        setup()
        nav = b.navigate('#/akis/gundem')
        assert_clean_nav(nav)
        ensure_akis_rows(b)
        clicked = b.eval("""(() => {
          const row = document.querySelector('#ana [data-id]');
          if (!row) return null;
          const id = row.dataset.id;
          const link = row.querySelector('h2 a, h3 a') || row;
          link.click();
          return id;
        })()""")
        assert clicked, f'No story row found on {mode}'
        b.wait_for("document.getElementById('panel')?.open")
        st = b.eval("""((id) => {
          const p = document.getElementById('panel');
          const okundu = JSON.parse(localStorage.getItem('akis-okundu') || '{}');
          return {
            open: p.open,
            modal: p.matches(':modal'),
            panelId: p.dataset.id,
            hash: location.hash,
            markedRead: Boolean(okundu[id]),
          };
        })(%s)""" % json.dumps(clicked))
        assert st['open'] and st['panelId'] == clicked, f'{mode} drawer state mismatch: {st}'
        assert st['modal'] is expect_modal, f'{mode} expected modal={expect_modal}, got {st}'
        assert st['markedRead'], f'{mode} opening story did not mark akis-okundu'
        assert 'k=' in st['hash'], f'{mode} URL did not include ?k= param: {st["hash"]}'

        b.click('#panel [data-act="kapat"]')
        b.wait_for("!document.getElementById('panel')?.open")
        hash_after = b.eval('location.hash')
        assert 'k=' not in hash_after, f'{mode} ?k= not cleared after close: {hash_after}'
        assert_clean_diag(b)


@e2e_test('E3_T1_02', 1, 'E3', 'Saving an item persists akis-kayit + akis2-durum and shows in #/kayit')
def test_e3_save_and_kayit_persistence(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/akis/gundem')
    assert_clean_nav(nav)
    ensure_akis_rows(b)
    sid = b.eval("document.querySelector('#ana [data-id]')?.dataset.id")
    assert sid, 'No story found to save'
    b.click('#ana [data-id] h3 a, #ana [data-id] h2 a')
    b.wait_for("document.getElementById('panel')?.open")
    b.click('#panel [data-act="kaydet"]')
    st = b.eval("""((id) => ({
      kayit: JSON.parse(localStorage.getItem('akis-kayit') || '{}')[id],
      durum: JSON.parse(localStorage.getItem('akis2-durum') || '{}')[id],
    }))(%s)""" % json.dumps(sid))
    assert st['kayit'], 'akis-kayit missing saved item'
    assert st['durum'] and st['durum']['d'] == 'kaydedildi', f'akis2-durum mismatch: {st["durum"]}'

    rel = b.navigate('#/kayit', reset_storage=False)
    assert_clean_nav(rel)
    present = b.eval(f"Boolean(document.querySelector('#ana [data-id=' + {json.dumps(sid)} + ']'))")
    assert present, f'Saved item {sid} not displayed in #/kayit after navigation'


@e2e_test('E3_T1_03', 1, 'E3', 'Hiding an item removes it, writes akis-gizli, and Geri al toast restores it')
def test_e3_hide_and_undo(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/akis/gundem')
    assert_clean_nav(nav)
    ensure_akis_rows(b)
    sid = b.eval("document.querySelector('#ana [data-id]')?.dataset.id")
    assert sid, 'No story found to hide'
    b.click('#ana [data-id] h3 a, #ana [data-id] h2 a')
    b.wait_for("document.getElementById('panel')?.open")
    b.click('#panel [data-act="gizle"]')
    after_hide = b.eval("""((id) => ({
      inDom: Boolean(document.querySelector('#ana [data-id="' + id + '"]')),
      gizli: Boolean(JSON.parse(localStorage.getItem('akis-gizli') || '{}')[id]),
      undoBtn: Boolean(document.querySelector('#toast [data-act="geri"]')),
    }))(%s)""" % json.dumps(sid))
    assert not after_hide['inDom'], 'Hidden item still present in DOM'
    assert after_hide['gizli'], 'akis-gizli did not record hidden item'
    assert after_hide['undoBtn'], 'Undo button Geri al missing in toast'

    b.click('#toast [data-act="geri"]')
    after_undo = b.eval("""((id) => ({
      inDom: Boolean(document.querySelector('#ana [data-id="' + id + '"]')),
      gizli: Boolean(JSON.parse(localStorage.getItem('akis-gizli') || '{}')[id]),
    }))(%s)""" % json.dumps(sid))
    assert after_undo['inDom'], 'Undo Geri al did not restore item to DOM'
    assert not after_undo['gizli'], 'Undo Geri al did not clear akis-gizli'


@e2e_test('E3_T1_04', 1, 'E3', 'Workflow status change and note entry persist across reload')
def test_e3_status_and_note_persistence(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/akis/gundem')
    assert_clean_nav(nav)
    ensure_akis_rows(b)
    sid = b.eval("document.querySelector('#ana [data-id]')?.dataset.id")
    assert sid, 'No story found'
    b.click('#ana [data-id] h3 a, #ana [data-id] h2 a')
    b.wait_for("document.getElementById('panel')?.open")
    b.eval("""(() => {
      const sel = document.querySelector('#panel select[data-act="durum"]');
      sel.value = 'senaryo-hazir';
      sel.dispatchEvent(new Event('change', { bubbles: true }));
      const ta = document.querySelector('#panel textarea[data-not]');
      ta.value = 'E2E test notu: somut giris';
      ta.dispatchEvent(new Event('input', { bubbles: true }));
    })()""")
    b.wait_for("""(() => {
      const n = JSON.parse(localStorage.getItem('akis2-not') || '{}');
      return Object.values(n).some(v => String(v).includes('E2E test notu'));
    })()""")
    rel = b.reload()
    assert_clean_nav(rel)
    st = b.eval("""((id) => ({
      durum: JSON.parse(localStorage.getItem('akis2-durum') || '{}')[id]?.d,
      notText: JSON.parse(localStorage.getItem('akis2-not') || '{}')[id] || '',
    }))(%s)""" % json.dumps(sid))
    assert st['durum'] == 'senaryo-hazir', f'Status did not persist: {st}'
    assert 'E2E test notu' in st['notText'], f'Note did not persist: {st}'


@e2e_test('E3_T1_05', 1, 'E3', 'Search modal filters with Turkish-folded matching and opens drawer')
def test_e3_search_turkish_fold(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/bugun')
    assert_clean_nav(nav)
    b.click('#araAc')
    b.wait_for("document.getElementById('arama')?.open")
    # Wait for indeks.json load so results include clusters
    b.eval("""(() => {
      const inp = document.getElementById('araK');
      inp.value = 'turkiye';
      inp.dispatchEvent(new Event('input', { bubbles: true }));
    })()""")
    b.wait_for("document.querySelectorAll('#araS [data-act=\"araSec\"]').length > 0", timeout_ms=7000)
    res_count = b.eval("document.querySelectorAll('#araS [data-act=\"araSec\"]').length")
    assert res_count >= 1, 'Turkish-folded query "turkiye" yielded zero results'
    b.click('#araS [data-act="araSec"]')
    b.wait_for("document.getElementById('panel')?.open")
    assert b.eval("!document.getElementById('arama')?.open"), '#arama did not close after selecting result'
    assert_clean_diag(b)


@e2e_test('E3_T1_06', 1, 'E3', 'Bugun radar/summary sections accessible on 390px and non-overlapping on 1440px', gate='M3_F9')
def test_e3_bugun_ergonomics_and_panel_coordination(ctx):
    b = ctx.browser
    # 1. Mobile 390px: summary/radar sections should be reachable without scrolling past 25+ news rows
    b.set_mobile()
    nav = b.navigate('#/bugun')
    assert_clean_nav(nav)
    mob = b.eval("""(() => {
      const txt = document.getElementById('ana')?.textContent || '';
      const hasCopy = Boolean(document.querySelector('[data-act="brif"]'));
      const radarHeadings = Array.from(document.querySelectorAll('#ana h2, #ana button, #ana [role="tab"]'))
        .filter(el => /Aranıyor, yazan az|Güncelleme radarı|Reels için|Radar|Özet/i.test(el.textContent || ''));
      const firstRadarTop = radarHeadings.reduce((mn, el) => {
        const r = el.getBoundingClientRect();
        return r.height > 0 ? Math.min(mn, r.top) : mn;
      }, 99999);
      return {
        hasCopy,
        hasRadarText: /Aranıyor, yazan az|Güncelleme radarı|Reels için/.test(txt) || radarHeadings.length > 0,
        firstRadarTop: Math.round(firstRadarTop),
      };
    })()""")
    assert mob['hasCopy'], 'Missing "Günün özetini kopyala" button on #/bugun'
    assert mob['hasRadarText'], 'Missing Bugün radar/summary sections on mobile'
    assert mob['firstRadarTop'] <= 1500, (
        f"Mobile radar/summary is buried too far down (top={mob['firstRadarTop']}px)"
    )

    # 2. Desktop 1440px: opening #panel on #/bugun must NOT overlap .ray or #ana controls
    b.set_desktop()
    nav = b.navigate('#/bugun')
    assert_clean_nav(nav)
    b.click('#ana [data-id] h2 a, #ana [data-id] h3 a')
    b.wait_for("document.getElementById('panel')?.open")
    lay = b.inspect_layout()
    assert lay['panelOverlapCount'] == 0, (
        f"Desktop #panel overlaps #/bugun content/ray: {lay['panelOverlaps']}"
    )


# ============================================================================
# E4: #/kaynak Source Browser & Filters (5 tests)
# ============================================================================

@e2e_test('E4_T1_01', 1, 'E4', '#/kaynak renders source health counters matching kaynaklar.json')
def test_e4_kaynak_counters(ctx):
    kj = load_json('site/data/kaynaklar.json')
    total = len(kj['kaynaklar'])
    assert sum(kj['durum_say'].values()) == total

    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/kaynak')
    assert_clean_nav(nav)
    counts = b.eval("""(() => {
      const btns = Array.from(document.querySelectorAll('#ana [data-act="kdur"]'));
      return btns.map(el => ({
        v: el.dataset.v,
        n: parseInt((el.querySelector('b')?.textContent || '0').replace(/\\D/g, ''), 10),
        txt: el.textContent.trim(),
      }));
    })()""")
    assert len(counts) == 4, f'Expected 4 status counter buttons, got {counts}'
    assert sum(x['n'] for x in counts) == total, (
        f"Sum of #/kaynak counters ({sum(x['n'] for x in counts)}) != kaynaklar.json total ({total})"
    )


@e2e_test('E4_T1_02', 1, 'E4', '#/kaynak switches between grouped and table view on desktop and mobile')
def test_e4_kaynak_grouped_vs_table(ctx):
    b = ctx.browser
    for mode, setup in (('desktop', b.set_desktop), ('mobile', b.set_mobile)):
        setup()
        nav = b.navigate('#/kaynak')
        assert_clean_nav(nav)
        b.click('[data-act="kgor"][data-v="tablo"]')
        has_table = b.eval("document.querySelectorAll('#ana table tbody tr').length > 0")
        assert has_table, f'{mode} table view has no rows'
        lay = b.inspect_layout()
        assert not lay['horizontalOverflow'], f'{mode} table view overflowed horizontally: {lay}'

        b.click('[data-act="kgor"][data-v="grup"]')
        has_groups = b.eval("document.querySelectorAll('#ana section').length > 0")
        assert has_groups, f'{mode} grouped view has no sections'


@e2e_test('E4_T1_03', 1, 'E4', '#/kaynak search, priority, category, layer filters narrow and Temizle resets')
def test_e4_kaynak_filters_and_reset(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/kaynak')
    assert_clean_nav(nav)
    initial_n = b.eval("""(() => {
      const m = (document.querySelector('#kSonuc .sayac b')?.textContent || '').replace(/\\D/g, '');
      return parseInt(m || '0', 10);
    })()""")
    assert initial_n > 100

    b.click('[data-act="konc"][data-v="1"]')
    b.click('[data-act="kalan"][data-v="tekno"]')
    b.click('[data-act="ktip"][data-v="editoryal"]')
    filtered_n = b.eval("""(() => {
      const m = (document.querySelector('#kSonuc .sayac b')?.textContent || '').replace(/\\D/g, '');
      return parseInt(m || '0', 10);
    })()""")
    assert 0 < filtered_n < initial_n, f'Expected 0 < {filtered_n} < {initial_n}'

    b.click('[data-act="kSifirla"]')
    reset_n = b.eval("""(() => {
      const m = (document.querySelector('#kSonuc .sayac b')?.textContent || '').replace(/\\D/g, '');
      return parseInt(m || '0', 10);
    })()""")
    assert reset_n == initial_n, f'Expected reset count {initial_n}, got {reset_n}'


@e2e_test('E4_T1_04', 1, 'E4', 'Mobile 390px #/kaynak filters are compact/collapsible and do not clip Ek (P3)', gate='M3_F11')
def test_e4_mobile_kaynak_filters_no_clip_and_collapsible(ctx):
    b = ctx.browser
    b.set_mobile()
    nav = b.navigate('#/kaynak')
    assert_clean_nav(nav)
    lay = b.inspect_layout()
    assert lay['clippedCount'] == 0, f"Mobile #/kaynak clipped controls (e.g. Ek P3): {lay['clipped']}"

    info = b.eval("""(() => {
      const toggle = document.querySelector('#ana [data-act="kSuzAc"]');
      const res = document.getElementById('kSonuc');
      const resTop = res ? res.getBoundingClientRect().top : 9999;
      return {
        collapsed: toggle ? toggle.getAttribute('aria-expanded') === 'false' : false,
        resTop: Math.round(resTop),
      };
    })()""")
    assert info['collapsed'] or info['resTop'] <= 680, (
        f"Mobile #/kaynak filter panel too tall/uncollapsed before source list: {info}"
    )
    # Also expand filters (if collapsible) and verify Ek (P3) and all filter controls remain unclipped
    if info['collapsed']:
        b.click('#ana [data-act="kSuzAc"]')
        lay2 = b.inspect_layout()
        assert lay2['clippedCount'] == 0, f"Mobile #/kaynak clipped controls when expanded: {lay2['clipped']}"
    p3_ok = b.eval("""(() => {
      const p3 = Array.from(document.querySelectorAll('#ana button')).find(el => /Ek \\(P3\\)/.test(el.textContent || ''));
      if (!p3) return false;
      const r = p3.getBoundingClientRect();
      return r.width > 0 && r.height > 0 && r.left >= -1 && r.right <= window.innerWidth + 1;
    })()""")
    assert p3_ok, 'Ek (P3) button missing or clipped outside 390px viewport'


@e2e_test('E4_T1_05', 1, 'E4', '#/kaynak grouped category counts reflect full filtered set accurately', gate='M3_F11')
def test_e4_kaynak_grouped_counts_accurate(ctx):
    kj = load_json('site/data/kaynaklar.json')
    by_cal = {}
    for s in kj['kaynaklar']:
        c = s.get('calisma') or 'gundem'
        by_cal[c] = by_cal.get(c, 0) + 1

    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/kaynak')
    assert_clean_nav(nav)
    groups = b.eval("""(() => {
      return Array.from(document.querySelectorAll('#kSonuc .k-grup, #kSonuc section')).map(sec => ({
        title: (sec.querySelector('h2')?.textContent || '').trim(),
        say: (sec.querySelector('.say')?.textContent || '').trim(),
      }));
    })()""")
    assert len(groups) == len(by_cal), (
        f"Expected all {len(by_cal)} categories in grouped #/kaynak view, got {len(groups)} "
        f"(pre-group slice(0, 80) truncation bug)"
    )
    reported_sum = 0
    for g in groups:
        m = re.search(r'(\d+)\s*kaynak', g['say'])
        assert m, f'Missing count in group header: {g}'
        reported_sum += int(m.group(1))
    assert reported_sum == len(kj['kaynaklar']), (
        f'Grouped category header sum ({reported_sum}) != total sources ({len(kj["kaynaklar"])})'
    )


# ============================================================================
# E5: Protected Browser/Template Contracts & Okan/Pırıl Isolation (5 tests)
# ============================================================================

@e2e_test('E5_T1_01', 1, 'E5', 'site/index.html embeds id="snap" once with valid schema and zero /*SNAP*/')
def test_e5_snap_contract(ctx):
    html_path = os.path.join(KOK, 'site', 'index.html')
    with open(html_path, encoding='utf-8') as f:
        html = f.read()
    snap_cnt = html.count('id="snap"')
    assert snap_cnt == 1, f'Expected id="snap" once, got {snap_cnt}'
    assert '/*SNAP*/' not in html, 'Unreplaced /*SNAP*/ placeholder in site/index.html'
    snap = parse_snap(html)
    assert snap.get('generated'), 'snap.generated missing'
    assert isinstance(snap.get('saglik'), dict) and snap['saglik'], 'snap.saglik invalid'
    assert isinstance(snap.get('feeds'), dict) and len(snap['feeds']) >= 50, 'snap.feeds missing/small'
    for sid, feed in list(snap['feeds'].items())[:30]:
        assert {'name', 'lang', 'cat', 'plat', 'items'} <= set(feed.keys()), f'Missing keys in snap feed {sid}'
        for it in feed['items'][:20]:
            assert {'l', 't'} <= set(it.keys()), f'Item missing l/t in {sid}'
            assert set(it.keys()) <= {'l', 'd', 't', 's', 'i', 'p', 'c', 'n'}, f'Unexpected keys in {sid}'
            if sid.startswith('trends-'):
                assert 'n' not in it, f'trends-* snap item still has stripped key n: {sid}'


@e2e_test('E5_T1_02', 1, 'E5', 'site/masa.json valid schema with 12 konular, 17 KUME keys, reels <= ids')
def test_e5_masa_contract(ctx):
    m = load_json('site/masa.json')
    ust = {'generated', 'saglik', 'konular', 'kumeler', 'reels', 'trendler', 'kaynaklar'}
    kume_keys = {'id', 't', 's', 'i', 'k', 'cat', 'dil', 'l', 'ks', 'son', 'ilk', 'hiz', 'r', 'ned', 'tur', 'elen', 'og'}
    assert ust <= set(m.keys()), f'Missing top-level masa.json keys: {ust - set(m.keys())}'
    assert len(m['konular']) == 12, f"Expected 12 konular in masa.json, got {len(m['konular'])}"
    assert len(m['kumeler']) > 0, 'Empty masa.json kumeler'
    for c in m['kumeler'][:100]:
        assert kume_keys <= set(c.keys()), f"Missing KUME keys in masa.json: {kume_keys - set(c.keys())}"
    ids = {c['id'] for c in m['kumeler']}
    assert set(m['reels']) <= ids, 'masa.json reels references unknown cluster IDs'


@e2e_test('E5_T1_03', 1, 'E5', 'piril.json & kisisel/piril/sources.json strictly non-TR and isolated')
def test_e5_piril_data_isolation(ctx):
    p = load_json('site/data/kisisel/piril.json')
    assert p.get('profil') == 'piril', f"Unexpected piril.json profil: {p.get('profil')}"
    assert p.get('ad') == 'Pırıl Cennet', f"Unexpected piril.json ad: {p.get('ad')}"
    assert len(p.get('kumeler', [])) > 0, 'piril.json kumeler empty'
    for c in p['kumeler']:
        assert c.get('dil') != 'tr', f"Turkish cluster leaked into piril.json: {c.get('t')}"
        for o in c.get('og', []):
            assert o.get('d') != 'tr', f"Turkish article leaked into piril.json: {o.get('t')}"

    psrc = load_json('kisisel/piril/sources.json')
    ana_src = load_json('sources.json')
    assert len(psrc) >= 60
    assert all(s['id'].startswith('pc-') and s['lang'] != 'tr' for s in psrc), 'piril sources violated pc-/non-tr'
    assert not any(s['id'].startswith('pc-') for s in ana_src), 'pc- IDs leaked into main sources.json'


@e2e_test('E5_T1_04', 1, 'E5', 'Okan controls hidden by default & on bad ?okan=, active on akis2-okx=1, off on ?okan=kapat')
def test_e5_okan_activation_and_dialogs(ctx):
    b = ctx.browser
    b.set_desktop()
    # 1. Default hidden
    nav = b.navigate('#/bugun')
    assert_clean_nav(nav)
    def_cnt = b.eval("document.querySelectorAll('[data-act=\"okxOto\"], [data-act=\"okxAc\"], [data-act=\"mOkx\"], a[href*=\"reels-sablonu\"]').length")
    assert def_cnt == 0, f'Okan controls visible by default: {def_cnt}'

    # 2. Wrong ?okan=yanlis-kod scrubs query & stays off
    nav2 = b.navigate('?okan=yanlis-kod#/bugun', reset_storage=True)
    assert_clean_nav(nav2)
    b.wait_for("!location.search.includes('okan=')")
    bad_st = b.eval("""({
      okx: localStorage.getItem('akis2-okx'),
      cnt: document.querySelectorAll('[data-act="okxOto"], [data-act="okxAc"]').length,
    })""")
    assert bad_st['okx'] is None and bad_st['cnt'] == 0, f'Bad ?okan= leaked state: {bad_st}'

    # 3. Activated via AKIS_OKAN_KOD env (if provided) or persisted akis2-okx=1
    kod = os.environ.get('AKIS_OKAN_KOD', '')
    if kod:
        nav3 = b.navigate(f'?okan={kod}#/bugun', reset_storage=True)
        assert_clean_nav(nav3)
        b.wait_for("localStorage.getItem('akis2-okx') === '1'")
    else:
        nav3 = b.navigate('#/bugun', reset_storage=True, pre_storage={'akis2-okx': '1'})
        assert_clean_nav(nav3)

    assert b.eval("Boolean(document.querySelector('[data-act=\"okxOto\"]'))"), 'okxOto button missing on #/bugun'

    # Open #okxD from detail drawer on #/akis/gundem and save draft
    b.set_hash('#/akis/gundem')
    ensure_akis_rows(b)
    b.click('#ana [data-id] h3 a, #ana [data-id] h2 a')
    b.wait_for("document.getElementById('panel')?.open")
    b.click('#panel [data-act="okxAc"]')
    b.wait_for("document.getElementById('okxD')?.open")
    for plat in ('en', 'fb', 'x'):
        b.click(f'#okxD [data-act="okxPl"][data-v="{plat}"]')
    b.click('#okxD [data-act="okxKaydet"]')
    saved_drafts = b.eval("JSON.parse(localStorage.getItem('akis2-okx-taslak') || '[]').length")
    assert saved_drafts >= 1, 'Okan draft failed to save to akis2-okx-taslak'
    b.click('#okxD [data-act="okxKapat"]')

    # Check reels-sablonu link on #/reels
    b.set_hash('#/reels')
    assert b.eval("Boolean(document.querySelector('a[href*=\"reels-sablonu.html\"]'))"), 'Okan reels-sablonu link missing'

    # 4. ?okan=kapat disables cleanly
    nav4 = b.navigate('?okan=kapat#/bugun', reset_storage=False)
    assert_clean_nav(nav4)
    off_st = b.eval("""({
      okx: localStorage.getItem('akis2-okx'),
      cnt: document.querySelectorAll('[data-act="okxOto"], [data-act="okxAc"]').length,
    })""")
    assert off_st['okx'] == '0' and off_st['cnt'] == 0, f'?okan=kapat failed to disable: {off_st}'


@e2e_test('E5_T1_05', 1, 'E5', 'Pırıl profile hides ALL Okan controls even when akis2-okx=1, zero X API secrets')
def test_e5_piril_blocks_okan_and_zero_secrets(ctx):
    html_text = open(os.path.join(KOK, 'site', 'index.html'), encoding='utf-8').read()
    for secret in ('api.x.com', 'api.twitter.com', 'Bearer ', 'oauth_consumer', 'client_secret'):
        assert secret not in html_text, f'Forbidden API secret/endpoint {secret!r} found in site/index.html'

    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/piril', reset_storage=True, pre_storage={'akis2-okx': '1'})
    assert_clean_nav(nav)
    b.click('#ana [data-id] h3 a, #ana [data-id] h2 a')
    b.wait_for("document.getElementById('panel')?.open")
    b.click('#panel [data-act="kaydet"]')
    okx_els = visible_okx_count(b)
    kayit_keys = b.eval("Object.keys(JSON.parse(localStorage.getItem('akis-kayit') || '{}'))")
    assert okx_els == 0, f'Okan controls leaked on #/piril: {okx_els}'
    assert kayit_keys and all(k.startswith('pc:') for k in kayit_keys), (
        f'Expected pc: prefix on Pırıl saved keys: {kayit_keys}'
    )


# ============================================================================
# E6: sources.json Integrity, cat Immutability & Expansion (5 tests)
# ============================================================================

@e2e_test('E6_T1_01', 1, 'E6', 'All 439 legacy source IDs preserved, IDs unique, URLs valid http(s)')
def test_e6_legacy_ids_and_urls(ctx):
    src = load_json('sources.json')
    eski = set(load_json('tests/fixtures/eski-kaynak-idleri.json'))
    ids = [s['id'] for s in src]
    assert len(ids) == len(set(ids)), 'Duplicate source IDs in sources.json'
    missing = eski - set(ids)
    assert not missing, f'Legacy source IDs deleted: {sorted(missing)[:10]}'
    for s in src:
        assert re.match(r'^https?://', s['url']), f"Invalid URL in {s['id']}: {s['url']}"


@e2e_test('E6_T1_02', 1, 'E6', 'cat values immutable vs baseline 214dce51 and in canonical 14-cat set')
def test_e6_cat_immutability(ctx):
    src = load_json('sources.json')
    for s in src:
        assert s.get('cat') in CAT_CANON, f"Unexpected cat {s.get('cat')!r} on {s['id']}"
    rc, out, err = git_cmd('show', '214dce51:sources.json')
    assert rc == 0, f'git show 214dce51:sources.json failed: {err}'
    base = {s['id']: s['cat'] for s in json.loads(out)}
    changed = [(s['id'], base[s['id']], s['cat']) for s in src if s['id'] in base and s['cat'] != base[s['id']]]
    assert not changed, f'Source cat values were modified: {changed[:10]}'


@e2e_test('E6_T1_03', 1, 'E6', 'Zero ShiftDelete anywhere in sources.json')
def test_e6_zero_shiftdelete_sources(ctx):
    src = load_json('sources.json')
    hits = [s['id'] for s in src if re.search(r'shift\s*delete', s['id'] + s['name'] + s['url'], re.I)]
    assert not hits, f'ShiftDelete found in sources.json: {hits}'


@e2e_test('E6_T1_04', 1, 'E6', 'Every new source (post-fixture) carries valid dogrulama metadata')
def test_e6_new_sources_dogrulama(ctx):
    src = load_json('sources.json')
    eski = set(load_json('tests/fixtures/eski-kaynak-idleri.json'))
    for s in src:
        if s['id'] in eski:
            continue
        d = s.get('dogrulama')
        assert isinstance(d, dict), f"New source {s['id']} missing dogrulama dict"
        assert d.get('durum') in ('gecti', 'bekliyor'), f"Invalid dogrulama.durum on {s['id']}: {d}"
        assert re.match(r'^\d{4}-\d{2}-\d{2}', str(d.get('tarih', ''))), f"Invalid dogrulama.tarih on {s['id']}"
        if d['durum'] == 'gecti':
            assert int(d.get('n', 0)) >= 3, f"dogrulama.n < 3 on {s['id']}: {d}"


@e2e_test('E6_T1_05', 1, 'E6', 'Active source count strictly exceeds 214dce51 baseline (781) with thin-cat expansion', gate='M1_F2')
def test_e6_active_source_expansion(ctx):
    src = load_json('sources.json')
    rc, out, _ = git_cmd('show', '214dce51:sources.json')
    base = json.loads(out) if rc == 0 else []
    base_active = sum(1 for s in base if s.get('aktif', True)) or 781
    cur_active = sum(1 for s in src if s.get('aktif', True))
    assert cur_active > base_active, f'Expected active sources > {base_active}, got {cur_active}'
    thin = ('adana', 'oyun', 'oto', 'siber', 'yz', 'ekonomi')
    base_thin = {c: sum(1 for s in base if s.get('aktif', True) and s.get('calisma') == c) for c in thin}
    cur_thin = {c: sum(1 for s in src if s.get('aktif', True) and s.get('calisma') == c) for c in thin}
    expanded = [c for c in thin if cur_thin[c] > base_thin.get(c, 0)]
    assert len(expanded) >= 4, f'Expected net expansion in >=4 thin categories; base={base_thin}, cur={cur_thin}'


# ============================================================================
# E7: Generated Data & Size Boundaries (5 tests)
# ============================================================================

@e2e_test('E7_T1_01', 1, 'E7', 'All 13 kume-<alan>.json files exist and each is < 1100 KB')
def test_e7_kume_files_and_size(ctx):
    cap = 1100 * 1024
    for a in ALANLAR_CANON:
        rel = f'site/data/kume-{a}.json'
        full = os.path.join(KOK, rel)
        assert os.path.isfile(full), f'Missing {rel}'
        sz = file_size(rel)
        assert sz < cap, f'{rel} exceeds 1100 KB: {sz} bytes'


@e2e_test('E7_T1_02', 1, 'E7', 'ozet.json < 450 KB and every dil-<k>.json < 700 KB with <= 150 clusters')
def test_e7_ozet_and_dil_caps(ctx):
    assert file_size('site/data/ozet.json') < 450 * 1024, 'ozet.json >= 450 KB'
    dl = load_json('site/data/diller.json')['diller']
    assert dl, 'diller.json empty'
    for x in dl:
        rel = f"site/data/dil-{x['k']}.json"
        assert file_size(rel) < 700 * 1024, f'{rel} >= 700 KB'
        d = load_json(rel)
        assert len(d['kumeler']) <= 150, f'{rel} has > 150 clusters'
        assert all(c['dil'] == x['k'] for c in d['kumeler']), f'{rel} language mismatch'


@e2e_test('E7_T1_03', 1, 'E7', 'All required site/data/*.json files valid and synchronized with masa.json')
def test_e7_required_json_and_freshness(ctx):
    req = {
        'ozet.json': ('generated', 'sicak', 'yukselen', 'son', 'sayim', 'alanlar', 'toplam'),
        'reels.json': ('generated', 'adaylar', 'elenen', 'kriterler', 'not_'),
        'kaynaklar.json': ('generated', 'saglik', 'kaynaklar', 'durum_say'),
        'trendler.json': ('generated', 'sira', 'ulkeler'),
        'guncellemeler.json': ('generated', 'urunler', 'turler', 'gun'),
        'videolar.json': ('generated', 'videolar', 'kanallar'),
        'diller.json': ('generated', 'diller'),
        'surum.json': ('generated',),
        'indeks.json': ('generated', 'kayitlar'),
    }
    for fn, keys in req.items():
        data = load_json(f'site/data/{fn}')
        for k in keys:
            assert k in data, f'Missing key {k!r} in site/data/{fn}'
    oz_gen = load_json('site/data/ozet.json')['generated']
    masa_gen = load_json('site/masa.json')['generated']
    assert oz_gen == masa_gen, (
        f'Stale site/data/ detected: ozet.json generated={oz_gen} != masa.json generated={masa_gen}'
    )


@e2e_test('E7_T1_04', 1, 'E7', 'Zero ShiftDelete across identity fields in site/data/*.json, masa.json, feeds.json')
def test_e7_zero_shiftdelete_outputs(ctx):
    rx = re.compile(r'shift\s*delete', re.I)
    id_keys = {'p', 'kaynak', 'ad', 'l', 'url', 'name', 'id'}

    def scan(node, path=''):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in id_keys and isinstance(v, str) and rx.search(v):
                    return f'{path}/{k}: {v}'
                if k in ('kaynaklar', 'k') and isinstance(v, list):
                    for x in v:
                        if isinstance(x, str) and rx.search(x):
                            return f'{path}/{k}[]: {x}'
                hit = scan(v, f'{path}/{k}')
                if hit:
                    return hit
        elif isinstance(node, list):
            for v in node:
                hit = scan(v, f'{path}[]')
                if hit:
                    return hit
        return None

    data_dir = os.path.join(KOK, 'site', 'data')
    for fn in sorted(os.listdir(data_dir)):
        if fn.endswith('.json'):
            hit = scan(load_json(f'site/data/{fn}'), fn)
            assert not hit, f'ShiftDelete leaked in {hit}'
    for fn in ('site/masa.json', 'site/feeds.json'):
        if os.path.isfile(os.path.join(KOK, fn)):
            hit = scan(load_json(fn), fn)
            assert not hit, f'ShiftDelete leaked in {hit}'


@e2e_test('E7_T1_05', 1, 'E7', 'Repo boundary: zero staged site/ files and site/data/ is gitignored')
def test_e7_repo_boundary(ctx):
    rc, out, err = git_cmd('diff', '--cached', '--name-only', '--', 'site/')
    assert rc == 0, f'git diff failed: {err}'
    assert not out.strip(), f'Staged files found under site/: {out.strip()}'
    rc2, _, _ = git_cmd('check-ignore', '-q', 'site/data/')
    assert rc2 == 0, 'site/data/ is not ignored by .gitignore'


# ============================================================================
# E8: Reels Quality, Hooks, Scoring Fairness & Disclaimers (5 tests)
# ============================================================================

@e2e_test('E8_T1_01', 1, 'E8', 'reels.json schema, total/profile caps, weights=100, required card fields')
def test_e8_reels_schema(ctx):
    r = load_json('site/data/reels.json')
    adaylar = r['adaylar']
    assert 0 < len(adaylar) <= 40, f'Expected 1..40 adaylar, got {len(adaylar)}'
    prof_counts = {}
    req_fields = {
        'id', 't', 'oneri_baslik', 'ozet', 'neden_gundemde', 'carpici_ayrinti',
        'turk_onemi', 'dogrulama', 'gorsel_potansiyel', 'hooklar', 'aci',
        'aci_etiket', 'anlatim', 'guc', 'puan', 'puan_gerekce', 'risk',
        'profil', 'alanlar', 'kb', 'kriter',
    }
    for c in adaylar:
        missing = req_fields - set(c.keys())
        assert not missing, f"Reels card {c.get('id')} missing fields: {missing}"
        assert len(c['hooklar']) == 3 and all(isinstance(h, str) and h.strip() for h in c['hooklar']), c['id']
        assert c['guc'] in (1, 2, 3), f"Invalid guc on {c['id']}: {c['guc']}"
        for p in c['profil']:
            prof_counts[p] = prof_counts.get(p, 0) + 1
    assert max(prof_counts.values()) <= 15, f'Profile cap > 15 exceeded: {prof_counts}'
    assert sum(k['w'] for k in r['kriterler']) == 100, 'Reels criteria weights do not sum to 100'


@e2e_test('E8_T1_02', 1, 'E8', 'Zero "3 saniyede özet:" template openers in reels.json hooklar', gate='M2_F4')
def test_e8_no_3_saniyede_ozet(ctx):
    r = load_json('site/data/reels.json')
    bad = [
        (c['id'], h)
        for c in r['adaylar']
        for h in c.get('hooklar', [])
        if '3 saniyede özet' in h.lower()
    ]
    assert not bad, f'Found {len(bad)} "3 saniyede özet" hooks, e.g.: {bad[:3]}'


@e2e_test('E8_T1_03', 1, 'E8', 'Zero question hooks or forbidden filler in reels.json hooklar', gate='M2_F4')
def test_e8_no_question_hooks_or_filler(ctx):
    r = load_json('site/data/reels.json')
    filler_rx = re.compile(
        r'arkadaşlar|inanamayacaksınız|beğenmeyi unutmayın|yorumlara yaz|sana ne etkisi var\?|hiç düşündünüz mü',
        re.I,
    )
    q_hooks = []
    filler_hooks = []
    for c in r['adaylar']:
        for h in c.get('hooklar', []):
            hs = h.strip()
            if '?' in hs:
                q_hooks.append((c['id'], hs))
            if filler_rx.search(hs):
                filler_hooks.append((c['id'], hs))
    assert not q_hooks, f'Found {len(q_hooks)} question hooks (forbidden by SENARYO.md), e.g.: {q_hooks[:3]}'
    assert not filler_hooks, f'Found forbidden filler in hooks: {filler_hooks[:3]}'


@e2e_test('E8_T1_04', 1, 'E8', 'No viral guarantee phrasing and numbers in aci/hooklar trace to source stats')
def test_e8_disclaimer_and_no_fake_numbers(ctx):
    r = load_json('site/data/reels.json')
    assert 'viral garantisi değildir' in r.get('not_', '').lower(), (
        f"reels.json not_ missing non-guarantee disclaimer: {r.get('not_')!r}"
    )
    for c in r['adaylar']:
        source_blob = ' '.join([
            c.get('t', ''),
            c.get('ozet', ''),
            c.get('carpici_ayrinti', ''),
            str(c.get('kb', '')),
            str(c.get('ks', '')),
            str(c.get('h6', '')),
            ' '.join(o.get('t', '') for o in c.get('og', [])),
        ])
        source_norm = re.sub(r'[.,]', '', source_blob)
        for n in re.findall(r'\d+', c.get('aci', '')):
            assert n in source_blob or n in source_norm, (
                f"Number {n!r} in aci not traceable to source: {c['aci']!r}"
            )
        for h in c.get('hooklar', []):
            for n in re.findall(r'\d+', h):
                assert n in source_blob or n in source_norm, (
                    f"Number {n!r} in hooklar not traceable to source: {h!r} (card {c['id']})"
                )

    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/reels')
    assert_clean_nav(nav)
    ui_txt = b.eval("document.getElementById('ana')?.textContent || ''")
    assert 'viral garantisi değildir' in ui_txt.lower(), 'Reels UI missing non-guarantee disclaimer'


@e2e_test('E8_T1_05', 1, 'E8', 'Reels adaylar free of war-casualty/lottery/SEO leaks and kb==1 crowding', gate='M2_F5_F6')
def test_e8_no_junk_misclassification_or_kb1_crowding(ctx):
    r = load_json('site/data/reels.json')
    adaylar = r['adaylar']
    war_rx = re.compile(r'askeri öldü|rosstat|cephede|hava saldırısında.*ölü|drone strike kills', re.I)
    junk_rx = re.compile(r'süper loto|sayısal loto|şans topu|on numara|vergi dairesi müdürlüğü|kimdir,\s*kaç yaşında', re.I)

    war_leaks = [
        c['t'] for c in adaylar
        if set(c.get('profil', [])) & {'teknoloji', 'siber'} and war_rx.search(c.get('t', ''))
    ]
    assert not war_leaks, f'War casualty items leaked into tech/siber Reels: {war_leaks}'

    junk_leaks = [c['t'] for c in adaylar if junk_rx.search(c.get('t', ''))]
    assert not junk_leaks, f'Junk lottery/tax/SEO items leaked into Reels: {junk_leaks}'

    kb1_non_official = [
        c for c in adaylar
        if c.get('kb', 0) <= 1 and 'resmî kaynaktan' not in (c.get('dogrulama') or '').lower()
    ]
    assert len(kb1_non_official) <= 2, (
        f'Too many kb==1 non-official items ({len(kb1_non_official)}/{len(adaylar)}) in Reels: '
        f"{[c['t'][:50] for c in kb1_non_official]}"
    )
