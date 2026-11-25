"""Tier 3: Pairwise combinatorial E2E tests covering UI matrix and data/CI interactions (12 tests)."""
import json
import os
import subprocess
import sys
from harness import (
    KOK,
    assert_clean_nav,
    e2e_test,
    file_size,
    git_cmd,
    load_json,
    parse_snap,
    visible_okx_count,
)

PAIRWISE_CASES = [
    ('T3_01', 'E1', '390px', 'acik', 'akis', 'default', '#/bugun'),
    ('T3_02', 'E2', '390px', 'koyu', 'kartlar', 'okan', '#/reels'),
    ('T3_03', 'E3', '1440px', 'acik', 'basliklar', 'default', '#/akis/gundem'),
    ('T3_04', 'E2', '1440px', 'koyu', 'akis', 'okan', '#/dunya'),
    ('T3_05', 'E5', '390px', 'koyu', 'basliklar', 'piril', '#/piril'),
    ('T3_06', 'E5', '1440px', 'acik', 'kartlar', 'piril', '#/piril'),
    ('T3_07', 'E4', '390px', 'acik', 'kartlar', 'okan', '#/kaynak'),
    ('T3_08', 'E1', '1440px', 'koyu', 'basliklar', 'default', '#/guncelleme'),
]


def _make_pairwise_fn(tid, feat, vp, theme, view, profile, route):
    def fn(ctx):
        b = ctx.browser
        if vp == '390px':
            b.set_mobile()
        else:
            b.set_desktop()
        pre = {
            'akis2-ayar': json.dumps({
                'tema': theme,
                'gorunum': view,
                'profil': 'piril' if profile == 'piril' else '',
            }),
        }
        if profile == 'okan':
            pre['akis2-okx'] = '1'
        elif profile == 'piril':
            # Explicitly test Okan flag ON + Pırıl profile -> Okan must STILL be hidden
            pre['akis2-okx'] = '1'

        nav = b.navigate(route, reset_storage=True, pre_storage=pre)
        assert_clean_nav(nav)

        lay = b.inspect_layout()
        assert not lay['horizontalOverflow'], f'{tid} ({vp},{theme},{view},{profile},{route}) overflow: {lay}'
        assert lay['clippedCount'] == 0, f'{tid} clipped controls: {lay["clipped"]}'
        assert lay['overlapCount'] == 0, f'{tid} overlapping controls: {lay["overlaps"]}'

        th = b.inspect_theme()
        assert th['tema'] == theme, f'{tid} theme mismatch: {th}'
        if theme == 'acik':
            assert th['bgLum'] > 0.5, f'{tid} light luminance invalid: {th}'
        else:
            assert th['bgLum'] < 0.2, f'{tid} dark luminance invalid: {th}'

        body_classes = b.eval("Array.from(document.body.classList)")
        okx_count = visible_okx_count(b)
        assert f'g-{view}' in body_classes, f'{tid} missing g-{view} class: {body_classes}'
        if profile == 'piril' or profile == 'default':
            assert okx_count == 0, f'{tid} Okan controls leaked under profile={profile}: {okx_count}'
        elif profile == 'okan' and route in ('#/bugun', '#/reels'):
            assert okx_count >= 1, f'{tid} Okan controls missing under okan profile on {route}'

    return fn


for _tid, _feat, _vp, _theme, _view, _prof, _route in PAIRWISE_CASES:
    e2e_test(
        _tid,
        3,
        _feat,
        f'Pairwise ({_vp} x {_theme} x {_view} x {_prof} x {_route})',
    )(_make_pairwise_fn(_tid, _feat, _vp, _theme, _view, _prof, _route))


