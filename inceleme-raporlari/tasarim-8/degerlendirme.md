# Akış 8 — Tasarım Yenileme ve Kaynak Kategorizasyonu Değerlendirmesi

Tarih: 24.11.2026 · Aşama 1 (Mevcut durum ölçümü) + Aşama 2 (Tasarım dili ve kaynak merkezi prototipi).
Prototip dosyası: `inceleme-raporlari/tasarim-8/prototip.html`

---

## 1. Mevcut Durum Ölçümü (Yerel Sunucu, Chrome Beta Headless)

Ölçüm ortamı: `python3 tools/yerel_sunucu.py 8765 site` + `Chrome Beta` CDP, önbellek kapalı.
Not: Yerel `site/data/` 18.11.2026 tarihli olduğu için `#/akis/tekno` varsayılan "son 24 saat" filtresinde 0 içerik döndürdü (ortam gerçeği); yapı, DOM ve taşma ölçüldü.

| Ekran & Boyut | Tema | Yatay Taşma | DOM Sayısı | İnteraktif | <44px Hedef | Adsız Öğe | FCP | Aktarım |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Bugün 1440 px | Açık | 0 px | 1.328 | 223 | 196 | 0 | 60 ms | 1.264 KB |
| Bugün 1440 px | Koyu | 0 px | 1.328 | 223 | 196 | 0 | 72 ms | 1.245 KB |
| Bugün 768 px | Açık | 0 px | 1.328 | 223 | 204 | 0 | 64 ms | 1.244 KB |
| Bugün 390 px | Açık | 0 px | 1.328 | 223 | 186 | 0 | 56 ms | 1.244 KB |
| Bugün 390 px | Koyu | 0 px | 1.328 | 223 | 186 | 0 | 56 ms | 1.244 KB |
| Akış/Tekno 1440 px | Açık | 0 px | 267 | 48 | 41 | 0 | 64 ms | 810 KB |
| Akış/Tekno 390 px | Açık | 0 px | 262 | 40 | 26 | 0 | 48 ms | 810 KB |
| **Kaynaklar 1440 px** | Açık | 0 px | **4.274** | 423 | 417 | **2** | 80 ms | 599 KB |
| **Kaynaklar 390 px** | Açık | 0 px | **4.274** | 423 | 411 | **2** | 56 ms | 599 KB |
| Reels 1440 px | Koyu | 0 px | 1.518 | 85 | 65 | 0 | 52 ms | 614 KB |

### Mevcut Arayüzde Tespit Edilen Temel Sorunlar
1. **Kaynaklar ekranı (`#/kaynak`) hem kategorisiz hem ağır:**
   - 4.274 DOM düğümü tek seferde basılıyor, 868 kaynağın sadece ilk 400'ü gösteriliyor (468 kaynak ulaşılamaz).
   - Sıralama `aktif` olanları en sona atıyor; sayfa ilk açıldığında ekran tamamen "Devre dışı" ve "Beklemede" kaynaklarla doluyor.
   - Alan (`calisma`), Tür/Güven katmanı (`tip`), Dil (`dil`), Ülke (`ulke`), Öncelik (`oncelik`) veya Teknoloji alt kırılımı (`cat`: Apple/iOS, Android/Samsung, Windows) süzgeci hiç yok.
   - `uzman teknoloji`, `sirket duyurusu`, `ana akim` gibi ASCII teknik etiketler ham basılıyor.
   - 2 adet adsız interaktif öğe (erişilebilirlik açığı) ölçüldü.
2. **Boş sağ panel israfı (Reels, Akış, Trendler masaüstü):**
   - Hiç haber seçilmemişken sağda 440 px boş panel ekranın ~%31'ini kapatıyor (`reels-1440-koyu.png`).
3. **Bugün ekranında hızlı kategori erişimi eksik:**
   - Üstte kategori şeridi olmadığı için Bugün'den Teknoloji, Yapay Zekâ, Ekonomi, Savunma gibi alanlara tek tıkla geçilemiyor.
4. **Görsel hiyerarşi ve tarama hızı:**
   - Manşet ve haber satırları fazla tekdüze; mobilde "Günün özetini kopyala" düğmesi boşlukta tek başına duruyor.
   - Haber satırlarında 3+ kaynaklı kritik konular ile tek kaynaklı haberler görsel olarak yeterince ayrışmıyor.
