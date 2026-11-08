# Akış 2.0

Haber merkezi + gündem radarı + Reels konu keşfi. GitHub Actions kaynakları çeker, GitHub Pages yayınlar. Arayüz canlı değildir: üstteki saat **son başarılı veri üretimini** gösterir.

## Ekranlar
- **Gündem Merkezi:** sıcak konular (1 s / 6 s / 24 s, en az 2 bağımsız kaynak), yükselen konular (hesap yöntemi ekranda), son gelişmeler.
- **Çalışma alanları:** Gündem, Teknoloji, Siyaset ve Jeopolitik, Spor, Ekonomi, Bilim ve Uzay, Siber Güvenlik, Otomobil ve Ulaşım, Eğlence/Oyun/Kültür. Alt konu, marka, ülke/lider, dil ve zaman süzgeçleri.
- **Reels Fikir Radarı:** Teknoloji / Gündem / Siyaset / Spor profilleri, bilim-siber-otomobil-ekonomi-ilginç alt kategorileri; 10 ölçütlü açık puan.
- **Kaynak Yönetim Merkezi:** durum renkleri, süzgeçler, yeni kaynak taslağı ve doğrulama adımları.
- **Kaydedilenler:** içerik durumu panosu (Yeni konu … Yayınlandı), notlar, JSON dışa/içe aktarma. Kişisel her şey tarayıcıda (localStorage).

Klavye: `/` ara, `J`/`K` gezin, `Enter` ayrıntı, `O` ilk kaynağı aç, `S` kaydet, `X` ilgisiz (Geri al), `R` Reels adayı, `Esc` kapat.

## Dosyalar
| Dosya | İş |
|---|---|
| `sources.json` | Kaynak listesi. Eski alanlar (`id,name,lang,cat,url,plat`) + `calisma, tip, ulke, oncelik, nitelik, aktif, dogrulama`. |
| `fetch_feeds.py` | Kaynakları çeker: ETag/Last-Modified (304), zaman aşımı, devre kesici, spam ve ShiftDelete süzgeci, yanıt süresi. → `site/feeds.json`, `site/kaynak-durum.json` |
| `masa.py` | **Eski** kümeleme/Reels çıktısı (`site/masa.json`). TechTurco paneli okur; davranışı değişmedi. |
| `akis2.py` | **Yeni** hat: çok dilli kümeleme, bağımsız kaynak sayımı, çalışma alanları, sıcak/yükselen, Reels v2, kaynak durumları. → `site/data/*.json` |
| `index.tpl.html`, `build.py` | Arayüz. `site/index.html` içindeki `id="snap"` bloğu **yalnız TechTurco paneli içindir**; arayüz onu okumaz, `data/*.json` dosyalarını yükler. |
| `tools/kaynak_test.py` | Aday kaynağı gerçekten sınar (HTTP, RSS/Atom ayrıştırma, ≥3 tarihli kayıt, ≤45 gün, mevcutlarla kopya oranı). |
| `tools/kaynak_birlestir.py`, `tools/adaylar*.py` | Test sonucuna göre `sources.json`'a ekleme. |
| `tools/yerel_sunucu.py`, `tools/ekran.mjs` | gzip'li yerel önizleme; ekran görüntüsü ve performans ölçümü (Chrome DevTools Protocol). |
| `tests/` | `python3 -m unittest discover -s tests -t .` |

## Veri akışı (parçalı)
İlk açılış: `index.html` + `data/ozet.json`. Diğerleri tembel: `data/kume-<alan>.json`, `data/reels.json`, `data/kaynaklar.json`, `data/indeks.json` (ilk aramada). `site/data/` git'e girmez (`.gitignore`); her turda üretilir ve yayın paketine girer.

## Kalıcı kaynak değişikliği
Statik sayfada “kaydet” yoktur. Yeni kaynak: `tools/kaynak_test.py` → `sources.json` → ana dala gönder → Actions çeker. Kaynak ShiftDelete kullanılmaz (çekim aşamasında süzülür).

## Kural ve sınırlar
- Aynı olayı anlatan haberler tek konuda; **bağımsız kaynak** sayısı kurum başınadır, ajans kopyaları ve aynı bültenden türeyenler bire iner.
- Farklı dillerdeki haberler ortak varlık sözlüğü (ülke, lider, şirket) **ve** ortak sayı/çok seyrek özel adla birleşir; yalnız başlık benzerliğiyle farklı olay birleştirilmez.
- Reddit/topluluk/trend kaynakları doğrulanmış haber sayılmaz, yalnız erken sinyaldir.
- Reels puanı tahmini editoryal değerlendirmedir (kural tabanlı), viral garantisi değildir.
- Güncelleme sıklığı: zincirleme yeniden başlatma ile ölçülen aralık ≈ 9 dk (cron `*/30` yedektir). Daha sık çekim için önce Actions süre/limit ölçümü gerekir; yapılmadı.
