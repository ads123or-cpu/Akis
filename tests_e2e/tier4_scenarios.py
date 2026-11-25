"""Tier 4: Real-world multi-step end-to-end editorial & data/repo scenarios (6 scenarios)."""
import json
import os
import re
from harness import (
    KOK,
    assert_clean_diag,
    assert_clean_nav,
    e2e_test,
    file_size,
    git_cmd,
    load_json,
    parse_snap,
    visible_okx_count,
)


@e2e_test('T4_01', 4, 'E1', 'Scenario 1: Mobile 390px Bugun -> Reels -> modal #panel save/read -> reload -> #/kayit')
def test_t4_scenario1_mobile_editorial_flow(ctx):
    b = ctx.browser
    b.set_mobile()
    nav = b.navigate('#/bugun')
    assert_clean_nav(nav)
    lay1 = b.inspect_layout()
    assert not lay1['horizontalOverflow']

    res = b.set_hash('#/reels')
    assert_clean_nav(res)
    sid = b.eval("document.querySelector('#ana [data-id]')?.dataset.id")
    assert sid, 'No Reels card available'
    b.click('#ana [data-id] h3 a')
    b.wait_for("document.getElementById('panel')?.open")
    assert b.eval("document.getElementById('panel').matches(':modal')") is True

    b.click('#panel [data-act="kaydet"]')
    b.click('#panel [data-act="kapat"]')
    b.wait_for("!document.getElementById('panel')?.open")

    rel = b.reload()
    assert_clean_nav(rel)
    b.set_hash('#/kayit')
    persisted = b.eval("""((id) => ({
      inDom: Boolean(document.querySelector('#ana [data-id="' + id + '"]')),
      kayit: Boolean(JSON.parse(localStorage.getItem('akis-kayit') || '{}')[id]),
      okundu: Boolean(JSON.parse(localStorage.getItem('akis-okundu') || '{}')[id]),
    }))(%s)""" % json.dumps(sid))
    assert all(persisted.values()), f'Scenario 1 persistence incomplete: {persisted}'


