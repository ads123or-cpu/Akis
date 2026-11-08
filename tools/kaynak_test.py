#!/usr/bin/env python3
"""Aday kaynaklari gercekten test eder: HTTP durumu, RSS/Atom ayrisimi, tarihli kayit sayisi, gecikme, mevcut akislarla kopya orani.
Kullanim: python3 tools/kaynak_test.py [adaylar.py] > tools/kaynak_test_sonuc.json
Gecme sarti: ayrisan >=3 kayit, >=3 tarihli, en yeni kayit <=45 gun, mevcut akislardaki baglantilarin <%60'i ortak."""
import sys, os, json, re, time, ssl, importlib.util, concurrent.futures as cf, urllib.request, urllib.parse
from datetime import datetime, timezone
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
import fetch_feeds as F

def mevcut():
    s = json.load(open(os.path.join(KOK, 'sources.json'), encoding='utf-8'))
    try: f = json.load(open(os.path.join(KOK, 'site', 'feeds.json'), encoding='utf-8'))['feeds']
    except Exception: f = {}
    return {x['url'] for x in s}, {i['l'] for v in f.values() for i in v['items'] if i.get('l')}

def kesif(url):
    """Ana sayfada <link rel=alternate type=rss/atom> arar (yalniz oneri; aday listesine elle eklenir)."""
    try:
        kok = '{0.scheme}://{0.netloc}/'.format(urllib.parse.urlparse(url))
        req = urllib.request.Request(kok, headers={'User-Agent': F.UA}); h = urllib.request.urlopen(req, timeout=12).read(200000).decode('utf-8', 'ignore')
        return list(dict.fromkeys(urllib.parse.urljoin(kok, m) for m in re.findall(r'<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]+href=["\']([^"\']+)', h, re.I) + re.findall(r'<link[^>]+href=["\']([^"\']+)["\'][^>]+type=["\']application/(?:rss|atom)\+xml', h, re.I)))[:4]
    except Exception: return []

def dene(a, bilinen_url, bilinen_link):
    id_, ad, dil, ulke, cat, cal, tip, url, nit = a
    r = dict(id=id_, url=url, tarih=datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    if url in bilinen_url: r.update(ok=False, neden='zaten kayitli'); return r
    t0 = time.time()
    try:
        data, _, _ = F.fetch(url)
        r['ms'] = int((time.time() - t0) * 1000); r['kod'] = 200
        items = F.parse(data)
    except Exception as e:
        r.update(ok=False, kod=getattr(e, 'code', None), neden=str(e)[:70], ms=int((time.time() - t0) * 1000)); r['kesif'] = kesif(url); return r
    tarihli = [i for i in items if i.get('d')]
    r.update(n=len(items), n_tarihli=len(tarihli))
    if len(items) < 3: r.update(ok=False, neden='3 kayittan az'); r['kesif'] = kesif(url); return r
    if len(tarihli) < 3: r.update(ok=False, neden='tarihli kayit yok'); return r
    son = max(i['d'] for i in tarihli); r['son_haber'] = son
    gun = (datetime.now(timezone.utc) - datetime.fromisoformat(son)).days; r['son_gun'] = gun
    ortak = sum(1 for i in items if i['l'] in bilinen_link) / len(items); r['ortak'] = round(ortak, 2)
    if gun > 45: r.update(ok=False, neden='45 gunden eski (guncellenmiyor)'); return r
    if ortak >= .6: r.update(ok=False, neden='mevcut akislarla kopya (%d%%)' % (ortak * 100)); return r
    r['ornek'] = [i['t'][:80] for i in items[:2]]
    r.update(ok=True); return r

if __name__ == '__main__':
    yol = sys.argv[1] if len(sys.argv) > 1 else os.path.join(KOK, 'tools', 'adaylar.py')
    sp = importlib.util.spec_from_file_location('adaylar', yol); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    bu, bl = mevcut()
    with cf.ThreadPoolExecutor(16) as ex: sonuc = list(ex.map(lambda a: dene(a, bu, bl), m.A))
    print(json.dumps(sonuc, ensure_ascii=False, indent=1))
    ok = sum(1 for r in sonuc if r['ok']); print('# %d/%d gecti' % (ok, len(sonuc)), file=sys.stderr)
