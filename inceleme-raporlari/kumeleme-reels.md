# Kümeleme ve Reels konu önerisi denetimi

Tarih: 19.11.2026. Salt okunur denetim; proje dosyalarında değişiklik yapılmadı.

## Nasıl ölçüldü
- Canlı veri `data/reels.json`, `data/ozet.json`, `data/kume-*.json` ve aynı tura ait `feeds.json` dosyası (generated 2026-11-19T16:35:03Z) scratchpad'e indirildi.
- `akis2.py` içindeki `ogeler_kur → kumele_tam → kumeler_kur → profil_bul` fonksiyonları bellekte, bu `feeds.json` ile yeniden çalıştırıldı. Dosya yazılmadı, `main()` çağrılmadı. Sonuç canlıyla neredeyse aynı çıktı: 9659 küme (canlı 9660). Reels listesi 81 kart; bunların 80'i canlıyla aynı.
- Reels seçim döngüsü (`akis2.py:716-740`) her kartın neden elendiğini yazacak biçimde birebir kopyalandı.
- Yorumlar elle yapıldı. Her bölümde kaç örneğe bakıldığı yazılıdır.
- Genel tablo: 11.607 haberden 9659 küme çıkıyor. Kümelerin 8709'u (%90) tek haberden oluşuyor.

## Özet tablo
| # | Önem | Konu | Ölçüm |
|---|---|---|---|
| 1 | Yüksek | Büyük olaylar onlarca kümeye bölünüyor | Anthropic halka arzı 105 küme / 128 haber; Myanmar soykırım kararı 21 küme; Trump-Şi-Putin zirvesi 73 küme |
| 2 | Yüksek | Reels tekrar süzgeci ters çalışıyor | 21 tekrar elemesinin 15'i yanlış (%71). Listede 7 kart aynı olayın tekrarı |
| 3 | Yüksek | Reels eşiğini rutin haber de geçiyor | 81 kartın 26'sı zayıf (%32), 7'si tekrar (%9) |
| 4 | Orta | Profil kotası güçlü konuları dışarıda bırakıyor | 52 aday "profil dolu" diye düştü; liste 90 yerine 81 kart |
| 5 | Orta | Alan kurallarında kelime içi ve çok anlamlı eşleşmeler | `iran` (Haziran, artıran), `ev` (Türkçe "ev"), `galaxy`, `euro`/`altın`, `sızıntı` |
| 6 | Orta | Siyaset ile Gündem çakışması | Siyaset kümelerinin %90,2'si Gündem'de de var (862/956) |
| 7 | Düşük | Bazı yanlış birleşmeler | İncelenen 7 büyük kümenin 3'ünde başka olay karışmış |
| 8 | Düşük | ELE ve CEZA kalıplarındaki boşluklar | e-Devlet SEO sayfası ve özel kişi cinayeti listeye girdi |

---

## 1. Büyük olaylar bölünüyor (en önemli kümeleme sorunu)
**Önem:** Yüksek. **Yer:** `akis2.py:255` (`seyrek`: en çok 25 haberde geçen ad), `akis2.py:276` (`df<=8`), `masa.py:112` (`nadir`: en çok 10 kümede geçen ad). `kumele_tam` (`akis2.py:291-298`) bu eşiği `masa.birlestir` üzerinden kullanıyor.

**Neden oluyor:** Birleştirme, "seyrek özel ad" ortaklığına dayanıyor. Bu eşik sabit bir sayı. Bir olay ne kadar çok yazılırsa adı o kadar çok haberde geçiyor ve "seyrek" sayılmaktan çıkıyor. Ölçülen geçiş sayıları: `anthropic` 178 haber, `myanmar` 67, `rohingya` 53, `galaxy` 173. Bu adlar artık eşleşmeye katkı vermiyor. Geriye yalnız kelime benzerliğinin ≥0,5 olması kalıyor, farklı başlıklar da bunu geçemiyor. Sonuç olarak en büyük olaylar en çok bölünüyor.

Diller arası birleşmede ayrıca en az 2 ortak sözlük varlığı gerekiyor (`akis2.py:278`). Varlık sözlüğünde `myanmar` ve `waymo` yok, `anthropic` ise tek başına kalıyor. Bu yüzden Türkçe ve İngilizce kümeler birleşemiyor.

