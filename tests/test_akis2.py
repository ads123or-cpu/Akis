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

    def test_latin_disi_yayinci_adlari_ayri_kurum(self):
        self.assertNotEqual(A.kurum('الجزيرة', 'gn-ar'), A.kurum('الشرق الأوسط', 'gn-ar'))
        self.assertEqual(A.kurum('الجزيرة', 'gn-ar'), A.kurum('الجزيرة', 'bbc-ar'))
        self.assertNotEqual(A.kurum('朝日新聞', 'gn-ja'), A.kurum('読売新聞', 'gn-ja'))
        self.assertNotEqual(A.kurum('Kyiv Independent', 'a'), A.kurum('The Independent', 'b'))

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

    def test_okunmayan_alanlar_yazilmaz(self):
        k = json.load(open('site/data/kume-gundem.json'))['kumeler'][0]
        for f in ('cat', 'h1', 'h6', 'h24', 'h6o', 'h24o', 'k6', 'k24', 'sicak1', 'sicak24', 'yog', 'yog24', 'resmi', 'reels_alt', 'ul', 'ld', 'mk', 'yuk'): self.assertNotIn(f, k, f)
        self.assertNotIn('tp', k['og'][0]); self.assertLessEqual(len(self.O['son']), 40)
        self.assertNotIn('cat', json.load(open('site/data/indeks.json'))['kayitlar'][0])
        for f in ('t', 'kb', 'son', 'og', 'alanlar', 'alt', 'kaynaklar', 'gundem_alt'): self.assertIn(f, k, f)

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


class ReelsViralVeServis(unittest.TestCase):
    """Reels: hizmet/SEO sayfaları elenir, gerçek afet haberi elenmez; viral puanı tek kaynaklı ya da ölüm/savaş içerikli konuya verilmez."""
    def test_servis_sayfasi_elenir_gercek_haber_kalir(self):
        for t in ('Son Depremler Listesi (13 Kasım 2026): En Son Nerede Deprem Oldu?', 'HAVA DURUMU TAHMİNLERİ İL İL 14 KASIM', 'T.C. İSTANBUL 54. ASLİYE CEZA MAHKEMESİNDEN /BAŞKANLIĞINDAN', 'Kırıkkale Namaz Vakitleri (14 Kasım)'):
            self.assertTrue(A.SERVIS.search(t), t)
        for t in ('Malatya’da 5,2 büyüklüğünde deprem', 'Sel felaketi: 3 ilde okullar tatil edildi', 'Mahkeme kararını verdi: tahliye'):
            self.assertFalse(A.SERVIS.search(t), t)
    def test_viral_kosullari(self):
        self.assertTrue(A.VIRAL.search('Influencer banned from marathon after bizarre stunt'))
        self.assertEqual(sum(w for _, w, _ in A.KRITER), 100)
        self.assertIn('viral', [k for k, _, _ in A.KRITER])


