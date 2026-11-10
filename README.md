# Akış

Haber merkezi + Google Trends + güncelleme radarı + Reels konu keşfi. GitHub Actions kaynakları çeker, GitHub Pages yayınlar. Arayüz canlı değildir: üstteki saat **son başarılı veri üretimini** gösterir.

## Ekranlar (Akış 3, 2026-11-10)
- **Bugün:** Google Trends şeridi (Türkiye), öne çıkanlar (1/6/24 sa, en az 2 bağımsız kaynak), takip ettiklerin, yükselen, son gelenler. Sağda: "Aranıyor, yazan az" (trend var, haberimiz yok/tek kaynak), güncelleme radarı özeti, Reels önerileri. "Günün özetini kopyala" gündem + trend + güncellemeleri metin olarak panoya alır.
- **Akış:** 9 çalışma alanı; zaman, 3+ kaynak, Türkçe, alt konu süzgeçleri; Önemli / En yeni sıralama.
- **Trendler:** Google Trends (TR, ABD, BK, Almanya, Fransa, Japonya, Kore). Hacim, başlangıç saati, hacim seyri, Google'ın gösterdiği haberler, Akış'taki eşleşen konu, "Bizde yok / az" süzgeci, son 48 saatte sönenler.
- **Güncellemeler:** iOS, Android, One UI, HyperOS, Windows, WhatsApp, Instagram, Chrome, ChatGPT, Gemini, Claude… ürün bazında; tür: Yayında / Yeni özellik / Arayüz / Beta / Güvenlik / Sızıntı.
- **Reels:** Teknoloji / Gündem / Siyaset / Spor profilleri, alt kategoriler, 10 ölçütlü puan, hook kopyalama.
- **Kayıtlı:** iş akışı durumu (Yeni konu … Yayınlandı), notlar, JSON dışa/içe aktarma. **Kaynaklar:** durum, süzgeç, yeni kaynak taslağı.
- **Ayarlar (⋯):** tema (sistem/açık/koyu), sıkı liste, görseller, takip kelimeleri (vurgu + Bugün'de liste).
- Kişisel her şey tarayıcıda (localStorage); eski anahtarlar korunur (`akis-kayit/okundu/gizli/ziyaret`, `akis2-not/durum/ayar`).

## Dosyalar
| Dosya | İş |
|---|---|
| `sources.json` | Kaynak listesi. Eski alanlar (`id,name,lang,cat,url,plat`) + `calisma, tip, ulke, oncelik, nitelik, aktif, dogrulama`. |
| `fetch_feeds.py` | Kaynakları çeker: ETag/Last-Modified (304), zaman aşımı, devre kesici, spam ve ShiftDelete süzgeci, yanıt süresi. → `site/feeds.json`, `site/kaynak-durum.json` |
| `masa.py` | **Eski** kümeleme/Reels çıktısı (`site/masa.json`). TechTurco paneli okur; davranışı değişmedi. |
| `ekler.py` | Google Trends (ht: alanları, `site/trend-gecmis.json` ile ilk görülme/tepe/seri, haber kümesiyle eşleştirme, "bizde yok") ve Güncelleme Radarı (ürün + güncelleme ifadesi aynı başlıkta yakın geçmeli). → `site/data/trendler.json`, `guncellemeler.json` |
| `akis2.py` | **Yeni** hat: çok dilli kümeleme, bağımsız kaynak sayımı, çalışma alanları, sıcak/yükselen, Reels v2, kaynak durumları. → `site/data/*.json` |
| `index.tpl.html`, `build.py` | Arayüz. `site/index.html` içindeki `id="snap"` bloğu **yalnız TechTurco paneli içindir**; arayüz onu okumaz, `data/*.json` dosyalarını yükler. |
| `tools/kaynak_test.py` | Aday kaynağı gerçekten sınar (HTTP, RSS/Atom ayrıştırma, ≥3 tarihli kayıt, ≤45 gün, mevcutlarla kopya oranı). |
| `tools/kaynak_birlestir.py`, `tools/adaylar*.py` | Test sonucuna göre `sources.json`'a ekleme. |
| `tools/yerel_sunucu.py`, `tools/ekran.mjs` | gzip'li yerel önizleme; ekran görüntüsü ve performans ölçümü (Chrome DevTools Protocol). |
| `tests/` | `python3 -m unittest discover -s tests -t .` |

## Veri akışı (parçalı)
İlk açılış: `index.html` + `data/ozet.json` (+ arkadan `data/trendler.json`). Diğerleri tembel: `data/guncellemeler.json`, `data/kume-<alan>.json`, `data/reels.json`, `data/kaynaklar.json`, `data/indeks.json` (ilk aramada). `site/data/` git'e girmez (`.gitignore`); her turda üretilir ve yayın paketine girer.

## Kalıcı kaynak değişikliği
Statik sayfada “kaydet” yoktur. Yeni kaynak: `tools/kaynak_test.py` → `sources.json` → ana dala gönder → Actions çeker. Kaynak ShiftDelete kullanılmaz (çekim aşamasında süzülür).

## Kural ve sınırlar
- Aynı olayı anlatan haberler tek konuda; **bağımsız kaynak** sayısı kurum başınadır, ajans kopyaları ve aynı bültenden türeyenler bire iner.
- Farklı dillerdeki haberler ortak varlık sözlüğü (ülke, lider, şirket) **ve** ortak sayı/çok seyrek özel adla birleşir; yalnız başlık benzerliğiyle farklı olay birleştirilmez.
- Reddit/topluluk/trend kaynakları doğrulanmış haber sayılmaz, yalnız erken sinyaldir.
- Reels puanı tahmini editoryal değerlendirmedir (kural tabanlı), viral garantisi değildir.
- Güncelleme sıklığı: zincirleme yeniden başlatma ile ölçülen aralık ≈ 9 dk (cron `*/30` yedektir). Daha sık çekim için önce Actions süre/limit ölçümü gerekir; yapılmadı.
