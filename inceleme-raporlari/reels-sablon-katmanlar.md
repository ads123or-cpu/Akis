# Reels şablonu: dört isteğe bağlı katman (22.11.2026)

Dosya: `araclar/reels-sablonu.html` (tek dosya; başka dosyaya dokunulmadı, derleme/commit/push yok).
Ayrışma uyarısı: `kurgu-kit/reels-artifact` ve Claude'daki yayınlanmış kopya GÜNCELLENMEDİ; CLAUDE.md gereği değişiklik oraya taşınmalı.

## Eklenenler (satır aralıkları yaklaşık)
- Arayüz: "Katmanlar" kartı, satır 290-331 (dört `fieldset`, her biri onay kutusu + alanlar, etiketli, "Katmanları önizle" düğmesi). CSS: 96-99 (`.katman-grup`, onay kutusu odak halkası; yalnız mevcut değişkenler).
- D, yavaş yakınlaştırma: `YAKIN` + `kirpim()` 425-433; `ciz()` 945-950. Yalnız `arkaPlan()` çağrısı sırasında 1,00→1,07; kırpma pencere ortasından küçülür, oran değişmez (kırpma/kadraj ile uyumlu). Yazı ve katmanlar zoomlanmaz.
- A/B/C: 813-937 (`ktAlan`, `ktRakamKur`, `ktKaynakKur`, `ktSoruKur`, `ktCiz`, `katmanlarCiz`). `ciz()` içinde 957'de çağrılır (önizleme ve iki dışa aktarım yolu aynı `ciz()`'i kullanır). Katmanlar küçük tuvale bir kez çizilir (anahtar: tasarım, marka, pencere, alan değerleri, yazı tipi durumu); karede yalnız `drawImage`.
- Tasarım ölçüsü: 5 tasarıma `S.icUst` (içeriğin üst sınırı) satırı eklendi (653, 685, 729, 752, 799) ve 806'da sıfırlanır. Çizime etkisi yok.
- Saklama/ön doldurma: 1085-1103 ve 1587-1603. Değerler `rs-kaRakam` vb. ile saklanır; onay kutuları her açılışta KAPALI (eski rakam yanlışlıkla yeni videoya girmesin). URL: `rakam, etiket, rakam2, etiket2, kaynak, soru` verilen katmanı açar.
- `window.__reels.ciz` test için dışarı açıldı.

## Konum kararları
- Rakam (A): üst güvenli alan altı (y=300) ile min(tuval yarısı, tasarım içeriğinin üstü−36) arası, ortalı. Haber ekranı ve renkli çerçevede üst alan logo+cümleyle dolu olduğundan video penceresinin üst kenarına oturur (haber ekranında pencere çoğu zaman yarının altında; sınır burada aşılıyor).
- Kaynak (B): x=64, y=262, 26 px, sağdan 150 px boşluk; 90 karakter sığmazsa "…". Haber ekranı ve çerçevede y=262 logoyla çakışır; bu ikisinde video penceresinin sol alt köşesine (pencere altından 52 px yukarı) yazılır.
- Soru (C): tasarım içeriğinin hemen üstünde (logodan 52 px yukarıda), haber/çerçevede video penceresinin altında; 42 px, en çok 3 satır, ortalı; son 2,2 sn, 0,3 sn giriş; süre <4 sn ise gizli. "Alt-orta" tasarım cümlesiyle çakışmamak için cümle bloğunun üstüne alındı.
- Rakam yalnız kullanıcı metni: boş rakam = katman çizilmez; ikinci rakam doluysa iki kart + "vs" (okun yazı tipinde olmama riski nedeniyle "↔" yerine "vs").

## Ölçülenler (gerçek Chrome, başsız, CDP; test videosu ffmpeg testsrc2 1080x1920, 8 sn, sentetik)
1. `node --check`: betik bloğu temiz.
2. Katmanlar kapalıyken 7 tasarımın tuval karesi (t=1 sn) ÖNCEKİ dosyayla bayt bayt AYNI (`cmp`, 7/7). Yakınlaştırma açık, t=0 ve kırpma (zoom 1,3) altında da önceki kareyle aynı.
3. Tüm katmanlar açık, 7 tasarımda rakam (t=1), soru (t=6,5), karşılaştırma düzeni ekran görüntüsüyle bakıldı: taşma yok, kaynak/soru/rakam okunuyor; uzun etiket 2 satırda "…" ile kesiliyor. Bant tasarımında soru logoya değiyordu, boşluk 28→52 px yapıldı, yeniden bakıldı.
4. Yakınlaştırma: t=7,9'da yalnız video büyüyor, yazı aynı (kare karşılaştırması).
5. URL parametreleri: verilen katman açık, verilmeyen kapalı; parametresiz açılışta hepsi kapalı. 3 sn'lik kesimde soru gizli (açık/kapalı kare aynı).
6. Dışa aktarım (`__reels.hazirla()`, WebCodecs yolu): 8 sn mp4 (h264 1080x1920 + aac) üretildi; 1,0 sn karesinde rakam+kaynak, 6,5 sn karesinde soru görünüyor (ffmpeg ile kare çıkarıldı, görüldü).
7. Kare maliyeti (200 çağrı ortalaması, sentetik; GPU bekleme dahil değil): 0,97 ms kapalı, 4,9 ms hepsi açık (yakınlaştırma dahil). Katman çizimi ayrı ölçülmedi.

## Yapılamayanlar / doğrulanmadı
- Telefonda/Safari'de deneme yok (doğrulanmadı); MediaRecorder yedek yolu denenmedi (aynı `ciz()` kullanıyor).
- Altyazı açıkken rakam/soru bölgesiyle çakışma denenmedi: altyazı katmanın üstüne çizilir, varsayılan "orta" konum (y≈960) rakam bandının altında, soru bandıyla örtüşebilir; kullanıcı konumu seçebilir.
- Gerçek video (insan yüzü, yatay kaynak) üzerinde kaynak şeridi okunurluğu bakılmadı; yalnız sentetik test deseni.
- Geçici dosyalar ve kopyalar: oturum scratchpad'inde; sunucu (8790) kapatıldı.
