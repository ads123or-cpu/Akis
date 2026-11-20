# Kaynak kalitesi ve kopya oranı denetimi

Tarih: 19.11.2026. Salt okunur denetim; hiçbir proje dosyası değiştirilmedi.
Veri: canlı siteden indirilen `data/kaynaklar.json`, `data/ozet.json`, `data/kume-*.json`, `kaynak-durum.json`, `feeds.json` (üretim 2026-11-19 16:35 UTC). Yerel `sources.json` canlıdakiyle aynı (829 kaynak; id, url, aktif ve calisma alanlarında fark yok).
Kümeler, projenin kendi `akis2.py` kodu scratchpad'deki bir kopyada canlı `feeds.json` ile yeniden çalıştırılarak sayıldı. Sonuç canlı `ozet.json` sayımıyla ±3 küme içinde tutuyor (örneğin gündem 2832 / canlı 2831).
Savunma sanayi kaynaklarına bakılmadı (koordinatör ayrıca sınıyor).

## 1. Genel tablo (ölçülen)

- 829 kaynak var: 766'sı aktif, 63'ü kapalı. Kapatma nedenleri: 25 geliştirici/kod, 12 sürekli 403, 12 hiç haber üretmemiş, 8 Reddit 429, 5 üç haftadır sessiz, 1 YouTube 404.
- Aktiflerin durumu: aktif 751, yavaş 7, beklemede 6, hata 2.
- Aktiflerin platformu: web 520, Google Haberler (gnews) 182, YouTube 60, Reddit 4.
- Yanıt süresi: medyan 330 ms, p90 762 ms. 2 sn'yi geçen 18, 3 sn'yi geçen 7 kaynak var.
- 33 aktif kaynak son 72 saatte hiç haber vermedi.

### Alan başına kaynak (aktif / çalışan / gnews / dil dağılımı)

"Çalışan" burada durumu aktif ya da yavaş olan ve akışında en az bir haber bulunan kaynaktır.

| Alan | Toplam | Aktif | Çalışan | GN | Dil (çalışan) |
|---|---|---|---|---|---|
| tekno | 374 | 334 | 329 | 97 | en 150, tr 71, zh 27, ja 12, de 11, ko 9, fr 9, es 7 |
| gundem | 176 | 168 | 168 | 33 | tr 96, en 49, ar 5, de 5, fr 3, zh 3, ro 2, es 1 |
| eglence | 75 | 67 | 58 | 9 | en 38, tr 20 |
| spor | 41 | 39 | 38 | 11 | tr 24, en 13, es 1 |
| bilim | 37 | 33 | 32 | 5 | en 22, tr 10 |
| ekonomi | 31 | 30 | 30 | 3 | tr 15, en 15 |
| siyaset | 31 | 31 | 31 | 13 | en 17, tr 11, ar 1, zh 1, fr 1 |
| oto | 20 | 20 | 20 | 4 | en 12, tr 8 |
| oyun | 19 | 19 | 19 | 3 | en 13, tr 6 |
| yz | 12 | 12 | 11 | 0 | **yalnız en 11** |
| siber | 9 | 9 | 9 | 2 | en 7, tr 2 (ikisi de GN) |
| adana | 4 | 4 | 4 | 2 | tr 4 |

Dil başına aktif/çalışan: en 355/347, tr 272/267, zh 31/31, de 17/16, fr 14/13, ja 14/13, ko 11/10, ar 9/9, es 9/9, ru 6/6. Diğer 9 dilde 2–5 kaynak var.

## 2. Bulgular

