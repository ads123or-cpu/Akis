import json, os, re, unittest
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = json.load(open(os.path.join(KOK, 'sources.json'), encoding='utf-8'))
TIPLER = {'ajans', 'ana akim', 'dogrulama', 'resmi kurum', 'uluslararasi kurum', 'uzman teknoloji', 'bilimsel', 'spor', 'topluluk/trend', 'sirket duyurusu', 'toplayici', 'video (YouTube)'}
CALISMA = {'gundem', 'tekno', 'siyaset', 'spor', 'ekonomi', 'bilim', 'siber', 'oto', 'eglence'}

class Kaynaklar(unittest.TestCase):
    def test_eski_kaynaklar_korundu(self):
        eski = set(json.load(open(os.path.join(KOK, 'tests', 'fixtures', 'eski-kaynak-idleri.json'))))
        self.assertFalse(eski - {s['id'] for s in S}, 'eski kaynak silinmis')

    def test_alanlar(self):
        ids = [s['id'] for s in S]; self.assertEqual(len(ids), len(set(ids)), 'yinelenen id')
        for s in S:
            for a in ('id', 'name', 'lang', 'cat', 'url', 'plat'): self.assertIn(a, s, s['id'])
            self.assertTrue(re.match(r'^https?://', s['url']), s['id'])
            self.assertIn(s['tip'], TIPLER, s['id']); self.assertIn(s['calisma'], CALISMA, s['id'])
            self.assertIn(s['oncelik'], (1, 2, 3)); self.assertIsInstance(s['nitelik'], list); self.assertIsInstance(s['aktif'], bool)
            if s['aktif'] is False: self.assertTrue(s.get('pasif_neden'), s['id'])

    def test_shiftdelete_yok(self):
        for s in S: self.assertFalse(re.search(r'shift\s*delete', s['id'] + s['name'] + s['url'], re.I), s['id'])

    def test_yeni_kaynak_dogrulama_kaydi(self):
        eski = set(json.load(open(os.path.join(KOK, 'tests', 'fixtures', 'eski-kaynak-idleri.json'))))
        for s in S:
            if s['id'] in eski: continue
            d = s.get('dogrulama'); self.assertTrue(d, s['id'])
            self.assertIn(d['durum'], ('gecti', 'bekliyor')); self.assertTrue(d['tarih'])
            if d['durum'] == 'gecti': self.assertGreaterEqual(d['n'], 3, s['id'])

    def test_ucretli_duvar_etiketli(self):
        for i in ('nyt', 'wapo', 'ft', 'economist', 'bloomberg'):
            s = next((x for x in S if x['id'] == i), None)
            if s: self.assertIn('ucretli-duvar', s['nitelik'], i)

    def test_topluluk_dogrulanmis_sayilmaz(self):
        for s in S:
            if s['plat'] == 'reddit': self.assertIn('erken-sinyal', s['nitelik'])
if __name__ == '__main__': unittest.main()
