# Akış

Teknoloji gündemi ve Reels konu masası. GitHub Actions her 30 dakikada kaynakları çeker, GitHub Pages yayınlar.

- **Gündem:** Aynı olayı anlatan haberler tek kartta, kaç kaynağın yazdığıyla.
- **Reels:** Konular açık kurallarla sıralanır ve her aday nedenini söyler. Puan tahmindir, görüntülenme garantisi değildir.
- **Son haberler:** Bölüm bölüm kronolojik akış. Genel gündem burada.
- **Kaynaklar:** Hangi kaynak ne zaman güncellendi, hangisi yanıt vermedi.

## Dosyalar
- `sources.json`: kaynak listesi. Yeni kaynak için satır ekle.
- `fetch_feeds.py`: kaynakları çeker, çöpü süzer, eksik görseli sayfadan bulur (`site/feeds.json`).
- `masa.py`: kümeleme, konu ve Reels sıralaması (`site/masa.json`).
- `index.tpl.html`, `build.py`: arayüz (`site/index.html`).

TechTurco paneli `site/index.html` içindeki `id="snap"` verisini okur; bu biçim değişirse panel de değişmeli.

Klavye: `/` ara, `j`/`k` gezin, `o` aç, `s` kaydet, `x` ilgisiz (listeden kaldırır, "Gizlenenler" ile geri gelir).

## Reels seçimi
Kanal Türkçe tüketici teknolojisi: telefon, uygulama, güvenlik, yapay zekâ kullanıcısı. `masa.py` içinde `KITLE` (ürün/uygulama adı) ve `ETKI` (kullanıcıya etki) kuralları puan verir; `REELS_RED` (kaza, dizi/film, borsa, yabancı ülke kampanyası, dava) Reels'e hiç almaz; `REELS_CEZA` puan düşürür. Aynı olayı anlatan kümeler `birlestir()` ile tek kartta toplanır, tek konu listeyi 12 adaydan fazla dolduramaz. Yeni bir alakasız konu görürsen ilgili deseni ekle.