class ReelsSikilik(unittest.TestCase):
    """2026-11-18: ilan, soru/SEO sayfası ve canlı blog Reels'e girmez; hava/sefer duyurusu ve küçük deprem ağır ceza alır."""
    def test_yeni_elemeler(self):
        for t, neden in [('T.C. Bakırköy 11. Asliye Hukuk Mahkemesinden İlan', 'resmi ilan'), ('HBO Max üyelik iptali nasıl yapılır?', 'soru/SEO sayfasi'),
                         ('EN DÜŞÜK EMEKLİ MAAŞI NE KADAR OLACAK 2027', 'soru/SEO sayfasi'), ('GTA 6 New Zealand time trick: How to play hours early', 'soru/SEO sayfasi'),
                         ('Dubai - Anadolu Efes maçı kaç kaç bitti, kim yendi?', 'soru/SEO sayfasi'), ('WATCH: Pope Leo leaves Peru', 'canlı blog')]:
            self.assertEqual(next((a for a, rx in A.ELE if rx.search(t)), None), neden, t)
    def test_servis_cezasi(self):
        rx = dict((ad, r) for ad, r, _, _ in A.CEZA)
        for t in ("18 Kasım Hava Durumu: İstanbul'da fırtına", "BUDO'nun yarınki 12 seferi iptal edildi"): self.assertTrue(rx['sıradan hava/ulaşım duyurusu'].search(t), t)
        self.assertTrue(rx['küçük deprem'].search("Van Gölü'nde 4,3 büyüklüğünde deprem")); self.assertFalse(rx['küçük deprem'].search('Malatya’da 5,2 büyüklüğünde deprem'))
    def test_siberia_siber_degil(self):
        self.assertFalse(A.KURAL['siber'].search('Plane crash in Siberia kills 19'))
    def test_yz_katman_gundemi_bastirmaz(self):
        a = A.alan_bul([dict(t='NSA iç ağı çöktü, yapay zekâ şüphesi')], 'NSA iç ağı çöktü, yapay zekâ şüphesi', {'gundem': 3, 'tekno': 1})
        self.assertIn('gundem', a); self.assertIn('yz', a)
        a = A.alan_bul([dict(t='OpenAI yeni GPT-6.2 modelini duyurdu')], 'OpenAI yeni GPT-6.2 modelini duyurdu', {'yz': 1})
        self.assertIn('tekno', a)
    def test_gelistirici_yanlis_pozitif(self):
        self.assertFalse(A.GELISTIRICI.search('Skydance cable shakeup: new executives to oversee programming'))
        self.assertFalse(A.KURAL['yz_guclu'].search('Biliyorum ki bu iş zor'))


class Gelistirici(unittest.TestCase):
    """Kod/geliştirici haberleri akışa girmez; tüketici sürüm ve oyun haberleri girer."""
    def test_kod_haberi_elenir(self):
        for t in ('GitHub Copilot artık ücretsiz', 'Python 3.15 released with JIT', 'Claude Code gets new agent mode', 'Linux kernel 7.2 lands', 'VS Code update adds AI'):
            self.assertTrue(A.GELISTIRICI.search(t), t)
    def test_tuketici_haberi_kalir(self):
        for t in ('iOS 27 developer beta 2 is out', 'Chrome 140 güncellemesi yayında', 'Developers of GTA 6 confirm delay', 'Galaxy S27 Ultra sızdı'):
            self.assertFalse(A.GELISTIRICI.search(t), t)


def ab(t, kay, s=''):
    """alan_bul kısayolu: tek başlıklı küme, kaynak bölümü sayacı."""
    return A.alan_bul([dict(t=t)], t + ' ' + s, kay)