**Örnekler** (olayın bütün kümelerine bakıldı, başlıkla elle doğrulandı):
- **Anthropic halka arzı:** Başlığında Anthropic ve halka arz/IPO geçen 105 küme, 128 haber var; 13'ü 2+ bağımsız kaynaklı. Örnekler: `6836e138ab` (en, 3 kaynak), `ca83bdcacf` (en, 4), `a7f9f3a513`, `e821adb043`, `2f982f86df`, `7908176728`, `65e72b1b5e` (tr), `a0e30df16e` (tr/de).
- **Myanmar soykırım kararı:** 21 küme, 65 haber. `766252955b` (en, 15 haber) ile `5a333b71b5` (tr, 14 haber) ayrı kaldı. Yalnız İngilizce içinde bile 5 küme var: `766252955b`, `23033fad85`, `ba1b3658cf`, `8e13c363b3`, `a6605e8eec`.
- **Trump-Şi-Putin zirvesi:** 73 küme, 114 haber. Bunların bir kısmı tepki haberi ve ayrı durması doğal. Ama aynı gelişmenin kümeleri de ayrı: "barış deklarasyonu" `a730423dfa` (tr) ile `3909f7a104` (en); "zirve başladı" `d20a12d522`, `ea020fb3c6`, `d208d2bd4b`, `24b7fcf3a7`.
- **Avrupa Komisyonu'na siber saldırı:** En az 11 küme. `f511c218f2`, `380eeb878e` (fr), `eea1c235cf`, `d2fbe2120b`, `09b78e105f`, `e0b94e5dd6`, `d6f2d013f8`, `f5cc00cf50`, `5f0d6e421f`, `05db2b6bea`…
- **Diğerleri:** Waymo'nun otoyoldan çekilmesi 6 küme. iPhone 20 Pro tasarım sızıntısı 31 küme; en büyükleri `07cee2d32e` (en, 9 kaynak) ile `12727c13bc` (tr, 7 kaynak) ayrı. Galaxy S27 kamera sızıntısı 8 küme. Canva'nın YZ kapatma düğmesi 5 küme. Galatasaray-Samsunspor maç önü 5 küme. FIFA başkanlık seçimi 6 küme.
- **Sorunsuz olanlar:** İncelenen 16 olayın 2'si tek kümede kaldı (Hürmüz tankeri `4df7311746`, Nothing YZ cihazı `82e79957c0`). 14'ü (%88) bölünmüş.

**Etkisi:** Kaynak sayısı küçük parçalara dağılıyor ve olay "sıcak" görünmüyor. Reels'te aynı olaydan birden çok kart çıkıyor (bkz. 2). Arama ve alan listeleri tekrarla doluyor.

**Öneri (kural):**
1. "Seyrek" hesabını tek ada göre değil **ad çiftine** göre yap. Örneğin `anthropic + nasdaq/ipo` ya da `myanmar + rohingya` çifti, aynı 36 saatte en çok N kümede geçiyorsa ayırt edici sayılsın. Tek ad büyüyünce sıradanlaşır, çift ise olaya özel kalır.
2. Eşiği sabit sayı yerine haber havuzunun oranı ya da 36 saatlik pencere içindeki geçiş sayısı yap.
3. `CANON` sözlüğüne o haftanın büyük özel adlarını el ile eklemek yerine, **iki dilde de aynı yazılan Latin harfli özel adları** (Myanmar, Waymo, Anthropic, Shenzhen) diller arası ortak varlık say.
4. İkinci geçiş (`masa.birlestir`) ortak olduğu için `masa.py`'ye dokunma. Akış'a özel bir üçüncü geçiş ekle. Böylece TechTurco panelinin çıktısı değişmez.

**Test fikri:** Aynı 12 saatte 40 farklı başlıklı "Anthropic IPO" haberi (en/tr/de, sayı 81 ya da 83), araya 60 ilgisiz "Anthropic" haberi koy. Beklenen: IPO haberleri en çok 3 kümede toplanır, ilgisiz haberler onlara girmez. İkinci test: 15 İngilizce + 10 Türkçe Myanmar/Rohingya başlığı en çok 2 kümede toplanmalı.

**Karar gerekir mi:** Hayır, kural düzeltmesi. Yalnız masa.py'nin eski hattının aynen kalacağı varsayıldı.

---

## 2. Reels tekrar süzgeci yanlış kartı atıyor, gerçek tekrarı kaçırıyor
**Önem:** Yüksek. **Yer:** `akis2.py:431-438` (`REELS_GENEL`, `reels_anahtar`), `akis2.py:716-718` (`seyrek`: aday havuzunda en çok 4 kez geçen anahtar), `akis2.py:727` (2 ortak anahtar varsa tekrar sayılır).

