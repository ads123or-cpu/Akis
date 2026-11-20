# Akış: sayfa hızı ve veri boyutu denetimi

Tarih: 19.11.2026. Salt okunur denetim; proje dosyalarında değişiklik yapılmadı. Ölçümler canlı sitede (https://ads123or-cpu.github.io/Akis) başsız Chrome ile alındı. Ölçümler üç ayrı veri turuna denk geldi (16:35, 16:46 ve 18:52 UTC); dosya boyutları turdan tura birkaç KB oynuyor.

Ölçüm betikleri proje dışında, geçici klasörde duruyor: `olc.mjs` ve `olc2.mjs` (scratchpad). Telefon benzetimi: 390 px genişlik, 4 kat yavaş işlemci, "yavaş 4G" (1,6 Mb/s, 150 ms gecikme).

## Kısa tablo: ilk açılışta inenler

| Ne | Sıkıştırılmış | Açık | Not |
|---|---|---|---|
| `index.html` | 266 KB | 699 KB | **227 KB'ı (gz) arayüzün okumadığı `snap` bloğu** |
| `data/ozet.json` | 97–111 KB | 308–325 KB | her açılışta yeniden iner (önbelleğe alınmaz) |
| `data/trendler.json` | 99 KB | 299 KB | her ekranda, Reels'te bile arkadan iner |
| Dış görseller (Bugün) | 0,76–2,2 MB | — | 76×56 küçük resim için 1200–2544 px'lik asıl resim |
| **Toplam, masaüstü Bugün** | **2 675 KB / 16 istek** | 3 513 KB | site 477 KB, görseller 2 198 KB |
| **Toplam, telefon Bugün** | **2 509 KB / 14 istek** | 3 348 KB | site 477 KB, görseller 2 032 KB |

## Ekranların veri dosyaları (canlı, 16:46 turu)

| Dosya | gz | açık | Sınır | Doluluk |
|---|---|---|---|---|
| kume-tekno | 266 KB | 906 KB | 1100 KB (`tests/test_cikti.py:61`) | **%82** |
| kume-gundem | 246 KB | 888 KB | 1100 KB | **%81** |
| kume-siyaset | 162 KB | 620 KB | 1100 KB | %56 |
| kume-yz | 154 KB | 558 KB | 1100 KB | %51 |
| kume-spor / oyun / ekonomi / bilim / eglence | 110–126 KB | 457–506 KB | 1100 KB | %42–46 |
| kume-oto / siber | 86–94 KB | 369–375 KB | 1100 KB | %34 |
| kume-adana | 18 KB | 74 KB | (test listesinde yok) | — |
| kisisel/piril | 185 KB | 638 KB | 1100 KB (`tests/test_cikti.py:95`) | %58 |
| ozet | 107 KB | 316 KB | 450 KB (`tests/test_cikti.py:60`) | %70 |
| dil-tr (en büyük dil) | 141 KB | 449 KB | 700 KB (`tests/test_cikti.py:52`) | %64 |
| indeks (arama) | 266–276 KB | 686–700 KB | sınır yok | — |
| reels | 71–75 KB | 253–274 KB | sınır yok | — |
| kaynaklar | 45 KB | 462–471 KB | sınır yok | — |
| guncellemeler | 62 KB | 190 KB | sınır yok | — |

GitHub Pages önbellek başlıkları: tüm dosyalarda `cache-control: max-age=600`, zayıf ETag ve gzip var. Brotli yok. Başlık ayarı GitHub Pages'te değiştirilemiyor.

---

## Bulgular (önem sırasıyla)

### 1. YÜKSEK: `index.html` içindeki `snap` bloğu her açılışta 227 KB (gz) fazladan indiriliyor
- **Yer:** `index.tpl.html:429` (`<script id="snap">`), `build.py` (bloğu dolduran kod; 400+400+240 haberlik kota).
- **Ölçüm:** `index.html` 266 KB gz / 699 KB açık. Bunun 227 KB gz / 559 KB açık kısmı `snap` bloğu; sayfanın geri kalanı yalnızca 36 KB gz. Telefonda `index.html` 1,5–1,9 sn'de iniyor ve `ozet.json` isteği ancak bundan sonra başlıyor (istek başlangıcı 1 533–1 772 ms). Ana betik bloğun arkasında durduğu için `DOMContentLoaded` telefonda 1 780 ms'ye kayıyor.
- **Neden:** Arayüz bu bloğu okumuyor (README: "yalnız TechTurco paneli içindir"). Paneldeki `AkisController::snapshotOku` bloğu canlı `index.html`'den okuyor; `tests/test_sozlesme.py` de bu düzeni koruyor.
- **Öneri:** Bloğu ayrı bir dosyaya (örneğin `site/snap.json`) taşıyın ve TechTurco paneli o dosyayı okusun. Panel güncellenene kadar bir geçiş dönemi gerekirse blok bir süre iki yerde birden tutulabilir.
- **Beklenen kazanç:** İlk açılışta 227 KB gz eksilir; HTML 266 KB'tan yaklaşık 40 KB'a iner. Yavaş 4G'de bu yaklaşık 1,1–1,2 sn daha erken veri isteği ve ilk içerik demek (**tahmin**, iletim hızından hesaplandı).
- **Karar gerekir mi:** **Evet.** Projenin `CLAUDE.md` dosyası "snap bloğu bozulmaz" diyor. TechTurco paneli (başka bir proje) ve sözleşme testi birlikte değişmeli; tek taraflı yapılırsa panel bozulur.

### 2. YÜKSEK: Küçük resimler için asıl boyutlu fotoğraflar iniyor
- **Yer:** `index.tpl.html:531` (`<img class="sat-g" loading="lazy" … src=c.i>`), CSS `index.tpl.html:79` (`.sat-g` 76×56 px). Görsel adresleri kaynağın kendi görseli; `fetch_feeds.py:341` → `site/gorsel.json` (4 000 adreslik og:image önbelleği). Boyut küçültme yapılmıyor.
- **Ölçüm (Bugün, masaüstü):** 11 dış görsel, toplam 2 198 KB. Örnekler: evrensel.net 1 001 KB (1200×800), ntvspor 673 KB (2544×1677), sozcu 209 KB. Üçü de 76×56 px kutuda gösteriliyor. Telefonda en büyük boyalı öğe (LCP) manşet görseli: 5,9 sn; yazı içeriği 3,0 sn'de geliyor.
- **Yan etki:** `loading="lazy"` var, ancak Bugün'deki görsellerin çoğu ilk 2 400 px içinde kaldığı için yine de iniyor. Bunlar yavaş hatta veri dosyalarıyla aynı bant genişliğini paylaşıyor (madde 3).
- **Öneri:** (a) Küçük resimleri bir boyutlandırma servisinden 152×112 (2x) WebP olarak isteyin, örneğin wsrv.nl ya da Cloudflare Images. Bu dış servis demek: ziyaretçinin IP'si ve görsel adresi o servise gider. (b) Sıfır maliyetli yol: telefonda listede görseli varsayılan olarak kapatın, yalnız manşette gösterin. (c) Asıl görselin yanında bilinen küçük varyantları kullanın; tmgrup, milliyet ve cnnturk adreslerinde boyut, URL'nin içinde yazıyor. Kaynağa özel kural ister.
- **Beklenen kazanç:** Bugün'de görsel yükü 2,2 MB'tan yaklaşık 100–150 KB'a iner (**tahmin**, 12 görsel × 8–12 KB). Telefonda LCP birkaç saniye erkene çekilir (**tahmin**).
- **Karar gerekir mi:** **Evet.** Dış servis (gizlilik) ya da varsayılan görünüm değişir.

### 3. YÜKSEK (telefon): Ekran geçişleri ve arama, arkada inen görsellerin altında kalıyor
- **Ölçüm, sıralı gezinti (telefon, yavaş 4G, önbellek kapalı; Bugün → 6 Akış alanı → "Daha fazla" ×6 → kaydırma → Reels → …):** Reels ekranı **14,7–15,0 sn**'de açıldı. Oysa `reels.json` yalnızca 71 KB ve doğrudan açılışta 1 sn'de iniyor. İlk arama **11,4 sn**'de hazır oldu (indeks.json 266 KB). Siyaset alanı 4,2–4,7 sn sürdü.
- **Kanıt:** Aynı gezinti dış görseller engellenerek tekrarlandı. Reels 1 017 ms'de, Kaynaklar 518 ms'de açıldı; indeks 1 657 ms'de indi. Yani gecikmenin nedeni görseller (ayrıntı aşağıdaki "Ayrı ölçüm" bölümünde).
- **Neden:** Her alan sayfası 10–13 görsel (0,5–1,6 MB) başlatıyor. 280 satır kaydırıldığında `loading="lazy"` onlarcasını daha tetikliyor. Yavaş hatta bu akış veri dosyalarını sıraya sokuyor.
- **Öneri:** Madde 2'deki küçültme sorunu kökten çözer. Ek olarak veri isteklerine `fetch(..., {priority:'high'})`, görsellere `fetchpriority="low"` verilebilir. Sayfa değişince bitmemiş görsel indirmeleri, eski `#ana` içeriği silindiğinde zaten iptal olur.
- **Beklenen kazanç:** Geçişler, ayrı ölçümdeki değerlere iner: dosya başına yaklaşık 1–3 sn (**tahmin**, engelli ölçüme dayanıyor).
- **Karar gerekir mi:** Hayır (öncelik ipuçları). Küçültme için madde 2'ye bakın.

### 4. ORTA: `ozet.json` hiç önbelleğe girmiyor; tekrar ziyarette her seferinde 99 KB iniyor
- **Yer:** `index.tpl.html:492-493`. `D.ozet` henüz yokken `v=Date.now()`, üstüne `cache:'no-cache'`.
- **Ölçüm:** Aynı veri turunda ikinci açılışta `index.html` ve `trendler.json` önbellekten geldi, `ozet.json` ise yine 99 KB indi.
- **Öneri:** Açılışta önce `surum.json`'u (48 bayt, `no-store`) çekin, sonra `ozet.json?v=<generated>` isteyin. O zaman aynı turdaki ikinci açılış önbellekten okur. Bedeli bir gidiş-dönüş (yavaş 4G'de yaklaşık 150–300 ms). Alternatif: `ozet.json`'u sorgusuz `no-cache` ile isteyin. ETag sayesinde değişmediyse 304 döner, ama GitHub Pages CDN'i 10 dakikaya kadar eski kopya verebilir.
- **Beklenen kazanç:** 9 dakikalık tur içindeki tekrar açılışta 99 KB ve yaklaşık 0,7 sn kazanılır (telefon, **tahmin**). Yeni tur geldiyse kazanç yok.
- **Karar gerekir mi:** Hayır, ama "bir gidiş-dönüş daha" ile "eski veri riski" arasında küçük bir seçim var.

