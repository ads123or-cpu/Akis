# Akış Masası

Çok dilli RSS okuyucu. Haberleri GitHub Actions her 30 dakikada bir çeker, GitHub Pages yayınlar.

## Yayına alma (bir kez, ~5 dakika)
1. github.com'da yeni bir **public** repo aç (ör. `akis`).
2. Bu klasörün içeriğini repoya yükle (`git push` ya da web arayüzünden "Upload files").
3. Repo > Settings > Pages > Source: **GitHub Actions**.
4. Repo > Actions > "Akışı yenile" > **Run workflow**.
5. Birkaç dakika sonra adres: `https://<kullanıcı-adın>.github.io/akis/`

## Kaynak ekleme
- Sitedeki **Kaynaklar** > "Kaynak ekle": o tarayıcıya özel eklenir (ücretsiz köprülerle çekilir, bazen çalışmayabilir).
- Kalıcı ve güvenilir yol: `sources.json` dosyasına bir satır ekle, commit et. Sonraki yenilemede herkese görünür.

## Dosyalar
- `sources.json`: kaynak listesi (id, ad, dil, kategori, adres). Yeni kaynak eklemek için satır ekle.
- `fetch_feeds.py`: kaynakları çekip `site/feeds.json` üretir (GitHub Actions bunu otomatik çalıştırır).
- `index.tpl.html` + `build.py`: arayüz şablonu. Değiştirince `python3 build.py` ile `site/index.html` yeniden üretilir.
