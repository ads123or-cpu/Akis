# Akış — arayüz ve kullanım (UX) denetimi

Tarih: 19.11.2026 · Salt okunur denetim, proje dosyası değiştirilmedi.
Bakılan: `index.tpl.html` (satır numaraları bu dosyaya göre), `build.py` (arayüzü etkileyen bir şey yok; yalnız `/*SNAP*/` yerine panel verisini gömüyor).
Ölçüm: canlı site (https://ads123or-cpu.github.io/Akis/), başsız Chrome, 390×844 (telefon, 2x) ve 1440×1000 (masaüstü). Taşma, dokunma hedefi boyutu ve adsız düğme sayımı sayfa içinde betikle ölçüldü; renk karşıtlığı WCAG formülüyle hesaplandı.

Ekran görüntüleri (hepsi bu klasörde):
`/private/tmp/claude-501/-Users-okangules-Developer/67a81fb3-7030-4143-89e6-f0cb785df56e/scratchpad/arayuz-ux/ekran/`
- Telefon: `m-bugun.png` (tam sayfa), `m-akis-liste.png`, `m-akis-siki.png`, `m-akis-izgara.png`, `m-akis-manset.png`, `m-akis-zaman.png`, `m-akis-baslik.png`, `m-trend.png`, `m-gunc.png`, `m-reels.png`, `m-kayit.png`, `m-kaynak.png`, `m-videolar.png`, `m-dunya.png`, `m-detay-koyu.png`, `m-ayar.png`, `m-arama.png`, `m-toast-koyu.png`, `m-toast-koyu-kirp.png`, `m-bugun-koyu-mor.png`, `m-akis-gece-kehribar.png`
- Masaüstü: `d-bugun.png`, `d-akis-liste.png`, `d-akis-siki.png`, `d-akis-izgara.png`, `d-akis-manset.png`, `d-akis-zaman.png`, `d-akis-baslik.png`, `d-trend.png`, `d-gunc.png`, `d-reels.png`, `d-reels-koyu.png`, `d-kayit.png`, `d-kaynak.png`, `d-detay.png`, `d-arama.png`, `d-akis-koyu-mor.png`, `d-akis-acik-kehribar.png`
- Ölçüm betiği ve ham sonuç: `.../scratchpad/arayuz-ux/olc.mjs`, `denetim.js`, `denetim.json`

Not: Görev metnindeki "Kayıtlı" sekmesinin sitedeki adı "Kayıtlar".

---

## Özet tablo

| # | Önem | Konu | Karar gerekir mi |
|---|---|---|---|
| 1 | Yüksek | Telefonda Güncellemeler ve Videolar sayfası yana taşıyor | Hayır |
| 2 | Yüksek | Telefonda Izgara görünümünde başlıklar sağdan kesiliyor | Hayır |
| 3 | Yüksek | Telefonda Trendler, Güncellemeler, Dünya, Kaynaklar menüde yok | Evet |
| 4 | Orta | Koyu temada "Geri al" düğmesi neredeyse görünmüyor | Hayır |
| 5 | Orta | Kaynak sayıları üç farklı biçimde yazılıyor ve çelişiyor | Evet |
| 6 | Orta | Akış başlığındaki konu sayısı ile listedeki sayı farklı | Hayır |
| 7 | Orta | Telefonda haber satırında saat ve kaynak adı kesiliyor | Hayır |
| 8 | Orta | Telefonda seçili alan çipi görünmüyor; "HABER" etiketi çip sırasına giriyor | Hayır |
| 9 | Orta | Telefonda dokunma hedefleri 32 px (önerilen 44) | Evet |
| 10 | Orta | Arama penceresinde kapat düğmesi, etiket ve odak tuzağı yok | Hayır |
| 11 | Orta | Ayarlar paneli diyalog olarak işaretlenmiyor, odak almıyor | Hayır |
| 12 | Orta | Telefonda "Aranıyor, yazan az" kutusu hiç görünmüyor | Evet |
| 13 | Orta | Görünüm düğmesi 6 görünüm arasında kör döngü; bazı sayfalarda etkisiz | Evet |
| 14 | Orta | Trend satırları ve Dünya kartları klavyeyle odaklanamıyor | Hayır |
| 15 | Düşük | Detay panelinde yazısız simge düğmeleri (kopyala, paylaş, gizle) | Hayır |
| 16 | Düşük | "Süzgeçler" düğmesinin simgesi "⋯" (Ayarlar ve Diğer ile aynı) | Hayır |
| 17 | Düşük | Meta satırı kırılınca yeni satır "·" ile başlıyor | Hayır |
| 18 | Düşük | Dil etiketi "EN +2 DIL" / "TR +2 DİL" farklı yazılıyor | Hayır |
| 19 | Düşük | Tek harfli kısayollar kapatılamıyor | Evet |
| 20 | Düşük | Elle seçilen koyu tema tarayıcı çubuğu rengine yansımıyor | Hayır |
| 21 | Düşük | Telefonda arama düğmesinde gereksiz "/" kısayol kutusu | Hayır |
| 22 | Düşük | Boş durum metinleri telefonda klavye tuşu öneriyor | Hayır |
| 23 | Düşük | Koyu temada logo içindeki beyaz çizgi zor seçiliyor | Hayır |
| 24 | Düşük | Kaynaklar tablosu başlığı telefonda 4 px aralık (doğrulanmadı) | Hayır |
| 25 | Düşük | Kaynak listesi yüklenemezse yeniden deneme yok | Hayır |

---

## Bulgular

### 1. Telefonda Güncellemeler ve Videolar sayfası yana taşıyor — Yüksek
- **Yer:** `index.tpl.html:693` (Güncellemeler tür segmenti), `:739` (Videolar tür segmenti), stil `:112` (`.seg` satır kırmıyor).
- **Senaryo:** 390 px, `#/guncelleme`: sayfa genişliği 687 px ölçüldü (ekran 390). "Hepsi · Güvenlik yaması · Sızıntı / iddia · Beta / test …" segmenti ekrandan taşıyor, bütün sayfa yana kayıyor; son düğmeler ancak sayfayı yana sürükleyerek görülüyor (`m-gunc.png`). `#/videolar`: sayfa genişliği 631 px.
- **Öneri:** Bu iki segmenti `.cipler` gibi kendi içinde yatay kaydırılan bir kaba koyun (`overflow-x:auto`) ya da telefonda `select` yapın. Genel önlem: `.arac .seg{max-width:100%;overflow-x:auto}`.
- **Karar gerekir mi:** Hayır.

### 2. Telefonda Izgara görünümünde başlıklar sağdan kesiliyor — Yüksek
- **Yer:** `:74` (`.sat{align-items:flex-start}`), `:306` (`.izgara .sat{flex-direction:column;overflow:hidden}`), `:361` (telefonda `.sat-ust` tek satır, `nowrap`).
- **Senaryo:** 390 px, Akış > Teknoloji, Görünüm = Izgara (`m-akis-izgara.png`). Kartlardaki başlıklar kelime ortasında kesiliyor: "Tchouaméni'nin sözleşm", "Motorola Razr Fold finally / stable update - GSMAren". Sebep: sütun yönündeki kartta metin bloğu kendi içeriği kadar genişliyor (tek satırlık meta satırı onu genişletiyor), kart da taşanı kesiyor. Başlık okunamıyor.
- **Öneri:** `.izgara .sat-m{width:100%;min-width:0}` ya da `.izgara .sat{align-items:stretch}`. Aynı kural Manşet için de güvenli olur.
- **Karar gerekir mi:** Hayır.

### 3. Telefonda Trendler, Güncellemeler, Dünya ve Kaynaklar menüde yok — Yüksek
- **Yer:** `:348` (telefonda `.sekme` ve `.diger` gizli), `:469-470` (`ANA_N=5`), `:831` (alt çubuk yalnız ilk 5 bölüm).
- **Senaryo:** 390 px'te alt çubukta Bugün, Akış, Videolar, Reels, Kayıtlar var. Trendler, Güncellemeler, Dünya ve Kaynaklar'a ancak sağ üstteki "⋯" (Ayarlar) içindeki "Bölümler" düğmeleriyle ya da Bugün'deki "Tüm trendler / Tümü" bağlantılarıyla gidilebiliyor (`m-ayar.png`). README'ye göre Trendler ve Güncellemeler ana ekranlar; telefonda keşfedilmeleri zor. Ayrıca bu sayfalardayken alt çubukta hiçbir sekme seçili görünmüyor (kullanıcı nerede olduğunu bilmiyor).
- **Öneri:** Seçenekler: (a) alt çubuğa 5. yerde "Daha" sekmesi koyup kalan bölümleri açılır listede göstermek; (b) Videolar ya da Kayıtlar yerine Trendler'i almak; (c) üst çubuğa telefonda da "Diğer" menüsünü açmak.
- **Karar gerekir mi:** Evet (hangi bölümler ana çubukta olsun).

### 4. Koyu temada "Geri al" düğmesi neredeyse görünmüyor — Orta
- **Yer:** `:231-232` (`.toast` zemini `--yaz`, düğme `--vr` + `filter:brightness(1.4)`).
- **Senaryo:** Koyu tema, telefon, bir haberi gizle (X). Bildirim kutusu açık krem zemin, "Geri al" yazısı açık turkuaz (`m-toast-koyu-kirp.png`). Hesaplanan karşıtlık yaklaşık 1:1 ile 1.5:1 arası (WCAG en az 4.5:1 ister); ekranda soluk seçiliyor. Kehribar vurgusunda aynı sonuç (açık sarı, krem zemin). Gizle ile Kaydet düğmesi yan yana olduğu için yanlışlıkla gizleme olası; geri alma tam bu durumda gerekiyor.
- **Öneri:** Düğme rengini temaya göre ayırın: açık temada `--vr-k`, koyu temada `--vr-a` (koyu ton) kullanın ve `filter` kaldırın; ya da düğmeye altı çizili/kalın stil verin.
- **Karar gerekir mi:** Hayır.

### 5. Kaynak sayıları üç farklı biçimde yazılıyor ve çelişiyor — Orta
- **Yer:** `:519-520` (`kaynakIlk`: `ks-1` + "kaynak daha"; telefonda "daha" `m-yok` ile gizli, `:361`), `:528`, `:785` (detay: "N bağımsız kaynak · M yayın").
- **Senaryo:** Aynı KIZILELMA haberi: masaüstü listede "CNBC-e · 17 kaynak daha", telefonda "19 kaynak" (ya da "18 kaynak"), detayda "9 bağımsız kaynak · 18 yayın" (`d-detay.png`, `m-akis-liste.png`). Telefonda "daha" kelimesi gizlendiği için sayı yanlış okunuyor (toplam değil, bir eksiği). Kullanıcı hangisinin gerçek olduğunu bilemiyor; README "bağımsız kaynak" sayısını esas alıyor.
- **Öneri:** Listede de bağımsız kaynak sayısını gösterin ("9 kaynak") ve yayın sayısını yalnız detayda verin; telefonda "daha" kelimesini gizlemek yerine sayıyı toplam yapın.
- **Karar gerekir mi:** Evet (listede hangi sayı görünecek).

### 6. Akış başlığındaki konu sayısı ile listedeki sayı farklı — Orta
- **Yer:** `:602` (başlık altı: toplam ve son 6 saat), `:621` (liste üstü: süzgeç sonrası sayı).
- **Senaryo:** Akış > Gündem: başlık altında "2.831 konu · son 6 saatte 1736", hemen altında "472 konu" (`m-akis-liste.png`). Varsayılan süzgeç 24 saat olduğu için 472 çıkıyor ama bu yazmıyor. Üstelik "son 6 saatte 1736" sayısı 24 saatlik 472'den büyük; iki sayı farklı şeyleri sayıyor (yayın / konu) gibi görünüyor ve çelişki izlenimi veriyor.
- **Öneri:** Liste üstüne neyin sayıldığını yazın: "Son 24 saatte 472 konu". Başlık altındaki sayılarla aynı birimi kullanın ya da başlık altındakini kaldırın. (Sayının neyi saydığı `akis2.py` tarafında doğrulanmadı.)
- **Karar gerekir mi:** Hayır.

### 7. Telefonda haber satırında saat ve kaynak adı kesiliyor — Orta
- **Yer:** `:361` (`.sat-ust` tek satır, taşan gizli), `:538` (sıra: tür, dil, çeviri, ürün, kaynak, saat, alan).
- **Senaryo:** 390 px, Güncellemeler: "Sızıntı · EN · Android · And… · 30" — saat "30" olarak kesik, "dk önce" görünmüyor (`m-gunc.png`). Akış'ta kaynak adı "Haberler.…", "Tek Hab…", "Habe…" olarak 3-6 harfe iniyor; "Star" gibi kısa adların sonrasında boşluk kalıyor (`.kn` `min-width:3.5em`).
- **Öneri:** Telefonda saati satırın başına alın ya da meta satırının iki satıra kırılmasına izin verin; Güncellemeler'de ürün adı ile kaynak adından birini telefonda gizleyin.
- **Karar gerekir mi:** Hayır.

### 8. Telefonda seçili alan çipi görünmüyor; "HABER" etiketi çip sırasına giriyor — Orta
- **Yer:** `:601` (sol menü), `:342` (≤1100 px'te sol menü yatay çip sırasına dönüşüyor), `:262` (`.grp` grup başlıkları).
- **Senaryo:** 390 px, `#/akis/tekno`: çip sırası "HABER · Gündem · Siyaset…" ile başlıyor, seçili "Teknoloji" çipi ekran dışında kalıyor (`m-akis-izgara.png`). Grup başlıkları (HABER, TEKNOLOJİ, YAŞAM) çiplerin arasında yazı olarak duruyor, dokunulamıyor ama düğme gibi yer kaplıyor.
- **Öneri:** Çizimden sonra seçili çipi görünür alana kaydırın (`scrollIntoView({inline:'center',block:'nearest'})`); telefonda `.sol-s .grp` gizlensin ya da ince bir ayraç olsun.
- **Karar gerekir mi:** Hayır.

### 9. Telefonda dokunma hedefleri 32 px — Orta
- **Yer:** `:93` (`.sat-e .ik-b` 32×32), `:107` (`.cip` 32 yükseklik), `:113` (`.seg button` 28), `:360`.
- **Senaryo:** 390 px Akış sayfasında 120 adet 32×32 simge düğmesi (Kaydet, Gizle, ⋯) ölçüldü; çipler 32, segment düğmeleri 28 px yüksek. WCAG en az 24 px'i (AA) geçiyor ama Apple'ın 44 px önerisinin altında. Kaydet / Gizle / ⋯ dikey üst üste ve aralarında boşluk az; yanlışlıkla Gizle'ye basmak kolay.
- **Öneri:** Telefonda simge düğmeleri 40-44 px yapın ya da görünür boyutu koruyup dokunma alanını `::after` ile büyütün. Gizle'yi ⋯ menüsüne taşımak satır sağını sadeleştirir.
- **Karar gerekir mi:** Evet (Gizle satırda kalsın mı).

### 10. Arama penceresinde kapat düğmesi, etiket ve odak tuzağı yok — Orta
- **Yer:** `:401`, `:924-934`.
- **Senaryo:** Telefonda arama açılınca kapatmak için yalnız kenardaki gri alana dokunmak var; Esc tuşu telefonda yok (`m-arama.png`). Arama kutusunun `aria-label`'ı yok (yalnız placeholder), diyalogda `aria-modal` yok, Tab ile arkadaki sayfaya çıkılabiliyor. Sonuçlar yalnız tarihe göre sıralı (`:932`); "apple" aramasında başlığında Apple geçmeyen bir haber ilk sırada çıktı. Eşleşen kelime vurgulanmıyor.
- **Öneri:** Kutuya "Kapat" düğmesi ekleyin; `aria-label="Ara"`, `aria-modal="true"`; başlıkta tam eşleşeni öne alan basit bir puan; eşleşen kelimeyi `<mark>` ile gösterin.
- **Karar gerekir mi:** Hayır.

### 11. Ayarlar paneli diyalog olarak işaretlenmiyor, odak almıyor — Orta
- **Yer:** `:907-909` (`ayarAc`), `:867` (yükleniyor panelindeki X).
- **Senaryo:** Ayarlar açıldığında panel `role="dialog"` almıyor, odak panele geçmiyor, telefonda arka sayfa kaydırması kilitlenmiyor (detay panelinde bunlar var, `:871-872`). Kapat (X) düğmesinde `aria-label` yok; ekran okuyucu yalnız "düğme" der. Aynısı "Konu yükleniyor…" panelindeki X için geçerli.
- **Öneri:** `ayarAc` içinde detay panelindeki rol/odak/kaydırma kilidi kodunu kullanın; tüm X düğmelerine `aria-label="Kapat"`.
- **Karar gerekir mi:** Hayır.

### 12. Telefonda "Aranıyor, yazan az" kutusu hiç görünmüyor — Orta
- **Yer:** `:592` (`masa-only`), `:342` (≤1100 px'te `.sag .masa-only{display:none}`).
- **Senaryo:** README'nin öne çıkardığı "trend var, haberimiz yok" listesi telefonda Bugün'de yok (`m-bugun.png`: sağ sütun altta yalnız Güncelleme radarı ve Reels için). Telefon kullanıcısı bu fırsat listesine ancak Trendler > "Bizde yok / az" ile ulaşabiliyor; o sayfa da menüde yok (bulgu 3).
- **Öneri:** Telefonda kısaltılmış hâlini (ilk 3) göstermek ya da trend şeridindeki "fırsat" kartlarını (`.tr-c.firsat`, kırmızı kenar) açıklayan kısa bir not koymak.
- **Karar gerekir mi:** Evet.

### 13. Görünüm düğmesi kör döngü; bazı sayfalarda etkisiz — Orta
- **Yer:** `:393`, `:989`.
- **Senaryo:** Üst çubuktaki görünüm simgesi her basışta bir sonraki görünüme geçiyor (Liste → Kompakt → Izgara → Manşet → Zaman → Başlıklar); istediğine varmak için 5 kez basmak gerekebiliyor, ne geleceği bilinmiyor (yalnız 2 sn'lik bildirim). Kaynaklar, Kayıtlar ve Videolar'da düğme görünür ama sayfa değişmiyor. Reels'te Izgara yalnız masaüstünde etkili.
- **Öneri:** Düğmeye basınca 6 seçenekli küçük menü açın (Ayarlar'daki segmentin aynısı); görünümün etkisiz olduğu sayfalarda düğmeyi gizleyin ya da soluk gösterin.
- **Karar gerekir mi:** Evet (menü mü döngü mü).

### 14. Trend satırları ve Dünya kartları klavyeyle odaklanamıyor — Orta
- **Yer:** `:549` (`.tr-s` div, bağlantı/tabindex yok), `:577` (`.dk` div), `:1038` (J/K yalnız odaklanabilen öğeye odak verir).
- **Senaryo:** Trendler sayfasında Tab ile trend satırlarına gelinemiyor, Enter ile detay açılamıyor (J/K satırı vurgular ama odak gitmez). Bugün'deki "Dünyada şimdi" kartları da yalnız fareyle açılıyor. Ekran okuyucu bunları tıklanabilir öğe olarak duyurmuyor.
- **Öneri:** Trend başlığını ve Dünya kartı başlığını `<a href="…?k=id">` yapın (haber satırlarındaki `.sat-t a` gibi) ya da `tabindex="0"` + `role="button"` + Enter işleyicisi.
- **Karar gerekir mi:** Hayır.

### 15. Detay panelinde yazısız simge düğmeleri — Düşük
- **Yer:** `:790-792`.
- **Senaryo:** Detayda Kaydet ve Reels fikri yazılı, ama kopyala, paylaş ve gizle yalnız simge (`m-detay-koyu.png`). Telefonda `title` görünmediği için ne yaptıkları anlaşılmıyor; gizle simgesi (üstü çizili göz) "görseli gizle" sanılabilir. Kopyala ve gizle düğmelerinde `aria-label` yok (yalnız `title`).
- **Öneri:** Kısa yazı ekleyin ("Kopyala", "Paylaş", "Gizle") ya da en azından `aria-label`.
- **Karar gerekir mi:** Hayır.

### 16. "Süzgeçler" simgesi "⋯" — Düşük
- **Yer:** `:613` (`ik('ayar')`), `:406`.
- **Senaryo:** Telefonda "Süzgeçler" düğmesindeki üç nokta, üst çubuktaki Ayarlar ve satırdaki "Diğer eylemler" ile aynı simge (`m-akis-liste.png`). Üç farklı işe aynı simge.
- **Öneri:** Süzgeç için huni ya da kaydırıcı simgesi ekleyin.
- **Karar gerekir mi:** Hayır.

### 17. Meta satırı kırılınca yeni satır "·" ile başlıyor — Düşük
- **Yer:** `:85` (`.sat-a>*+*:before{content:"·"}`).
- **Senaryo:** Telefonda Trendler: "2 saat önce başladı / · 4 bağımsız kaynak · Spor" (`m-trend.png`); masaüstü Izgara'da "· 47 dk önce" (`d-akis-izgara.png`); Reels kartında "· 46 dk".
- **Öneri:** Ayracı öğenin sonuna koyup satır sonunda gizlemek zor; daha basit yol `gap` ile boşluk bırakıp nokta kullanmamak ya da ayracı `margin-left` ile önceki öğeye bağlamak.
- **Karar gerekir mi:** Hayır.

### 18. Dil etiketi "EN +2 DIL" / "TR +2 DİL" farklı yazılıyor — Düşük
- **Yer:** `:266` (`text-transform:uppercase`), `:535` (`lang` özniteliği etiketin diline göre).
- **Senaryo:** Başlıklar ve Izgara görünümünde İngilizce haberlerde "EN +2 DIL", Türkçe haberlerde "TR +2 DİL" (`m-akis-baslik.png`). Büyük harfe çevirme etiketin `lang` değerine göre yapıldığı için "dil" kelimesi iki biçimde çıkıyor.
- **Öneri:** "+2 dil" kısmını `lang="tr"` olan ayrı bir `span` içine alın ya da büyük harf dönüşümünü kaldırıp metni hazır büyük yazın.
- **Karar gerekir mi:** Hayır.

### 19. Tek harfli kısayollar kapatılamıyor — Düşük
- **Yer:** `:1025-1045`.
- **Senaryo:** J, K, S, X, O, R, Z, G ve 1-9 tuşları değiştirici olmadan çalışıyor. Sesle yazma ya da ekran okuyucu kullanan biri istemeden kaydedebilir/gizleyebilir (WCAG 2.1.4). Masaüstünde güçlü bir özellik, ama kapatma seçeneği yok.
- **Öneri:** Ayarlar'a "Klavye kısayolları" aç/kapa ekleyin.
- **Karar gerekir mi:** Evet (varsayılan açık mı kalsın).

### 20. Elle seçilen koyu tema tarayıcı çubuğuna yansımıyor — Düşük
- **Yer:** `:8-9` (yalnız sistem temasına göre `theme-color`), `:483` (`temaUygula` meta etiketini güncellemiyor).
- **Senaryo:** Sistem açıkken Ayarlar'dan Koyu seçilirse telefonda tarayıcı çubuğu açık renk kalıyor, sayfa koyu (doğrulanmadı: başsız tarayıcıda çubuk görünmüyor; koddan çıkarım).
- **Öneri:** `temaUygula` içinde `meta[name=theme-color]` değerini `--bg` ile güncelleyin.
- **Karar gerekir mi:** Hayır.

### 21. Telefonda arama düğmesinde "/" kutusu — Düşük
- **Yer:** `:392`, `:348`.
- **Senaryo:** 390 px'te arama düğmesinde büyüteç yanında "/" kısayol kutusu duruyor (`m-akis-liste.png`); telefonda klavye kısayolu yok, yer kaplıyor ve anlamsız.
- **Öneri:** `@media (max-width:860px){.ara-b kbd{display:none}}`.
- **Karar gerekir mi:** Hayır.

### 22. Boş durum metinleri telefonda klavye tuşu öneriyor — Düşük
- **Yer:** `:754` (Kayıtlar: "S tuşuna basın"), `:862` (masaüstü ayrıntı boş durumu; telefonda görünmüyor, sorun yok).
- **Senaryo:** Telefonda Kayıtlar boşken "simgesine ya da S tuşuna basın" yazıyor.
- **Öneri:** Telefonda tuş kısmını gizleyin (`m-yok` sınıfı zaten var).
- **Karar gerekir mi:** Hayır.

### 23. Koyu temada logo çizgisi zor seçiliyor — Düşük
- **Yer:** `:33-34`.
- **Senaryo:** Koyu temada logo zemini açık vurgu rengine dönüyor (ör. #4cc9bd), içindeki çizgi beyaz kalıyor: karşıtlık 2.0-2.4:1 (`m-bugun-koyu-mor.png`). Süs öğesi, okumayı etkilemiyor.
- **Öneri:** Çizgiyi `var(--vr-y)` rengine bağlayın.
- **Karar gerekir mi:** Hayır.

### 24. Kaynaklar tablosu başlığı telefonda 4 px aralık — Düşük (doğrulanmadı)
- **Yer:** `:213` (`th{top:56px}`), `:349` (telefonda üst çubuk 52 px).
- **Senaryo:** Telefonda tablo kaydırılınca yapışkan başlık üst çubuğun 4 px altında durur, arada satır içeriği görünebilir. Ekranda kaydırılarak doğrulanmadı. Zaman çizelgesindeki saat başlığı (`:291`) aynı durumda.
- **Öneri:** Telefonda `top:52px` ya da ortak bir `--ust-h` değişkeni.
- **Karar gerekir mi:** Hayır.

### 25. Kaynak listesi yüklenemezse yeniden deneme yok — Düşük
- **Yer:** `:883`.
- **Senaryo:** Detay panelinde kaynak listesi alınamazsa yalnız "Yüklenemedi." yazıyor; düğme yok, panel kapatılıp açılmalı. (Ağ kesilerek denenmedi; koddan.)
- **Öneri:** Yanına "Yeniden dene" bağlantısı (`getir(id)` çağırır).
- **Karar gerekir mi:** Hayır.

---

## İyi çalışanlar (ölçüldü)
- Masaüstünde (1440 px) ölçülen 9 sayfanın hiçbirinde yatay taşma yok; adsız (etiketsiz) bağlantı/düğme sayısı tüm sayfalarda 0.
- Gövde metni karşıtlıkları yeterli: açık temada ikincil yazı 5.3-7.0:1, koyu temada 5.5-7.0:1; beş vurgu renginin hepsi açık ve koyu zeminde 5:1'in üstünde.
- Telefonda Liste, Kompakt, Manşet, Zaman çizelgesi ve Başlıklar görünümleri düzgün; detay paneli tam ekran açılıyor, geri tuşu ile kapanıyor, odak kapat düğmesine geçiyor.
- Gizle sonrası 5 sn geri alma, ⋯ menüsünde ok tuşu/Esc desteği, seçili düğmelerde `aria-pressed` ve sekmelerde `aria-current` var.

## Kapsam dışı ama görülen
- Akış > Teknoloji ilk sırada "Real Madrid … sözleşmesini uzattı" haberi duruyor (`d-akis-manset.png`); sınıflandırma sorunu, arayüz değil. Reels kartındaki hook metni başlığın İngilizce tekrarı ("3 saniyede özet: Galaxy Buds Active leak shows…", `m-reels.png`); içerik üretimi konusu.
