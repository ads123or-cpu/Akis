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

Klavye: `/` ara, `j`/`k` gezin, `o` aç, `s` kaydet.