### B1. Tek kaynaklı konu oranı çok yüksek: %92
- **Önem:** orta (ürünün "bağımsız kaynak" vaadini doğrudan etkiliyor)
- **Yer:** `akis2.py:300` `bagimsiz_say`, `akis2.py:599` `kumeler_kur`
- **Kanıt:** 9657 kümeden 8907'si (%92,2) tek bağımsız kaynaklı. Bunların 8710'u tek haberden oluşuyor. 1945 tanesi yalnız Google Haberler öğesinden oluşuyor.
- kb dağılımı: 1 → 8907, 2 → 504, 3 → 106, 4 → 55, 5 → 29, 6+ → 56.
- Alan başına tek kaynaklı oran (son 24 saat içindekiler parantezde): gündem %90 (%88), adana %87 (%82), tekno %92 (%92), yz %90 (%88), siyaset %86 (%84), spor %88 (%86), ekonomi %88 (%86), bilim %95 (%93), siber %88 (%86), oto %90 (%84), oyun %92 (%92), eğlence %95 (%93).
- Dile göre: tr %86, en %94, zh %98, de %95, ja %98.
- 3+ bağımsız kaynaklı küme sayıları: gündem 110, tekno 93, siyaset 51, spor 24, ekonomi 23, yz 19, bilim 12, oto 10, oyun 9, eğlence 9 (canlıda 10), siber 8, adana 3.
- **Yorum:** Uzun kuyruklu toplayıcıda bu oranın yüksek olması beklenir. Kaçan birleştirmelerin (aynı olay, iki küme) payı **ölçülmedi**.
- **Öneri:** Kaçan birleştirmeleri ayrı bir örneklemle ölçün: tek kaynaklı TR kümelerinde 18 saat içinde yüksek başlık benzerliği olan çiftler. Yeni kaynak eklerken tekno yerine az kaynaklı alanlara öncelik verin (B6).
- **Karar gerekir mi:** hayır (ölçüm işi).

### B2. Aynı akış iki kez kayıtlı: 6 çift birebir aynı URL
- **Önem:** düşük-orta (boşa çekim; haberin hangi alana yazılacağı dosyadaki sıraya bağlı kalıyor)
- **Kaynak id'leri:** `9to5mac`/`ios-9to5`, `macrumors`/`ios-macrumors`, `appleinsider`/`ios-appleinsider`, `apple-news`/`mac-newsroom`, `ntv-otomobil` (tekno)/`auto-oto-ntv` (oto), `electrek` (tekno)/`auto-electrek` (oto)
- **Kanıt:** Kanonik URL'ler aynı. 7 günlük haberlerin %100'ü ortak (örneğin electrek 23/23, appleinsider 20/20).
- **Öneri:** Her çiftten birini `aktif:false` yapın. Hangisinin kalacağına alan (`calisma`) bakarak karar verin. `cat` alanına dokunulmaz.
- **Karar gerekir mi:** evet, küçük karar: hangi kopya kalsın (özellikle oto/tekno çiftlerinde).

### B3. Farklı URL ama aynı içerik: 6 çift daha birebir kopya
- **Önem:** düşük (bağımsız sayımı şişirmiyor, çünkü kurum aynı; yalnız boşa çekim ve yanlış alan etiketi)
- **Kaynak id'leri ve kanıt:**
  - `ntv` ↔ `ntv-turkiye`: 20/20
  - `trthaber` ↔ `trt-sondakika`: 25/25
  - `milliyet` ↔ `milliyet-son` ↔ `milliyet-eko`: 15/15
  - `merlin` ↔ `gamingturk`: ikisi de merlininkazani.com, 25/25
  - `webtekno` ↔ `gnq-webtekno`: GN `site:` sorgusu, 23/25
  - `onedio` ↔ `gnq-onedio`: 9/12
- **Ek kanıt:** curl ile `milliyet.com.tr/rss/rssnew/ekonomirss.xml` ile `gundemrss.xml` indirildi. İkisi de 150 355 bayt geldi, ilk başlıklar aynı. Yani `milliyet-eko` ekonomi akışı değil, gündem akışı veriyor; ekonomi alanına gündem haberi taşıyor.
- **Öneri:** `milliyet-eko`, `gamingturk` (ya da `merlin`), `ntv-turkiye` ya da `ntv`, `trt-sondakika` kapatılabilir. Doğrudan RSS'i çalışan sitenin GN `site:` sorgusu (`gnq-webtekno`, `gnq-onedio`) gereksiz.
- **Karar gerekir mi:** evet (hangisinin kapanacağı).

