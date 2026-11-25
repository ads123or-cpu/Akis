"""UI ve UX sozlesme testleri: index.tpl.html uzerinde yapisal ve kontrat kontrolleri. Ag ve site/ gerektirmez."""
import os
import re
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(KOK, 'index.tpl.html')


def sablon_oku():
    with open(TPL, encoding='utf-8') as f:
        return f.read()


class UiSozlesmeTest(unittest.TestCase):
    def test_tek_dosya_ve_dis_bagimlilik_yok(self):
        s = sablon_oku()
        self.assertNotRegex(s, r'<script[^>]+src=["\']https?://')
        self.assertNotRegex(s, r'<link[^>]+rel=["\']stylesheet["\'][^>]+href=["\']https?://')
        self.assertEqual(s.count('<script id="snap" type="application/json">/*SNAP*/</script>'), 1)

    def test_alan_ve_sayfa_butunlugu(self):
        s = sablon_oku()
        alan_m = re.search(r"var ALAN=\{([^}]+)\};", s)
        self.assertIsNotNone(alan_m)
        alanlar = set(re.findall(r"([a-z]+):'[^']+'", alan_m.group(1)))
        self.assertEqual(len(alanlar), 13)
        grup_m = re.search(r"var GRUP=(\[.*?\]);", s)
        self.assertIsNotNone(grup_m)
        for a in alanlar:
            self.assertIn("'" + a + "'", grup_m.group(1), a)
        sayfalar_m = re.search(r"var SAYFALAR=(\[.*?\]);", s)
        self.assertIsNotNone(sayfalar_m)
        for sid in ('bugun', 'akis', 'reels', 'trend', 'guncelleme', 'dunya', 'videolar', 'kayit', 'kaynak'):
            self.assertIn("'" + sid + "'", sayfalar_m.group(1), sid)

    def test_localstorage_ve_geriye_uyumluluk(self):
        s = sablon_oku()
        for anahtar in (
            'akis-kayit',
            'akis-okundu',
            'akis-gizli',
            'akis-tema',
            'akis-ziyaret',
            'akis2-ayar',
            'akis2-not',
            'akis2-durum',
            'akis2-okx',
            'akis2-okx-son',
            'akis2-okx-atla',
        ):
            self.assertIn("'" + anahtar + "'", s, anahtar)
        self.assertIn('var GESKI={', s)

    def test_dokunma_hedefi_ve_mobil_eylem(self):
        s = sablon_oku()
        stil = s[:s.index('</style>')]
        coarse_m = re.search(r"@media \(pointer:coarse\)\{([^}]+(?:\{[^}]*\}[^}]*)*)\}", stil)
        self.assertIsNotNone(coarse_m)
        self.assertIn('44px', coarse_m.group(1))
        dokun_m = re.search(r"@media \(max-width:860px\),\(pointer:coarse\)\{(.*?)\n\}", stil, re.S)
        self.assertIsNotNone(dokun_m)
        dokun = dokun_m.group(1)
        self.assertIn('.rk-okx .dg', dokun)
        self.assertIn('44px', dokun)
        self.assertIn('details>summary', dokun)
        self.assertNotIn('.rk details summary,details.kutu>summary', dokun)
        self.assertIn('.sag-l{min-width:44px', dokun)
        self.assertIn('.k-item-u a{min-width:44px', dokun)
        self.assertNotIn('@media (hover:none){.sat-e{display:none}}', s)
        self.assertIn('data-act="mKaydet"', s)
        self.assertIn('data-act="mGizle"', s)

    def test_bos_durum_ve_suzgec_kurtarma(self):
        s = sablon_oku()
        akis_m = re.search(r"function sayfaAkis\(\)\{(.*?)\n\}", s, re.S)
        self.assertIsNotNone(akis_m)
        gov = akis_m.group(1)
        self.assertIn('data-act="zaman" data-v="72"', gov)
        self.assertIn('data-act="zaman" data-v="0"', gov)
        self.assertIn('data-act="akisSifirla"', gov)
        self.assertIn('Son 3 günü göster', gov)
        self.assertIn('Tüm zamanlar', gov)
        self.assertIn('ayar.zaman', s)
        self.assertIn('String(ayar.zaman)', s)
        self.assertIn('ayar.cok', s)
        self.assertIn('ayar.sira', s)
        gizle_m = re.search(r"function gizle\(id\)\{(.*?)\n\}", s, re.S)
        self.assertIsNotNone(gizle_m)
        self.assertIn("querySelector('[data-id]')", gizle_m.group(1))
        self.assertIn("sayfaCiz()", gizle_m.group(1))

    def test_kaynak_gruplama_dilimlemeden_once(self):
        s = sablon_oku()
        kay_m = re.search(r"function kaynakIcerik\(\)\{(.*?)\n\}", s, re.S)
        self.assertIsNotNone(kay_m)
        gov = kay_m.group(1)
        self.assertIn('l.forEach(function(k)', gov)
        self.assertNotIn('goster.forEach', gov)

    def test_bugun_masaustu_panel_ve_rtl(self):
        s = sablon_oku()
        stil = s[:s.index('</style>')]
        uc_m = re.search(r"var UC_SAYFA=\{([^}]+)\};", s)
        self.assertIsNotNone(uc_m)
        self.assertIn('bugun:1', uc_m.group(1))
        self.assertIn('dir="auto"', s)
        self.assertIn('unicode-bidi:isolate', s)
        iso_m = re.search(r"([^\n{}]+)\{unicode-bidi:isolate\}", stil)
        self.assertIsNotNone(iso_m)
        iso_sel = iso_m.group(1)
        for sel in ('.kn', '.dil-k b', '.dk-u b', '.kp', '.k-item-u a', '.tbl td b', '.vk-u span', '.ara-s .a', '.cip'):
            self.assertIn(sel, iso_sel, sel)
        self.assertIn('<span class="kn" dir="auto">', s)
        self.assertIn('<b lang="\'+x.k+\'" dir="auto">', s)
        self.assertIn('@media (max-width:1099px)', stil)
        self.assertNotIn('@media (max-width:1100px)', stil)
        trs_m = re.search(r"\.tr-s\{([^}]+)\}", stil)
        self.assertIsNotNone(trs_m)
        self.assertNotIn('margin:0 -12px', trs_m.group(1))

    def test_reels_karti_ve_okxo_css(self):
        s = sablon_oku()
        stil = s[:s.index('</style>')]
        self.assertIn('#okxO .okx-f select', stil)
        self.assertIn('#okxO .okx-f textarea', stil)
        self.assertIn('viral garantisi değildir', s)
        self.assertIn('kural tabanlı', s)
        rk_m = re.search(r"function reelsKart\(c\)\{(.*?)\n\}", s, re.S)
        self.assertIsNotNone(rk_m)
        self.assertIn('carpici_ayrinti', rk_m.group(1))
        self.assertIn('gorsel_potansiyel', rk_m.group(1))
        self.assertIn("replace(/[….]+$/,'')", rk_m.group(1))
        kisi_m = re.search(r"function sayfaKisi\(\)\{(.*?)\n\}", s, re.S)
        self.assertIsNotNone(kisi_m)
        self.assertIn("oi.innerHTML=''", kisi_m.group(1))


if __name__ == '__main__':
    unittest.main()