**Neden oluyor:** `reels_anahtar`, `M.varlik` fonksiyonunu kullanıyor. Bu fonksiyon büyük harfle başlayan her kelimeyi özel ad sayıyor. İngilizce başlıklarda her kelime büyük harfle başladığı için (Title Case) `leak`, `design`, `feature`, `first`, `like`, `report`, `says` gibi sıradan kelimeler "özel ad" oluyor. Türkçe büyük harfli SEO başlıkları için de aynısı geçerli: `kimdir`, `kaç`, `nereli`, `yaşında`. Ayrıca `rusya`, `çin`, `dünya`, `yapay`, `zekâ`, `elon`, `musk`, `jeff`, `bezos` gibi genel adlar süzülmüyor.

Eşik "en çok 4 adayda geçen" diye kurulduğu için ters de çalışıyor: Anthropic gibi çok tekrar eden bir konunun anahtarı seyrek sayılmıyor, bu yüzden tekrarı yakalanmıyor.

**Ölçüm:** Bu turdaki 21 "tekrar-anahtar" elemesinin hepsine elle bakıldı. **15'i yanlış (%71)**, 6'sı doğru.

**Yanlış eleme örnekleri** (atılan kart ← tekrarı sayıldığı kart, ortak anahtar):
- `d6f9671e1d` KIZILELMA envantere girdi (puan 62,1, 8 kaynak) ← `dcda27f65d` Çin'de 151 insansı robot dansı: `dünya`, `insans`. Bu, *insansız* ve *insansı* kelimelerinin aynı köke inmesinden kaynaklanıyor.
- `07cee2d32e` Apple'ın 20. yıl iPhone'u için iki tasarım (9 kaynak) ← `ef61b50c54` Galaxy Buds sızıntısı: `design`, `leak`.
- `e3c22ce9f8` CHP kurultay davasında karar ← `6f6e245e57` İmamoğlu'nun paylaşımı: `ekrem`, `imamoğ`.
- `aed8587f5a` Antalya ve Tekirdağ AKP'ye geçti (12 kaynak) ← `d71a1ff4f9` Kavcıoğlu: `kaç`, `kimdir`, `nereli`, `yaşınd`.
- `249215a33f` Yeni James Bond Robert Pattinson (13 kaynak) ← `97a083bcf6` Google'ın New Glenn ile YZ uydusu: `jeff`, `bezos`.
- `127c2696b1` Google'ın Claude Opus 5.5'e rakip yeni modeli ← `97a083bcf6`: `yapay`, `zekâ`.
- Diğer yanlışlar: `a09cb6477e`, `8f8c90c4c9`, `1f451d728d`, `7871684bbe`, `1417ecf7cd`, `ff18c3d28e`, `ddc41074ca`, `419d170df2`, `457bb17f33`.

**Kaçırılan tekrarlar** (81 kartlık canlı listede):
- Anthropic halka arzı 4 kart: #5 `ca83bdcacf`, #10 `6836e138ab`, #14 `a0e30df16e`, #68 `7908176728`.
- Waymo 2 kart: #17 `884228ddde`, #42 `d245c51110`.
- Zirve 3 kart: #48 `47f359ca43`, #73 `f33a01feb6`, #79 `d20a12d522`.
- FIFA seçimi 2 kart: #65 `4f7a1d1858`, #80 `5e78ed82e0`.
- Galatasaray rekor 2 kart: #4 `0c3d40871f`, #71 `4d035f8b9c`. Aynı maçın önü #78 de listede.
- Toplam 7 gereksiz tekrar kart (%9).

**Öneri (kural):**
- Anahtar yalnız şunlardan oluşsun: CANON marka ve kişileri (ülkeler hariç), model adları (`iphone 20`, `s27`) ve **cümle başında olmayan, Title Case olmayan başlıklarda büyük harfle yazılmış** sözcükler. Büyük harfli SEO başlıklarının kelimeleri ve İngilizce Title Case başlıklar anahtar üretmesin.
- `REELS_GENEL` listesine ülkeleri ve genel kelimeleri ekle: `rusya`, `çin`, `dünya`, `yapay`, `zekâ`, `leak`, `design`, `report`, `first`.
- Tekrar kararı için df eşiğine güvenme. "Aynı ana varlık + 36 saat + (ortak sayı ya da tüm başlıklarda kelime benzerliği ≥0,2)" koşulunu kullan.
- Konu sınırını (`akis2.py:729-730`, en çok 2 kart) model adlarından CANON varlık çiftlerine de genişlet. Örneğin `anthropic` + halka arz en çok 1 kart olsun.

