"""Üretilmiş site/ çıktısı: YALNIZ belirlenimci denetimler (iş akışında yayın kapısıdır).
Haber akışına bağlı dağılım denetimleri (profil sayısı, sıcak konu varlığı) tests/test_dagilim.py'de ve kapı değildir:
sakin bir gece yarısı bir profilde aday bulunamaması yayını durdurmamalı."""
import json, os, re, unittest
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(KOK, 'site', 'data')
VAR = os.path.exists(os.path.join(D, 'ozet.json'))
def j(a): return json.load(open(os.path.join(D, a), encoding='utf-8'))
ALANLAR = ['gundem', 'tekno', 'siyaset', 'spor', 'ekonomi', 'bilim', 'siber', 'oto', 'eglence']
YASAK = re.compile(r'shift\s*delete', re.I)
KIMLIK_ALANLARI = {'p', 'kaynak', 'ad', 'l', 'url', 'name', 'id'}   # yayıncı adı, bağlantı, kaynak adı: özet metni DEĞİL

def yasak_ara(n, yol=''):
    """Yalnız yayıncı/bağlantı/kaynak alanlarında ShiftDelete arar (bir Windows rehberinin özeti 'shift delete' diyebilir)."""
    if isinstance(n, dict):
        for k, v in n.items():
            if k in KIMLIK_ALANLARI and isinstance(v, str) and YASAK.search(v): yield yol + '/' + k
            elif k in ('kaynaklar', 'k') and isinstance(v, list):
                for x in v:
                    if isinstance(x, str) and YASAK.search(x): yield yol + '/' + k
            else:
                for r in yasak_ara(v, yol + '/' + k): yield r
    elif isinstance(n, list):
        for i, v in enumerate(n): 
            for r in yasak_ara(v, yol + '[]'): yield r

@unittest.skipUnless(VAR, 'site/data üretilmemiş')
class Cikti(unittest.TestCase):
    def test_json_gecerli(self):
        for a in ['ozet', 'reels', 'kaynaklar', 'indeks', 'trendler', 'guncellemeler'] + ['kume-' + x for x in ALANLAR]: j(a + '.json')
        o = j('ozet.json')
        for k in ('generated', 'sicak', 'yukselen', 'son', 'sayim', 'yontem', 'kaynak_durum', 'toplam'): self.assertIn(k, o)

    def test_trend_ve_guncelleme(self):
        t = j('trendler.json'); g = j('guncellemeler.json')
        for geo in t['sira']:
            for x in t['ulkeler'][geo]['trendler']:
                self.assertTrue(x['t']); self.assertIn(x['firsat'], (True, False) if geo in ('TR', 'US', 'GB') else (None,))
                if x['kume']: self.assertTrue(x['kume']['id'])
        for u in g['urunler']:
            self.assertTrue(u['ogeler'])
            for x in u['ogeler']: self.assertIn(x['tur'], {k['k'] for k in g['turler']})
        o = j('ozet.json'); self.assertIn('trend_tr', o); self.assertIn('guncelleme_ozet', o)

    def test_ilk_yukleme_kucuk(self):
        self.assertLess(os.path.getsize(os.path.join(D, 'ozet.json')), 450 * 1024)
        for x in ALANLAR: self.assertLess(os.path.getsize(os.path.join(D, 'kume-%s.json' % x)), 1100 * 1024)

    def test_shiftdelete_kimlik_alanlarinda_yok(self):
        for f in os.listdir(D): self.assertEqual(list(yasak_ara(j(f))), [], f)
        for f in ('masa.json', 'feeds.json'):
            yol = os.path.join(KOK, 'site', f)
            if os.path.exists(yol): self.assertEqual(list(yasak_ara(json.load(open(yol, encoding='utf-8')))), [], f)

    def test_sicak_ve_yukselen_en_az_iki_bagimsiz(self):
        o = j('ozet.json')
        for w in o['sicak'].values():
            for c in w: self.assertGreaterEqual(c['kb'], 2)
        for c in o['yukselen']: self.assertGreaterEqual(c['kb'], 2)

    def test_kume_yapisi(self):
        for a in ALANLAR:
            for c in j('kume-%s.json' % a)['kumeler'][:60]:
                self.assertIn(a, c['alanlar']); self.assertTrue(c['t']); self.assertTrue(c['og'])

    def test_kaynak_durumu_tutarli(self):
        k = j('kaynaklar.json'); self.assertEqual(sum(k['durum_say'].values()), len(k['kaynaklar']))
        for s in k['kaynaklar']:
            if s['durum'] == 'devre-disi': self.assertFalse(s['aktif'])
            self.assertTrue(s['url'].startswith('http'))

if __name__ == '__main__': unittest.main()
