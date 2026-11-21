"""Gerçek veride dağılım denetimleri (yayın kapısı DEĞİL: sakin saatlerde başarısız olabilir). Kural değişikliklerinden sonra elle koşulur."""
import json, os, unittest
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(KOK, 'site', 'data')
@unittest.skipUnless(os.path.exists(os.path.join(D, 'reels.json')), 'site/data yok')
class Dagilim(unittest.TestCase):
    def test_reels_dort_profil(self):
        r = json.load(open(os.path.join(D, 'reels.json'), encoding='utf-8'))
        pr = {p for a in r['adaylar'] for p in a['profil']}
        # 2026-11-21: liste "daha az, daha iddialı" (en çok 40 kart, doldurulmaz); sakin saatte spor/siyaset boş kalabilir.
        # En az 3 profil (kart azsa kart sayısı kadar) ve her profil bilinen dörtlüden olmalı.
        self.assertGreaterEqual(len(pr), min(3, len(r['adaylar'])), pr)
        self.assertTrue(pr <= {'teknoloji', 'gundem', 'siyaset', 'spor'}, pr)
    def test_yeterli_haber(self):
        o = json.load(open(os.path.join(D, 'ozet.json'), encoding='utf-8'))
        self.assertGreater(o['toplam']['haber'], 500); self.assertTrue(o['sicak']['24'])
if __name__ == '__main__': unittest.main()