### 5. ORTA: `trendler.json` (99 KB gz) her girişte arkadan iniyor, telefonda asıl dosyayla yarışıyor
- **Yer:** `index.tpl.html:1059`, `ozetYukle().then(function(){rota();trendYukle()…})`.
- **Ölçüm:** Doğrudan `#/akis/tekno` açılışında `kume-tekno.json` (251 KB) ile `trendler.json` (100 KB) aynı anda başlıyor (2 293 ms). Tekno dosyası 4 281–4 818 ms'de bitiyor. Bugün ekranı trendleri zaten `ozet.trend_tr` alanından çiziyor. Trend dosyası yalnızca Trendler ekranında, trend ayrıntısında (`index.tpl.html:880`) ve aramada (TREG) gerekiyor.
- **Öneri:** `trendYukle()` çağrısını sayfanın kendi verisi bittikten sonraya ya da `requestIdleCallback`'e alın. Aramada `araAc()` içinde de çağrılsın.
- **Beklenen kazanç:** Telefonda Akış alanlarının ilk içeriği yaklaşık 0,5 sn erkene gelir (100 KB ÷ 1,6 Mb/s; **tahmin**). Her açılışta 99 KB eksilir (Trendler'e gidilmezse).
- **Karar gerekir mi:** Hayır.

### 6. ORTA: Alan dosyaları gereğinden büyük. İlk ekranda 40 konu gösteriliyor ama 360–564 konu iniyor
- **Yer:** `akis2.py:28` `KUME_ALAN_SINIR = 360`, `akis2.py:31` `DIL_AYRILAN = 12`, `akis2.py:757-767` (dil payı ekleme), `index.tpl.html:621` (`S.adet=40`).
- **Ölçüm:** kume-tekno'da 564 kayıt var: 360 sınır + diğer diller için ayrılan pay. Bunların yalnız 223'ü Türkçe/İngilizce. İlk 40 kayıt 42 KB gz, ilk 80 kayıt 70 KB gz, tamamı 251–266 KB gz. Gündem: 480 kayıt, ilk 40'ı 49 KB gz. Bu iki dosya 1100 KB sınırının %81–82'sinde. Bir yoğun haber gününde dil payının büyümesi testi kırabilir ve yayını durdurabilir (test yayın kapısı).
- **Öneri:** Alan dosyasını ikiye bölün: `kume-<alan>.json` ilk 60 konu, `kume-<alan>-2.json` geri kalanı. İkinci parça ilk çizimden sonra arkadan, ya da "Daha fazla" / süzgeç kullanılınca insin. Dil ve alt konu sayaçları ilk anda yalnız birinci parçadan hesaplanır, ikinci parça gelince düzelir. Daha basit seçenek: dil payını alan başına 12'den 6'ya indirin.
- **Beklenen kazanç:** Telefonda tekno ve gündem ilk içeriği yaklaşık 1–1,2 sn erken gelir (200 KB gz daha az; **tahmin**). Dosya sınırı riski de kalkar.
- **Karar gerekir mi:** **Evet.** Sayaçların bir an eksik görünmesi kabul edilebilir mi? Yoksa dil payı mı küçülsün?

### 7. DÜŞÜK–ORTA: JSON'da arayüzün okumadığı alanlar var (açık boyutta %14, sıkıştırılmışta yalnız %3–4)
- **Yer:** `akis2.py:750-754` (`sade`), `akis2.py:779-784` (`ozet_kume`, `tam`), `akis2.py:635` (`og[].tp`).
- **Doğrulama:** Arayüzün betiğinde şu alanlara hiç başvuru yok: `cat, h1, h6, h24, h6o, h24o, k6, k24, sicak1, sicak6, sicak24, yog, yog24, yuk, resmi, ul, ld, mk, reels_alt` ve `og[].tp`. Arama yapıldı, dinamik erişim (`c[k]`) yalnız `reg()` birleştirmesinde var. Testler bu alanları denetlemiyor. `kisisel.py:45-47` kendi dosyasında benzer alanları ayrıca yazıyor; o dosya da arayüzde okunmuyor.
- **Ölçüm:** kume + dil + ozet dosyalarının toplamı açıkta 8 681 KB'tan 7 421 KB'a (−%15), gz'de 2 234 KB'tan 2 155 KB'a (−%3,5) iner. Örnek: kume-tekno açıkta 885 KB'tan 759 KB'a, gz'de 256 KB'tan 247 KB'a.
- **Ek tekrarlar:** `c.l` her kayıtta `og[]` içinde de var (564/564). `farkli[]` başlıklarının 283'ünden 281'i `og[]` başlıklarıyla aynı. Konuların %14'ü birden fazla alan dosyasında tekrarlanıyor (4 302 kayıt, 3 840 tekil).
- **Öneri:** Kullanılmayan alanları alan, dil ve ozet çıktılarından çıkarın. Bu, telefonda JSON ayrıştırma süresini ve belleği azaltır; aktarılan baytı az etkiler. Özet metni (`s`) zaten 160–220 karakterle sınırlı (ortalama 133 karakter), uzun özet sorunu yok.
- **Beklenen kazanç:** İndirmede küçük (yaklaşık 4–9 KB/dosya). Ayrıştırmada %15 daha az veri (**tahmin**, ölçülmedi).
- **Karar gerekir mi:** Hayır. Yalnız "TechTurco ya da başka bir araç bu alanları `data/*.json`'dan okuyor mu?" sorusu sahibine teyit ettirilmeli. README'ye göre okumuyor. Buradaki `cat`, küme kaydındaki alandır. `CLAUDE.md`'nin korunmasını istediği kaynak `cat` alanı (`sources.json`, `masa.json`, snap) bundan etkilenmez.

### 8. DÜŞÜK–ORTA: Arama dizini 266 KB gz; özet alanı çıkarılırsa %28 küçülür
- **Yer:** `akis2.py:807` (`s=c['s'][:70]`, `cat`), `index.tpl.html:930` (arama yalnız `t`, `k`, `e` alanlarında arıyor).
- **Ölçüm:** 2 600 kayıt, 685 KB açık / 260 KB gz. `s` çıkarılınca 528 KB / 188 KB gz, `s` ile `cat` birlikte çıkarılınca 495 / 185 KB gz. Telefonda ilk "/" araması 1,6 sn'de hazır (ağ boşken), masaüstünde 941 ms. İndeks bellekteyken her tuş vuruşu 26–31 ms.
- **Not:** `s` alanı takip listesinde ve indeksten açılan ayrıntıda geçici özet olarak kullanılıyor (`index.tpl.html:583, 879`). Ayrıntı panelinde asıl alan dosyası yüklenince tam özet geliyor.
- **Öneri:** İndeksten `s` ve `cat` alanlarını çıkarın. İsteğe bağlı: arama kutusuna odaklanınca (ya da Bugün çizildikten sonra boşta) indeksi önceden isteyin.
- **Beklenen kazanç:** −75 KB gz, telefonda yaklaşık 0,4 sn (**tahmin**).
- **Karar gerekir mi:** Hayır.

### 9. DÜŞÜK: `ozet.json` içindeki "son" listesi 120 kayıt; Bugün ekranı 24 tane gösteriyor
- **Yer:** `akis2.py:791` (`[:120]`), `index.tpl.html:558` (`.slice(0,24)`).
- **Ölçüm:** `son` 88 KB açık / 31 KB gz. 40 kayda indirilince ozet 97 KB'tan 76 KB gz'ye iner (−%22). Fazla kayıtlar yalnız `reg()` ile kayıt defterine giriyor ve aramaya katkı veriyor, ama indeks zaten aynı konuları içeriyor.
- **Öneri:** `son` listesini 40 kayıtla sınırlayın.
- **Beklenen kazanç:** İlk açılışta −21 KB gz, telefonda yaklaşık 0,1 sn (**tahmin**).
- **Karar gerekir mi:** Hayır.

### 10. DÜŞÜK: "Daha fazla" her basışta tüm listeyi baştan çiziyor
- **Yer:** `index.tpl.html:981` (`S.adet+=40;ciz()`), `index.tpl.html:845` (`$('ana').innerHTML=f()`).
- **Ölçüm (gündem):** Telefonda (4 kat yavaş işlemci) betik süresi 40 satırda 14 ms, 280 satırda 41 ms. Ekrana yansıması 55 ms'den 177 ms'ye çıkıyor. Masaüstünde 6–9 ms (kareye kadar 29–38 ms). 280 satırda DOM yaklaşık 1 100 öğe (alan sayfası, 40 satırla).
- **Öneri:** Yalnız yeni 40 satırı `insertAdjacentHTML` ile ekleyin, ya da `.sat` satırlarına `content-visibility:auto` verin.
- **Beklenen kazanç:** Telefonda 280 satırda yaklaşık 177 ms'den 40–60 ms'ye (**tahmin**).
- **Karar gerekir mi:** Hayır.

### 11. BİLGİ: Kaydırma akıcı
- **Ölçüm (dokunma hareketiyle 6 000 px kaydırma, kare aralıkları):** Gündem 280 satır, telefonda ortalama 17,1 ms/kare, en kötü 33 ms, 50 ms'yi aşan kare yok, düşen kare oranı %3. Reels ve Kaynaklar'da (401 satır, DOM 4 219 öğe) ortalama 16,7 ms, düşen kare yok. Masaüstünde de aynı.
- **Sınır:** Bu, başsız Chrome'da ana iş parçacığının kare ölçümü. **Gerçek telefonda doğrulanmadı.** Yapışkan üst çubuktaki `backdrop-filter: blur(14px)` (`index.tpl.html:30`) gerçek bir GPU'da daha pahalı olabilir.
- **Karar gerekir mi:** Hayır.

### 12. BİLGİ: Uzun görevler kısa, kayma yok
- Telefon Bugün: 1 uzun görev, 159 ms. Dünya (dil-zh): 2 görev, toplam 234 ms, en uzunu 117 ms. Kaynaklar: 2 görev, toplam 138 ms. Düzen kayması (CLS): 0,003–0,014, iyi.
- Bellek değeri (`heapMB` 3–12 MB) başsız Chrome'da yuvarlanmış geliyor, yaklaşıktır.

### 13. DÜŞÜK: Projenin kendi ölçüm aracı yanıltıcı sayı veriyor
- **Yer:** `tools/ekran.mjs:42-46`.
- **Sorun:** Sabit 9 sn bekliyor ve dış görsellerin baytlarını da topluyor. Telefon ölçümünde gösterdiği "941 KB / 14 istek" yavaş hatta 9 sn'de bitebilen kısım; aynı ekran tam yüklenince 2 509 KB. Masaüstündeki "2 648 KB"ın 2,2 MB'ı görsel. Sitenin kendi baytını ayrı göstermiyor. Ölçtüğü `fcp` yalnızca kabuğun boyandığı an (250–650 ms); haberlerin göründüğü an değil.
- **Öneri:** Site ve dış bayt ayrı yazılsın. "İlk içerik" (ilk `.sat` görünene kadar) ve LCP eklensin. Bekleme süresi "ağ boşalana kadar" olsun.
- **Karar gerekir mi:** Hayır.

### Yan gözlem (performans dışı, doğrulanmalı)
kume-tekno'nun ilk kaydı bir spor haberi ("Real Madrid, Tchouaméni'nin sözleşmesini uzattı"). Kayıtta `alanlar=[gundem, tekno, siyaset]`, `alt.tekno=[apple, telefon, oyun]`, `mk=[apple]` yazıyor. Sınıflandırmada bir eşleşme hatası olabilir; bu denetimin kapsamı dışında, ayrıca bakılmalı.

---

## Ayrı ölçüm: her ekran kendi başına soğuk açılış (telefon, 4 kat yavaş işlemci, yavaş 4G)

"İlk içerik", haber satırının göründüğü an (FCP değil). FCP 250–650 ms; o an yalnız kabuk boyanıyor.

| Ekran | İlk içerik (görselli) | LCP (görselli) | İlk içerik (dış görsel engelli) | LCP (engelli) | Ekranın kendi dosyası (gz) | Dış görsel |
|---|---|---|---|---|---|---|
| Bugün | 2 264–2 966 ms | **5 248–5 892 ms** (manşet görseli) | 2 264–3 105 ms | 2 420–3 212 ms | ozet 100 KB | 9 istek, 759 KB |
| Akış/gündem | 4 480 ms | 4 524 ms | 4 493 ms | 4 544 ms | kume-gundem 251 KB | 11 istek, 818 KB |
| Akış/tekno | 4 840 ms | 4 900 ms | 4 254 ms | 4 320 ms | kume-tekno 251 KB | 13 istek, 823 KB |
| Akış/siyaset | 3 809 ms | 3 868 ms | — | — | kume-siyaset 166 KB | 11 istek, 510 KB |
| Reels | 3 482 ms | 3 588 ms | — | — | reels 71 KB | yok |
| Kaynaklar | 2 943–2 978 ms | ~3 080 ms | — | — | kaynaklar 45 KB | yok |
| Güncellemeler | 3 104–3 142 ms | ~3 200 ms | — | — | guncellemeler 62 KB | 10 istek, 1 603 KB |
| Trendler | 2 932 ms | 2 980 ms | — | — | trendler 100 KB | yok |
| Dünya | 3 046–3 241 ms | 3 388–3 572 ms | — | — | dil-zh 55 KB | 9 istek, 1 133 KB |
| Arama (ilk "/", Bugün yüklendikten 15 sn sonra) | 1 617–1 649 ms | — | — | — | indeks 266 KB | — |

Her ekranda zincir aynı: `index.html` yaklaşık 1,5–1,9 sn'de bitiyor, ardından `ozet.json` (+0,7 sn), ardından ekranın kendi dosyası geliyor. `trendler.json` da onunla aynı anda iniyor.

**Sıralı gezintide görsel etkisi (madde 3'ün kanıtı).** Telefonda aynı sıra iki kez gezildi: Bugün → alanlar → "Daha fazla" ×6 → 280 satır kaydırma → Reels → Kaynaklar → …

| Adım | Görseller açık | Dış görseller engelli |
|---|---|---|
| Reels açılışı (reels.json 71 KB) | **14 749–15 030 ms** | 1 017 ms |
| Kaynaklar (45 KB) | 2 538–2 790 ms | 518 ms |
| Güncellemeler (62 KB) | 1 515–2 149 ms | 640 ms |
| Dünya (55 KB) | 2 977–3 954 ms | 501 ms |
| İlk arama, indeks.json (266 KB) indirme | **11 374 ms** | 1 657 ms |
| Akış/tekno (251 KB) | 2 406–2 510 ms | 2 660 ms (fark yok) |

Sonuç: soğuk ilk açılışta görseller ilk içeriği geciktirmiyor (veri dosyaları önce başlıyor), yalnız LCP'yi 2,4 sn'den 5,2–5,9 sn'ye taşıyor. Kaydırma ve gezinti sonrasında ise biriken görsel indirmeleri yavaş hatta sonraki veri dosyalarını 3–15 kat geciktiriyor.

Ölçüm notu: Geçiş ölçümünde bazı satırlar (gündem, spor, siyaset; 1–4 ms, DOM 205 öğe) önceki sayfanın içeriğini yakalamış. Bunlar geçersizdir ve tabloya alınmadı. Masaüstünde (ağ sınırsız) alan geçişleri 391–578 ms, Reels 300 ms, Kaynaklar 285 ms, ilk arama 941 ms.

## Kullanılan komutlar
- Boyut ve başlık: `curl -sI -H 'Accept-Encoding: gzip'` ile her dosya; gz ve açık boyut ayrı ayrı indirilerek ölçüldü.
- Projenin aracı: `TABAN=https://ads123or-cpu.github.io/Akis node tools/ekran.mjs olcum` → masaüstü fcp 848 / dcl 1 055 / 2 648 KB / 17 istek; telefon fcp 392 / dcl 1 642 / 941 KB / 14 istek; Reels dcl 4 642 / 538 KB / 4 istek. Bu sayıların neden yanıltıcı olduğu madde 13'te.
- Ayrıntılı ölçüm: geçici klasördeki `olc.mjs` (açılış, geçiş, "Daha fazla", kaydırma, tekrar ziyaret) ve `olc2.mjs` (her ekran ayrı soğuk açılış; `engel` seçeneğiyle dış görseller engellenir).
