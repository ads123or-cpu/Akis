# Akış 7 — yeni tasarım kararları (2026-11-21)

Okan'ın isteği: sil baştan, karmaşık olmayan, modern ve profesyonel bir tasarım; kategoriler yeniden; Reels sade ve daha iddialı konular; konuya tıklayınca donma çözülsün.

## Donmanın nedeni (kodda doğrulandı)
`sec0()` (index.tpl.html ~975) ve `rota()` (~1031) konu açılıp kapanırken `ciz()` çağırıyor. `ciz()` bütün sayfayı `$('ana').innerHTML=f()` ile baştan kuruyor: alan kümelerini yeniden süzüyor/sıralıyor, yüzlerce satırı yeniden yazıyor, görselleri yeniden gözlüyor. Telefonda her açma ve kapamada (geri tuşu da `rota()`→`ciz()`) bu birkaç yüz ms–saniye sürüyor.
**Kural:** konu açmak/kapamak listeyi yeniden çizmez. Yalnız panel çizilir, satırda seçili/okundu sınıfı değişir. Süzgeç ve sıralama sonucu, veri ya da süzgeç değişmedikçe önbellekte kalır.
**Bütçe:** masaüstünde tıklamadan panel görünene kadar < 50 ms; 4 kat yavaş işlemcide < 150 ms. Uzun görev (>50 ms) yok.

## Kategoriler (arayüzde 7 ana başlık)
Veri dosyaları (`kume-<alan>.json`) ve adresler (`#/akis/<alan>`) aynen kalır; arayüz bunları gruplar.
| Ana başlık | Alt sekmeler (veri alanı) |
|---|---|
| Gündem | Tümü (gundem) · Siyaset ve Dünya (siyaset) · Adana (adana) |
| Teknoloji | Tümü (tekno) · Yapay Zekâ (yz) · Siber Güvenlik (siber) · Oyun (oyun) |
| Savunma | (savunma) |
| Ekonomi | (ekonomi) |
| Spor | (spor) |
| Bilim | (bilim) |
| Yaşam | Otomobil (oto) · Kültür ve Eğlence (eglence) |
Alt konular (`alt` etiketleri) alt sekmenin altında ince bir süzgeç satırı olarak kalır, varsayılan kapalı/tek satır kaydırmalı.

## Sayfalar
Ana menü: **Bugün · Akış · Reels · Trendler**. "Daha": Güncellemeler, Dünya, Videolar, Kayıtlar, Kaynaklar, Ayarlar. Kişisel sayfa (`#/piril`) çalışmaya devam eder. Eski adresler çalışır.

## Görsel dil
- Editoryal ve sakin: bol boşluk, net hiyerarşi, tek vurgu rengi; alan rengi yalnız küçük nokta/etiket olarak.
- Yazı: sistem yazı tipi (`system-ui`/`-apple-system`/Segoe UI/Inter yoksa sistem), başlıklarda sıkı satır aralığı ve hafif negatif harf aralığı; sayılar `tabular-nums`.
- Yüzeyler: düz, ince kenarlık yerine boşluk ve hafif zemin farkı; köşe yarıçapı tutarlı (8/12/16).
- Açık ve koyu tema (sistem/açık/koyu, mevcut `akis2-ayar.tema`), vurgu renk seçimi kalabilir ama en çok 4.
- Görünümler 6'dan 3'e: **Akış** (küçük resimli liste), **Kartlar** (ızgara), **Başlıklar** (yoğun liste). Eski `gorunum` değerleri bunlara eşlenir (liste/zaman→akış, izgara/manset→kartlar, siki/baslik→başlıklar).
- Telefon önce: 390 px'te yatay taşma yok, dokunma hedefi ≥ 44 px, alt menü, detay tam ekran alt sayfa; masaüstünde sağda panel.
- Satırda en fazla: alan noktası, başlık, kaynak adı + "N kaynak", saat, (varsa) dil rozeti. Gerisi detayda.

## Reels
- Daha az ve daha iddialı: en çok 40 kart (profil başına en çok 15). Rutin maç özeti/sonucu, tanıtım-fiyat sayfası, deneme sınavı/yerel duyuru, sıradan transfer söylentisi girmez.
- "İddialı" = tartışma, büyük para/rekor, ilk kez, yasak/dava/ceza, güvenlik/gizlilik riski, cebe dokunan (fiyat, vergi, zam), Türkiye'ye doğrudan etki, şaşırtıcı bilim/teknoloji.
- Kart sade: başlık, tek cümlelik **açı** (`aci`), neden şimdi (tek satır), kaynak sayısı, "hook kopyala". Puan ayrıntıları açılır bölmede.
- Sahte sayı ve kaynakta olmayan iddia yok; `aci` başlık/özetteki bilgiden kural şablonuyla kurulur.

## Değişmeyecekler
`id="snap"` bloğu, `masa.json`, localStorage anahtar adları, kaynakların `cat` alanı, `data/*.json` adları.