@e2e_test('T3_09', 3, 'E6', 'Pairwise: sources.json categories x kume-<alan>.json <1100KB x DIL_AYRILAN')
def test_t3_sources_kume_dil_interaction(ctx):
    src = load_json('sources.json')
    active_cats = {s['calisma'] for s in src if s.get('aktif', True)}
    oz = load_json('site/data/ozet.json')
    dl = load_json('site/data/diller.json')['diller']
    cap = 1100 * 1024
    alan_data = {}
    for a in active_cats:
        rel = f'site/data/kume-{a}.json'
        assert os.path.isfile(os.path.join(KOK, rel)), f'Active category {a} missing {rel}'
        assert file_size(rel) < cap, f'{rel} >= 1100 KB'
        alan_data[a] = load_json(rel)['kumeler']

    for x in dl:
        if x['k'] in ('tr', 'en'):
            continue
        fk = load_json(f"site/data/dil-{x['k']}.json")['kumeler']
        for a, kumeler in alan_data.items():
            m = sum(1 for c in fk if a in c['alanlar'])
            got = sum(1 for c in kumeler if c['dil'] == x['k'])
            assert got >= min(6, m), f"Pairwise DIL_AYRILAN ({x['k']}, {a}): {got} < {min(6, m)}"
    assert len(oz['alanlar']) >= 12


@e2e_test('T3_10', 3, 'E8', 'Pairwise: reels.json x #/reels UI profile & sub-filter combinations')
def test_t3_reels_ui_filter_pairs(ctx):
    b = ctx.browser
    b.set_desktop()
    nav = b.navigate('#/reels')
    assert_clean_nav(nav)
    for prof, ralt in (('hepsi', ''), ('teknoloji', 'yabanci'), ('gundem', 'viral'), ('siyaset', ''), ('spor', '')):
        b.click(f'[data-act="profil"][data-v="{prof}"]')
        b.click(f'[data-act="ralt"][data-v="{ralt}"]')
        st = b.eval("""(() => ({
          cards: document.querySelectorAll('#ana [data-id]').length,
          empty: Boolean(document.querySelector('#ana .bosluk')),
          hasDisclaimer: /viral garantisi değildir/i.test(document.getElementById('ana')?.textContent || ''),
        }))()""")
        assert st['cards'] > 0 or st['empty'], f'Reels filter ({prof}, {ralt}) rendered blank'
        assert st['hasDisclaimer'], f'Disclaimer disappeared on ({prof}, {ralt})'
    # Reset and open first card drawer to inspect aci/dogrulama/risk
    b.click('[data-act="profil"][data-v="hepsi"]')
    b.click('[data-act="ralt"][data-v=""]')
    b.click('#ana [data-id] h3 a')
    b.wait_for("document.getElementById('panel')?.open")
    panel_txt = b.eval("document.getElementById('panel')?.textContent || ''")
    for label in ('Açı', 'Doğrulama', 'Dikkat'):
        assert label in panel_txt, f'Reels detail drawer missing {label}'


@e2e_test('T3_11', 3, 'E5', 'Pairwise: id="snap" x masa.json x piril.json isolation contract')
def test_t3_snap_masa_piril_isolation(ctx):
    html = open(os.path.join(KOK, 'site', 'index.html'), encoding='utf-8').read()
    snap = parse_snap(html)
    masa = load_json('site/masa.json')
    piril = load_json('site/data/kisisel/piril.json')
    assert not any(k.startswith('pc-') for k in snap['feeds']), 'pc- feed leaked into snap'
    assert not any(c.get('id', '').startswith('pc:') for c in masa['kumeler']), 'pc: cluster leaked into masa.json'
    assert all(c.get('dil') != 'tr' for c in piril['kumeler']), 'TR cluster leaked into piril.json'


@e2e_test('T3_12', 3, 'E7', 'Pairwise: unittest discover -s tests excludes tests_e2e and site/ stays unstaged')
def test_t3_ci_discovery_and_git_unstaged(ctx):
    # List discovered test IDs in-process via unittest.TestLoader (avoids nested socket spawn)
    import unittest
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=os.path.join(KOK, 'tests'), top_level_dir=KOK)

    def collect_names(s):
        out = []
        for item in s:
            if isinstance(item, unittest.TestSuite):
                out.extend(collect_names(item))
            else:
                out.append(item.id())
        return out

    names = collect_names(suite)
    assert len(names) >= 100, f'Expected >=100 unit tests in tests/, got {len(names)}'
    assert not any('tests_e2e' in n for n in names), f'tests_e2e discovered by unittest: {names}'

    rc, out, err = git_cmd('diff', '--cached', '--name-only', '--', 'site/')
    assert rc == 0, err
    assert not out.strip(), f'Staged site/ files detected: {out.strip()}'