**Test fikri:**
- (a) `reels_anahtar` "Galaxy Buds Active Leak Shows Workout Design" ve "Leak Says Apple Is Developing Two Designs" için ortak anahtar döndürmemeli.
- (b) KIZILELMA ve "151 İnsansı Robot" kartlarının ikisi de listede kalmalı.
- (c) Üç farklı dilde Anthropic IPO kümesi verildiğinde listede en çok 1 kart çıkmalı.

**Karar gerekir mi:** Hayır.

---

## 3. Reels eşiği rutin haberle aşılıyor ("aşırı gereksiz" şikâyetinin ana nedeni)
**Önem:** Yüksek. **Yer:** `akis2.py:241-242` (`KRITER` ağırlıkları), `akis2.py:428` (`REELS_ESIK=48`).

**Neden oluyor:** Ağırlıkların %40'ı içerikle ilgisiz ölçütlerden geliyor: güncellik, haber değeri, çok kaynakta doğrulanma ve Türkçe izleyiciye uygunluk. Görsel ve özgünlüğün taban puanı da bunlara ekleniyor. Yeni, çok kaynaklı, görselli bir Türkçe haber, hayata etkisi, şaşırtıcılığı, hikâyesi ve viral potansiyeli sıfır olsa bile yaklaşık **52,5** puan alıyor ve 48 eşiğini geçiyor.

Örnekler: #64 "TBMM Genel Kurulu toplandı" `1730097852` 52,2 puan (bu dört ölçütün toplamı 1,7/40); #70 "Fenerbahçe maç hazırlıklarını sürdürdü" `509897241e` 51,0; #37 "Borsa günü düşüşle tamamladı" `4dcfeb05e4` 57,2.

**Ölçüm:** 81 kartın hepsi elle tek tek değerlendirildi; teknoloji ve gündem odaklı Türk izleyici esas alındı.
- **Zayıf, 26 kart (%32):** #11 OMÜ Diş Hekimliği, #16 iMac OLED siparişi, #18 Motorola güncellemesi, #26 balık uyarısı, #28 e-Devlet SEO sayfası, #30/#34 yerel robot yarışmaları, #31 operasyon, #35 Fransa'da sel, #37 Borsa, #39 Konyaspor maç hazırlığı videosu, #41 koca cinayeti, #44 araç yangını, #47 Fold 8 güncellemesi, #49 hakemler, #50 trafik yoğunluğu, #55 rezervler, #56 Clair Obscur senaristi, #60 Emine Erdoğan görüşmesi, #64 TBMM, #66 UEFA ziyareti, #70 Fenerbahçe hazırlığı, #72 Trabzonspor, #75 Erdoğan'ın teşkilat uyarısı, #76 ABD yaptırımı, #81 DEM çağrısı.
- **Tekrar, 7 kart (%9):** bkz. 2.
- **Güçlü, yaklaşık 13 kart (%16):** #3 Nothing YZ cihazı, #5 Anthropic halka arzı, #7 AB'ye YZ destekli siber saldırı, #8 GTA 6 sırrı, #13 robot dansı rekoru, #32 Instagram hikâye düzenleme, #33 GTA 6 haritası, #43 Kore'de telefonla sınav kopyası, #52 AYM kararı, #58 9 belediye AKP'ye geçti, #61 500 bin elektrikli araç, #77 Hürmüz tankerleri, #79 zirve.
- Geri kalan yaklaşık 35 kart orta düzeyde.

**Ayrıca:**
- `CARPICI` kalıbında (`masa.py:31`) `leak`, `finally`, `surpris` var. Bu kelimeleri içeren her kart şaşırtıcılıktan 6 puan alıyor ve rutin sürüm cezasından muaf tutuluyor (`akis2.py:413`). Örnekler: #18 Motorola "finally receives Android 17 stable update" 60,5 puan; #47 Fold 8 "mise à jour surprise".
- Listenin 1. sırası Galaxy Buds Active sızıntısı (82,1). Bu kartın Türkçe izleyiciye uygunluk puanı 0, ama yalnız yabancı kaynakta olduğu için özgünlükten +4, viral potansiyelden +2 alıyor.

