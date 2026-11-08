# Akış 2.0 — teslim raporu (2026-11-08)

Durum: **hazır, yayınlanmadı.** Her şey yerel `akis-2.0` dalında; hiçbir şey `main`e ya da uzak depoya gönderilmedi. Push = yayın olduğu için onayınızı bekliyor.

- Dal: `akis-2.0` (yerel). Yedek: etiket `yedek-akis-1-2026-11-08` (main'in bu günkü ucu) + `~/Developer/Akis-yedek-akis-1-2026-11-08.tar.gz` (çalışma ağacı, .git hariç).
- Çalışan eski sistem silinmedi: `masa.py`, `build.py` ve `id="snap"` bloğu aynen duruyor.
- Ekran görüntüleri: `docs/ekran/*.png` (14 adet). **Hepsi gerçek veriyle**: 2026-11-08 ~19:10–19:31 (yerel saat) yerel makineden çekilen 590 kaynak. Sentetik veri yalnız testlerde kullanıldı, ekran görüntülerinde yok. Actions'ın canlı verisi değildir.

## 1. Ne değişti
**Mimari.** Eski hat korundu; yanına yeni hat eklendi: `akis2.py` → `site/data/` (ozet, kume-<9 alan>, reels, kaynaklar, indeks). Arayüz `id="snap"` bloğunu okumaz; ilk açılışta yalnız `index.html` + `ozet.json` iner (ölçüm: masaüstü ≈ 284 KB aktarım, gzip'li). `site/data/` git'e girmez (`.gitignore`) çünkü her tur ≈ 6 MB üretir ve depo zaten ~800 MB; yayın paketi `refresh` işinde üretilip doğrudan Pages'e verilir.

**Çekme (`fetch_feeds.py`).** ETag/Last-Modified ile koşullu istek; 304 başarı sayılır (ikinci yerel turda 95 kaynak 304 verdi). Yanıt süresi (hareketli ortalama), son kontrol, son haber, haber sayısı kaynak durumuna yazılıyor. `aktif:false` kaynaklar çekilmez. ShiftDelete: yayıncı alanı, bağlantı ve başlık sonu üzerinden çekim aşamasında süzülüyor (eski çıktıda 11 sızıntı vardı; testlenmiş).

**Kümeleme (`akis2.py`).** URL kanonikleştirme, kurum takma adları (NTV/NTV Spor, DW.com/DW Türkçe, BirGün/birgun.net…), aynı kurumun aynı başlığı tek haber; bağımsız kaynak sayısı kurum başınadır, ajans kopyaları/aynı bülten bire iner; çok dilli birleştirme (TR/EN/DE/FR/AR/ZH… 60 varlık sözlüğü + ortak sayı ya da çok seyrek ortak özel ad, 12 saat penceresi); ülke/lider adı tek başına birleştirmez; ikinci geçişte aynı olayın farklı anlatımları seyrek özel adlarla birleşir. Çıktıda 26 çok dilli küme (gündem+siyaset dosyaları).

**Arayüz.** Koyu varsayılan + açık tema, sabit kompakt üst çubuk (son senkron, kaynak sağlığı, yeni konu sayısı, yükselen konular, arama, hızlı kategori, görünüm, tema), sol menü, orta akış, sağ detay/trend paneli, mobilde alt gezinme + sağ panel tam ekran. Liste/kart, "daha fazla yükle", tembel görseller, framework yok. Gündem Merkezi (sıcak 1s/6s/24s, yükselen + hesap yöntemi, son gelişmeler: tümü/yeni/okunmamış/kaydedilen/gizlenen), 9 çalışma alanı (alt konu, marka, ülke/lider, spor kapsamı TR/dünya/federasyon, dil, zaman 1s–7g + özel aralık), Reels Fikir Radarı, Kaynak Yönetim Merkezi, Kaydedilenler/içerik durumu panosu, Ayarlar (JSON dışa/içe aktarma). Detay: tüm kaynaklar ve orijinal başlıklar (yeni sekme, `noopener noreferrer`), olay gelişim sırası, farklı anlatılan ayrıntılar, ilgili haberler, kaydet, not, 8 içerik durumu, Reels adayı, gizle, başlık/bağlantı kopyala. Kısayollar `/ J K O S X Esc` korundu, `Enter`, `R` eklendi. Eski localStorage anahtarları (`akis-kayit/okundu/gizli/tema/gorunum/ziyaret`) aynen okunur: kayıtlı konularınız kaybolmaz.

## 2. Kaynaklar
**439 → 590.** Eski 439'un hiçbiri silinmedi (test var). Hepsine ek alan eklendi: `calisma, tip, ulke, oncelik, nitelik, aktif` (+ yeni olanlara `dogrulama`). `yt-spacex` (404, 5 ardışık hata) `aktif:false`, nedeni yazılı; başka bir şey kapatılmadı.

**Yeni 151 kaynak**, 199+49 aday içinden `tools/kaynak_test.py` ile gerçekten sınanarak: HTTP 200, RSS/Atom ayrışması, ≥3 tarihli kayıt, son kayıt ≤45 gün, mevcut akışlarla ortak bağlantı <%60. Dağılım: ana akım 38 (FT, WSJ, Le Monde, Spiegel, Tagesschau, DW/BBC/France24 çok dilli, Haaretz, Kyiv Independent, Euractiv, TRT World, HDN…), resmî kurum 10 (ABD Dışişleri/Savunma/Beyaz Saray, CISA ×2, Fed, AMB, Dışişleri TR (EN), USGS ×2), uluslararası kurum 7 (BM ×4 dil, AB Komisyonu, WHO, ICG), ajans 3, doğrulama 1 (Teyit), uzman teknoloji 10, şirket duyurusu 7, spor 9, bilimsel 7 (Science, Lancet, PLOS, bioRxiv ön çalışma…), topluluk/trend 12 (Product Hunt, GitHub sürümleri, HN Best, DEV, Google Trends DE/FR/JP/KR), toplayıcı 47 (Google Haberler site:/konu aramaları — açıkça "toplayıcı" etiketli, resmî kurumun kendi akışı gibi gösterilmedi).

**Doğrulanamayanlar.** `t24, turkishminute, wsj-world, wsj-tech`: bu makineden alan adlarına ağ erişimi yok (DNS), test edilemedi. Bilinen RSS adresleriyle **aktif** eklendi ama `dogrulama.durum = "bekliyor"` — arayüzde "Doğrulama bekliyor"; ilk Actions çekişi sonucu belli olur, hata verirse devre kesici ve durum rozeti gösterir.

**Eklenemeyenler (test sonucu).** Reuters/AP/AFP ve ücretli/engelli bazıları: genel RSS yok ya da 404/403. TBMM, Resmî Gazete, YSK, TÜİK, TCMB, BTK, KVKK, AFAD, bakanlıklar, NATO, IMF, Dünya Bankası: çalışan açık RSS bulunamadı ya da boş/engelli → bunlar için yalnız Google Haberler `site:`/ad aramaları "toplayıcı" olarak eklendi. Anthropic, Meta AI, Microsoft AI, ESA, EurekAlert, FIFA, UEFA, NBA, ATP, WTA, TFF/TBF/TVF, Fanatik, Sporx, beIN, Eurosport, Top Gear, Doğruluk Payı, ANKA, VOA Türkçe, Duvar: 404/403/boş (tam liste `tools/kaynak_birlestir_rapor.json`). X/Instagram/TikTok/Reddit API/YouTube Data API: anahtar ya da izin gerektirir, arayüze gizli bilgi konmayacağı için eklenmedi; mevcut Reddit akışları 429 vermeye devam ediyor (devre kesicide).

**Hâlâ çalışmayan (son yerel tur):** erişim engelli (403) 10: Gazete Duvar, İnternet Haber, En Son Haber, Technopat, Teknoseyir, Gizmodo, Halk TV, Donanım Arşivi, Huawei Central, Teknoburada. Beklemede (429 devre kesici) 15 (Reddit). Uzun süredir güncellenmiyor 3 (Hürriyet Magazin, WHO, IGN Türkiye — son kayıt 25–29 gün). Yavaş 3 (WaPo, Daily Mail, HN). Hata 1 (KVKK araması boş döndü). Doğrulama bekliyor 4. Bunlar silinmedi, arayüzde kendi renkleriyle görünür. Eski çiftler (aynı URL iki kayıt: 9to5mac, macrumors, ntv-otomobil, electrek, apple-news) olduğu gibi bırakıldı; çıktıda link bazlı tekilleştiriliyor.

## 3. Reels algoritması: ne değişti
Eski: yalnız "Türkçe tüketici teknolojisi" süzgeci. `GENEL_RED` (suç, siyaset, spor, deprem, savaş, dava, maaş…) bir haber **ne kadar önemli olursa olsun** konuyu masaya hiç sokmuyordu; `REELS_RED` dizi/film/borsa/ABD/dava/kaza/milli takımı topluca atıyordu. Sonuç: 52 aday, hepsi teknoloji.

Yeni (`akis2.py`):
- **10 ölçüt, toplam 100:** güncellik 12, haber değeri 12, hayata etki 12, özgünlük 8, şaşırtıcılık 10, hikâye potansiyeli 10, görsel malzeme 8, çok kaynakta doğrulanma 12, Türkçe izleyiciye uygunluk 8, ilk 3 saniyede anlatılabilirlik 8. Her aday için dökümü arayüzde ("Puan dökümü").
- **Eleme yalnız içerik niteliğine:** alışveriş/indirim, yayın rehberi, burç/kumar, özel kişilerin trajedisi (tecavüz, istismar, kadın cinayeti…), sponsorlu. Haber türü elenmez.
- **Ceza (eleme değil), dar ve alana bağlı:** rutin sürüm notu, kurumsal finans dili, ürün incelemesi/liste (yalnız teknoloji/siber/oto/eğlence); yalnızca yerel kaza (yalnız gündem); yalnız ABD pazarı (yalnız teknoloji). **Siyaset ve spor hiçbir cezaya tabi değil** (test).
- **Çok kategorili konu** tek profile kilitlenmez; birden çok profilde görünür. Profiller Teknoloji/Gündem/Siyaset/Spor; alt: bilim, siber, otomobil, ekonomi, ilginç.
- Gerçek veride: 218 aday (Gündem 107, Siyaset 61, Teknoloji 61, Spor 60); eski kurallarla elenecek olan 61 aday artık giriyor (siyaset 25, spor 23, gündem 36). Elenenler: yayın rehberi 26, özel kişi trajedisi 9, burç/kumar 9, alışveriş 3.
- Her adayda: önerilen başlık, 1 cümle özet, neden gündemde, en çarpıcı ayrıntı (başlığı tekrar etmeyen cümle), Türk izleyicisi için önemi, doğrulama durumu (≥2 bağımsız kaynak adlarıyla ya da "DOĞRULANMADI"), görsel/video potansiyeli, 3 hook, anlatım açısı, puan + gerekçe, risk. Hook ve açı **kural şablonudur** (yapay zekâ değil); kümeden hesaplanan değerleri kullanır, uydurma iddia içermez. Not: "Tahmini editoryal değerlendirme, viral garantisi değildir."
- **Panel uyarısı:** TechTurco panelinin Akış sayfası hâlâ eski `masa.json` Reels listesini (teknoloji ağırlıklı) gösterir; panelin blade ikizi güncellenene kadar yeni Reels yalnız Akış 2.0 sayfasındadır. Panel koduna dokunulmadı (talimat).

## 4. Testler (hepsi geçti: 62 test, `python3 -m unittest discover -s tests -t .`)
| Alan | Ne sınandı |
|---|---|
| Panel sözleşmesi | `id="snap"` PHP'deki gibi okunuyor (ilk `id="snap"` → `>` → `</script>`), tam bir kez geçiyor, `/*SNAP*/` kalmıyor; `masa.json` üst anahtarlar + küme anahtarları; baseline (bugünkü canlı çıktı) ve üretilen çıktı |
| RSS/çekme | yerel HTTP sunucusuyla: 200, ETag, 304, gzip, bozuk XML yedek ayrıştırma, 403/404/429 + Retry-After |
| Hata yalıtımı | hatalı kaynaklar istisna fırlatmaz, diğerleri çekilir; 304 ardışık hatayı sıfırlar; devre kesici |
| Kümeleme | aynı olay farklı başlık; farklı olaylar (aynı kişi) birleşmez; Gazze genel haberleri dil ortak diye birleşmez; uzak zaman birleşmez; ikinci geçiş (UFC/Trump) birleşir |
| Çok dilli | TR/EN/DE deprem; Fransızca/İngilizce aynı başlık; CJK/Arapça jetonları |
| Bağımsız kaynak | ajans kopyası 1 sayılır; bağımsız anlatım 3; kurum takma adları; Latin dışı (Arapça/CJK) yayıncılar ayrı kurum, aynı ad farklı akışta aynı kurum; Kyiv Independent ≠ The Independent; kanonik URL |
| Reels | siyaset/spor/gündem başlıkları elenmiyor; yalnız dar listedeki içerik niteliği eleniyor; siyaset/spor cezaya tabi değil; uçtan uca 4 profil var |
| Kaynak durumları | aktif/yavaş/hata/erişim-engelli/güncellenmiyor/devre dışı/beklemede |
| Kaynak listesi | eski 439'un tümü duruyor, alanlar, ShiftDelete yok, yeni kaynak doğrulama kaydı, ücretli duvar etiketi, Reddit "erken sinyal" |
| Çıktı (yayın kapısı) | Yalnız belirlenimci denetimler: JSON geçerli, boyut sınırları, ShiftDelete yayıncı/bağlantı/kaynak alanlarında yok (özet metninde değil), sıcak/yükselen konularda ≥2 bağımsız kaynak, küme/kaynak durumu yapısı. Haber akışına bağlı dağılım denetimleri (4 profil var mı, haber sayısı) `tests/test_dagilim.py`'de ve kapı **değil**: sakin bir gece yayını durdurmasın |
| İş akışı | **YAML gerçekten ayrıştırılıyor** (Ruby/PyYAML; ilk sürümde bir adım adındaki `: ` YAML'ı bozmuştu, yakalandı ve düzeltildi), adım sırası, `push` yalnız `main`, zincir kopmaz, eşzamanlı çalışma yok, gizli anahtar yok |

**Arayüz (gerçek tarayıcıda, Chrome):** 9 alan + Reels + Kaynaklar + Kaydedilen + Ayarlar hatasız açılıyor (uygulama hatası yok; konsolda yalnız üçüncü taraf bir haber görselinin 402 yanıtı görüldü, görsel hata olunca kaldırılıyor); daha fazla yükle, kaydet/kaldır, gizle/Geri al, J/K, Esc, zaman (1s), dil (TR), alt konu, spor TR/Dünya, arama (genel ve `kaynak:ntv`), içerik durumu, not, Reels işareti, kart görünümü, tema, dış bağlantı `_blank`+`noopener noreferrer`, JSON dışa/içe aktarma gidiş-dönüş, kaynak merkezi durum/tip filtresi, yeni kaynak taslağı, "kaydet" düğmesinin **olmaması**. Eski şemayla kaydedilmiş bir konu (bugünkü canlı `masa.json` biçimi) localStorage'a konup Kaydedilenler ve detay paneli açıldı: görünüyor, 6 kaynak listeleniyor, hata yok; eski tema/okundu/gizli anahtarları da okunuyor. Bu arayüz denetimleri betik olarak depoya konmadı (elle yürütüldü).

**Performans (Chrome DevTools, gzip'li yerel sunucu, önbellek kapalı):**
| Senaryo | FCP | DOMContentLoaded/load | Aktarım |
|---|---|---|---|
| Masaüstü, ana ekran | 52 ms | 38 / 39 ms | 284 KB, 4 istek |
| Mobil 390 px, 4× CPU, ~1,6 Mbps/150 ms | 224 ms | 1160 / 1166 ms | 284 KB, 3 istek |
| Mobil Reels (tembel parça dahil) | 236 ms | 1157 / 1162 ms | 490 KB, 6 istek |
FCP başlık çubuğunun boyanmasıdır; içerik `ozet.json` gelince çıkar. Gerçek ağ/cihaz ölçümü değildir (yerel sunucu, CDP kısıtlaması); GitHub Pages üzerinde yeniden ölçülmeli. `id="snap"` bloğu yüzünden `index.html` hâlâ ~440 KB (panel için); panel `masa.json`/`data/*` okumaya geçerse ~150 KB'a iner.

## 5. Actions ve güncelleme sıklığı
- **Ölçüm:** son 8 çalıştırmanın başlangıçları 8,8–9,2 dk arayla (`gh run list`). Yani `tekrar` zinciri etkin olarak **≈9 dakikada bir** çalışıyor; "30 dakika" yalnız yedek cron. Eski README yanlıştı, düzeltildi. Çalıştırma ≈1 dk iş + 8 dk bekleme. **Sıklığı artırmadım**: önce Actions dakika limiti, `git push` yarışı ve kaynak yükü (ortalama yanıt 437 ms, p90 1,0 s; 590 kaynak, 24 iş parçacığı) ölçülmeli. ETag/304 yükü zaten düşürüyor (ikinci turda 590'ın 95'i 304).
- **Depo büyümesi (dikkat):** `.git` ≈ 800 MB / 1647 commit; her tur `site/` (feeds.json ≈ 5 MB) commitleniyor. Yeni çıktıyı commitlemedim. Öneri (yapılmadı): durum dosyalarını da commit yerine artefakt/cache ile taşımak.
- **İş akışı değişiklikleri:** testler → çek → `masa.py` → `akis2.py` → `build.py` → çıktı doğrulama → commit → yayın paketi; doğrulama bozuk üretimi commitlemeden durdurur (önceki site yayında kalır, `tekrar` zinciri `!cancelled()` ile sürer). `push` tetikleyicisi yalnız `main` (gelişme dalı yayın zinciri başlatmasın) ve `akis2.py`/`tests/**` yollarını kapsar. Bu iş akışı **GitHub'da hiç çalıştırılmadı** (yalnız metin testleri + yerel zincir); ilk çalıştırma main'e push sonrası olur.

## 6. Yayına alma (onayınız gerekli) ve geri alma
`main` bot tarafından ≈9 dakikada bir ilerliyor; `akis-2.0` geride. Onay verirseniz sırası:
```bash
cd ~/Developer/Akis
git fetch origin
git rebase origin/main            # dal site/ dosyalarına dokunmuyor; temiz geçmeli (site/ yerelde değişiklikli ise önce: git checkout -- site)
python3 -m unittest discover -s tests -t .
git push origin akis-2.0:main     # push = yayın
gh run watch --repo ads123or-cpu/Akis
```
İlk çalıştırma aynı zamanda ilk kez Python 3.12'de ve `upload-pages-artifact` yeni düzeniyle çalışır; kırmızı olursa site önceki sürümde kalır (deploy çalışmaz). Panel `masa.json`/`id="snap"` biçimini aynen okumaya devam eder.
Geri alma: `git revert --no-edit <ilk-akis-2.0-commit>^..<son-akis-2.0-commit>` (ya da `git revert -m` ile birleştirme commit'i) ve push. Not: `yedek-akis-1-2026-11-08` etiketi ve tar.gz yedeği **yalnız bu makinede**; uzak depoya itilmedi (gerekirse `git push origin yedek-akis-1-2026-11-08` ile siz karar verin).

## 7. Bilinen sınırlar / yapılacaklar
1. TechTurco panelinin Reels ve Gündem sekmesi eski `masa.json`'u okur (yeni Reels paneli yansımaz).
2. Kümeleme yalnız başlık/özet üzerinde; haber gövdesi çekilmediği için içerik benzerliği yok. Farklı dil birleştirme muhafazakâr (kaçırabilir, yanlış birleştirmez).
3. "Kişi" araması: lider/şirket/ülke sözlüğüyle (≈60 varlık); keyfi kişi adları başlık/özet metin aramasıyla bulunur.
4. Zaman penceresi 7 gün; alan başına en güncel 360 konu dosyaya yazılır.
5. Spor: "Federasyon/lig açıklamaları" süzgeci kaynak adı/başlık ifadesine dayanır; TFF/TBF/TVF resmî akışı bulunamadığı için Google Haberler aramasıdır.
6. Hızlı kategori çipleri ve mobil alt gezinme tarayıcıda denendi; gerçek telefonda (dokunma, klavye) denenmedi.
7. Reels hook/açı şablon metnidir; yayından önce editoryal gözden geçirme şart. "Çarpıcı ayrıntı" kaynak özetinden alınır; özet İngilizceyse İngilizce gelir (çeviri yok).
