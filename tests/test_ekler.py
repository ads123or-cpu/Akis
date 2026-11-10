"""Akış 3 ekleri: Google Trends ayrıştırma ve haber eşleştirme, trend geçmişi, Güncelleme Radarı, arayüz sözleşmesi. Ağ gerekmez."""
import json, os, shutil, sys, tempfile, time, unittest
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
import fetch_feeds as F
import ekler as E

TRENDS_RSS = '''<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:ht="https://trends.google.com/trending/rss" version="2.0"><channel><title>Daily Search Trends</title>
<item><title>vincenzo montella</title><ht:approx_traffic>2000+</ht:approx_traffic><link>https://trends.google.com/trending/rss?geo=TR</link>
<pubDate>Tue, 10 Nov 2026 11:30:00 -0800</pubDate><ht:picture>https://img.test/m.jpg</ht:picture>
<ht:news_item><ht:news_item_title>Montella&apos;nın yeni adresi belli oldu</ht:news_item_title><ht:news_item_url>https://spor.test/montella</ht:news_item_url><ht:news_item_source>Spor Test</ht:news_item_source></ht:news_item>
<ht:news_item><ht:news_item_title>Montella yeni takımında</ht:news_item_title><ht:news_item_url>https://shiftdelete.net/x</ht:news_item_url><ht:news_item_source>ShiftDelete.Net</ht:news_item_source></ht:news_item>
</item>
<item><title>togg kampanya</title><ht:approx_traffic>200+</ht:approx_traffic><link>https://trends.google.com/trending/rss?geo=TR</link><pubDate>Tue, 10 Nov 2026 11:00:00 -0800</pubDate></item>
<item><title>tatil</title><ht:approx_traffic>5000+</ht:approx_traffic><link>https://trends.google.com/trending/rss?geo=TR</link><pubDate>Tue, 10 Nov 2026 10:00:00 -0800</pubDate></item>
</channel></rss>'''.encode('utf-8')


def kume(id_, t, kb=3, son=None, alanlar=('gundem',), og=None):
    son = son or int(time.time()) - 600
    return dict(id=id_, t=t, kb=kb, ks=kb, son=son, ilk=son - 3600, l='https://x.test/' + id_, i=None, s='', dil='tr', kaynaklar=['A', 'B'], alanlar=list(alanlar),
                og=og or [dict(t=t, l='https://x.test/' + id_, p='A', z=son, d='tr')])


class TrendAyristirma(unittest.TestCase):
    def test_hacim_ve_haberler(self):
        it = F.parse(TRENDS_RSS)
        m = next(x for x in it if x['t'] == 'vincenzo montella')
        self.assertEqual((m['n'], m['tr']), (2000, '2000+'))
        self.assertEqual(m['i'], 'https://img.test/m.jpg')
        self.assertTrue(m['l'].startswith('https://www.google.com/search?q='))
        self.assertEqual([h['p'] for h in m['hn']], ['Spor Test'])       # ShiftDelete haberi trend kartına girmez
        self.assertEqual(m['hn'][0]['t'], "Montella'nın yeni adresi belli oldu")


class TrendEslestirme(unittest.TestCase):
    def setUp(self):
        E._SIMDI[0] = time.time()
        self.k = [kume('a', "Vincenzo Montella'nın yeni adresi netleşti", kb=1, alanlar=('spor',)),
                  kume('b', 'Peugeot Kasım 2026 kampanya ve fiyat listesi', kb=4, alanlar=('oto',)),
                  kume('c', "Yarın okullar tatil mi? Ankara'da kar yağışı", kb=5)]
        for c in self.k:
            c['_otok'] = [E._tok(o['t']) for o in c['og']]; c['_kel'] = {w for o in c['og'] for w in E.M.sozcuk(o['t'])}

    def test_cok_sozcuklu_ve_turkce_ek(self):
        c, p = E.trend_eslestir(dict(t='vincenzo montella', hn=[]), self.k)
        self.assertEqual(c['id'], 'a'); self.assertGreater(p, .9)

    def test_tek_ortak_sozcuk_yetmez(self):
        # "togg kampanya" ile yalnız "kampanya" geçen Peugeot haberi eşleşmemeli
        self.assertEqual(E.trend_eslestir(dict(t='togg kampanya', hn=[]), self.k), (None, 0))

    def test_tek_sozcuk(self):
        self.assertEqual(E.trend_eslestir(dict(t='tatil', hn=[]), self.k)[0]['id'], 'c')

    def test_kok_carpismasi_eslesmez(self):
        # "ağaçlandırma" ile "ağaçların" kökü aynı 6 harf; tam sözcük önekiyle eşleşmemeli
        k = [kume('d', 'Ağaçların yaprakları neden farklı yönlere uzanıyor')]
        k[0]['_otok'] = [E._tok(k[0]['t'])]; k[0]['_kel'] = set(E.M.sozcuk(k[0]['t']))
        self.assertIsNone(E.trend_eslestir(dict(t='ağaçlandırma', hn=[]), k)[0])


