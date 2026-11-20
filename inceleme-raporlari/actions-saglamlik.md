# GitHub Actions hattı: sağlamlık denetimi

Tarih: 2026-11-19 · Salt okuma. Hiçbir proje dosyası değişmedi, workflow tetiklenmedi.
Kaynak: `.github/workflows/refresh.yml`, `tests/`, `gh run list -L 1000` (12-19 Kasım, 1000 çalıştırma), 60 başarılı turun iş/adım süreleri (`gh api .../jobs`), `git count-objects`, `gh repo view`.

## Kısa tablo (ölçülen)

| Ölçü | Değer |
|---|---|
| Son 1000 tur (12-19 Kasım) | 956 başarılı, 5 başarısız, 38 iptal, 1 sürüyor |
| Son 300 tur (17-19 Kasım) | 291 başarılı, 0 başarısız, 8 iptal (hepsi bekleyen cron/push turunun yerini alması) |
| Bir turun toplam süresi | medyan 11,6 dk, %90'ı 12,6 dk, en çok 17,4 dk (8 dk'sı bekleme) |
| İki tur başlangıcı arası | medyan 11,5 dk (README "≈9 dk", arayüz "yaklaşık 10 dk" diyor) |
| En uzun boşluk | 45,5 dk (16 Kasım 12:30Z), 32,2 dk (12 Kasım 23:24Z) |
| İş süreleri (medyan / en çok) | refresh 177 / 255 sn, deploy 11 / 37 sn, tekrar 485 / 490 sn |
| En yavaş adımlar | akis2.py 87 sn, fetch_feeds.py 62 sn (en çok 129 sn) |
| Faturalanan dakika (iş başına yukarı yuvarlanmış) | tur başına ~13 dk, günde ~125 tur, yani günde ~1600 dk |
| Depo | herkese açık (PUBLIC); GitHub disk kullanımı 1,36 GB |
| Bot commit'i | 3053 adet (9 Ekim'den beri), günde ~120-140 |

## Bulgular