@e2e_test('T4_02', 4, 'E3', 'Scenario 2: Desktop 1440px #/akis/gundem filter -> empty recovery -> side #panel', gate='M3_F10')
def test_t4_scenario2_desktop_akis_recovery_and_panel(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/akis/gundem')
    assert_clean_nav(nav)

    # Narrow to 1h + 3+ sources or hide remaining rows to reach empty state
    b.eval("""(() => {
      const suz = document.querySelector('[data-act="suzAc"][aria-expanded="false"]');
      if (suz) suz.click();
    })()""")
    b.click('[data-act="zaman"][data-v="1"]')
    b.click('[data-act="cok"]')
    if b.eval("document.querySelectorAll('#ana [data-id]').length > 0"):
        b.eval("""(() => {
          document.querySelectorAll('#ana [data-id]').forEach(el => {
            const btn = el.querySelector('[data-act="gizle"]');
            if (btn) btn.click();
          });
        })()""")
        b.wait_for("document.querySelectorAll('#ana [data-id]').length === 0")

    # Click inline recovery CTA
    has_cta = b.eval("Boolean(document.querySelector('#ana .bosluk button, #ana [role=\"alert\"] button'))")
    assert has_cta, 'Scenario 2: empty state missing inline recovery CTA'
    b.click('#ana .bosluk button, #ana [role="alert"] button')
    b.wait_for("document.querySelectorAll('#ana [data-id]').length > 0", timeout_ms=4000)

    # Open cluster in side #panel and verify non-overlap + sources list
    b.click('#ana [data-id] h3 a')
    b.wait_for("document.getElementById('panel')?.open")
    b.wait_for("document.querySelectorAll('#panel .kay a').length > 0", timeout_ms=6000)
    lay = b.inspect_layout()
    assert not lay['horizontalOverflow'] and lay['panelOverlapCount'] == 0, f'Scenario 2 layout error: {lay}'


@e2e_test('T4_03', 4, 'E4', 'Scenario 3: Mobile 390px #/kaynak filter, Tablo/Gruplu toggle, zero clipping, accurate counts', gate='M3_F11')
def test_t4_scenario3_mobile_kaynak_admin(ctx):
    b = ctx.browser
    b.set_mobile()
    nav = b.navigate('#/kaynak')
    assert_clean_nav(nav)
    lay = b.inspect_layout()
    assert not lay['horizontalOverflow'] and lay['clippedCount'] == 0, f'Scenario 3 initial layout fail: {lay}'

    # Expand collapsible mobile filters if collapsed before interacting
    b.eval("""(() => {
      const t = document.querySelector('#ana [data-act="kSuzAc"][aria-expanded="false"]');
      if (t) t.click();
    })()""")
    # Filter by layer and area
    b.click('[data-act="ktip"][data-v="editoryal"]')
    b.click('[data-act="kalan"][data-v="tekno"]')
    b.click('[data-act="kgor"][data-v="tablo"]')
    assert b.eval("document.querySelectorAll('#ana table tbody tr').length > 0")
    lay_tbl = b.inspect_layout()
    assert not lay_tbl['horizontalOverflow']

    b.click('[data-act="kgor"][data-v="grup"]')
    b.click('[data-act="kSifirla"]')
    kj = load_json('site/data/kaynaklar.json')
    expected_cats = {s.get('calisma') or 'gundem' for s in kj['kaynaklar']}
    groups_n = b.eval("document.querySelectorAll('#kSonuc .k-grup, #kSonuc section').length")
    assert groups_n == len(expected_cats), f'Scenario 3 grouped categories {groups_n} != {len(expected_cats)}'


@e2e_test('T4_04', 4, 'E5', 'Scenario 4: Okan #/reels -> ?okan mode -> #okxD & #okxO -> #/piril hiding -> ?okan=kapat')
def test_t4_scenario4_okan_editorial_workflow(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/reels', reset_storage=True, pre_storage={'akis2-okx': '1'}, intercept_window_open=True)
    assert_clean_nav(nav)
    reels_txt = b.eval("document.getElementById('ana')?.textContent || ''")
    assert 'viral garantisi değildir' in reels_txt.lower()
    assert b.eval("Boolean(document.querySelector('#ana a[href*=\"reels-sablonu.html\"]'))")

    # Open #okxD from Reels card detail drawer
    b.click('#ana [data-id] h3 a')
    b.wait_for("document.getElementById('panel')?.open")
    b.click('#panel [data-act="okxAc"]')
    b.wait_for("document.getElementById('okxD')?.open")
    b.eval("document.getElementById('okxM').value = '[eksik]'; document.getElementById('okxM').dispatchEvent(new Event('input', {bubbles:true}));")
    b.click('#okxD [data-act="okxGit"]')
    assert b.eval("(window.__openedUrls || []).length === 0 && Boolean(document.querySelector('#okxL .hata'))")
    b.click('#okxD [data-act="okxKapat"]')

    # Navigate to #/bugun and open #okxO
    b.set_hash('#/bugun')
    b.click('[data-act="okxOto"]')
    b.wait_for("document.getElementById('okxO')?.open")
    b.click('#okxO [data-act="okxOKapat"]')

    # Switch to #/piril and confirm complete Okan hiding (even inside open #panel)
    b.set_hash('#/piril')
    assert visible_okx_count(b) == 0, 'Okan controls leaked on #/piril'
    b.click('#ana [data-id] h3 a, #ana [data-id] h2 a')
    b.wait_for("document.getElementById('panel')?.open")
    assert visible_okx_count(b) == 0, 'Okan controls leaked in #/piril open #panel'

    # Disable via ?okan=kapat
    b.navigate('?okan=kapat#/bugun', reset_storage=False)
    assert b.eval("localStorage.getItem('akis2-okx') === '0'")
    assert visible_okx_count(b) == 0, 'Okan controls stayed visible after ?okan=kapat'


@e2e_test('T4_05', 4, 'E7', 'Scenario 5: Full local data & repo sanity workflow (sources, caps, freshness, snap, reels, git)', gate='M1_M2_DATA')
def test_t4_scenario5_full_data_and_repo_sanity(ctx):
    # 1. sources.json integrity + zero ShiftDelete
    src = load_json('sources.json')
    assert not any(re.search(r'shift\s*delete', s['id'] + s['name'] + s['url'], re.I) for s in src)
    # 2. kume-*.json caps
    for fn in sorted(os.listdir(os.path.join(KOK, 'site', 'data'))):
        if fn.startswith('kume-') and fn.endswith('.json'):
            assert file_size(f'site/data/{fn}') < 1100 * 1024, fn
    # 3. ozet/masa freshness
    oz = load_json('site/data/ozet.json')
    masa = load_json('site/masa.json')
    assert oz['generated'] == masa['generated'], f"Stale site/data/: {oz['generated']} != {masa['generated']}"
    # 4. id="snap"
    html = open(os.path.join(KOK, 'site', 'index.html'), encoding='utf-8').read()
    assert html.count('id="snap"') == 1 and '/*SNAP*/' not in html
    snap = parse_snap(html)
    assert len(snap['feeds']) >= 50
    # 5. reels.json quality gates
    reels = load_json('site/data/reels.json')
    assert 'viral garantisi değildir' in reels.get('not_', '').lower()
    for c in reels['adaylar']:
        assert not any('3 saniyede özet' in h.lower() or '?' in h for h in c['hooklar']), (
            f"Baseline Reels hook defect on {c['id']}: {c['hooklar']}"
        )
    # 6. git staged site/ empty
    rc, out, _ = git_cmd('diff', '--cached', '--name-only', '--', 'site/')
    assert rc == 0 and not out.strip()


@e2e_test('T4_06', 4, 'E5', 'Scenario 6: Piril editorial session (390px & 1440px) -> filters -> pc: save/note -> default profile reload')
def test_t4_scenario6_piril_editorial_session(ctx):
    b = ctx.browser
    b.set_mobile()
    nav = b.navigate('#/piril', reset_storage=True, pre_storage={'akis2-okx': '1'})
    assert_clean_nav(nav)
    assert not b.inspect_layout()['horizontalOverflow']

    b.set_desktop()
    nav2 = b.navigate('#/piril', reset_storage=False)
    assert_clean_nav(nav2)
    b.click('[data-act="ptr"]')
    rows = b.eval("document.querySelectorAll('#ana [data-id]').length")
    if rows == 0:
        b.click('[data-act="ptr"]')  # unfilter if no turkey-related in sample
    sid = b.eval("document.querySelector('#ana [data-id]')?.dataset.id")
    assert sid, 'No Pırıl cluster available'
    b.click('#ana [data-id] h3 a')
    b.wait_for("document.getElementById('panel')?.open")
    b.click('#panel [data-act="kaydet"]')
    b.eval("""(() => {
      const ta = document.querySelector('#panel textarea[data-not]');
      ta.value = 'Piril notu';
      ta.dispatchEvent(new Event('input', { bubbles: true }));
    })()""")
    b.wait_for("Object.keys(JSON.parse(localStorage.getItem('akis2-not') || '{}')).some(k => k.startsWith('pc:'))")
    b.click('[data-act="pvars"][data-v="piril"]')

    # Reload root / -> should land directly on #/piril with zero Okan leaks
    rel = b.navigate('/', reset_storage=False)
    assert_clean_nav(rel)
    st = b.eval("""(() => ({
      h1: document.querySelector('#ana h1')?.textContent || '',
      okxEls: document.querySelectorAll('[data-act="okxOto"], [data-act="okxAc"], [data-act="mOkx"], a[href*="reels-sablonu"]').length,
      kayitKeys: Object.keys(JSON.parse(localStorage.getItem('akis-kayit') || '{}')),
      notKeys: Object.keys(JSON.parse(localStorage.getItem('akis2-not') || '{}')),
    }))()""")
    assert 'Pırıl' in st['h1'], f'Expected direct landing on Pırıl desk, got: {st}'
    assert st['okxEls'] == 0, f'Okan controls leaked on Pırıl reload: {st}'
    assert len(st['kayitKeys']) > 0, f'Expected saved pc: kayitKeys after saving in Piril, got: {st}'
    assert all(k.startswith('pc:') for k in st['kayitKeys']), f'Non-pc: kayit key: {st}'
    assert len(st['notKeys']) > 0, f'Expected saved pc: notKeys after adding note in Piril, got: {st}'
    assert all(k.startswith('pc:') for k in st['notKeys']), f'Non-pc: not key: {st}'
