"""Kişisel masa (Pırıl Cennet · Dünya masası): kaynak listesi ayrı, yalnız yabancı dil, ana akışla karışmaz. Ağ gerekmez."""
import json, os, shutil, sys, tempfile, time, unittest
from datetime import datetime, timezone, timedelta
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
import fetch_feeds as F
import kisisel as K

def yukle(y): return json.load(open(os.path.join(KOK, y), encoding='utf-8'))


class KaynakListesi(unittest.TestCase):
    P = yukle('kisisel/piril/sources.json')
    ANA = yukle('sources.json')

    def test_yalniz_yabanci_dil_ve_onek(self):
        self.assertGreaterEqual(len(self.P), 60)
        for s in self.P:
            self.assertNotEqual(s['lang'], 'tr', s['id'])
            self.assertTrue(s['id'].startswith('pc-'), s['id'])
            self.assertNotEqual(s.get('ulke'), 'TR', s['id'])
            self.assertNotRegex(s['id'] + s['name'] + s['url'], F.YASAK_YAYINCI)
        self.assertEqual(len({s['id'] for s in self.P}), len(self.P))

    def test_ana_listeye_karismaz(self):
        self.assertFalse([s['id'] for s in self.ANA if s['id'].startswith('pc-')])

    def test_dosya_yollari_ana_dosyalardan_ayri(self):
        y = F.profil_yollari('piril')
        for v in y.values():
            self.assertNotIn(v, ('sources.json', 'site/feeds.json', 'site/kaynak-durum.json', 'site/gorsel.json'))


class Uretim(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.eski = os.getcwd(); os.chdir(self.d)
        y = F.profil_yollari('piril')
        os.makedirs(os.path.dirname(y['kaynak'])); os.makedirs(os.path.dirname(y['cikti']))
        src = [dict(id='pc-a', name='World A', lang='en', cat='world', url='https://a.test/rss', calisma='gundem', tip='ana akim'),
               dict(id='pc-b', name='Welt B', lang='de', cat='world', url='https://b.test/rss', calisma='gundem', tip='ana akim'),
               dict(id='pc-t', name='Türk C', lang='tr', cat='world', url='https://c.test/rss', calisma='gundem', tip='ana akim')]
        json.dump(src, open(y['kaynak'], 'w'))
        z = lambda m: (datetime.now(timezone.utc) - timedelta(minutes=m)).isoformat()
        it = lambda t, l, m: dict(t=t, l=l, d=z(m), s='')
        feeds = {'pc-a': dict(name='World A', lang='en', cat='world', items=[it('Ceasefire talks resume in Geneva between envoys', 'https://a.test/1', 30)]),
                 'pc-b': dict(name='Welt B', lang='de', cat='world', items=[it('Wahl in Frankreich: Ergebnis überrascht Beobachter', 'https://b.test/1', 50)]),
                 'pc-t': dict(name='Türk C', lang='tr', cat='world', items=[it('Cenevre’de ateşkes görüşmeleri yeniden başladı', 'https://c.test/1', 40)]),
                 'yabanci-ana': dict(name='Ana', lang='en', cat='world', items=[it('Main feed story should not appear here', 'https://m.test/1', 20)])}
        json.dump(dict(generated=datetime.now(timezone.utc).isoformat(), feeds=feeds), open(y['cikti'], 'w'))

    def tearDown(self):
        os.chdir(self.eski); shutil.rmtree(self.d, ignore_errors=True)

    def test_turkce_ve_ana_kaynak_girmez(self):
        K.uret('piril')
        o = json.load(open(os.path.join(K.CIKTI, 'piril.json'), encoding='utf-8'))
        self.assertEqual(o['ad'], 'Pırıl Cennet')
        diller = {c['dil'] for c in o['kumeler']} | {x['d'] for c in o['kumeler'] for x in c['og']}
        self.assertEqual(diller, {'en', 'de'})
        self.assertFalse([c for c in o['kumeler'] if 'm.test' in c['l']])
        self.assertFalse(os.path.exists('site/data/ozet.json'))


class Arayuz(unittest.TestCase):
    T = open(os.path.join(KOK, 'index.tpl.html'), encoding='utf-8').read()
    def test_kisisel_sayfa(self):
        for x in ("getJ('kisisel/'+p)", "'pc:'+c.id", 'function sayfaKisi', "piril:{ad:'Pırıl Cennet'"):
            self.assertIn(x, self.T, x)
    def test_ana_sekmelerde_yok(self):
        import re
        sek = re.search(r"var SAYFALAR=(\[.*?\]);", self.T).group(1)
        self.assertNotIn('piril', sek)
    def test_rota_buyuk_kucuk_harf_ve_turkce(self):
        self.assertIn("s=fold(s)", self.T)


class Siralama(unittest.TestCase):
    def test_eski_buyuk_konu_ustte_kalmaz(self):
        """Saatlerdir süren konu (son makale yeni) ile yeni çıkan konu: yaş ilk görülmeden de düşmeli."""
        import inspect
        self.assertIn("simdi - c['ilk']", inspect.getsource(K.uret))


if __name__ == '__main__': unittest.main()