### 1. Depo her gün ~50-70 MB büyüyor, şimdiden 1,36 GB — Önem: YÜKSEK
- Kanıt: `gh repo view` diskUsage = 1.358.870 KB. Yerelde `git count-objects -vH` size-pack 2,62 GiB (aynı boyutta iki paket dosyası var, aşağıya bakın). 18 Kasım'daki bot commit'leri 1107 yeni dosya sürümü ekledi: sıkıştırılmış 70 MB (ham 1976 MB). 12 Kasım'da 48 MB.
- Geçmişteki payı en büyük dosya `site/feeds.json`: 3053 sürüm, diskte ~1064 MB (her sürüm ~7 MB). Sonra `site/index.html` 109 MB, `site/kisisel/piril/feeds.json` 69 MB, `site/masa.json` 54 MB, `site/trend-gecmis.json` 39 MB.
- Bu dosyalar git'te duruyor çünkü bir sonraki tur onları "önceki durum" olarak okuyor: `fetch_feeds.py:399` (eski feeds, 304 yanıtında eski kopya), `fetch_feeds.py:401` (kaynak-durum, ETag), `fetch_feeds.py:353` (gorsel.json), `ekler.py:52` (trend-gecmis). `masa.json` TechTurco paneli tarafından Pages adresinden okunuyor (`techturco-site/.../AkisController.php:261`), git'ten değil.
- Neden önemli: GitHub depoların 1 GB altında, kesinlikle 5 GB altında kalmasını öneriyor. Bu hızla 5 GB'a yaklaşık 50-70 günde varılır (tahmin, büyüme hızı sabit kabul edildi). Yerel klonda her `git pull` günde yüzlerce MB indirir.
- Öneri: durum dosyalarını ana dalın geçmişinden çıkarmak. Seçenekler: (a) `actions/cache` ile turdan tura taşımak (git'e hiç girmez; önbellek düşerse bir tur soğuk çekim yapar); (b) ayrı bir `durum` dalına geçmişsiz (orphan) commit atıp her tur zorla üzerine yazmak; (c) yalnız küçük durum dosyalarını (kaynak-durum, trend-gecmis, gorsel) git'te tutmak, `feeds.json`'u önbelleğe almak. Sonra mevcut geçmişin temizlenmesi (geçmiş yeniden yazma) ayrı ve geri dönüşü zor bir iştir.
- Karar gerekir mi: EVET (yöntem seçimi ve geçmiş temizliği yapılsın mı).

### 2. Zincir kopunca tek emniyet cron; bir kez 32 dk boşluk oldu — Önem: ORTA
- Kanıt: run 43328637981 (12 Kasım 23:35Z) `tekrar` işi `gh workflow run` çağrısında "HTTP 500: Failed to run workflow dispatch" aldı; yeniden deneme yok (`refresh.yml:79`). Zincir koptu, cron turu 43333072006 ancak 32 dk sonra başladı.
- Cron pratikte yalnız yedek: 1000 turda 27 cron turundan 24'ü iptal (zincir varken bekleyen yeri dolu olduğu için yerini dispatch alıyor), 3'ü çalıştı.
- Elle "Cancel" yapılan bir tur zinciri de koparır (`refresh.yml:70` `!cancelled()`); o zaman da cron devralır (doğrulanmadı, tasarımdan çıkarım).
- Öneri: `gh workflow run` satırını 3 deneme + kısa bekleme döngüsüne almak. Karar gerekir mi: HAYIR.

### 3. Kuyruk gecikmesi: 45 dk'lık en uzun boşluk GitHub tarafında — Önem: DÜŞÜK
- Kanıt: run 43867228320 12:30:42Z'de oluştu, `refresh` işi 13:04:21Z'de başladı (34 dk sunucu bekleme). Normalde bekleme medyan 3 sn, en çok 6 sn (60 tur).
- Bizim elimizde değil. Arayüz bunu gösteriyor: `index.tpl.html:836` 30 dk'dan eski veride sarı, 90 dk'dan eskide kırmızı nokta. Karar gerekir mi: HAYIR.

### 4. Bir adım düşerse eski veri yayında kalır, ama sahibine aktif uyarı yok — Önem: ORTA
- Davranış (dosyadan): testler, çekim, akis2, build ya da çıktı kapısı başarısız olursa `refresh` düşer, `deploy` atlanır, Pages'te önceki paket kalır; `tekrar` yine çalışır (`!cancelled()`), zincir sürer. Ölçülen örnek: 15 Kasım'daki iki push hatasında (43708786501, 43710531351) deploy "skipped", tekrar "success".
- Pages tarafı hataları: 43159697052 (configure-pages "Server Error"), 43270725412 (deploy-pages 502). Bunlarda da eski site kaldı, bir sonraki tur düzeltti.
- Eksik: sürekli düşen bir adımda (ör. bir Python hatası) site saatlerce eski kalır, kimse haber almaz; GitHub'ın e-posta bildirimi dispatch ile başlayan turlarda kime gider, doğrulanmadı. Ziyaretçi yalnız saat noktasının rengini görür.
- Öneri: art arda N tur başarısızsa issue açan ya da Pages'te `durum.json` yazan küçük bir adım; ya da TechTurco paneline "Akış X dk'dır güncellenmedi" uyarısı. Karar gerekir mi: EVET (uyarı nereye gitsin).

### 5. Çıktı kapısı veri yoksa "geçti" sayar — Önem: DÜŞÜK
- Kanıt: `tests/test_cikti.py:27` `skipUnless(VAR)` — `site/data/ozet.json` yoksa bütün `Cikti` testleri atlanır, adım başarılı biter. `site/data/` git'te olmadığı için (`.gitignore`) CI'da bu dosya yalnız akis2 üretirse var olur. akis2 hata kodu verirse zaten önceki adım düşer; ama 0 ile çıkıp dosya yazmazsa boş paket yayına gider (doğrulanmadı, senaryo).
- Kapıda en az içerik denetimi yok (ör. "en az X küme / Y kaynak başarılı"). Tüm kaynaklar düşerse 12 saatlik eski kopya kuralı (`fetch_feeds.py:471`) bitince boş akış yayına girebilir (doğrulanmadı).
- Öneri: iş akışında kapıyı `AKIS_KAPI=1` gibi bir bayrakla çalıştırıp atlamayı hataya çevirmek; `saglik.basarili` için alt sınır. Karar gerekir mi: HAYIR (eşik değeri sahibine sorulabilir).

### 6. Bot push'u ile elle push çakışması: düzeltme çalışıyor — Önem: BİLGİ
- Kanıt: 15 Kasım 11:24Z ve 11:46Z iki tur "rejected / cannot lock ref" ile düştü; aynı gün 12:10Z'de (commit 5167c341) rebase + 3 deneme döngüsü eklendi. Sonrasında 0 başarısız tur. Run 44217531088 (18 Kasım 01:43Z) gerçek çakışmayı yaşadı: "rejected (fetch first)" → "Successfully rebased" → push başarılı.
- Kalan küçük nokta: rebase sonrası yayınlanan paket eski kodla üretilmiştir; yeni kod bir sonraki turda (≤12 dk) yayına girer. Push turları 17'den 11'i iptal edildi, çünkü bekleyen yeri sonraki dispatch aldı; dispatch `main`'in son hâlini çalıştırdığı için kod yine de yayına giriyor. Elle push `site/` altına dokunursa rebase çakışır ve tur düşer (`refresh.yml:51`). Karar gerekir mi: HAYIR.

### 7. Yetkiler gereğinden geniş — Önem: ORTA
- Kanıt: `refresh.yml:12-14` iş akışı düzeyinde `contents: write` ve `actions: write`. `refresh` işi kendi `permissions` bloğu olmadığı için ikisini de alır, ama `actions: write`'a ihtiyacı yok (yalnız `tekrar` kullanıyor, onun kendi bloğu var: satır 72). `refresh` dış kaynaklardan gelen veriyi işliyor; `actions/checkout` jetonu `.git/config`'te bırakıyor (varsayılan).
- Gizli anahtar (`secrets.*`) kullanılmıyor; yalnız `github.token`. Eylemler sürüm etiketiyle sabitli (`@v4`, `@v5`, `@v3`), commit SHA ile değil.
- Öneri: üst düzeyi `contents: read` yapıp `refresh` işine `contents: write` vermek; `actions: write` yalnız `tekrar`da kalsın. Karar gerekir mi: HAYIR.

### 8. İş zaman aşımı yok — Önem: DÜŞÜK
- Kanıt: hiçbir işte `timeout-minutes` yok; varsayılan 360 dk. `refresh` en çok 255 sn sürdü. Asılan bir tur 6 saate kadar `refresh` grubunu tutar, bu sürede cron turları yalnız bekler; site 6 saat eski kalır (doğrulanmadı, ölçülmüş asılma yok).
- Öneri: `refresh: timeout-minutes: 15`, `deploy: 10`, `tekrar: 12`. Zaman aşımında `tekrar` çalışır mı doğrulanmadı (`!cancelled()` zaman aşımını iptal sayabilir); denenmeli. Karar gerekir mi: HAYIR.

### 9. Actions dakikası: depo açık olduğu için ücretsiz, ama 8 dk'lık bekleme ana yük — Önem: DÜŞÜK / BİLGİ
- Kanıt: depo PUBLIC; standart koşucular açık depolarda ücretsiz. Tur başına ~13 faturalanabilir dakika, bunun ~9'u `tekrar` işinin `sleep 480`'i (`refresh.yml:78`). Günde ~1600 dk.
- Risk: depo özel yapılırsa ücretsiz kota (ayda 2000 dk) ~1,2 günde biter. Sürekli bekleyen iş GitHub kullanım koşullarına uygun mu, doğrulanmadı.
- README'deki "≈9 dk" ölçümü güncel değil: başlangıçtan başlangıca medyan 11,5 dk. Karar gerekir mi: HAYIR (depo özel yapılmayacaksa).

### 10. Yerel klonda iki kopya paket (2,6 GB) — Önem: DÜŞÜK
- Kanıt: `.git/objects/pack/` içinde aynı boyutta iki paket (1.409.867.033 ve 1.409.867.497 bayt) ve `multi-pack-index`. Yerel `.git` 2,6 GB. Yalnız bu Mac'i etkiler.
- Öneri: `git gc` ile yarıya iner (bu denetimde çalıştırılmadı). Karar gerekir mi: HAYIR.

## Doğrulanmayanlar
- Başarısız turda GitHub e-postasının kime gittiği.
- Zaman aşımı olan işte `tekrar`ın çalışıp çalışmadığı.
- Kapının boş `site/data` ile atlanıp boş paket yayınlaması (senaryo, denenmedi).
- 5 GB'a varış süresi (büyüme sabit varsayıldı).
