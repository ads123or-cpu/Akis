"""Panel sozlesmesi: TechTurco paneli site/index.html icindeki id="snap" verisini ve masa.json'u okur.
Bu testler AkisController::snapshotOku ile ayni yontemle okur ve eski alanlarin bozulmadigini denetler."""
import gzip, json, os, re, sys, unittest
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(KOK, 'tests', 'fixtures')

def snap_oku(html):
    """PHP kodundaki gibi: ilk 'id="snap"', sonraki '>', sonraki '</script>'."""
    kimlik = html.find('id="snap"'); assert kimlik >= 0, 'id="snap" yok'
    bas = html.find('>', kimlik); son = html.find('</script>', bas)
    assert bas >= 0 and son >= 0
    return json.loads(html[bas + 1:son])

MASA_UST = {'generated', 'saglik', 'konular', 'kumeler', 'reels', 'trendler', 'kaynaklar'}
KUME = {'id', 't', 's', 'i', 'k', 'cat', 'dil', 'l', 'ks', 'son', 'ilk', 'hiz', 'r', 'ned', 'tur', 'elen', 'og'}

class Sozlesme(unittest.TestCase):
    def kontrol_snap(self, j):
        self.assertTrue(j['feeds'])
        for v in j['saglik'].values(): int(v)
        for f in j['feeds'].values():
            self.assertTrue({'name', 'lang', 'cat', 'plat', 'items'} <= set(f))
            for it in f['items'][:50]:
                self.assertTrue({'l', 't'} <= set(it)); self.assertTrue(set(it) <= {'l', 'd', 't', 's', 'i', 'p', 'c', 'n'})

    def kontrol_masa(self, m):
        self.assertTrue(MASA_UST <= set(m))
        for c in m['kumeler']: self.assertTrue(KUME <= set(c), KUME - set(c))
        ids = {c['id'] for c in m['kumeler']}
        self.assertTrue(set(m['reels']) <= ids)

    def test_baseline_snap(self):
        h = gzip.open(os.path.join(FIX, 'baz-index.html.gz'), 'rt', encoding='utf-8').read()
        self.assertEqual(h.count('id="snap"'), 1)
        self.kontrol_snap(snap_oku(h))

    def test_baseline_masa(self):
        self.kontrol_masa(json.load(gzip.open(os.path.join(FIX, 'baz-masa.json.gz'), 'rt', encoding='utf-8')))

    @unittest.skipUnless(os.path.exists(os.path.join(KOK, 'site', 'index.html')), 'site/ uretilmemis')
    def test_uretilen_snap(self):
        h = open(os.path.join(KOK, 'site', 'index.html'), encoding='utf-8').read()
        self.assertEqual(h.count('id="snap"'), 1, 'id="snap" tam bir kez gecmeli (PHP ilkini okur)')
        self.assertEqual(h.count('/*SNAP*/'), 0, 'yer tutucu kalmamali')
        self.kontrol_snap(snap_oku(h))

    @unittest.skipUnless(os.path.exists(os.path.join(KOK, 'site', 'masa.json')), 'site/ uretilmemis')
    def test_uretilen_masa(self):
        self.kontrol_masa(json.load(open(os.path.join(KOK, 'site', 'masa.json'), encoding='utf-8')))

    def test_sablon_yer_tutucu(self):
        t = open(os.path.join(KOK, 'index.tpl.html'), encoding='utf-8').read()
        self.assertEqual(t.count('/*SNAP*/'), 1)
        self.assertEqual(t.count('id="snap"'), 1)
        self.assertLess(t.index('id="snap"'), t.index('/*SNAP*/'))

if __name__ == '__main__': unittest.main()
