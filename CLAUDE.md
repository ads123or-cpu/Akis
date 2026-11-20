# Akış — çalışma notu

Genel düzen: `~/Developer/CALISMA-DUZENI.md` (üst model karar verir, alt modeller ayrı dosyalarda uygular, kanıtsız "bitti" yok). Ayrıntılı dosya haritası: `README.md`.

## Ne
Okan'ın haber merkezi: ~770 RSS kaynağı, çok dilli kümeleme, 12 çalışma alanı, Google Trends, güncelleme radarı, Reels konu önerisi. Statik site: https://ads123or-cpu.github.io/Akis/ (depo `ads123or-cpu/Akis`, dal `main`).

## Hat
`fetch_feeds.py` → `masa.py` (eski çıktı, TechTurco paneli okur) → `akis2.py` (`site/data/*.json`) → `build.py` (`index.tpl.html` → `site/index.html`) → `kisisel.py`. GitHub Actions `refresh.yml` yapar; "tekrar" işi ~8 dk bekleyip kendini yeniden başlatır, cron `*/30` yedektir.

## Çalıştırma ve test
- Testler: `python3 -m unittest discover -s tests -t .` (ağsız, birkaç saniye). Kapı testleri: `tests.test_sozlesme tests.test_cikti`.
- Yerel üretim: yukarıdaki sırayla betikleri çalıştır, sonra `python3 tools/yerel_sunucu.py` (port 8765).
- Ekran/ölçüm: `node tools/ekran.mjs ekran <klasör> '<iş-json>'`, `node tools/ekran.mjs olcum`. Canlı için `TABAN=https://ads123or-cpu.github.io/Akis`. Telefon 390px, masa 1440px.
- Yeni kaynak: `tools/kaynak_test.py` ile sına, sonra `sources.json`.

## Yayın
`main`'e push = canlı (push, workflow'u tetikler). **Push Okan'a sorulmadan yapılmaz.** Bot her turda `site/` altına commit atar; push'tan önce `git pull --ff-only`.

## Ortam gerçekleri
- Yerel `site/data/` eski olabilir (git'e girmez); güncel veri canlı `data/*.json`.
- Yerelde erişilen kaynak Actions'tan erişilemeyebilir (403/429); kaynak durumu ilk turdan sonra canlı `data/kaynaklar.json`'da görülür.
- `kume-<alan>.json` sınırı 1100 KB (test_cikti).
- Kişisel ayarlar tarayıcıda (`akis2-ayar` vb. localStorage); anahtar adları değiştirilmez.

## Yapılmayacaklar
- `site/` dosyaları stage edilmez/commitlenmez (bota ait).
- Kaynakların `cat` alanı yeniden adlandırılmaz (TechTurco paneli kullanır); `masa.py` davranışı ve `site/index.html` içindeki `id="snap"` bloğu bozulmaz.
- ShiftDelete kaynak olarak kullanılmaz.
- Geliştirici/kod haberi eklenmez (Okan istemiyor; kaynaklar `aktif:false`, başlık süzgeci `GELISTIRICI`).
- Reels puanı viral garantisi gibi sunulmaz; sahte sayı yazılmaz.

## Dersler
(Okan aynı hatayı ikinci kez söylerse kural buraya eklenir.)