### B4. Genel kopya oranı ve Google Haberler toplayıcıları
- **Önem:** orta
- **Kanıt (7 gün, 12 814 haber):**
  - Haberlerin 2206'sı (%17,2) başka bir aktif kaynakta da aynı bağlantı ya da aynı başlıkla var.
  - Platforma göre: web %14,8 (8717 haberde 1291), gnews %25,6 (3507 haberde 898), YouTube %2,9.
  - GN öğelerinin %31,2'si (1094/3507), zaten doğrudan web akışı olan bir kurumdan geliyor (Sabah, Habertürk, AA, TRT, Hürriyet, Milliyet, NTV, CNN Türk, Webtekno, DonanımHaber vb.).
  - GN öğelerinde 1017 farklı yayıncı var; 574'ü yalnız 1 haberle görünüyor. Bu uzun kuyruk, kalitesi bilinmeyen sitelerin akışa girdiği yer.
  - En çok görünen GN yayıncıları: sabah 139, vietnamvn 87, teknoblog 56, yahoo 51, technopat 43.
- **Kendi içinde çakışan GN sorguları (ölçülen ortak oran):**
  - `gn-galaxy-tr` %89, `gn-oneui-tr` %86, `android-tr-gn` %83, `gn-tr-samsung` %82, `gn-android17-tr` %83, `gn-galaxy-s-tr` %56: Samsung/Android TR sorguları birbirini tekrar ediyor.
  - `gnq-ai` ↔ `gnq-yapayzeka2`: %76
  - `gnq-deprem` ↔ `gn-tr-afet`: %60 / %52
  - `gnq-aa` %84 (AA'nın kendi akışlarıyla), `gnq-trt` %84, `gnq-sondakika` %84
- **Öneri:** Doğrudan akışı olan kurumların GN `site:`/kurum sorgularını (`gnq-aa`, `gnq-trt`, `gnq-webtekno`, `gnq-onedio`) kapatın. Samsung/Android TR sorgularını 2–3 sorguda birleştirin. Bu, çekim sayısını ve Google 429 riskini azaltır (`gn-tr-dolandirici` şu an 429 beklemesinde). Bağımsız sayım bundan etkilenmez, çünkü kurum aynı sayılıyor.
- **Karar gerekir mi:** evet (hangi GN sorgularının kalacağı editoryal tercih).

### B5. Kurum eşleştirmesinde gevşek desenler, ilgisiz yayıncılar "Sabah" sayılıyor
- **Önem:** orta (şu an etkisi ölçülemeyecek kadar az, ama Adana'yı doğrudan ilgilendiriyor)
- **Yer:** `akis2.py:57` deseni `sabah|a haber|ahaber|atv`, `akis2.py:69` `kurum()`
- **Kanıt:** "a haber" ve "atv" alt dize olarak eşleşiyor. 7 günlük 74 öğe Sabah grubu sayılıyor. Örnekler: Dosya Haber 26, **Adana Haber 14**, Anka Haber 11, Mağusa Haber Ajansı 6, Afyon Ana Haber 4, **Küçük Saat (Adana Haberleri) 3**, Odatv 2, Yeni Malatya Haber 2.
- **Benzer gevşek eşleşmeler:**
  - `aa`: "Kayseri Anadolu Haber"
  - `hurriyet`: "Haber Hürriyeti"
  - `ntv`: Alman "n-tv.de"
  - `cnbc`: "CNBC-e"
  - `google`: tüm Google blogları ve Trends tek kurum (bu bilinçli olabilir)
- **Etki ölçümü:** Desen sözcük sınırlı hale getirilip kümeleme kopyada yeniden koşturuldu. Bu veride **0 küme** etkilendi; hiçbir alanda kb≥2 ya da kb≥3 sayısı değişmedi. Risk ileride doğuyor: Adana Haber ile Sabah aynı olayı yazınca tek kaynak sayılır. `akis2.py:588`'deki (kurum, başlık) tekilleştirmesi de aynı başlıklı Adana haberini düşürebilir.
- **Öneri:** Desenleri sözcük sınırı ve tam ad ile yazın, örneğin `^a haber$`, `^atv\b`, `\bsabah\b`. Testlere ilgili yayıncı adlarını ekleyin.
- **Karar gerekir mi:** hayır.

### B6. Zayıf alanlar: az kaynak, tek dil
- **Önem:** orta-yüksek (alanlar ince kalıyor)
- **Kanıt:**
  - **yz:** 12 kaynağın tamamı İngilizce, Türkçe kaynak yok. TR yapay zekâ haberi bu alana yalnız içerik kuralıyla tekno kaynaklarından geliyor.
  - **siber:** 9 kaynak. TR olan 2'si de GN sorgusu (`gn-resmi-kvkk`, `gn-tr-siber`). 7 gün içinde 8 küme 3+ kaynaklı.
  - **adana:** 4 kaynak, ikisi GN (`gnq-adana`, `gnq-adana-ilce`). 53 kümenin 46'sı tek kaynaklı; 3+ kaynaklı küme 3.
  - **oto** (20) ve **oyun** (19): TR tarafı ince. Oyunda TR 6 kaynak var, ikisi aynı site (B3).
- **Yanlış alanda duran güvenlik kaynakları:** `bleepingcomputer`, `krebs`, `hacker-news-sec`, `y-malwarebytes`, `y-welivesecurity`, `y-helpnetsecurity`, `y-securityweek`, `gnq-siber`. Hepsi `calisma: tekno`. Bunlar `siber` alanına alınırsa siber kaynak sayısı 9'dan 17'ye çıkar. (Yalnız `calisma` değişir; `cat` değişmez.)
- **Öneri:** Önce güvenlik kaynaklarının `calisma` değerini `siber` yapın. Sonra aşağıdaki doğrulanmış adayları `tools/kaynak_test.py` ile resmi olarak sınayın.
- **Karar gerekir mi:** evet (calisma değişikliği alan sayımlarını değiştirir).

**Yeni kaynak adayları (curl ile indirildi, projenin `parse` işleviyle ayrıştırıldı):**

| Aday | Alan | Sonuç | Mevcutla ortak |
|---|---|---|---|
| `https://www.5ocakgazetesi.com/rss` | adana | 25 kayıt, 25 tarihli, en yenisi 19.11 16:34 | 2/25 |
| `https://www.kucuksaat.com/rss` | adana | 25 kayıt, 25 tarihli, en yenisi 19.11 16:20 | 5/25 |
| `https://www.otoaktuel.com.tr/rss` | oto (TR) | 25 kayıt, 25 tarihli, en yenisi 19.11 13:51 | 0/25 |
| `https://www.autoclub.com.tr/feed/` | oto (TR) | 10 kayıt, 10 tarihli, en yenisi 15.11 (seyrek) | 0/10 |
| `https://webrazzi.com/kategori/yapay-zeka/feed/` | yz (TR) | 15 kayıt, 15 tarihli | 15/15 (mevcut `webrazzi` akışının alt kümesi; ancak yz alanına TR kaynak olarak taşınabilir) |

**Elenen adaylar:**
- Zaten kayıtlı: `bleepingcomputer`, `krebs`, `oyungezer`, `y-darkreading`, `y-securityweek`, `therecord`.
- btnet.com.tr/feed: en yeni kayıt 02.02.2026, bayat.
- **Doğrulanmadı** (HTML ya da 404 döndü, ya da kayıt ayrışmadı): yenisoz.com.tr/rss, adanamedya.com/rss, adanahaber.com/rss, ajansadana, haberadana, cukurovaexpress, adanaekspres, siberbulten.com/feed, siberguvenlik.web.tr, cybermagonline, otohaber.com.tr/rss, otomobilgazetesi, teknoblog yapay-zeka, donanimhaber kategori, webtekno yapay-zeka.

### B7. Hata veren, uzun süredir sessiz ve yavaş kaynaklar
- **Önem:** düşük
- **Hata:**
  - `sabah-tek`: 8 ardışık "boş". curl ile 830 baytlık boş RSS geliyor; son haber 13 gün önce. Kapatılabilir.
  - `espn`: 7 ardışık "boş" Actions'ta. Ama Mac'ten curl ile 25 kayıt geldi; sorun Actions IP'si ya da UA olabilir, **doğrulanmadı**.
- **Beklemede (429):**
  - `r-iaf` ve 4 Reddit kaynağı: `rd-technology` 14 ardışık, `rd-localllama` 12, `rd-kgbtr` 13, `rd-openai` 10. 8 Reddit kaynağı aynı nedenle zaten kapatılmış; bu 4'ü ve `r-iaf` de aynı yolda.
  - `gn-tr-dolandirici`: 1 ardışık, geçici.
- **Yavaş (3 sn üstü ortalama):** `mfa-en2` 10 822 ms, `eu-komisyon` 5433, `mandiant` 3975, `cn-solidot` 3945, `cn-geekpark` 3698, `rt` 3650, `webtekno` 3035.
- **Sessiz:** 7–14 gün sessiz 13 kaynak (`sabah-tek`, `cisa-haber` 10,2 gün, `science` 9,2, `gn-site-halktv` 9,4, `gn-tr-windows-gunc` 10,4, `googleblog-pixel` 8,9, `tumblr-staff` 12,7…). 14–30 gün sessiz 5 kaynak (`netflix-about` GN 28,4 gün; YouTube `yt-mrbeast` 25, `yt-basakkarahan` 27, `yt-mkbhd` 18,8, `yt-dave2d` 14,1). 30 günü aşan yok.
- **Öneri:** `sabah-tek` kapatılabilir. Kalan 4 Reddit kaynağı ve `r-iaf` için önceki 8 kaynağın kararını uygulayın. `gn-site-halktv` sorgusunu kontrol edin.
- **Karar gerekir mi:** evet (Reddit ve sessiz kaynakların kapatılması).

### B8. "72 saatte haber" sayısı aslında 72 saati ölçmüyor
- **Önem:** düşük (gösterim hatası; Kaynaklar ekranında yanlış sayı görünüyor)
- **Yer:** `akis2.py:578` `n72[sid] += 1`. Sayaç 168 saatlik pencere süzgecinden önce, akıştaki tüm (30 güne kadar) öğeleri sayıyor. `index.tpl.html:668` ve `:772` bunu "72 saatte" diye gösteriyor.
- **Kanıt:** 766 aktif kaynağın 256'sında `haber72` gerçek 72 saat sayısından farklı. Örnekler: `livescience` 25 / gerçek 12, `openai` 25 / 14, `quanta` 5 / 1.
- **Öneri:** Sayacı yalnız `simdi - z <= 72*3600` olan öğeler için artırın.
- **Karar gerekir mi:** hayır.

### B9. Kullanıcı istekleri: ShiftDelete ve geliştirici haberi
- **Önem:** düşük (büyük ölçüde sağlanmış)
- **ShiftDelete:** `sources.json`'da yok. Canlı `feeds.json`'da ve tüm `data_*.json` dosyalarında "shift delete" geçen öğe 0. Süzgeç `fetch_feeds.py:382-384` ve `:397`'de.
- **Geliştirici haberi:** 25 geliştirici kaynağı kapalı (örneğin `android-dev-blog`). `GELISTIRICI` süzgeci (`akis2.py:560`) 13 981 öğeden 28'ini eliyor.
  - Gevşek bir terim taramasında süzgeçten geçen 39 başlık çıktı. Bunların küçük bir kısmı gerçekten geliştirici odaklı: "PHP 8.6 正式发布" (cnbeta), "Easy Lens CLI" (webrazzi), "Frames CLI Updated" (macstories), "Unix pipes… Linux terminal" (xda), "Gemini Decisions API" (google-ai), "NVIDIA DGX Spark Developer Kit" (nvidia-blog).
  - `chrome-releases` aktif; sürüm notları kısmen geliştiriciye yönelik olabilir, **değerlendirilmedi**.
- **Öneri:** `GELISTIRICI` desenine `php \d`, `\bcli\b`, `developer kit`, `\bapi\b` (yalnız başlıkta model/ürün adı yoksa) eklenmesi düşünülebilir. Yanlış eleme riski var, testle sınanmalı.
- **Karar gerekir mi:** evet, küçük karar: süzgecin ne kadar sıkı olacağı.

## 3. Ölçülmeyenler
- Kaçan küme birleştirmeleri (aynı olayın iki kümeye bölünmesi).
- Uzun kuyruk GN yayıncılarının tek tek kalitesi.
- ESPN'in Actions'ta neden boş döndüğü.
- Önerilen adayların `tools/kaynak_test.py` ile resmi testi; yalnız curl ve `parse` ile bakıldı.
