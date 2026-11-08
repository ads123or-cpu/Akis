"""Akış 2.0 veri hattı: kümeleme doğruluğu, çok dilli birleştirme, ajans kopyaları, Reels adaleti, uçtan uca çıktı biçimi.
Veri SENTETİKTİR (testlere özel); gerçek yayın verisi gibi gösterilmez."""
import json, os, shutil, sys, tempfile, unittest
from datetime import datetime, timezone, timedelta
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
import akis2 as A, masa as M

Z0 = datetime.now(timezone.utc).timestamp()
def oge(t, dil='tr', org='x', dk=10, s='', nit=(), plat='web', cal='gundem'):
    o = dict(id='%08x' % (abs(hash((t, org))) % 16 ** 8), t=t, l='http://%s.test/%d' % (org, abs(hash(t)) % 99999), z=Z0 - dk * 60, s=s, i=None, cat='tr', dil=dil, kaynak=org, sid=org, org=org,
             plat=plat, n=None, tip='ana akim', nit=set(nit), cal=cal, ulke='')
    o['tok'] = A.tok2(t); o['ent'] = A.canon_bul(t); o['var'] = M.varlik(t) | {'@' + e for e in o['ent']}
    return o
def kume_say(ogeler): return sorted(len(k['ogeler']) for k in A.kumele_tam(ogeler))

class Kumeleme(unittest.TestCase):
    def test_ayni_olay_farkli_basliklar(self):
        k = A.kumele2([oge("Samsung Galaxy S26 Ultra'nın fiyatı sızdı", org='a'), oge("Galaxy S26 Ultra fiyatı ortaya çıktı: Samsung planı sızdırıldı", org='b', dk=20),
                       oge("Samsung Galaxy S26 Ultra fiyat sızıntısı", org='c', dk=30)])
        self.assertEqual(len(k), 1)

    def test_farkli_olaylar_birlesmez(self):
        # Aynı kişi, farklı olay: yalnız ortak ad ve 'Trump' ile birleşmemeli
        a = [oge('Trump Kongre’de bütçe teklifini imzaladı', org='a'), oge('Trump Çin ile ticaret anlaşması için Pekin’e gidiyor', org='b'),
             oge('Trump UFC patronuna Beyaz Saray sözcülüğü teklif etti', org='c')]
        self.assertEqual(kume_say(a), [1, 1, 1])

    def test_cok_dilli_sayi_ve_varlik(self):
        k = A.kumele2([oge("Japonya'da 5,7 büyüklüğünde deprem: 20'den fazla yaralı", 'tr', 'a'), oge('5.7-magnitude earthquake hits central Japan, injuring at least 20', 'en', 'b', 20),
                       oge('Erdbeben der Stärke 5,7 erschüttert Japan: mindestens 20 Verletzte', 'de', 'c', 25)])
        self.assertEqual(len(k), 1, [len(x['ogeler']) for x in k])

    def test_genel_gazze_haberleri_dil_ortak_diye_birlesmez(self):
        a = [oge("İsrail Gazze'de iki Filistinliyi öldürdü", 'tr', 'a'), oge('Israel deports journalist among 14 on Palestinian solidarity flotilla to Gaza', 'en', 'b'),
             oge('Israel to release body of Palestinian teen who died in prison', 'en', 'c')]
        self.assertEqual(kume_say(a), [1, 1, 1])

    def test_ayni_olay_farkli_anlatim_ikinci_gecis(self):
        a = [oge("Trump offers UFC boss White House press secretary role: 'Dana, please take the job!'", 'en', 'a'), oge("Will Dana White Take Trump's Job Offer? UFC Chief Keeps Reporters Guessing", 'en', 'b', 20),
             oge("Trump asks UFC boss Dana White to be White House press secretary", 'en', 'c', 30)]
        self.assertEqual(kume_say(a), [3])

    def test_etiketi_yanlis_dil_ayni_baslik(self):
        k = A.kumele2([oge('Israël : Eisenkot, opposant à Netanyahu, au défi de former une coalition', 'fr', 'a'), oge('Israël : Eisenkot, opposant à Netanyahu, au défi de former une coalition', 'en', 'b', 12)])
        self.assertEqual(len(k), 1)

    def test_uzak_zaman_birlesmez(self):
        self.assertEqual(kume_say([oge("Galatasaray Fenerbahçe derbisinde gol sesi", org='a', dk=10), oge("Galatasaray Fenerbahçe derbisinde gol sesi", org='b', dk=60 * 50)]), [1, 1])

    def test_cjk_arapca_jeton(self):
        self.assertTrue(any(t.startswith('cj:') for t in A.tok2('日本发生5.7级地震')))
        self.assertTrue(any(t.startswith('ar:') for t in A.tok2('زلزال في اليابان')))

