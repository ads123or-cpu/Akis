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
        veri = re.search(r"function okxVeri\(c,a,p\)\{(.*?)\n\}", s, re.S).group(1)
        self.assertIn("c.kanit==='iddia'", veri)
        self.assertIn("kaynakBicim", veri)
        # özet yalnız haberin kendi özetidir; kod metin uydurmaz
        self.assertIn("ozetTemiz(c.s)", s)
        self.assertIn("function okxTaslak(c,a,p)", s)

    def test_kural_denetimi_hata_ve_uyarilari_var(self):
        s = sablon()
        den = re.search(r"function okxDenetle\(m,c,hay,p\)\{(.*?)\n\}", s, re.S).group(1)
        for parca in ("yer tutucu", "Doldurulmamış şablon", "Ana gönderide bağlantı", "Etkileşim tuzağı", "bulunmayan sayı", "iddia olarak işaretli", "Metinde doğrudan alıntı var", "bağlamı değiştiren bir kesme"):
            self.assertIn(parca, den)
        self.assertIn("s==='hata'", re.search(r"function okxHata\(m\)\{(.*?)\n", s, re.S).group(1))
        # hata varsa X, Facebook sayfası ve Facebook profili açılmaz
        for ad in ("okxGit", "okxFbSayfa", "okxFbProfil"):
            gov = re.search(r"function " + ad + r"\(\)\{(.*?)\n\}", s, re.S).group(1)
            self.assertIn("okxHata(m)", gov, ad)
            self.assertLess(gov.index("okxHata(m)"), gov.index("window.open"), ad)

    def test_ayarlar_ayri_anahtarda_ve_varsayilana_donulur(self):
        s = sablon()
        self.assertIn("oku(okxAnahtar(p,'ayar'),{})", s)
        self.assertIn("yaz(okxAnahtar(okxP(),'ayar'),{})", s)
        # X ve Facebook ayrı anahtarlarda: X eski adı korur, Facebook "-fb-" alır
        self.assertIn("(p==='fb'?'akis2-okx-fb-':'akis2-okx-')+ad", s)
        self.assertNotIn('ayar.okx', s)
        for sb in ("sade", "ozetli", "kanca", "ozel"):
            self.assertRegex(s, sb + r":\['")

    def test_reels_baglantilari_yalniz_okx_ile(self):
        s = sablon()
        self.assertEqual(len(re.findall(r"\(okx\(c\)\?'<(?:a|div)[^']*(?:href|class)=\"[^\"]*\"[^']*'\+esc\(okxReelsUrl\(c\)\)", s)), 2)
        self.assertIn("reels-sablonu.html?marka='", s)

    def test_taslaklar_yerel_ve_sinirli(self):
        s = sablon()
        self.assertIn("yaz(okxAnahtar(d.p,'taslak'),tl.slice(0,50))", s)

class OkanFacebookTest(unittest.TestCase):
    def test_facebook_sablonlari_ve_varsayilani(self):
        s = sablon()
        self.assertIn("var OKF_SABLON={", s)
        self.assertIn("link:['Bağlantılı: başlık + kaynak + haber bağlantısı'", s)
        self.assertIn("sablon:'link'", s)
        for sb in ("sade", "kanca", "ozetli"):
            self.assertIn(sb + ":OKX_SABLON." + sb, s)

    def test_facebook_denetimi_madde_listesi_ve_kisalik(self):
        s = sablon()
        den = re.search(r"function okxDenetle\(m,c,hay,p\)\{(.*?)\n\}", s, re.S).group(1)
        self.assertIn("p==='fb'", den)
        for parca in ("Madde listesi var", "450 karakteri aşıyor", "Birden fazla emoji"):
            self.assertIn(parca, den)
        # ana gönderide bağlantı uyarısı yalnız X için
        self.assertIn("p==='x'&&/https?:", den)

    def test_facebook_hedefleri_dogru_adrese_gider(self):
        s = sablon()
        self.assertIn("https://business.facebook.com/latest/posts/published_posts", s)
        self.assertIn("https://www.facebook.com/sharer/sharer.php?u='+encodeURIComponent(pl)", s)
        self.assertIn("utm_source',p==='fb'?'facebook':'x'", s)
        prof = re.search(r"function okxFbProfil\(\)\{(.*?)\n\}", s, re.S).group(1)
        # kişisel profilde bağlantı satırı metinden çıkarılır (kart pencereden gelir)
        self.assertIn("split(pl).join('')", prof)
        for ad in ("okxFbSayfa", "okxFbProfil"):
            gov = re.search(r"function " + ad + r"\(\)\{(.*?)\n\}", s, re.S).group(1)
            self.assertIn("d.p!=='fb'", gov)

    def test_facebook_taslagina_yalniz_techturco_baglantisi_girer(self):
        s = sablon()
        veri = re.search(r"function okxVeri\(c,a,p\)\{(.*?)\n\}", s, re.S).group(1)
        self.assertIn("p==='fb'&&!okxTechturcoMu(c.l)", veri)
        self.assertIn("?'':okxLink(c,a,p)", veri)

    def test_platform_degisince_metin_yenilenir_ve_son_secim_saklanir(self):
        s = sablon()
        pl = re.search(r"function okxPl\(v\)\{(.*?)\n\}", s, re.S).group(1)
        self.assertIn("d.m=null", pl)
        self.assertIn("yaz('akis2-okx-son',v)", pl)
        self.assertIn("window.confirm", pl)


class OkanFotografTest(unittest.TestCase):
    def test_fotograf_dogrudan_olmazsa_gorsel_servisine_duser_ve_kapatilabilir(self):
        s = sablon()
        al = re.search(r"function okxGorselAl\(u,tur\)\{(.*?)\n\}", s, re.S).group(1)
        self.assertIn("mode:'cors'", al)
        self.assertIn("https://wsrv.nl/?url='+encodeURIComponent(u)", al)
        self.assertIn("a.gorselVekil===false", al)
        self.assertIn("gorselVekil:true", s)
        # ayarlarda açık ve anlaşılır bir onay kutusu
        self.assertIn("ck('gorselVekil'", s)

    def test_fotograf_kopyalama_vaadi_kullanici_hareketini_korur_ve_indirme_var(self):
        s = sablon()
        kop = re.search(r"function okxGorsel\(u\)\{(.*?)\n\}", s, re.S).group(1)
        # ClipboardItem'a söz verilir: tıklama izni uzun indirmede kaybolmaz
        self.assertIn("new ClipboardItem({'image/png':png})", kop)
        self.assertIn("data-act=\"okxGorInd\"", s)
        self.assertIn("case'okxGorInd':okxGorselIndir(v)", s)


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
