"""Üretilmiş site/ çıktısı: JSON'lar geçerli mi, boyutlar makul mü, ShiftDelete sızmış mı, kaynak durumları tutarlı mı. site/ yoksa atlanır."""
import json, os, re, unittest
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(KOK, 'site', 'data')
VAR = os.path.exists(os.path.join(D, 'ozet.json'))
def j(a): return json.load(open(os.path.join(D, a), encoding='utf-8'))
ALANLAR = ['gundem', 'tekno', 'siyaset', 'spor', 'ekonomi', 'bilim', 'siber', 'oto', 'eglence']

@unittest.skipUnless(VAR, 'site/data üretilmemiş')
class Cikti(unittest.TestCase):
    def test_json_gecerli_ve_dolu(self):
        for a in ['ozet', 'reels', 'kaynaklar', 'indeks'] + ['kume-' + x for x in ALANLAR]: j(a + '.json')
        o = j('ozet.json'); self.assertGreater(o['toplam']['haber'], 500); self.assertTrue(o['sicak']['24']); self.assertIn('sicak', o['yontem'])

    def test_ilk_yukleme_kucuk(self):
        # İlk açılışta yalnız index.html + ozet.json inmeli; ağır parçalar tembel
        self.assertLess(os.path.getsize(os.path.join(D, 'ozet.json')), 450 * 1024)
        for x in ALANLAR: self.assertLess(os.path.getsize(os.path.join(D, 'kume-%s.json' % x)), 1100 * 1024)

    def test_shiftdelete_hicbir_ciktida_yok(self):
        for f in os.listdir(D):
            self.assertNotRegex(open(os.path.join(D, f), encoding='utf-8').read(), re.compile(r'shift\s*delete', re.I), f)
        for f in ('masa.json', 'feeds.json', 'index.html'):
            yol = os.path.join(KOK, 'site', f)
            if os.path.exists(yol): self.assertNotRegex(open(yol, encoding='utf-8').read(), re.compile(r'shift\s*delete', re.I), f)

    def test_cok_kaynakli_konular_en_az_iki_bagimsiz(self):
        for c in j('ozet.json')['sicak']['24']: self.assertGreaterEqual(c['kb'], 2)
        for c in j('ozet.json')['yukselen']: self.assertGreaterEqual(c['kb'], 2)

    def test_kume_alanlari(self):
        for a in ALANLAR:
            k = j('kume-%s.json' % a)
            for c in k['kumeler'][:60]:
                self.assertIn(a, c['alanlar']); self.assertTrue(c['t']); self.assertTrue(c['og']); self.assertLessEqual(c['kb'], c['ks'] + 0)

    def test_reels_siyaset_spor_gundem_var(self):
        pr = {p for r in j('reels.json')['adaylar'] for p in r['profil']}
        self.assertTrue({'teknoloji', 'gundem', 'siyaset', 'spor'} <= pr, pr)

    def test_kaynak_durumu_tutarli(self):
        k = j('kaynaklar.json'); self.assertEqual(sum(k['durum_say'].values()), len(k['kaynaklar']))
        for s in k['kaynaklar']:
            if s['durum'] == 'devre-disi': self.assertFalse(s['aktif'])
            self.assertTrue(s['url'].startswith('http'))

if __name__ == '__main__': unittest.main()