class SavunmaAlani(unittest.TestCase):
    """2026-11-20: Savunma Sanayi alanı. Katmandır (yz gibi): Gündem/Siyaset'i bastırmaz. 'savunma' kelimesi tek başına sayılmaz."""
    def test_alan_listesi_ve_adlar(self):
        self.assertEqual(A.ALANLAR[A.ALANLAR.index('siber') + 1], 'savunma')
        self.assertEqual(A.ALAN_AD['savunma'], 'Savunma Sanayi')
        for k, _ in A.ALT['savunma']: self.assertIn(k, A.ALT_AD, k)
        self.assertEqual([k for k, _ in A.ALT['savunma']], ['yerli', 'hava', 'deniz', 'kara', 'fuze-hava-savunma', 'iha', 'ihracat-anlasma', 'uluslararasi'])
    def test_savunma_haberi(self):
        for t, kay in [('KIZILELMA envantere girdi, Baykar teslimatı tamamladı', {'gundem': 3}), ('ASELSAN yeni hava savunma sözleşmesi imzaladı', {'ekonomi': 2}),
                       ('Lockheed Martin wins $2B F-35 contract', {'tekno': 1}), ('Yunanistan yeni fırkateyn ve denizaltı alımını onayladı', {'gundem': 2}),
                       ('Çelik Kubbe için SİPER teslimatı başladı', {'gundem': 1}), ('TCG Anadolu tatbikata katıldı', {'savunma': 1}),
                       ('Army tests new missile launcher', {'savunma': 1}), ('Defense industry stocks rally in Europe', {'ekonomi': 2})]:
            self.assertIn('savunma', ab(t, kay), t)
    def test_katman_gundemi_bastirmaz(self):
        a = ab('KIZILELMA envantere girdi, Erdoğan tören düzenledi', {'gundem': 3})
        self.assertIn('gundem', a); self.assertIn('savunma', a)
    def test_saldiri_haberi_savunma_degil(self):
        for t in ('Şehit ailesine İHA saldırısı', "İsrail SİHA ile Gazze'yi vurdu: 4 ölü", 'Drone strike kills 5 in Kharkiv'):
            self.assertNotIn('savunma', ab(t, {'gundem': 3}), t)
        for t in ('Ukrayna İHA tedarikini iki katına çıkaracak', 'Polonya F-35 teslim aldı'): self.assertIn('savunma', ab(t, {'gundem': 1}), t)
        for t, k in (('Korkut Özal açıklama yaptı', {'gundem': 2}), ('Otokar yeni otobüsünü tanıttı', {'oto': 2}), ('Saab 9-3 classic car review', {'oto': 2})):
            self.assertNotIn('savunma', ab(t, k), t)
        self.assertTrue(A.TURKIYE_SAVUNMA.search('KAAN ilk uçuşunu yaptı'))
    def test_savunma_kelimesi_tek_basina_yetmez(self):
        for t, kay in [('Fenerbahçe savunmada hata yaptı, maç 2-2 bitti', {'spor': 3}), ('Sanığın savunması alındı, mahkeme kararını verdi', {'gundem': 2}),
                       ('Galatasaray savunma oyuncusu transferi için görüşüyor', {'spor': 2}), ('Kaan Ayhan gol attı', {'spor': 2}),
                       ("Rusya Kiev'e füze saldırısı düzenledi: 5 ölü", {'gundem': 3}), ('Israeli drone strike kills 3 in Gaza', {'gundem': 2}),
                       ('WIXOSS TCG to End New Production in February 2027', {'eglence': 1}), ('Nvidia RTX 5080 gaming PC discount', {'tekno': 2})]:
            self.assertNotIn('savunma', ab(t, kay), t)
    def test_savunma_kaynagi_ilgisiz_haber_gundeme(self):
        self.assertEqual(ab('Cevdet Yılmaz Özbekistan Cumhurbaşkanı ile görüştü', {'savunma': 1}), ['gundem'])
        self.assertEqual(ab('KAAN için yeni teslimat takvimi', {'savunma': 1}), ['savunma'])
    def test_alt_etiketler(self):
        self.assertIn('yerli', A.alt_etiket('savunma', 'ROKETSAN Tayfun füzesini test etti'))
        self.assertIn('fuze-hava-savunma', A.alt_etiket('savunma', 'ROKETSAN Tayfun füzesini test etti'))
        self.assertIn('deniz', A.alt_etiket('savunma', 'TCG Anadolu yeni görev için limandan ayrıldı'))
        self.assertIn('uluslararasi', A.alt_etiket('savunma', 'Rheinmetall wins Ukraine ammunition contract'))
    def test_reels_profili(self):
        c = dict(alanlar=['savunma'], kb=3, _kr=dict(saskin=0))
        pr, alt = A.profil_bul(c, 'Baykar KIZILELMA teslimatı tamamladı')
        self.assertEqual(pr, ['teknoloji']); self.assertIn('savunma', alt)
        pr, alt = A.profil_bul(c, 'Pentagon approves new frigate procurement plan')
        self.assertEqual(pr, ['gundem']); self.assertIn('savunma', alt)