class Bagimsizlik(unittest.TestCase):
    def test_ajans_kopyasi_tek_sayilir(self):
        og = [oge('Merkez Bankası faizi yüzde 40 olarak sabit tuttu', org='aa', dk=30), oge('Merkez Bankası faizi yüzde 40 olarak sabit tuttu', org='sabah', dk=25), oge('Merkez Bankası faizi yüzde 40 olarak sabit tuttu', org='ntv', dk=20)]
        kb, kopya = A.bagimsiz_say(og)
        self.assertEqual(kb, 1); self.assertEqual(len(kopya), 2)

    def test_bagimsiz_farkli_anlatim(self):
        og = [oge('Merkez Bankası faizi yüzde 40 olarak sabit tuttu', org='aa', dk=30), oge('TCMB politika faizini değiştirmedi; piyasalar karışık seyretti', org='bbc', dk=25),
              oge('Faiz kararı sonrası dolar ve borsa nasıl hareket etti', org='dw', dk=20)]
        self.assertEqual(A.bagimsiz_say(og)[0], 3)

    def test_kurum_takma_adlari(self):
        self.assertEqual(A.kurum('NTV Spor', 'x'), A.kurum('NTV', 'y')); self.assertEqual(A.kurum('DW.com', 'x'), A.kurum('DW Türkçe', 'y'))
        self.assertEqual(A.kurum('BirGün', 'a'), A.kurum('birgun.net', 'b'))

    def test_kanonik_url(self):
        self.assertEqual(A.kanonik('https://www.example.com/a/b/?utm_source=x&id=3#frag'), A.kanonik('http://example.com/a/b?id=3&fbclid=zz'))
        self.assertEqual(A.kanonik('https://m.site.com/haber/amp'), A.kanonik('https://site.com/haber'))

class ReelsAdalet(unittest.TestCase):
    """Siyaset, spor ve gündem konuları teknoloji kuralına uymadığı için elenmemeli; elenenler dar ve gerekçeli olmalı."""
    def test_elenmeyenler(self):
        for t in ['Erdoğan Bakü’de Aliyev ile görüştü, enerji anlaşması imzalandı', 'Galatasaray Fenerbahçe’yi 3-1 yendi, derbide gol yağmuru', 'Meteoroloji’den 18 il için sarı kod uyarısı',
                  'NATO zirvesinde Ukrayna için yeni yaptırım paketi', 'Merkez Bankası faiz kararını açıkladı', 'Avrupa Birliği Rusya’ya yeni yaptırımlar getirdi',
                  'Trump says new tariffs on China will start Monday', 'Milli takım Euro 2028 elemelerinde Galler’i mağlup etti', 'İşçi servisi kaza yaptı 5 yaralı']:
            self.assertFalse(any(rx.search(t) for _, rx in A.ELE), t)

    def test_elenenler(self):
        for t, neden in [('Black Friday deals: the best coupon codes', 'alisveris/indirim'), ('Galatasaray maçı nereden izlenir, hangi kanalda?', 'yayin rehberi'),
                         ('Günlük burç yorumları 8 Kasım', 'burc/kumar'), ('Kadın cinayeti: cesedi bulundu', 'ozel kisi trajedisi')]:
            self.assertEqual(next((a for a, rx in A.ELE if rx.search(t)), None), neden, t)

    def test_ceza_siyaset_spor_gundemde_uygulanmaz(self):
        for ad, rx, d, alanlar in A.CEZA:
            self.assertFalse(set(alanlar) & {'siyaset', 'spor'}, ad)