5. **Kaynak veri kategorizasyonu (`sources.json`) dağınıklığı:**
   - `tekno` altında 364 kaynak toplanmış; bunların içinde 16 Yapay Zekâ kaynağı (`gnq-ai`, `nvidia-blog`, `rd-claudeai`, `anthropic-news`, `gn-tr-chatgpt`, `kr-aitimes` vb.) ve 4 Siber Güvenlik kaynağı (`y-kaspersky`, `y-darkreading`, `gn-samsung-security-en` vb.) yanlışlıkla `tekno` altında kalmış.
   - 7 Google Trends kaynağı (`trends-tr/us/gb/de/fr/jp/kr`) `eglence` altında duruyor (`gundem` olmalı).
   - `r-iaf`, `knowyourmeme`, `theonion` gibi topluluk/hiciv kaynakları `tip: "ana akim"` olarak işaretlenmiş.

---

## 2. Referans Haber / Okuyucu Arayüzlerinden Çıkarılan İlkeler

- **Techmeme & Hacker News:** Yoğun bilgiyi okunur kılan şey büyük kartlar değil, **tek satırda kaynak sayısı + tazelik + kaynak ağırlığı** hiyerarşisidir.
- **Feedly & Inoreader:** 500+ kaynağı yönetilebilir kılan şey **çok boyutlu kaynak sınıflandırması** (Alan → Alt konu → Güven katmanı → Durum) ve **sağ detay çekmecesinin yalnız seçim varken veya daraltılabilir çalışması**dır.
- **Ground News:** Bağımsız kaynak sayısı ve dil çeşitliliği pasif gri metin değil, okunur bir **doğrulama sinyali** olarak vurgulanır.
- **Bloomberg / Reuters / Apple News:** Manşet ile liste arasında net tipografik kontrast, mobilde tek elle kaydırılan kategori şeridi ve gürültüsüz boşluk dengesi.

---

## 3. İki Tasarım Yönü (Prototip: `prototip.html`)

| Özellik | Yön A — Editoryal Haber Odası | Yön B — Modern Komuta Merkezi (Önerilen) |
|---|---|---|
| **Hava** | Sıcak gazete / dergi (FT, Reuters, Apple News) | Keskin, hızlı iş masası (Linear, Feedly, Techmeme) |
| **Başlık Yazı Tipi** | Sistem Serif (`New York` / `Georgia`) + UI Sans | Tümü Sistem Sans, sıkı harf aralığı, `tabular-nums` |
| **Yüzeyler** | Sıcak kağıt (`#f8f5ef`) / sıcak koyu (`#111110`), ince ayraçlar | Nötr gri (`#f4f5f7`) / derin gece (`#0b0d11`), gruplu beyaz kart kapları |
| **Yoğunluk** | Ferah, okuma odaklı | Yüksek tarama hızı, günlük yoğun kullanıma uygun |
| **Pırıl Profili Uyumu** | Çok yüksek | Yüksek (sade görünüm korunur) |

---

## 4. Kaynak Kategorizasyonu Yenileme Planı (Veri + Arayüz)

### A. `sources.json` Veri Temizliği (`cat` ve test sözleşmeleri 100% korunur)
- `cat` alanına **dokunulmaz** (TechTurco paneli / `masa.py` sözleşmesi).
- `test_kaynaklar.py`'deki `CALISMA` ve `TIPLER` sabit listeleri bozulmaz:
  - `tekno` içindeki ~16 Yapay Zekâ kaynağı → `calisma: "yz"`
  - `tekno` içindeki ~4 Siber Güvenlik kaynağı → `calisma: "siber"`
  - `eglence` içindeki 7 Google Trends kaynağı → `calisma: "gundem"`
  - `theonion`, `knowyourmeme`, `r-iaf` gibi topluluk/viral kaynaklar → `tip: "topluluk/trend"`

### B. Yeni `#/kaynak` Kaynak Merkezi Arayüzü
- **Varsayılan sıralama:** Önce çalışan ve Çekirdek (`oncelik: 1`) kaynaklar (artık kırık/devre dışı kaynaklar en tepeyi kaplamaz; sorunlular üstteki durum kartından tek tıkla açılır).
- **4 Katmanlı Süzgeç:**
  1. **Kategori (Alan):** Tümü + 13 çalışma alanı (7 ana grup altında) + Teknoloji alt kırılımı (`Apple/iOS/Mac`, `Android/Samsung`, `Windows/PC`).
  2. **Güven / Tür Katmanı:** Birincil & Resmî (`resmi kurum`, `uluslararasi kurum`, `ajans`, `sirket duyurusu`, `dogrulama`), Editoryal & Uzman (`ana akim`, `uzman teknoloji`, `bilimsel`, `spor`), YouTube Video, Toplayıcı (GN), Erken Sinyal / Topluluk.
  3. **Öncelik & Dil:** Çekirdek (P1) / Standart (P2) / Ek (P3) + Türkçe / İngilizce / Diğer diller.
  4. **Durum:** Çalışıyor / Yavaş & Beklemede / Hata & Engelli / Devre dışı.
