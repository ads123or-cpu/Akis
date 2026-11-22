"""Okan'a özel "X'te paylaş" (22.11.2026): varsayılan görünmez, Pırıl'a hiçbir koşulda görünmez, sitede X anahtarı yok. Ağ gerekmez."""
import os
import re
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sablon():
    return open(os.path.join(KOK, 'index.tpl.html'), encoding='utf-8').read()


class OkanXTest(unittest.TestCase):
    def test_kod_yerine_yalniz_hash_var(self):
        s = sablon()
        m = re.search(r"var OKX_HASH='([0-9a-f]+)'", s)
        self.assertIsNotNone(m)
        self.assertEqual(len(m.group(1)), 64)
        self.assertIn('crypto.subtle.digest', s)
        self.assertIn("k==='kapat'", s)

    def test_varsayilan_kapali_ve_pirila_hic_gorunmez(self):
        s = sablon()
        self.assertIn("var okxAcik=oku('akis2-okx',0)===1", s)
        fn = re.search(r"function okx\(c\)\{(.*?)\}\n", s).group(1)
        for parca in ("okxAcik", "ayar.profil!=='piril'", "S.sayfa!=='piril'", "'pc:'"):
            self.assertIn(parca, fn)

    def test_her_giris_noktasi_okx_ile_korunur(self):
        s = sablon()
        self.assertRegex(s, r"\(okx\(c\)\?'<button[^']*data-act=\"okxAc\"")
        self.assertIn("if(okx(c))it.push('<button type=\"button\" data-act=\"mOkx\"", s)
        # ayar nesnesinde iz bırakmaz (Pırıl ayarlara bakabilir); bayrak ayrı anahtarda
        self.assertNotIn('ayar.okx', s)

    def test_sitede_x_anahtari_ve_api_yok(self):
        s = sablon()
        for yasak in ('api.x.com', 'api.twitter.com', 'Bearer ', 'oauth_consumer', 'client_secret'):
            self.assertNotIn(yasak, s)

    def test_x_acilisi_niyet_adresiyle_ve_acilir_pencere_dogru(self):
        s = sablon()
        self.assertIn("https://x.com/intent/post?text='+encodeURIComponent(m)", s)
        # 'noopener' özelliği window.open'ı her zaman null döndürür: engellendi sanılır
        self.assertNotIn("'_blank','noopener');\n  if(w){try{w.opener=null}", s)
        gov = re.search(r"function okxGit\(\)\{(.*?)\n\}", s, re.S).group(1)
        self.assertNotIn("'noopener'", gov)
        self.assertIn('w.opener=null', gov)

    def test_taslak_olgu_katmaz_iddia_ve_kaynak_sablondan_gelir(self):
        s = sablon()
        veri = re.search(r"function okxVeri\(c,a\)\{(.*?)\n\}", s, re.S).group(1)
        self.assertIn("c.kanit==='iddia'", veri)
        self.assertIn("kaynakBicim", veri)
        # özet yalnız haberin kendi özetidir; kod metin uydurmaz
        self.assertIn("ozetTemiz(c.s)", s)
        self.assertIn("function okxTaslak(c,a)", s)

    def test_kural_denetimi_hata_ve_uyarilari_var(self):
        s = sablon()
        den = re.search(r"function okxDenetle\(m,c,hay\)\{(.*?)\n\}", s, re.S).group(1)
        for parca in ("yer tutucu", "Doldurulmamış şablon", "Ana gönderide bağlantı", "Etkileşim tuzağı", "bulunmayan sayı", "iddia olarak işaretli"):
            self.assertIn(parca, den)
        git = re.search(r"function okxGit\(\)\{(.*?)\n\}", s, re.S).group(1)
        # hata varsa X açılmaz
        self.assertIn("s==='hata'", git)
        self.assertLess(git.index("s==='hata'"), git.index("window.open"))

    def test_ayarlar_ayri_anahtarda_ve_varsayilana_donulur(self):
        s = sablon()
        self.assertIn("oku('akis2-okx-ayar',{})", s)
        self.assertIn("yaz('akis2-okx-ayar',{})", s)
        self.assertNotIn('ayar.okx', s)
        for sb in ("sade", "ozetli", "kanca", "ozel"):
            self.assertRegex(s, sb + r":\['")

    def test_reels_baglantilari_yalniz_okx_ile(self):
        s = sablon()
        self.assertEqual(len(re.findall(r"\(okx\(c\)\?'<(?:a|div)[^']*(?:href|class)=\"[^\"]*\"[^']*'\+esc\(okxReelsUrl\(c\)\)", s)), 2)
        self.assertIn("reels-sablonu.html?marka='", s)

    def test_taslaklar_yerel_ve_sinirli(self):
        s = sablon()
        self.assertIn("yaz('akis2-okx-taslak',tl.slice(0,50))", s)


class ReelsSablonuTest(unittest.TestCase):
    def sab(self):
        return open(os.path.join(KOK, 'araclar', 'reels-sablonu.html'), encoding='utf-8').read()

    def test_uyari_ve_dizinleme_kapali(self):
        s = self.sab()
        self.assertIn('X\'te ödeme uyarısı', s)
        self.assertIn('Orijinal İçerik Ödülleri', s)
        self.assertIn('noindex', s)

    def test_baglanti_parametreleri_ve_indirme_yedegi(self):
        s = self.sab()
        for k in ('"yazi"', '"marka"', '"kicker"', '"tasarim"'):
            self.assertIn('q.get(' + k + ')', s)
        self.assertIn('a.download = ad', s)

    def test_build_siteye_tasir(self):
        b = open(os.path.join(KOK, 'build.py'), encoding='utf-8').read()
        self.assertIn("'reels-sablonu.html'", b)
        self.assertIn("'araclar'", b)


if __name__ == '__main__':
    unittest.main()