class BuyukOlay(unittest.TestCase):
    """2026-11-20: büyük olaylar onlarca kümeye bölünmesin (ad çifti geçişi); farklı olaylar yine birleşmesin."""
    def test_anthropic_halka_arzi_toplanir(self):
        ipo_en = ['Anthropic IPO raises record $81.3 billion', 'Anthropic shares close 17% higher on first day of trading', 'Anthropic starts trading on Nasdaq after largest IPO in history',
                  'Anthropic sets share price at $83 for stock market debut', 'Investors cheer Anthropic IPO as AI demand surges', 'What the Anthropic IPO means for OpenAI',
                  'Anthropic IPO: employees become millionaires overnight', 'Anthropic market debut beats SpaceX record', 'Analysts split on Anthropic valuation after IPO',
                  'Anthropic IPO lifts Nvidia and Amazon shares', 'Anthropic pulled off the biggest IPO ever', 'How the Anthropic IPO was priced', 'Anthropic IPO day protest outside office',
                  'Anthropic debuts on Nasdaq with $2 trillion valuation', 'Anthropic IPO: retail investors face allocation limits', 'Dario Amodei rings Nasdaq bell as Anthropic goes public',
                  'Anthropic IPO oversubscribed 20 times', 'After Anthropic IPO, what comes next for Claude', 'Anthropic first day of trading ends up 17%', 'Anthropic IPO tops Saudi Aramco record']
        ipo_tr = ['Anthropic halka arzla 81 milyar dolar topladı', "Anthropic'in halka arzı rekor kırdı", 'Anthropic hisseleri Nasdaq’ta ilk işlem gününde yükseldi',
                  'Yapay zekâ devi Anthropic halka arz oldu', 'Anthropic halka arzında hisse fiyatı 83 dolar', "Anthropic halka arzı sonrası Nvidia yükseldi",
                  'Anthropic halka arzı: çalışanlar milyoner oldu', "Claude'un sahibi Anthropic halka arzla borsada", 'Anthropic halka arzına yoğun talep', 'Anthropic halka arzı SpaceX rekorunu geçti']
        ipo_de = ['Anthropic Börsengang bringt 81 Milliarden Dollar', 'Rekord-Börsengang: Anthropic startet an der Nasdaq', 'Anthropic Börsengang übertrifft Erwartungen',
                  'Was der Anthropic Börsengang für Anleger bedeutet', 'Anthropic Aktie nach Börsengang 17 Prozent im Plus', 'Anthropic Börsengang: Mitarbeiter werden Millionäre',
                  'Anthropic Börsengang lässt Nvidia steigen', 'Anthropic Börsengang mit Rekordbewertung', 'Analysten zum Anthropic Börsengang', 'Anthropic Börsengang: Kleinanleger leer ausgegangen']
        diger = ['Anthropic releases Claude Opus %d.%d with longer memory' % (5, i) for i in range(10)] + \
                ['Anthropic opens new office in city number %d' % i for i in range(10, 30)] + \
                ['Anthropic researchers publish safety paper %d on interpretability' % i for i in range(30, 50)] + \
                ["Anthropic'ten yeni Claude özelliği %d" % i for i in range(50, 60)]
        ipo = [oge(t, 'en', 'e%d' % i, dk=5 + i * 7) for i, t in enumerate(ipo_en)] + [oge(t, 'tr', 't%d' % i, dk=8 + i * 9) for i, t in enumerate(ipo_tr)] + \
              [oge(t, 'de', 'd%d' % i, dk=11 + i * 11) for i, t in enumerate(ipo_de)]
        ilgisiz = [oge(t, 'en' if i < 50 else 'tr', 'x%d' % i, dk=3 + i * 6) for i, t in enumerate(diger)]
        ks = A.kumele_akis(ipo + ilgisiz)
        ipo_id = {o['id'] for o in ipo}
        ipo_kume = [k for k in ks if any(o['id'] in ipo_id for o in k['ogeler'])]
        self.assertLessEqual(len(ipo_kume), 3, [len(k['ogeler']) for k in ipo_kume])
        for k in ipo_kume: self.assertFalse([o['t'] for o in k['ogeler'] if o['id'] not in ipo_id])
    def test_myanmar_iki_dilde_toplanir(self):
        en = ['ICJ rules Myanmar committed genocide against Rohingya', 'Myanmar committed genocide against its Rohingya minority, UN court rules', 'World court finds Myanmar guilty of Rohingya genocide',
              'Rohingya refugees celebrate genocide ruling against Myanmar', 'What the Myanmar genocide verdict means for the Rohingya', 'Myanmar junta rejects genocide ruling',
              'Tears in court as Rohingya vindicated in Myanmar genocide case', 'Gambia hails ICJ verdict on Myanmar genocide', 'Myanmar genocide ruling sets precedent for other cases',
              'Rohingya genocide: what was said in court', 'Inside a Rohingya camp after the Myanmar genocide ruling', 'Myanmar must pay reparations to Rohingya, court says',
              'Aung San Suu Kyi era army found responsible for Rohingya genocide', 'Myanmar genocide case: key moments', 'UN chief welcomes Myanmar genocide ruling']
        tr = ["UAD: Myanmar Arakanlı Müslümanlara soykırım yaptı", "Uluslararası Adalet Divanı Myanmar'ı soykırımdan sorumlu tuttu", "Myanmar soykırım kararı: Arakanlılar sevindi",
              "Myanmar'a soykırım kararı", "Arakanlı Müslümanlar için tarihi soykırım kararı: Myanmar suçlu bulundu", "Myanmar soykırım davasında karar açıklandı",
              "Türkiye'den Myanmar soykırım kararına destek", "Myanmar ordusu soykırım kararını reddetti", "Myanmar soykırımı kararı İsrail davasına emsal olabilir", "Gambiya Myanmar soykırım kararını memnuniyetle karşıladı"]
        og = [oge(t, 'en', 'm%d' % i, dk=10 + i * 20) for i, t in enumerate(en)] + [oge(t, 'tr', 'n%d' % i, dk=15 + i * 25) for i, t in enumerate(tr)]
        # Önce 25 başlık 8 kümeye bölünüyordu. Kavramı olmayan, başlığı da benzemeyen yan haber ('tazminat ödemeli') ayrı kalabilir.
        ks = A.kumele_akis(og)
        self.assertLessEqual(len(ks), 3, [len(k['ogeler']) for k in ks]); self.assertGreaterEqual(max(len(k['ogeler']) for k in ks), 20)
    def test_ayni_kulup_farkli_oyuncu_birlesmez(self):
        # üçüncü geçiş ortak kulüp adıyla (tek ad, ad çifti değil) farklı oyuncu haberlerini birleştirmez.
        # Not: iki başlık neredeyse aynıysa (j>=.5) ilk geçiş zaten birleştirir; o davranış bu düzeltmenin kapsamı dışında.
        og = [oge('Real Madrid extends Tchouaméni contract until 2032', 'en', 'a'), oge('Arda Güler signs new long-term deal with Real Madrid', 'en', 'b', dk=40),
              oge('Real Madrid confirm Mbappé injury before derby', 'en', 'c', dk=80)]
        self.assertEqual(sorted(len(k['ogeler']) for k in A.kumele_akis(og)), [1, 1, 1])
    def test_iki_lider_cifti_olay_sayilmaz(self):
        self.assertFalse(A.ad_ciftleri({'trump', 'putin'})); self.assertFalse(A.ad_ciftleri({'chatgpt', 'claude'}))
        self.assertIn(('#ipo', 'anthropic'), A.ad_ciftleri(A.adlar('Anthropic IPO raises record sum', {'anthropic'})))
    def test_title_case_siradan_kelime_ad_degil(self):
        h = A.ozel_ad_havuzu(['Samsung yeni Galaxy Buds tanıttı', 'Apple yeni iPhone için çalışıyor', 'Bugün Apple ve Samsung açıklama yaptı'])
        self.assertFalse(A.adlar('Galaxy Buds Active Leak Shows Workout Design', h) & {'leak', 'shows', 'design', 'workout'})