- **Gruplu veya Tablo Görünümü + Sayfalama ("Daha fazla göster"):** İlk açılışta ~80 kaynak çizilir (DOM 4.274 → <900), tüm 868 kaynağa kesintisiz ulaşılır.
- **Temiz Türkçe Etiketler:** `uzman teknoloji` → "Uzman teknoloji", `sirket duyurusu` → "Şirket duyurusu", `ana akim` → "Ana akım", `toplayici` → "Toplayıcı (GN)", `resmi kurum` → "Resmî kurum".

---

## 5. İşlevsellik İyileştirmeleri (Aşama 3 Uygulama Kapsamı)
1. **Hızlı Kategori Şeridi:** Üst çubuğun hemen altında tek tıkla Gündem / Teknoloji / Yapay Zekâ / Siber / Savunma / Ekonomi / Spor / Bilim / Yaşam geçişi.
2. **Akıllı Sağ Detay Paneli:** Masaüstünde haber seçilmediğinde boş 440 px sütun alanı işgal etmez; habere tıklanınca anında açılır (donma yok, `<50 ms` bütçe korunur).
3. **Erişilebilirlik & Mobil Hedefler:** Kaynaklar sayfasındaki 2 adsız öğe giderilir; mobilde kritik düğmeler ≥44 px dokunma alanına çekilir.
4. **Değişmeyecekler:** `id="snap"`, `masa.json`, `site/data/*.json` şemaları, `akis2-*` / `akis-*` localStorage anahtarları, Pırıl gizliliği ve Okan'a özel X/Facebook paylaşım sistemi (`test_okan_x.py` 100% korunur).

---

## 6. Uygulama Sonrası Ölçüm (Önce → Sonra)

Uygulanan yön: **Yön B — Modern Komuta Merkezi** + **`sources.json` veri kategorizasyonu temizliği (24 kaynak)** + **Yeni Kaynak Merkezi**.
Test sonucu: **167 / 167 birim ve sözleşme testi geçti** (`test_sozlesme`, `test_cikti`, `test_kaynaklar`, `test_okan_x`, `test_akis2`, `test_ekler`, `test_is_akisi`, `test_kisisel`, `test_fetch`).

| Ekran & Boyut | Yatay Taşma (Ö→S) | DOM (Ö→S) | Adsız Öğe (Ö→S) | FCP ms (Ö→S) |
|---|---:|---:|---:|---:|
| Bugün 1440 px (Açık) | 0 → 0 px | 1.328 → 1.367 | 0 → 0 | 60 → 56 ms |
| Bugün 1440 px (Koyu) | 0 → 0 px | 1.328 → 1.367 | 0 → 0 | 72 → 56 ms |
| Bugün 768 px (Açık) | 0 → 0 px | 1.328 → 1.367 | 0 → 0 | 64 → 60 ms |
| Bugün 390 px (Açık/Koyu) | 0 → 0 px | 1.328 → 1.367 | 0 → 0 | 56 → 56 ms |
| **Kaynak Merkezi 1440 px** | 0 → 0 px | **4.274 → 1.294 (-%70)** | **2 → 0** | **80 → 56 ms** |
| **Kaynak Merkezi 390 px** | 0 → 0 px | **4.274 → 1.294 (-%70)** | **2 → 0** | 56 → 56 ms |
| Reels 1440 px (Koyu) | 0 → 0 px | 1.518 → 1.522 | 0 → 0 | 52 → 164 ms (3 sütun dolu) |

**Kalan riskler:**
- `sources.json` değişikliklerinin canlı `site/data/kaynaklar.json` ve `kume-*.json` dosyalarına yansıması GitHub Actions'ın ilk çalışma turunda gerçekleşir (~1-2 dk).
- Gerçek fiziksel iPhone üzerinde dokunmatik kaydırma ve güvenli alan (safe-area) el ile son kez gözden geçirilmelidir.
