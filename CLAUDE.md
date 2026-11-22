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

## Okan'a özel "X'te paylaş" (22.11.2026)
- Haber ayrıntısında ve kart menüsünde "X'te paylaş (@okangules13)": taslak metin + fotoğrafı kopyala + `x.com/intent/post`. Gönderiyi X'te Okan'ın kendi tıklaması yayınlar.
- **Varsayılan görünmez; Pırıl profilinde/masasında (`pc:` kimlikleri dahil) hiçbir koşulda görünmez.** Ayarlar ekranına, ayar nesnesine ya da herhangi bir listeye eklenmez (bayrak ayrı anahtarda: `akis2-okx`).
- Açmak: cihazda bir kez `…/Akis/?okan=<kod>`; kapatmak: `?okan=kapat`. Depoda yalnız kodun SHA-256'sı (`OKX_HASH`) var; kod Okan'da. Kod kaybolursa yeni kod üret, hash'i değiştir (`python3 -c "import secrets,hashlib;k=secrets.token_urlsafe(9);print(k,hashlib.sha256(k.encode()).hexdigest())"`) ve kodu yalnız Okan'a söyle, depoya yazma.
- Site statik ve herkese açık: **X anahtarı/API belirteci sitede ve depoda tutulmaz** (`tests/test_okan_x.py` denetler). Otomatik gönderim gerekiyorsa ayrı, kapalı bir arka uç gerekir; Okan karar verir.
- Taslak şablondan gelir (`okxTaslak`): sade / özetli / kanca (yer tutuculu) / özel; olgu eklenmez, iddia ise öntakı (`İddia: `) eklenir. Bağlantı ana gönderide değil ilk yanıtta (`okxYanit`).
- Pencerede 3 sekme: Taslak, Taslaklarım (en çok 50, `akis2-okx-taslak`), Ayarlar (`akis2-okx-ayar`: şablon, kaynak biçimi/sayısı, öntak, yanıt metni, UTM). Hepsi bu cihazda; Pırıl'a görünmez.
- Kural denetimi (`okxDenetle`): kırmızı hata (yer tutucu, doldurulmamış `{alan}`) varsa "X'te aç" çalışmaz; sarı uyarılar: ana gönderide bağlantı, abartı/etkileşim tuzağı kalıbı, haberin başlık/özetinde olmayan sayı, iddia haberde "iddia" ifadesi yok.
- Reels şablonu: `araclar/reels-sablonu.html` (kurgu-kit/reels-artifact kopyası, noindex, X ödeme uyarılı); `build.py` onu `site/reels-sablonu.html` yapar (Actions). Akış'tan yalnız Okan modunda bağlanır (haber ayrıntısı, X penceresi, Reels kartı); `?yazi=&marka=&kicker=&tasarim=&rakam=&etiket=&rakam2=&etiket2=&kaynak=&soru=` ile ön dolar. Kapalı başlayan 4 katman: açılış rakamı (tek ya da ikili karşılaştırma), kaynak şeridi, kapanış sorusu, yavaş yakınlaştırma (≤%7); rapor: `inceleme-raporlari/reels-sablon-katmanlar.md`. Hiçbiri açık değilken çıktı kareleri eskisiyle aynı kalmalı. İki kopya (bu ve Claude'daki yayınlanmış sürüm) ayrışabilir: değişikliği ikisine de taşı.

## Dersler
(Okan aynı hatayı ikinci kez söylerse kural buraya eklenir.)