class ReelsTekrarVeKapi(unittest.TestCase):
    """2026-11-20: tekrar süzgeci ortak ad ÇİFTİne bakar (Title Case kelimeleri değil); içerik kapısı rutin haberi dışarıda bırakır."""
    def test_farkli_sizintilar_tekrar_degil(self):
        h = A.ozel_ad_havuzu(['Apple yeni iPhone için çalışıyor', 'Samsung yeni Galaxy Buds tanıttı', 'Bugün Apple açıklama yaptı'])
        a1, c1 = A.reels_anahtar([oge('Galaxy Buds Active Leak Shows Workout Design')], h)
        a2, c2 = A.reels_anahtar([oge('Leak Says Apple Is Developing Two Designs')], h)
        self.assertFalse(c1 & c2); self.assertFalse(a1 & a2)
    def test_kizilelma_ve_robot_dansi_ayri(self):
        h = A.ozel_ad_havuzu(['Türkiye KIZILELMA teslim aldı', "Çin'de robotlar dans etti"])
        a1, c1 = A.reels_anahtar([oge('KIZILELMA envantere girdi: dünyada bir ilk')], h)
        a2, c2 = A.reels_anahtar([oge("Çin'de 151 insansı robot aynı anda dans ederek dünya rekoru kırdı")], h)
        self.assertFalse(c1 & c2)
    def test_ayni_olay_farkli_dil_tekrar(self):
        _, c1 = A.reels_anahtar([oge('Anthropic shares jump after record IPO', 'en')], {'anthropic'})
        _, c2 = A.reels_anahtar([oge("Anthropic halka arzda 81 milyar dolar topladı")], {'anthropic'})
        self.assertTrue(c1 & c2)
    def kart(self, **k):
        kr = dict(etki=0, saskin=0, viral=0, hikaye=0); kr.update(k.pop('kr', {}))
        c = dict(t=k.pop('t', 'x'), kb=3, alanlar=['gundem'], gundem_alt=['turkiye'], _kr=kr); c.update(k); return c
    def test_icerik_kapisi(self):
        self.assertFalse(A.icerik_kapisi(self.kart(t='Fenerbahçe maç hazırlıklarını sürdürdü', alanlar=['spor'], kb=3)))
        self.assertFalse(A.icerik_kapisi(self.kart(t='Borsa günü düşüşle tamamladı', alanlar=['ekonomi', 'gundem'], kb=3)))
        self.assertTrue(A.icerik_kapisi(self.kart(t="Hürmüz'de tanker mayına çarptı", kb=4, gundem_alt=['dunya', 'savas'])))
        self.assertTrue(A.icerik_kapisi(self.kart(t='Yeni vergi düzenlemesi', kr=dict(etki=6))))
        self.assertTrue(A.icerik_kapisi(self.kart(t='HONOR Türkiye’de üretime başladı', alanlar=['tekno'], kb=11)))
        # 'leak' tek başına gerçek şaşırtıcılık değil
        self.assertFalse(A.icerik_kapisi(self.kart(t='Latest leak showcases Motorola Razr Flex colors', alanlar=['tekno'], kr=dict(saskin=6))))
    def test_yabanci_sizinti_hafif_ceza(self):
        og = [oge('Galaxy S27 Ultra design leaks in new renders', 'en', 'a'), oge('Galaxy S27 Ultra leak shows new camera', 'en', 'b')]
        def c(yab): return dict(son=Z0, h6=2, h24=2, kb=2, resmi=False, gundem_alt=['dunya'], sadece_yabanci=yab, n_tr=0 if yab else 2, farkli=[], i=None,
                                alanlar=['tekno'], kategoriler=['tech'], ulkeler=[], liderler=[], markalar=['samsung'], plat_topluluk=False)
        for yab in (True, False):
            _, _, ceza, _ = A.reels_puanla(c(yab), og, og[0], ' '.join(o['t'] for o in og), Z0, None)
            self.assertEqual('yalnız yabancı kaynaklı sızıntı/söylenti' in ceza, yab)
        # siyaset/spor rutin haberine ceza yok kararı (2026-11-20) korunur
        for ad, rx, d, alanlar in A.CEZA: self.assertFalse(set(alanlar) & {'siyaset', 'spor'}, ad)

    def test_leak_finally_rutin_muafiyeti_yok(self):
        t = 'Motorola Razr Fold finally receives Android 17 stable update'
        self.assertFalse(A.carpici_gercek(t)); self.assertTrue(A.RUTIN.search(t))
        self.assertTrue(A.carpici_gercek('Dünyada ilk kez: insansız savaş uçağı envantere girdi'))