class UcUca(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(); cls.eski = os.getcwd(); os.chdir(cls.dir); os.makedirs('site')
        now = datetime.now(timezone.utc)
        def it(t, dk, s='', i=None): return dict(t=t, l='https://x.test/%s' % abs(hash(t + str(dk))), d=(now - timedelta(minutes=dk)).isoformat(), s=s, **({'i': i} if i else {}))
        hikayeler = [
            ('siyaset', 'tr', 'tr', ['Erdoğan Bakü’de Aliyev ile görüştü: enerji anlaşması imzalandı', 'Cumhurbaşkanı Erdoğan, Aliyev ile Bakü’de enerji anlaşması imzaladı', 'Erdoğan ve Aliyev Bakü’de bir araya geldi, enerji anlaşması imzalandı', 'Erdoğan Azerbaycan’da: enerji anlaşmasını Aliyev ile imzaladı']),
            ('spor', 'sport', 'tr', ['Galatasaray Fenerbahçe’yi 3-1 yendi: derbide gol yağmuru', 'Derbide Galatasaray Fenerbahçe’yi 3-1 geçti', 'Galatasaray, Fenerbahçe karşısında 3-1 kazandı derbi sonrası açıklamalar', 'Fenerbahçe derbide Galatasaray’a 3-1 yenildi']),
            ('gundem', 'tr', 'tr', ['Meteoroloji’den 18 il için sarı kod uyarısı: sağanak ve kar', 'Meteoroloji 18 il için sarı kodlu uyarı yaptı sağanak kar bekleniyor', '18 ilde sarı kod: Meteoroloji sağanak ve kar uyarısı verdi', 'Sarı kodlu uyarı 18 ilde: Meteoroloji yağış uyarısı']),
            ('tech', 'tech', 'tr', ['Samsung Galaxy S26 Ultra’nın fiyatı sızdı: 70 bin TL', 'Galaxy S26 Ultra fiyatı sızdırıldı Samsung 70 bin TL', 'Samsung Galaxy S26 Ultra Türkiye fiyatı ortaya çıktı sızıntı']),
            ('alisveris', 'tech', 'en', ['Black Friday deals: best coupon codes for every gadget', 'Black Friday deals and coupons you should know', 'Amazon Black Friday deals coupon list']),
        ]
        src, feeds, n = [], {}, 0
        for ad, cat, dil, basliklar in hikayeler:
            for j, t in enumerate(basliklar):
                sid = '%s%d' % (ad, j); n += 1
                src.append(dict(id=sid, name='Kaynak %s %d' % (ad, j), lang=dil, cat=cat, url='https://%s%d.test/rss' % (ad, j), plat='web', calisma={'siyaset': 'siyaset', 'spor': 'spor', 'gundem': 'gundem', 'tech': 'tekno', 'alisveris': 'tekno'}[ad], tip='ana akim', ulke='TR', oncelik=2, nitelik=[], aktif=True))
                feeds[sid] = dict(name='Kaynak %s %d' % (ad, j), lang=dil, cat=cat, plat='web', url='x', items=[it(t, 15 + j * 7, 'Ayrıntılar için haberin devamına bakın. 70 bin TL rekor.', 'https://img.test/a.jpg')])
        json.dump(dict(generated=now.isoformat(), saglik={'kaynak': n}, feeds=feeds), open('site/feeds.json', 'w'))
        json.dump(src, open('sources.json', 'w'))
        json.dump({s['id']: {'son_basari': now.isoformat(), 'ardisik_basarisiz': 0, 'son_kod': 200, 'ms': 300, 'son_haber': now.isoformat()} for s in src[:-1]}, open('site/kaynak-durum.json', 'w'))
        shutil.copy(os.path.join(KOK, 'masa.py'), 'masa.py') if False else None
        A.main()
        cls.O = json.load(open('site/data/ozet.json')); cls.R = json.load(open('site/data/reels.json')); cls.K = json.load(open('site/data/kaynaklar.json'))
    @classmethod
    def tearDownClass(cls): os.chdir(cls.eski); shutil.rmtree(cls.dir, ignore_errors=True)

    def test_dosyalar(self):
        for f in ['ozet', 'reels', 'kaynaklar', 'indeks'] + ['kume-' + a for a in A.ALANLAR]: self.assertTrue(os.path.exists('site/data/%s.json' % f), f)

    def test_kume_sayilari(self):
        top = self.O['sicak']['24']; self.assertGreaterEqual(len(top), 3)
        for c in top: self.assertGreaterEqual(c['kb'], 2)      # tek haberle sıcak konu yok

    def test_reels_profilleri_dengeli(self):
        pr = {p for r in self.R['adaylar'] for p in r['profil']}
        self.assertTrue({'siyaset', 'spor', 'gundem', 'teknoloji'} <= pr, pr)

    def test_reels_alisveris_elenir_ama_siyaset_spor_kalir(self):
        basliklar = ' '.join(r['t'] for r in self.R['adaylar'])
        self.assertNotIn('Black Friday', basliklar); self.assertIn('Erdoğan', basliklar); self.assertIn('Galatasaray', basliklar)
        self.assertGreaterEqual(self.R['elenen'].get('alisveris/indirim', 0), 1)

    def test_reels_alanlari(self):
        r = self.R['adaylar'][0]
        for k in ['oneri_baslik', 'ozet', 'neden_gundemde', 'carpici_ayrinti', 'turk_onemi', 'dogrulama', 'gorsel_potansiyel', 'hooklar', 'aci', 'puan', 'puan_gerekce', 'risk', 'kriter']: self.assertIn(k, r)
        self.assertEqual(len(r['hooklar']), 3); self.assertEqual(sum(w for _, w, _ in A.KRITER), 100); self.assertIn('viral garantisi', self.R['not_'])

    def test_kaynak_durumlari(self):
        d = {k['id']: k['durum'] for k in self.K['kaynaklar']}
        self.assertEqual(d[self.K['kaynaklar'][0]['id']], 'aktif')
        self.assertEqual(d[self.K['kaynaklar'][-1]['id']], 'beklemede')     # durum kaydı yok: beklemede

    def test_kume_alanlari(self):
        sp = json.load(open('site/data/kume-spor.json'))['kumeler']; self.assertTrue(any('Galatasaray' in c['t'] for c in sp))
        sy = json.load(open('site/data/kume-siyaset.json'))['kumeler']; self.assertTrue(any('Erdoğan' in c['t'] for c in sy))

class KaynakDurumu(unittest.TestCase):
    def d(self, s, d): return A.durum_hesapla(s, d, '2026-11-08T12:00:00+00:00', datetime(2026, 11, 8, 12, tzinfo=timezone.utc).timestamp(), {})
    def test_durumlar(self):
        ok = {'son_basari': 'x', 'ardisik_basarisiz': 0, 'son_kod': 200, 'ms': 400, 'son_haber': '2026-11-08T10:00:00+00:00'}
        s = {'plat': 'web', 'oncelik': 2}
        self.assertEqual(self.d(s, ok), 'aktif')
        self.assertEqual(self.d(s, dict(ok, ms=4500)), 'yavas')
        self.assertEqual(self.d(s, dict(ok, ardisik_basarisiz=5, son_kod=403)), 'erisim-engelli')
        self.assertEqual(self.d(s, dict(ok, ardisik_basarisiz=5, son_kod=500)), 'hata')
        self.assertEqual(self.d(s, dict(ok, son_haber='2026-10-01T00:00:00+00:00')), 'guncellenmiyor')
        self.assertEqual(self.d(dict(s, aktif=False), ok), 'devre-disi')
        self.assertEqual(self.d(s, dict(ok, ardisik_basarisiz=1, son_kod=429, bekle_kadar='2027-01-01')), 'beklemede')

if __name__ == '__main__': unittest.main()