**Öneri (eşik/kural):**
- Bir **içerik kapısı** ekle: hayata etki ≥6, şaşırtıcılık ≥6, viral ≥5 ya da hikâye ≥5 koşullarından en az biri sağlanmalı.
  - Bu tur üzerinde ölçtüm: kapı 80 kartın 25'ini düşürüyor. Zayıf 26 karttan 13'ünü ayıklıyor, güçlü 13 karttan 3'ünü de yanlışlıkla düşürüyor (#58 AKP, #77 Hürmüz, #79 zirve).
  - Bu yüzden kapıya bir istisna ekle: 4+ bağımsız kaynaklı siyaset ve dünya olayları kapıdan muaf olsun.
- `leak` ve `finally` kelimelerini rutin ceza muafiyetinden çıkar. Muafiyet yalnız gerçek şaşırtıcılık kelimelerine kalsın.
- "Maç hazırlıkları", "hakemleri açıklandı", "Genel Kurulu toplandı", "günü …la tamamladı", "ile görüştü" için yeni bir CEZA kalıbı ekle. Ceza siyaset ve spor alanlarında da geçerli olsun.

**Test fikri:** 4 kaynaklı ve görselli bir "TBMM Genel Kurulu toplandı" kümesi Reels'e girmemeli. 4 kaynaklı "Hürmüz'de tanker mayına çarptı" kümesi girmeli. "Motorola Razr Fold finally receives Android 17 stable update" rutin cezası almalı.

**Karar gerekir mi:** Evet, iki karar var:
1. Siyaset ve spor rutin haberlerine ceza verilsin mi? Mevcut CEZA tasarımı bilinçli olarak siyaset ve sporu dışarıda bırakıyor (`akis2.py:228`, `test_ceza_siyaset_spor_gundemde_uygulanmaz`).
2. Yalnız yabancı kaynaklı sızıntılar öne mi çıksın? README "özgünlük öne" diyor.

---

## 4. Profil kotası güçlü konuları dışarıda bırakıyor
**Önem:** Orta. **Yer:** `akis2.py:430` (`REELS_PROFIL=30`), `akis2.py:734-740`.

Her profile en çok 30 kart ayrılıyor ve kartlar puan sırasıyla alınıyor. Gündem ve teknoloji kotaları zayıf ve tekrar kartlarla doluyor. Spor ve siyaset kotası boş kaldığı için liste 81'de kalıyor. **52 aday "profil dolu" diye düştü**, aralarında daha iyileri var:
- `742c6d74c1` Real Madrid/Arda Güler sözleşmesi (11 kaynak; profili yanlışlıkla "gündem", bkz. 5)
- `7ccebef96b` OpenAI'ın yeni modelleri GPT-6.2
- `f53f56544e` Instagram Direct Türkiye'de test ediliyor
- `209d2be974` Türkiye'de Sony/PlayStation rekabet soruşturması
- `c704106eec` Hibrit ve elektrikli araç payı %51
- `0401b26d2e` Voyager 1 bir ışık gününe ulaştı
- `c2475d6b8a` Lamborghini Temerario

Eşik altında kalan güçlü konular:
- `9fd33252b0` HONOR Türkiye'de üretime başladı: 11 kaynak ama 40,5 puan. Görseli yok ve haber değeri yalnız son 6 saatten hesaplanıyor (3,2/10).
- `8806f6d90a` iOS 27.3 beta, iPhone Duo'ya yüz tanıma: 13 kaynak, 47,1 puan, rutin ceza aldı.

**Öneri:** Önce 2 ve 3'teki düzeltmeler yapılsın; kota sorununun çoğu bunlarla çözülür. Ayrıca haber değeri ölçütü (`akis2.py:393`) 24 saatlik bağımsız kaynak sayısını da hesaba katsın. Görseli olmayan haber 0 yerine en az 3 puan alsın.

**Test fikri:** 11 kaynaklı, 18 saatlik, görselsiz ve Türkiye geçen bir teknoloji haberi eşiği geçmeli.

**Karar gerekir mi:** Evet. Profil başına 30 sınırı ve toplam 90 kart sayısı korunacak mı?

---

## 5. Yanlış alana düşen haberler
**Önem:** Orta. **Yer:** `akis2.py:131-143` (KURAL), `akis2.py:321-354` (`alan_bul`), `akis2.py:440-458` (`profil_bul`).