class TrendGecmisi(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.eski = os.getcwd(); os.chdir(self.d); os.makedirs('site')
    def tearDown(self):
        os.chdir(self.eski); shutil.rmtree(self.d, ignore_errors=True)

    def test_ilk_gorulme_korunur_firsat_ve_sonme(self):
        feeds = {'trends-tr': dict(items=F.parse(TRENDS_RSS))}
        k = [kume('a', "Vincenzo Montella'nın yeni adresi netleşti", kb=1, alanlar=('spor',)), kume('c', 'Okullar tatil mi? Valilik açıkladı', kb=5)]
        t0 = time.time()
        r1 = E.trendler_uret(feeds, k, t0)
        tr = {x['t']: x for x in r1['ulkeler']['TR']['trendler']}
        self.assertTrue(tr['vincenzo montella']['firsat'])        # tek bağımsız kaynak: "bizde az"
        self.assertFalse(tr['tatil']['firsat'])
        self.assertTrue(tr['togg kampanya']['firsat']); self.assertIsNone(tr['togg kampanya']['kume'])
        self.assertEqual(tr['vincenzo montella']['alan'], 'spor')
        ilk = tr['tatil']['ilk']
        # ikinci tur: tatil artık listede değil, hacmi artan montella var
        feeds2 = {'trends-tr': dict(items=[dict(x, n=5000) for x in F.parse(TRENDS_RSS) if x['t'] == 'vincenzo montella'])}
        r2 = E.trendler_uret(feeds2, k, t0 + 3600 * 4)
        tr2 = {x['t']: x for x in r2['ulkeler']['TR']['trendler']}
        self.assertEqual(tr2['tatil']['ilk'], ilk); self.assertFalse(tr2['tatil']['aktif'])
        self.assertTrue(tr2['vincenzo montella']['artis']); self.assertEqual(tr2['vincenzo montella']['tepe'], 5000)
        self.assertEqual(r2['ulkeler']['TR']['trendler'][0]['t'], 'vincenzo montella')   # aktifler önce
        # 48 saat sonra sönmüş trend geçmişten düşer
        r3 = E.trendler_uret({'trends-tr': dict(items=[])}, k, t0 + 3600 * 60)
        self.assertEqual(r3['ulkeler']['TR']['trendler'], [])
        self.assertEqual(json.load(open(E.GECMIS))['TR'], {})


class Guncelleme(unittest.TestCase):
    def tur(self, t, *diger):
        og = [dict(t=x, l='https://x.test/%d' % i, p='A', z=int(time.time()), d='tr') for i, x in enumerate((t,) + diger)]
        r = E.guncellemeler_uret([kume('k', t, og=og)], time.time())
        return [(u['k'], u['ogeler'][0]['tur']) for u in r['urunler']]

    def test_urun_ve_tur(self):
        self.assertEqual(self.tur("Apple'dan iOS 27.2.1 güncellemesi: güvenlik açıkları kapatıldı"), [('ios', 'guvenlik')])
        self.assertEqual(self.tur('Motorola, 14 telefon için Android 17 beta kayıtlarını açtı'), [('android', 'beta')])
        self.assertEqual(self.tur("WhatsApp'a Kişiler sekmesi geliyor"), [('whatsapp', 'ozellik')])
        self.assertEqual(self.tur('YouTube rolling out app redesign without Subscriptions tab'), [('youtube', 'tasarim')])
        self.assertEqual(self.tur('HyperOS 4 kararlı sürümü 82 cihaz için dağıtılıyor'), [('hyperos', 'yayinda')])

    def test_urun_adi_gecen_her_haber_guncelleme_degil(self):
        self.assertEqual(self.tur('New GTA 6 trailer showcases PS5 exclusive content'), [])
        self.assertEqual(self.tur("Everything We Know About Netflix's 'Better Than The Movies' Feature Adaptation"), [])
        self.assertEqual(self.tur('WhatsApp CEO testifies before Congress'), [])

    def test_eski_konu_girmez(self):
        r = E.guncellemeler_uret([kume('k', 'iOS 27.2 update released', son=int(time.time()) - 9 * 86400)], time.time())
        self.assertEqual(r['urunler'], [])


class Arayuz(unittest.TestCase):
    T = open(os.path.join(KOK, 'index.tpl.html'), encoding='utf-8').read()

    def test_kisisel_veri_anahtarlari_korunur(self):
        # Eski kullanıcının kayıtları yeni arayüzde kaybolmasın
        for k in ('akis-kayit', 'akis-okundu', 'akis-gizli', 'akis2-not', 'akis2-durum', 'akis2-ayar', 'akis-ziyaret'):
            self.assertIn("'%s'" % k, self.T, k)

    def test_yeni_bolumler_ve_veri_dosyalari(self):
        for s in ("'trendler'", "'guncellemeler'", "'kume-'", "'reels'", "'kaynaklar'", "'indeks'", '#/trend', '#/guncelleme'):
            self.assertIn(s, self.T, s)

    def test_dis_baglanti_guvenli(self):
        import re
        for a in re.findall(r'target="_blank"[^>]*', self.T): self.assertIn('noopener', a)

    def test_harici_betik_yok(self):
        self.assertNotRegex(self.T, r'<script[^>]+src=')


if __name__ == '__main__': unittest.main()