class YanlisAlan(unittest.TestCase):
    """2026-11-20: kelime içi ve çok anlamlı eşleşmeler (kumeleme-reels raporu bulgu 5)."""
    def test_iran_kelime_siniri(self):
        for t in ("Real Madrid, Tchouaméni'nin sözleşmesini 30 Haziran 2032'ye uzattı", 'Trafiği artıran yol çalışması başladı', 'YKS tarihi Haziran ayında'):
            self.assertFalse(A.KURAL['siyaset'].search(t), t)
        for t in ("İran'ın dışişleri bakanı konuştu", 'Iran rejects new sanctions', 'İranlı yetkililer açıkladı'):
            self.assertTrue(A.KURAL['siyaset'].search(t), t)
    def test_turkce_ev_oto_degil(self):
        self.assertNotIn('oto', ab('Ev gençlerinin lideri seçildi', {'gundem': 2}))
        self.assertFalse(A.KURAL['oto_guclu'].search('Ev gençlerinin lideri seçildi'))
        self.assertTrue(A.KURAL['oto_guclu'].search('EV sales jump in Europe as EVs get cheaper'))
    def test_samsung_galaxy_bilim_degil(self):
        for t in ('Galaxy S27 Ultra kamerası sızdı', 'Samsung Galaxy Buds Active leak', 'Galaxy Z Fold 8 update'):
            self.assertFalse(A.KURAL['bilim_guclu'].search(t), t); self.assertNotIn('bilim', ab(t, {'tekno': 3}))
        self.assertTrue(A.KURAL['bilim_guclu'].search('Astronomers find a galaxy older than expected'))
    def test_euro_2028_ve_altin_madalya_ekonomi_degil(self):
        for t in ('EURO 2028 kurası çekildi', 'Milli sporcumuz altın madalya kazandı', 'Altın top ödülü sahibini buldu'):
            self.assertFalse(A.KURAL['ekonomi_guclu'].search(t), t); self.assertNotIn('ekonomi', ab(t, {'spor': 2, 'gundem': 1}))
        for t in ('Euro rekor kırdı', 'Gram altın 3 bin lirayı aştı'): self.assertTrue(A.KURAL['ekonomi_guclu'].search(t), t)
    def test_spor_kaynakli_real_madrid(self):
        t = "Real Madrid, Tchouaméni'nin sözleşmesini 30 Haziran 2032'ye uzattı"
        s = 'Oyun kurucu akıllı oyunu ve uygulama gücüyle öne çıktı. Apple TV yayınında maçın oyun planı konuşuldu.'
        a = ab(t, {'spor': 8}, s)
        self.assertIn('spor', a); self.assertNotIn('tekno', a); self.assertNotIn('siyaset', a)