Alan başına 40'ar rastgele örneğe (tohum sabit) ve tetikleyen kelime taramasına bakıldı.

| Kalıp | Satır | Sorun | Ölçüm ve örnek |
|---|---|---|---|
| `iran` (siyaset) | 131 | Kelime sınırı yok; Haziran, artıran, kıran içinde eşleşiyor (`re.I` ile ı/i de eşleşiyor) | 26 siyaset kümesinde kelime içinde geçiyor; 20'sinde tek tetik bu. Örnekler: `742c6d74c1` Real Madrid (Haziran), `2988f0ebc7` İstanbul trafiği (artıran), `acfc67d75d` klozet temizliği, `a1912028e5` YKS tarihi |
| `harris`, `president`, `summit`, `zirve` | 131 | Şirket yöneticisi ve zirve toplantıları siyasete giriyor | `f3afc638a5` Snap'ten Ronan Harris |
| `\bev\b` (oto) | 137 | Türkçe "ev" kelimesi elektrikli araç sayılıyor | `f814b19fb9` "Ev gençlerinin lideri" Oto'da ve Reels #36'da |
| `trafik` (oto) | 137 | Şehir trafiği Oto'ya düşüyor | `2988f0ebc7` |
| `galaxy` (bilim) | 136 | Samsung Galaxy, Bilim ve Uzay'a düşüyor | 21/471 bilim kümesi; Reels #1, #20, #25, #47 "tekno, bilim" |
| `euro\b`, `altın` (ekonomi) | 135 | EURO 2028 ve altın madalya ekonomiye giriyor | `f45c124a74`, `34df9a8681` |
| `teknoloji`, `oyun`, `uygulama`, `akıllı` (tekno) | 138 | Tek genel kelimeyle Teknoloji | Yalnız teknoloji alanındaki ve tek tetiği bu genel kelimeler olan 63 küme. Örnekler: `1d7bdc51dc` OMÜ Diş Hekimliği (Reels #11), `917c38c4b0` koyun aranan dron, `0385d51c4e` |
| `sızıntı`, `saldırgan`, `hack\b`, `exploit` (siber) | 133 | Ürün sızıntısı, okul saldırganı, "hayat hilesi", sömürü haberleri Siber'e giriyor | Rastgele 40 siber örneğinde 3 açık hata (%7,5): `52a438925f` iPhone tasarım sızıntısı, `1497bc8d4a` mülteci çocuklar, `f500bbb7a3` iOS ipucu. Tetiği yalnız bu kelimeler olan 74/273 kümenin bir kısmı geçerli (dolandırıcılık uyarıları) |
| `\bai\b` (yz) | 140 | İtalyanca/Portekizce "ai" ve ürün adındaki "AI" | Rastgele 40 YZ örneğinde 3 hata (%7,5): `2f59150208` (İtalyanca "ai competitor"), `707e78305b` Predator Helios 16S AI dizüstü, `8732893b62` |
| spor kuralı | 334 | Spor kaynaklı ama spor kelimesi geçmeyen haber Spor'a girmiyor | `742c6d74c1` Real Madrid: 8 spor kaynağı var, alan "gündem, tekno, siyaset", **Spor yok**. Bu yüzden Reels profili de yanlış |
| `profil_bul` | 444 | `tekno_guclu` kalıbında "phone" ve "oneplus" yok; oyun başlığı tanınmıyor | #29 OnePlus 17 ve #56 Clair Obscur "gündem" profiline düştü |

Oyun alanı: rastgele 40 örnekte 1-2 sınırda hata var. Örneklerin 24'ü GTA 6; bu yanlış değil, o haftanın gerçek gündemi.

Siyaset: rastgele 40 örnekte 3 açık hata (%7,5), 3 sınırda.

**Öneri:**
- `\biran\b` kullan; aynısını `\bab\b` gibi kısa kalıplara da uygula.
- Oto'dan `\bev\b` kalıbını çıkar ya da yalnız İngilizce başlıkta say; `trafik` kelimesini oto'dan çıkar.
- Bilim'de `galaxy` için `(?<!samsung )galaxy(?! (s|z|a|tab|buds|watch|fold|flip)\b)` gibi bir sınır koy.
- Ekonomi'de `euro\b` ve `altın` spor bağlamında sayılmasın (`madalya`, `euro 20\d\d`).
- Siber'de `sızıntı` yalnız `veri|bilgi|kişisel` ile birlikte sayılsın; `saldırgan` çıkarılsın; `hack\b` kelimesi `hack(ed|er|lendi)` biçimine dar tutulsun.
- YZ'de `\bai\b` İngilizce olmayan başlıkta sayılmasın.
- Spor: kaynakların %60'ından fazlası spor bölümüyse ve en az 3 spor kaynağı varsa içerik kelimesi aranmasın.

**Test fikri:** `alan_bul` için tablodaki her satırdan birer başlık:
- "Real Madrid, Tchouaméni'nin sözleşmesini 30 Haziran 2032'ye uzattı" + 8 spor kaynağı → `spor` var, `siyaset` yok.
- "Deprem sonrası evine kapandı" → `oto` yok.
- "Galaxy S27 Ultra kamerası sızdı" → `bilim` yok, `siber` yok.
- "EURO 2028 kurası" → `ekonomi` yok.

**Karar gerekir mi:** Hayır.

---

## 6. Siyaset ile Gündem çakışması
**Önem:** Orta. **Yer:** `akis2.py:344-346`.

Ölçüm: siyaset kümelerinin **%90,2'si** (862/956) Gündem'de de görünüyor. Gündem'in %30,4'ü siyaset. Bu bir hata değil; kural bilerek böyle yazılmış: siyaset alanına giren ve gündem kaynağı olan her küme Gündem'e de ekleniyor.

Kullanıcı açısından Gündem ve Siyaset sekmeleri büyük ölçüde aynı içeriği tekrar ediyor. Reels'te de bu kartlar hem "gündem" hem "siyaset" profiline yazılıyor ve gündem kotasını erken dolduruyor (bkz. 4).

**Öneri:** Seçenekler:
- (a) Mevcut hali koru.
- (b) Gündem yalnız Türkiye siyasetini (`tr-siyaset` alt etiketi) alsın, dış siyaset yalnız Siyaset'te kalsın.
- (c) Gündem siyaseti tutsun, ama Reels'te siyaset kartı gündem kotasından düşmesin.

**Test fikri:** "Trump, Xi ve Putin Shenzhen'de buluştu" kümesi (b) seçeneğinde yalnız `siyaset` alır; "TBMM'de bütçe görüşmesi" ise `gundem` + `siyaset` alır.

**Karar gerekir mi:** Evet (a/b/c).

---

## 7. Yanlış birleşmiş kümeler
**Önem:** Düşük-orta. Haber sayısına göre en büyük 7 küme elle incelendi (`58ff7191e0`, `f54433ce2d`, `aed8587f5a`, `249215a33f`, `ea7669b984`, `742c6d74c1`, `9fd33252b0`). **3'ünde başka olay karışmış:**
- `742c6d74c1`: Tchouaméni'nin sözleşmesi ile Arda Güler'in sözleşmesi aynı kümede. İkisi de "Real Madrid, 2032" haberi ama farklı olaylar.
- `ea7669b984`: Bulgaristan'dan 2 firarinin iadesi kümesine "Bakan Gürlek: 6 firari getirildi" haberi girmiş.
- `58ff7191e0`: Sağlık Bakanlığı personel alımı kümesine "TCDD işçi alımı kura sonuçları" girmiş.
- Ayrıca `f54433ce2d` "son depremler listesi" farklı illerin SEO sayfalarını (Malatya, Edirne, Muğla, Van) tek kümede topluyor. Bu küme Reels'ten zaten elendiği için zararı az.

Kümeleme genelde bölünmeye eğilimli; birleşme hataları az ve küçük. Bu nedenle 1'deki gevşetme yapılırken aşağıdaki test şart.

**Öneri:** Aynı kurum ve aynı sayı (2032) ortaklığı tek başına birleşme nedeni olmasın. Birleşmek için başlıktaki kişi adlarının da örtüşmesi gereksin.

**Test fikri:** "Real Madrid, Tchouaméni'nin sözleşmesini 2032'ye uzattı" ve "Real Madrid, Arda Güler'in sözleşmesini 2032'ye uzattı" iki ayrı küme olmalı.

**Karar gerekir mi:** Hayır.

---

## 8. ELE ve CEZA kalıplarındaki boşluklar
**Önem:** Düşük. **Yer:** `akis2.py:216-239`.

- #28 `d5de3d1fe1` "e-Devlet Çöktü mü, Neden Açılmıyor? 19 Kasım 2026…" bir SEO sayfası, ama elenmedi. `soru/SEO` kalıbında yalnız `neden yok\??` var; `çöktü mü` ve `neden açılmıyor` yok.
- #41 `d7b7d9948c` "Kocasını ağzına böcek ilacı sıkarak öldürdü" özel kişi trajedisi, ama `ozel kisi trajedisi` kalıbı yalnız kadın cinayetini kapsıyor.
- #39 `2ca0ddebc4` "Hazırlıklarımız Devam Ediyor 💪 | 17 Kasım" bir kulübün kendi YouTube videosu. Rutin içerik, CEZA almıyor.
- #51 `f45c124a74` "Kura çekimi ne zaman?" eleme kalıbına girmiyor (soru eki tek başına).
- ELE'nin doğru elemediği güçlü haber bulunmadı. 54 "soru/SEO" elemesinin her birine bakılmadı (**doğrulanmadı**).

**Öneri:**
- `soru/SEO` kalıbına `çöktü mü|neden açılmıyor|ne zaman\?$` ekle.
- `ozel kisi trajedisi` kalıbına `(kocasını|eşini|annesini|babasını) .{0,30}öldürdü` ekle.
- Kulübün kendi kanalından gelen "hazırlık/antrenman" videolarına CEZA ver.

**Test fikri:** `test_yeni_elemeler` testine bu üç başlık eklensin: ilk ikisi elenmeli, üçüncüsü ceza almalı.

**Karar gerekir mi:** Hayır.

---

## Kaçırılmış güçlü konular (bu tur)
| Küme | Konu | Neden kaçtı |
|---|---|---|
| `d6f9671e1d` | KIZILELMA envantere girdi (8 kaynak, 62,1) | Yanlış tekrar sayıldı (2) |
| `07cee2d32e` | 20. yıl iPhone'u için iki tasarım (9 kaynak) | Yanlış tekrar (2) |
| `aed8587f5a` | Antalya ve Tekirdağ AKP'ye geçti (12 kaynak) | Yanlış tekrar (2) |
| `e3c22ce9f8` | CHP kurultay davasında karar | Yanlış tekrar (2) |
| `249215a33f` | Yeni James Bond, Bezos (13 kaynak) | Yanlış tekrar (2) |
| `127c2696b1` | Google'ın yeni modeli | Yanlış tekrar (2) |
| `742c6d74c1` | Arda Güler ve Real Madrid | Alan hatası, profil dolu (4, 5) |
| `9fd33252b0` | HONOR Türkiye'de üretim (11 kaynak) | Eşik altında, 40,5 (4) |
| `8806f6d90a` | iOS 27.3, iPhone Duo'ya yüz tanıma (13 kaynak) | Rutin ceza, 47,1 |
| `7ccebef96b`, `f53f56544e`, `209d2be974` | OpenAI modelleri, Instagram Direct TR, PlayStation soruşturması | Profil dolu (4) |

## Ölçülmeyenler (doğrulanmadı)
- Tek bir turun verisine bakıldı; başka saatlerde oranlar farklı olabilir.
- Önerilen kuralların kümeleme sonucuna etkisi simüle edilmedi. Yalnız 3'teki içerik kapısının Reels listesine etkisi ölçüldü.
- Adana, eğlence ve ekonomi alanlarından rastgele örnek alınmadı.
- Kümelerin bölünme oranı yalnız 16 seçilmiş olay ve en çok kaynaklı 40 kümenin aday taramasıyla ölçüldü; bütün kümeler için bir oran çıkarılmadı.
- `masa.py` çıktısı (TechTurco paneli) bu denetimde incelenmedi. Önerilerin hiçbiri `masa.py` değişikliği gerektirmiyor; `masa.birlestir` ve `masa.varlik` ortak kullanıldığı için düzeltmeler `akis2.py` içinde ayrı yardımcı fonksiyonla yapılmalı.

## Karar listesi (sahibine)
1. Siyaset ve spor rutin haberlerine Reels cezası verilsin mi? (3)
2. Yalnız yabancı kaynaklı ürün sızıntıları öne çıkmaya devam etsin mi? Galaxy Buds kartı 1. sırada. (3)
3. Profil başına 30 ve toplam 90 kart sınırı korunsun mu? (4)
4. Gündem/Siyaset çakışması: a) koru, b) Gündem yalnız Türkiye siyasetini alsın, c) Reels kotasında ayır. (6)
