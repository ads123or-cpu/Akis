"""Kaynak cekme: ETag/304, hata yalitimi, devre kesici, ShiftDelete filtresi. Yerel HTTP sunucusuyla, ag gerekmez."""
import gzip, json, os, sys, threading, unittest, http.server
from datetime import datetime, timezone, timedelta
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
import fetch_feeds as F

def rss(n=3, baslik='Haber'):
    simdi = datetime.now(timezone.utc)
    ogeler = ''.join('<item><title>%s %d</title><link>http://x.test/%d</link><pubDate>%s</pubDate><description>özet</description></item>'
                     % (baslik, i, i, (simdi - timedelta(minutes=i)).strftime('%a, %d %b %Y %H:%M:%S GMT')) for i in range(n))
    return ('<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>%s</channel></rss>' % ogeler).encode()

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == '/ok':
            if self.headers.get('If-None-Match') == '"v1"':
                self.send_response(304); self.end_headers(); return
            self.send_response(200); self.send_header('ETag', '"v1"'); self.send_header('Content-Type', 'application/xml'); self.end_headers(); self.wfile.write(rss())
        elif self.path == '/gz':
            b = gzip.compress(rss()); self.send_response(200); self.send_header('Content-Encoding', 'gzip'); self.end_headers(); self.wfile.write(b)
        elif self.path == '/bozuk':
            self.send_response(200); self.end_headers(); self.wfile.write(b'<rss><channel><item><title>Kirik</title><link>http://x/1</link></rss>')
        elif self.path == '/429':
            self.send_response(429); self.send_header('Retry-After', '120'); self.end_headers()
        elif self.path == '/403':
            self.send_response(403); self.end_headers()
        else:
            self.send_response(404); self.end_headers()

class Sunucu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H)
        cls.url = 'http://127.0.0.1:%d' % cls.sv.server_address[1]
        threading.Thread(target=cls.sv.serve_forever, daemon=True).start()
    @classmethod
    def tearDownClass(cls): cls.sv.shutdown()
    def setUp(self): F.ESKI_DURUM.clear()
    def kaynak(self, yol, sid='t'): return dict(id=sid, name='T', lang='en', cat='tech', url=self.url + yol, plat='web')

    def test_basari_ve_etag(self):
        s, items, err, kod, _, ek = F.go(self.kaynak('/ok'))
        self.assertEqual((len(items), kod, err), (3, 200, None)); self.assertEqual(ek['etag'], '"v1"'); self.assertGreaterEqual(ek['ms'], 0)

    def test_304_basari_sayilir(self):
        F.ESKI_DURUM['t'] = {'etag': '"v1"'}
        s, items, err, kod, _, ek = F.go(self.kaynak('/ok'))
        self.assertEqual((items, kod, err), ([], 304, None)); self.assertTrue(ek['degismedi'])

    def test_gzip(self):
        self.assertEqual(len(F.go(self.kaynak('/gz'))[1]), 3)

    def test_bozuk_xml_yedek_ayrisim(self):
        self.assertEqual(len(F.go(self.kaynak('/bozuk'))[1]), 1)

    def test_hata_yalitimi(self):
        # Hatali kaynaklar istisna firlatmaz, digerlerini durdurmaz.
        sonuc = [F.go(self.kaynak(y, 'k' + y)) for y in ('/403', '/404', '/429', '/ok')]
        self.assertEqual([r[3] for r in sonuc], [403, 404, 429, 200])
        self.assertEqual(sonuc[2][4], 120)

    def test_durum_304_ardisik_hata_sifirlar(self):
        d = {'t': {'ardisik_basarisiz': 2, 'etag': '"v1"'}}
        F.durum_guncelle(d, 't', True, 304, None, None, datetime.now(timezone.utc), {'degismedi': True, 'ms': 50}, 7, '2026-01-01')
        self.assertEqual(d['t']['ardisik_basarisiz'], 0); self.assertEqual(d['t']['etag'], '"v1"'); self.assertEqual(d['t']['n'], 7)

    def test_devre_kesici(self):
        d = {}; simdi = datetime.now(timezone.utc)
        F.durum_guncelle(d, 'a', False, 429, 'x', 120, simdi); self.assertIn('bekle_kadar', d['a'])
        for _ in range(3): F.durum_guncelle(d, 'b', False, 500, 'x', None, simdi)
        self.assertIn('bekle_kadar', d['b'])
        F.durum_guncelle(d, 'c', False, 500, 'x', None, simdi); self.assertNotIn('bekle_kadar', d['c'])

class Yasak(unittest.TestCase):
    def test_shiftdelete_gercek_ornekler(self):
        import gzip as gz
        m = json.load(gz.open(os.path.join(KOK, 'tests', 'fixtures', 'baz-masa.json.gz'), 'rt', encoding='utf-8'))
        bulunan = [dict(p=o['p'], l=o['l'], t=o['t']) for c in m['kumeler'] for o in c['og'] if 'shiftdelete' in (o['p'] + o['l']).lower()]
        self.assertGreaterEqual(len(bulunan), 10)
        for it in bulunan: self.assertTrue(F.yasak_mi(it), it)

    def test_normal_yayinci_yasaklanmaz(self):
        self.assertFalse(F.yasak_mi(dict(p='Webrazzi', l='https://webrazzi.com/x', t='Apple yeni çip tanıttı')))
    def test_baslik_eki(self):
        self.assertTrue(F.yasak_mi(dict(p='', l='https://news.google.com/x', t='iPhone 18 sızdı - ShiftDelete.Net')))

if __name__ == '__main__': unittest.main()