class KaynakDuzeltmeleri(unittest.TestCase):
    """2026-11-20: kaynak-kalitesi raporu (kurum adı, 72 saat sayacı, geliştirici süzgeci)."""
    def test_kurum_alt_dize_eslesmez(self):
        sabah = A.kurum('Sabah', 'x')
        for p in ('Adana Haber', 'Odatv', 'Dosya Haber', 'Afyon Ana Haber', 'Küçük Saat (Adana Haberleri)', 'Gazeta Spor'): self.assertNotEqual(A.kurum(p, 'x'), sabah, p)
        for p in ('A Haber', 'atv', 'ATV Haber', 'A Spor', 'Fanatik'): self.assertEqual(A.kurum(p, 'x'), sabah, p)
        self.assertNotEqual(A.kurum('Kayseri Anadolu Haber', 'x'), A.kurum('AA', 'y')); self.assertEqual(A.kurum('Anadolu Ajansı', 'x'), A.kurum('AA', 'y'))
        self.assertNotEqual(A.kurum('Haber Hürriyeti', 'x'), A.kurum('Hürriyet', 'y')); self.assertNotEqual(A.kurum('CNBC-e', 'x'), A.kurum('CNBC', 'y'))
    def test_72_saat_sayaci(self):
        now = datetime.now(timezone.utc)
        it = lambda t, saat: dict(t=t, l='https://k.test/%d' % saat, d=(now - timedelta(hours=saat)).isoformat())
        j = dict(feeds={'k': dict(name='K', lang='tr', cat='tr', items=[it('Bir', 2), it('İki', 50), it('Üç', 100), it('Dört', 300)])})
        _, n72 = A.ogeler_kur(j, {'k': {'id': 'k'}}, now.timestamp())
        self.assertEqual(n72['k'], 2)
    def test_gelistirici_kacaklari(self):
        for t in ('PHP 8.6 正式发布 新增部分函数应用与流监测 API', "Snapchat'ten yapay zeka asistanlarıyla AR Lens geliştirme aracı: Easy Lens CLI", 'Frames CLI Updated',
                  'NVIDIA DGX Spark Developer Kit Turns a Desk Into a Supercomputing Lab'):
            self.assertTrue(A.GELISTIRICI.search(t) and not A.TUKETICI.search(t), t)
        for t in ('Mercedes CLA yeni kasa tanıtıldı', 'iOS 27 developer beta 2 is out', 'Galaxy S27 Ultra sızdı', 'Clinic opens in Adana'):
            self.assertFalse(A.GELISTIRICI.search(t), t)


class Videolar(unittest.TestCase):
    def test_dil_yazidan_ve_tur(self):
        self.assertEqual(A.video_dil('الرئيس الأمريكي: لا حاجة لواشنطن', 'en'), 'ar')
        self.assertEqual(A.video_dil('Starship Flight 15 launch', 'en'), 'en')
        c = dict(alanlar=['gundem'], gundem_alt=['turkiye'])
        self.assertEqual(A.video_tur(dict(t='Portekiz - Danimarka | MAÇ ÖZETİ', cat='tr', dil='tr'), c), 'diger')
        self.assertEqual(A.video_tur(dict(t='Pope Leo returns to Peru', cat='world', dil='en'), c), 'dunya')
        self.assertEqual(A.video_tur(dict(t='Fon dosyasında yeni gelişme', cat='tr', dil='tr'), c), 'turkiye')

    def test_youtube_gecici_hata_uzun_beklemeye_alinmaz(self):
        import fetch_feeds as F
        from datetime import datetime, timezone
        d = {}
        for _ in range(4): F.durum_guncelle(d, 'yt-x', False, 404, 'HTTP Error 404', None, datetime.now(timezone.utc))
        self.assertNotIn('bekle_kadar', d['yt-x'])
        for _ in range(3): F.durum_guncelle(d, 'web-x', False, 404, 'HTTP Error 404', None, datetime.now(timezone.utc))
        self.assertIn('bekle_kadar', d['web-x'])
        self.assertTrue(F.youtube_mu('https://www.youtube.com/feeds/videos.xml?channel_id=UC1'))
        self.assertEqual(d['yt-x']['ardisik_basarisiz'], 0)          # geçici YouTube hatası sayacı şişirmez

    def test_youtube_429_kisa_bekleme_ve_tavan(self):
        import fetch_feeds as F
        from datetime import datetime, timezone, timedelta
        simdi = datetime.now(timezone.utc); d = {'yt-y': {'ardisik_basarisiz': 40}}
        F.durum_guncelle(d, 'yt-y', False, 429, 'HTTP Error 429', None, simdi)
        bk = datetime.fromisoformat(d['yt-y']['bekle_kadar'])
        self.assertLessEqual(bk - simdi, timedelta(minutes=91))
        for n in (1, 5, 40, 200): self.assertLessEqual(F.bekleme_suresi(n, None), F.TAVAN_SN)

if __name__ == '__main__': unittest.main()
