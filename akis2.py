#!/usr/bin/env python3
"""Akış 2.0 veri üreticisi. site/feeds.json + sources.json + site/kaynak-durum.json -> site/data/*.json

Eski çıktılar (site/masa.json, site/index.html içindeki id="snap") masa.py/build.py ile aynen üretilmeye devam eder;
TechTurco paneli onları okur. Bu betik yalnız yeni arayüzün parçalı verisini üretir:

  data/ozet.json       ana ekran: sıcak konular (1s/6s/24s), yükselen konular, son gelişmeler, sayılar, yöntem notları
  data/kume-<alan>.json çalışma alanı başına konu kümeleri (tembel yüklenir)
  data/reels.json      Reels Fikir Radarı adayları (v2 puanlama)
  data/kaynaklar.json  Kaynak Yönetim Merkezi
  data/indeks.json     arama dizini (ilk aramada yüklenir)

Kümeleme ve puanlama açık kuraldır, yapay zekâ değildir; her puanın dökümü çıktıda durur."""
import json, re, math, hashlib, os, sys, urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ekler as E  # Akış 3: Google Trends ve Güncelleme Radarı
import masa as M   # sozcuk/kok yardımcıları ve STOP listesi eski hattan alınır

SAAT = 168                     # kümelemeye giren haber yaşı (saat)
CIKTI = 'site/data'
ALANLAR = ['gundem', 'adana', 'tekno', 'yz', 'siyaset', 'spor', 'ekonomi', 'bilim', 'siber', 'savunma', 'oto', 'oyun', 'eglence']
ALAN_AD = {'gundem': 'Gündem Radarı', 'adana': 'Adana', 'tekno': 'Teknoloji Radarı', 'siyaset': 'Siyaset ve Jeopolitik', 'spor': 'Spor', 'ekonomi': 'Ekonomi ve Finans',
           'bilim': 'Bilim ve Uzay', 'siber': 'Siber Güvenlik', 'oto': 'Otomobil ve Ulaşım', 'eglence': 'Kültür ve Eğlence',
           'yz': 'Yapay Zekâ', 'oyun': 'Oyun', 'savunma': 'Savunma Sanayi'}
KUME_ALAN_SINIR = 360          # alan başına dosyaya yazılan küme sayısı
# Türkçe/İngilizce dışındaki diller çoğunlukla tek kaynaklı kalır ve önem sıralamasında 360'ın altına düşer;
# her alan dosyasında her dile ayrıca bu kadar yer ayrılır (Akış'taki dil süzgeci boş kalmasın).
DIL_AYRILAN = 6            # 2026-11-20: 12'den indirildi (kume-tekno/gundem 1100 KB sınırına yaklaşıyordu)
DIL_DOSYA_SINIR = 150          # dil-XX.json başına küme
DIL_AD = {'tr': ('Türkçe', 'Türkçe'), 'en': ('English', 'İngilizce'), 'zh': ('中文', 'Çince'), 'ja': ('日本語', 'Japonca'),
          'ko': ('한국어', 'Korece'), 'de': ('Deutsch', 'Almanca'), 'fr': ('Français', 'Fransızca'), 'es': ('Español', 'İspanyolca'),
          'it': ('Italiano', 'İtalyanca'), 'ru': ('Русский', 'Rusça'), 'uk': ('Українська', 'Ukraynaca'), 'pt': ('Português', 'Portekizce'),
          'ar': ('العربية', 'Arapça'), 'hi': ('हिन्दी', 'Hintçe'), 'vi': ('Tiếng Việt', 'Vietnamca'), 'id': ('Bahasa Indonesia', 'Endonezce'),
          'pl': ('Polski', 'Lehçe'), 'nl': ('Nederlands', 'Felemenkçe'), 'ro': ('Română', 'Rumence'),
          'he': ('עברית', 'İbranice'), 'el': ('Ελληνικά', 'Yunanca'), 'fa': ('فارسی', 'Farsça')}

# ------------------------------------------------------------------ kimlik / URL
IZ_PARAM = re.compile(r'^(utm_|fbclid|gclid|mc_|ref$|ref_|source$|cmpid|ocid|at_|igshid|spm|share)', re.I)
def kanonik(url):
    """Aynı sayfanın izleme parametreli, amp'li, www'li biçimlerini tek adrese indirir."""
    try:
        u = urllib.parse.urlsplit(url.strip())
        host = u.netloc.lower()
        host = re.sub(r'^(www\d?|m|amp|mobile)\.', '', host)
        yol = re.sub(r'/(amp|amp/)$', '', u.path).rstrip('/') or '/'
        yol = re.sub(r'\.amp(\.html)?$', '', yol)
        q = [(k, v) for k, v in urllib.parse.parse_qsl(u.query) if not IZ_PARAM.match(k)]
        if 'news.google.com' in host: return url            # yönlendirme adresi: olduğu gibi
        return urllib.parse.urlunsplit(('https', host, yol, urllib.parse.urlencode(sorted(q)), ''))
    except Exception:
        return url

ORG_ALIAS = [  # (desen, kurum) — aynı kuruluşun farklı bölüm akışları / yazımları tek kurum sayılır
    (r'anadolu (ajans|agency)|^aa$|\baa\b', 'aa'), (r'^trt|trt ', 'trt'), (r'^ntv|ntv ', 'ntv'), (r'\bh[üu]rriyet\b(?! ?(i|haber))', 'hurriyet'), (r'milliyet', 'milliyet'),
    (r'\bsabah\b|^a ?haber$|^a haber\b|^ahaber|^atv\b', 'sabah'), (r'sözcü|sozcu', 'sozcu'), (r'habertürk|haberturk', 'haberturk'), (r'cnn ?türk|cnnturk', 'cnnturk'),
    (r'bbc', 'bbc'), (r'\bdw\b|deutsche welle', 'dw'), (r'france ?24', 'france24'), (r'al ?jazeera|aljazeera', 'aljazeera'),
    (r'guardian', 'guardian'), (r'new york times|nytimes|^nyt', 'nyt'), (r'washington post|wapo', 'wapo'), (r'reuters', 'reuters'),
    (r'associated press|^ap$|ap news', 'ap'), (r'\bafp\b|agence france', 'afp'), (r'bloomberg', 'bloomberg'), (r'cnbc(?!-?e\b)', 'cnbc'),
    (r'euronews', 'euronews'), (r'^(the )?independent\b', 'independent'), (r'daily sabah', 'dailysabah'), (r'9to5mac|9to5google', '9to5'),
    (r'ars technica|arstechnica|ars$', 'ars'), (r'the verge|theverge|^verge', 'verge'), (r'google', 'googlehaber'), (r'youtube|^yt-', 'youtube'),
    (r'fanatik|^a ?spor\b', 'sabah'),
]
ORG_RX = [(re.compile(a, re.I), b) for a, b in ORG_ALIAS]
AJANS_ISARET = re.compile(r'\((aa|dha|iha|ihlas|anka|reuters|afp|ap|apa|epa)\)|^(aa|dha|iha|reuters|afp|ap)\b|\b(reuters|afp|associated press)\b.{0,12}(reported|dedi|aktardı)', re.I)
AJANS_KURUM = {'aa', 'reuters', 'ap', 'afp', 'dha', 'iha', 'anka', 'xinhua', 'tass', 'yonhap'}
def kurum(p, sid):
    ad = re.sub(r'\.(com\.tr|com|net|org|info|tr|co\.uk|de|fr)$', '', (p or '').strip().lower().translate(M.TR))
    for rx, k in ORG_RX:
        if rx.search(ad): return k
    ham = ad.strip()
    ad = ad.translate(str.maketrans('çğıöşü', 'cgiosu'))
    ascii_ = re.sub(r'[^a-z0-9]+', '', ad)[:24]
    # Latin dışı yayıncı adı (Arapça, CJK…): kaynak kimliğine değil adın kendisine düş; yoksa bir akıştaki tüm yayıncılar tek kurum olurdu
    return ascii_ or re.sub(r'\s+', '', ham)[:24] or sid

# ------------------------------------------------------------------ çok dilli varlık sözlüğü
# Aynı varlığın dillerdeki yazımı tek jetona iner; farklı dildeki iki haber ancak ortak varlıklarla eşleşir.
CANON = {
 'rusya': r'rusya|russia|russland|russie|俄罗斯|俄国|روسيا|ロシア|러시아|россия', 'ukrayna': r'ukrayna|ukraine|ukraina|乌克兰|أوكرانيا|ウクライナ|우크라이나|украин',
 'abd': r'\babd\b|amerika|united states|\bu\.?s\.?\b|états-unis|vereinigte staaten|usa\b|美国|أمريكا|الولايات المتحدة|アメリカ|미국', 'cin': r'\bçin\b|çin\'|china|chine|中国|الصين|中国|중국',
 'iran': r'\biran|\bİran|إيران|イラン|이란|伊朗', 'israil': r'israil|israel|israël|以色列|إسرائيل|イスラエル|이스라엘', 'filistin': r'filistin|palestin|巴勒斯坦|فلسطين|パレスチナ|팔레스타인',
 'gazze': r'gazze|gaza|加沙|غزة|ガザ|가자', 'hamas': r'hamas|哈马斯|حماس', 'suriye': r'suriye|syria|syrie|syrien|叙利亚|سوريا|シリア|시리아',
 'turkiye': r'türkiye|turkey|türkei|turquie|土耳其|تركيا|トルコ|튀르키예|터키', 'almanya': r'almanya|germany|deutschland|allemagne|德国|ألمانيا|ドイツ|독일',
 'fransa': r'fransa|france\b|frankreich|法国|فرنسا|フランス|프랑스', 'ingiltere': r'ingiltere|britain|\buk\b|united kingdom|großbritannien|royaume-uni|英国|بريطانيا|イギリス|영국',
 'japonya': r'japonya|japan|japon\b|日本|اليابان|일본', 'hindistan': r'hindistan|india|inde\b|indien|印度|الهند|インド|인도',
 'trump': r'trump|特朗普|ترامب|トランプ|트럼프', 'biden': r'biden|拜登|بايدن', 'putin': r'putin|普京|بوتين|プーチン|푸틴', 'zelenski': r'zelen[sc]k|泽连斯基|زيلينسكي',
 'erdogan': r'erdoğan|erdogan|埃尔多安|أردوغان', 'netanyahu': r'netanyahu|内塔尼亚胡|نتنياهو', 'macron': r'macron|马克龙|ماكرون', 'xi': r'şi cinping|xi jinping|习近平|شي جين',
 'nato': r'\bnato\b|北约|الناتو', 'bm': r'\bbm\b|birleşmiş milletler|united nations|\bun\b|nations unies|联合国|الأمم المتحدة|国連', 'ab': r'avrupa birliği|european union|\beu\b|\bab\b|union européenne|欧盟|الاتحاد الأوروبي',
 'apple': r'\bapple\b|iphone|ipad|macbook|苹果|أبل|アップル', 'samsung': r'samsung|galaxy|三星|سامسونج|サムスン|삼성', 'google': r'\bgoogle\b|pixel|gemini|谷歌|جوجل|グーグル|구글',
 'microsoft': r'microsoft|windows|copilot|微软|مايكروسوفت', 'openai': r'openai|chatgpt|sam altman', 'anthropic': r'anthropic|\bclaude\b', 'meta': r'\bmeta\b|facebook|instagram|whatsapp',
 'nvidia': r'nvidia|英伟达|엔비디아', 'tesla': r'tesla|特斯拉|تسلا', 'musk': r'\bmusk\b|马斯克', 'spacex': r'spacex|starship', 'nasa': r'\bnasa\b',
 'xiaomi': r'xiaomi|小米', 'huawei': r'huawei|华为|هواوي', 'tiktok': r'tiktok|抖音', 'togg': r'\btogg\b', 'bitcoin': r'bitcoin|比特币|بيتكوين', 'altin': r'\baltın|\bgold price|goldpreis|黄金',
 'dolar': r'\bdolar|\bdollar\b|美元', 'faiz': r'faiz|interest rate|zinsen|taux d.intérêt|利率', 'fed': r'\bfed\b|federal reserve', 'tcmb': r'merkez bankası|tcmb|central bank of turkey',
 'galatasaray': r'galatasaray', 'fenerbahce': r'fenerbahçe|fenerbahce', 'besiktas': r'beşiktaş|besiktas', 'trabzonspor': r'trabzonspor', 'real': r'real madrid', 'barcelona': r'barcelona|barça',
 'f1': r'formula ?1|\bf1\b|一级方程式', 'nba': r'\bnba\b', 'uefa': r'\buefa\b|şampiyonlar ligi|champions league', 'fifa': r'\bfifa\b|dünya kupası|world cup',
 'deprem': r'deprem|earthquake|erdbeben|séisme|地震|زلزال|地震', 'sel': r'\bsel\b|flood|hochwasser|inondation|洪水|فيضان',
}
CANON_RX = [(k, re.compile(v, re.I)) for k, v in CANON.items()]
LIDER = {'trump', 'biden', 'putin', 'zelenski', 'erdogan', 'netanyahu', 'macron', 'xi'}
ULKE = {'rusya', 'ukrayna', 'abd', 'cin', 'iran', 'israil', 'filistin', 'suriye', 'turkiye', 'almanya', 'fransa', 'ingiltere', 'japonya', 'hindistan'}
MARKA = {'apple', 'samsung', 'google', 'microsoft', 'openai', 'anthropic', 'meta', 'nvidia', 'tesla', 'xiaomi', 'huawei', 'tiktok', 'togg', 'spacex'}
def canon_bul(t):
    return {k for k, rx in CANON_RX if rx.search(t)}

def sayilar(t):
    """Başlıktaki anlamlı sayılar (5,7 -> 5.7; tek haneli tam sayılar yok). Farklı dillerdeki aynı olayı ayırt eder."""
    out = set()
    for m in re.findall(r'\d+(?:[.,]\d+)?', t):
        m = m.replace(',', '.')
        if '.' in m or len(m) >= 2: out.add('n:' + m)
    return out

def tok2(t):
    """Latin sözcükleri kökleştirir; Arapça sözcükleri ve CJK karakter ikililerini ekler (Türkçe tokenizer bunları görmez)."""
    s = {M.kok(w) for w in M.sozcuk(t) if not w[0].isdigit() or len(w) > 1}
    s |= sayilar(t)
    for w in re.findall(r'[؀-ۿ]{3,}', t): s.add('ar:' + w)
    for run in re.findall(r'[぀-ヿ㐀-鿿가-힯]{2,}', t):
        for i in range(len(run) - 1): s.add('cj:' + run[i:i + 2])
    return s

# ------------------------------------------------------------------ çalışma alanı kuralları
KURAL = {
 # Adana: il adı, ilçeler (başka anlamı olan Seyhan/Ceyhan/Kozan/İmamoğlu/Aladağ/Feke yalnız "Adana" ile birlikte sayılır), kurum ve kulüpler
 'adana': re.compile(r"\badana|yüreğir|sarıçam|karaisalı|pozantı|yumurtalık|tufanbeyli|saimbeyli|incirlik|seyhan barajı|çukurova üniversitesi|adana demirspor|adanaspor|\bçukurova(da|'da|’da)?\b", re.I),
 # Başka anlamı da olan ilçe adları: yalnız Adana kaynaklı haberde sayılır. İmamoğlu yalnız yer ekiyle (İmamoğlu'nda) ilçe sayılır.
 'adana_ilce': re.compile(r"\b(seyhan|ceyhan|kozan|karataş|feke|aladağ|çukurova)\b|imamoğlu['’]n(da|dan)\b|İmamoğlu['’]n(da|dan)\b|imamoğlu ilçe", re.I),
 'siyaset': re.compile(r"erdoğan|cumhurbaşkan|chp\b|akp\b|mhp\b|dem parti|tbmm|meclis|seçim|siyasi|muhalefet|iktidar|özgür özel|bahçeli|yaptırım|diplomasi|diplomat|zirve|büyükelçi|dışişleri|nato\b|birleşmiş milletler|güvenlik konseyi|trump|biden|harris|putin|zelen|netanyahu|macron|şi cinping|xi jinping|kongre|senato|beyaz saray|kremlin|brüksel|avrupa birliği|\bab\b|israil|filistin|gazze|hamas|hizbullah|\biran(?!\w)|\biran(lı|ian)|\biran['’]|suriye|ukrayna|rusya|tayvan|savunma bakan|savunma sanayi|election|parliament|sanction|diplomat|summit|ambassador|president|prime minister|congress|senate|white house|kremlin|nato\b|united nations|security council|ceasefire|ateşkes|treaty|referendum|coalition|opposition party|defen[cs]e minister|sanctions", re.I),
 'savas': re.compile(r"savaş|çatışma|saldırı|füze|hava saldırısı|ateşkes|asker|ordu\b|cephe|işgal|bombardıman|silahlı|terör|drone saldırı|war\b|attack|missile|airstrike|strike|troops|frontline|invasion|military|ceasefire|offensive|bombing|terror", re.I),
 'siber': re.compile(r"siber(?!ia)|güvenlik açığ|sızıntı|veri ihlali|fidye|ransomware|zero-?day|malware|zararlı yazılım|oltalama|phishing|hacker|hack\b|saldırgan|cve-\d|vulnerab|data breach|botnet|exploit|backdoor|apt\d|cyberattack|cyber attack|ddos|kimlik avı|dolandırıcı", re.I),
 'spor_guclu': re.compile(r"maç|gol\b|futbol|basketbol|voleybol|süper lig|şampiyonlar ligi|teknik direktör|hakem|transfer|milli takım|\bnba\b|euroleague|uefa|fifa|olimpiyat|formula ?1|\bf1\b|motogp|tenis|wimbledon|grand slam|\batp\b|\bwta\b|ufc|boks|güreş|espor|e-spor|premier league|la liga|serie a|bundesliga|champions league|football|soccer|basketball|volleyball|tennis|coach|goal\b|stadium|tournament|athlete|olympic|grand prix|galatasaray|fenerbahçe|beşiktaş|trabzonspor|başakşehir|real madrid|barcelona|atletico|manchester (united|city)|liverpool|bayern|juventus|inter milan|\binter['’](in|e|i)\b|ac milan|\bpsg\b|arsenal|chelsea|tottenham|sözleşmesini uzattı|futbolcu|kaleci|forvet|stoper", re.I),
 'ekonomi_guclu': re.compile(r"dolar|euro\b(?!\s?(20\d\d|cup|kupa|league|lig|elemeler))|altın(?!\s?(madalya|top\b|gol|eldiven|krampon|küre|kelebek|portakal|yaş|kız|çocuk))|borsa|bist|enflasyon|faiz|merkez bankası|ekonomi|asgari ücret|emekli maaş|vergi|ihracat|ithalat|bütçe|petrol|akaryakıt|benzin|motorin|konut|kira artış|bitcoin|kripto|\bfed\b|inflation|interest rate|stocks?\b|wall street|gdp|tariff|oil price|currency|ticaret|piyasa|cari açık|işsizlik|unemployment|central bank|recession|ipo\b|nasdaq|s&p", re.I),
 'bilim_guclu': re.compile(r"nasa\b|uzay|gezegen|astronom|teleskop|asteroid|fosil|keşfetti|araştırmacılar|bilim insanları|genetik|\bdna\b|kanser tedavi|iklim değişikliği|kuantum|fizik|evren|mars\b|ay'a|space station|scientists|researchers|study finds|astronomers|physics|biology|quantum|exoplanet|(?<!samsung )galax(y|ies)(?!\s?([szamf]\d|z (fold|flip)|tab|buds|watch|fold|flip|ring|book|ai\b|xr\b|unpacked|store|phone|series|ultra|edge|\d))|black hole|climate|vaccine|clinical trial|peer-reviewed", re.I),
 'oto_guclu': re.compile(r"otomobil|araba\b|otomotiv|elektrikli (araç|otomobil|araba|suv)|togg|tesla|bmw|mercedes|audi|volkswagen|porsche|ferrari|ford\b|fiat|renault|hyundai|toyota|byd\b|şarj istasyon|sürücüsüz|otonom|suv\b|sedan|electric vehicle|\bevs\b|\bev (charging|charger|battery|sales|maker|market|startup|range|tax|subsid)|self-driving|autonomous|car maker|automaker|recall|lamborghini|mclaren|yeni model|raylı sistem|metro hattı|hızlı tren|havalimanı|thy\b|pegasus|ulaşım|trafik|köprü|otoyol|airline|flight", re.I),
 'tekno_guclu': re.compile(r"iphone|ipad|macbook|android|samsung|galaxy|xiaomi|huawei|google|pixel|microsoft|windows|openai|chatgpt|claude|gemini|anthropic|yapay zek|artificial intelligence|\bai\b|işlemci|ekran kart|nvidia|intel\b|amd\b|qualcomm|snapdragon|telefon|akıllı|bilgisayar|laptop|yazılım|uygulama|siber(?!ia)|robot|drone|oyun|playstation|xbox|steam|nintendo|teknoloji|whatsapp|instagram|tiktok|youtube|netflix|starlink|spacex|çip|yarı iletken|chip|startup|giyilebilir|akıllı saat|kulaklık|tablet|5g|bulut|veri merkezi|ios \d|one ui|oneplus|motorola|\boppo\b|realme|\bhonor\b|smartphone|akıllı telefon", re.I),
 # Yapay zekâ ve oyun 2026-11-18'de ayrı alan oldu (Teknoloji ve Eğlence içindeki en kalabalık iki konu); oyun artık Eğlence'ye girmez.
 'yz_guclu': re.compile(r"yapay zek|chatgpt|openai|claude|anthropic|gemini|grok\b|deepseek|\bllm|büyük dil model|language model|\bai\b|artificial intelligence|midjourney|\bsora\b|copilot|mistral|perplexity|\bgpt-?\d|\bagi\b|chatbot|sohbet robotu|deepfake|künstliche intelligenz|intelligence artificielle|inteligencia artificial|人工智能|生成式|人工知能|인공지능", re.I),
 'oyun_guclu': re.compile(r"playstation|\bps5\b|\bps6\b|xbox|nintendo|switch 2|\bsteam\b|\bgta\b|video ?game|videogame|gaming|oyun (dünyası|severler|sektörü|stüdyosu|konsolu)|bilgisayar oyunu|mobil oyun|oyunu\b|oyunun\b|game awards|game pass|epic games|ubisoft|rockstar|bethesda|blizzard|riot games|valorant|fortnite|minecraft|call of duty|battlefield|zelda|pokemon|pokémon|elden ring|\bdlc\b|game (studio|developer|update|trailer|release|director)|games? (industry|studio)|(new|upcoming|indie|mobile|pc|console) games?\b|\bgamers?\b", re.I),
 'eglence_guclu': re.compile(r"dizi|film|sinema|oyuncu|şarkıcı|ünlü|konser|albüm|festival|oscar|gişe|fragman|yönetmen|survivor|masterchef|sanatçı|netflix dizisi|trailer|box office|movie|series|actor|singer|album|anime|hollywood|billboard|grammy|emmy|viral|fenomen|tiktok", re.I),
 # Savunma sanayi (2026-11-20). İki katman: ÖZEL (şirket, ürün, program, "savunma sanayi") tek başına yeter;
 # GENEL (füze, savaş uçağı, denizaltı…) en az iki terim ya da savunma kaynağı ister. "savunma" kelimesi tek başına
 # (futbolda savunma, sanığın savunması) sayılmaz; yalnız sanayi/bakanlık/sistem bağlamında.
 'savunma_guclu': re.compile(r"savunma sanayi|savunma (bakan|sistem|teknoloji|şirket|firma|ihracat|proje|harcama|bütçe|tedarik|fuar|sektör|ürün|dev[iı]|alanında|işbirliği|anlaşma|platform|araştırma)|(hava|füze|milli|ulusal|çok katmanlı) savunma|savunma ve havacılık|(?<!tonluk )çelik kubbe(?!.{0,40}(vinç|cami))|(?-i:\bSSB\b)|savunma sanayii başkan|haluk görgün|aselsan|roketsan|tusaş|havelsan|\bmkek?\b|\bfnss\b|otokar (cobra|arma|altay|tulpar|kaya|savunma|zırhlı)|nurol (makina|ejder|yörük)|\bstm (savunma|kargu|togan)|baykar|bayraktar (tb\d|akıncı|kızılelma|kizilelma)|selçuk bayraktar|akıncı (tiha|siha|iha)|kızılelma|kizilelma|(?-i:\bKAAN\b)|kaan (savaş|uçağı|milli|projesi|motor)|milli muharip uçak|hürjet|hurjet|\banka-?3\b|\bgökbey\b|altay tank|(?-i:\bTCG [A-ZÇĞİÖŞÜ])|anadolu (gemisi|sınıfı)|milgem|\bhisar-?[ao]\b|\bsiper\b (füze|hava|sistem)|korkut (hava|sistem|namlu)|\btayfun (füze|blok)|atmaca (füze|seyir|gemisavar)|\bçakır füze|defen[cs]e (industry|industr|contractor|firm|company|companies|ministry|minister|budget|spending|procurement|deal|export|sector|tech|startup)|defen[cs]e and aerospace|aerospace and defen[cs]e|lockheed|raytheon|\brtx (corp|corporation)|northrop|general dynamics|bae systems|rheinmetall|saab (gripen|globaleye|defen|ab\b)|gripen|dassault|\brafale\b|eurofighter|\bthales\b|\bmbda\b|\bkongsberg\b|\banduril\b|palantir.{0,40}(army|pentagon|military|defen)|loyal wingman", re.I),
 # platform adları (İHA, F-35, Patriot…): savaş/saldırı haberinde de geçer; saldırı dili varsa tek başına savunma açmaz
 'savunma_platform': re.compile(r"(?-i:\bS?İHA(lar|ların|ları|sı|'lar|'ların|'sı)?\b)|\bsiha(lar|sı)?\b|silahlı insansız|insansız (hava|deniz|kara|savaş) (aracı|uçağı|botu)|\bf-?(16|35|47)\b|\bb-21\b|\buav\b|\bucav\b|\bhimars\b|\bpatriot (missile|system|battery|air)|iron dome|\bthaad\b|s-400", re.I),
 'savunma_genel': re.compile(r"füze(si|ler|leri)?\b|balistik|seyir füzesi|hava savunma|savaş uçağı|savaş uçakları|savaş gemisi|fırkateyn|korvet|denizaltı|muharip|mühimmat|zırhlı (araç|personel)|obüs|tank(ı|lar|ları)?\b|savaş helikopteri|taarruz helikopteri|donanma|hava kuvvetleri|kara kuvvetleri|deniz kuvvetleri|tatbikat|missiles?\b|ballistic|air defen[cs]e|fighter (jet|aircraft)s?|warships?|frigate|corvette|submarine|munitions?|ammunition|artillery|armou?red vehicle|\btanks?\b|navy|air force|\barmy\b|military (contract|procurement|aircraft|drone)|pentagon|nato (tedarik|procurement|summit|exercise|tatbikat)|military exercise|drills?\b|hypersonic|hipersonik", re.I),
 'savunma_saldiri': re.compile(r"saldırı|saldırdı|vurdu|bombard|hayatını kaybetti|öldü|yaralandı|\bstrikes?\b|airstrike|attack|killed|dead\b|wounded|shot down|düşürüldü", re.I),
 'gundem_guclu': re.compile(r"cinayet|gözaltı|tutuklandı|soruşturma|dava\b|mahkeme|savcılık|yargıtay|anayasa mahkemesi|hapis|ceza\b|belediye|valilik|yangın|sel\b|deprem|afet|kaza\b|yaralandı|hayatını kaybetti|okul|üniversite|sınav|yks|meb\b|öğrenci|hastane|sağlık bakan|salgın|aşı\b|ilaç|grip|zam\b|maaş|emekli|asgari ücret", re.I),
}
RE_HUKUK = re.compile(r"mahkeme|dava\b|savcı|yargıtay|anayasa mahkemesi|hakim|hâkim|tutuklan|beraat|iddianame|court|judge|lawsuit|indict|trial|verdict|sentenc", re.I)
RE_AFET = re.compile(r"deprem|sel\b|yangın|orman yangını|fırtına|hortum|çığ|heyelan|afet|afad|earthquake|flood|wildfire|storm|hurricane|tornado|landslide|tsunami|eruption|volkan", re.I)
RE_SAGLIK = re.compile(r"sağlık|hastane|salgın|aşı\b|ilaç|grip|kanser|tedavi|doktor|virüs|health|hospital|outbreak|vaccine|disease|cancer|virus|who\b", re.I)
RE_EGITIM = re.compile(r"okul|üniversite|sınav|yks|lgs|meb\b|öğrenci|öğretmen|eğitim|karne|school|university|exam|student|teacher|education", re.I)
RE_TOPLUM = re.compile(r"toplum|kadın|çocuk|göç|mülteci|yoksulluk|işsiz|emekli|asgari ücret|kira|barınma|şiddet|eşitlik|protesto|grev|society|migrant|refugee|poverty|protest|strike|housing", re.I)
ALT = {
 'adana': [('seyhan', r'\bseyhan\b'), ('cukurova', r'\bçukurova\b'), ('yuregir', r'yüreğir'), ('saricam', r'sarıçam'), ('ceyhan', r'\bceyhan\b'), ('kozan', r'\bkozan'),
           ('imamoglu', r"imamoğlu['’]n(da|dan)\b|İmamoğlu['’]n(da|dan)\b|imamoğlu ilçe"), ('karatas', r'karataş'), ('karaisali', r'karaisalı'), ('pozanti', r'pozantı'), ('yumurtalik', r'yumurtalık'),
           ('kuzey-ilceler', r'tufanbeyli|saimbeyli|\bfeke\b|\baladağ'),
           ('asayis', r'gözaltı|tutukla|kaza(sı|da|ya)?\b|yaralan|hayatını kaybet|\böldü|cinayet|operasyon|yangın|bıçak|silahlı|saldır|jandarma|\bpolis|emniyet|uyuşturucu|hırsız|dolandırıc'),
           ('belediye', r'belediye|büyükşehir|muhtar|kaymakam|\bvali(lik)?\b|asfalt|altyapı|\bpark(ı|ı|lar)?\b|otogar|toplu taşıma|\bmetro'),
           ('ekonomi-adana', r'pamuk|narenciye|mandalina|portakal|çiftçi|üretici|hasat|tarım|\bosb\b|aosb|organize sanayi|fabrika|ihracat|yatırım'),
           ('spor-adana', r'adanaspor|demirspor|futbol|\bmaç|\bgol\b|turnuva|basketbol|voleybol|\blig\b')],
 'tekno': [('apple', r'iphone|ipad|macbook|\bmac\b|ios \d|apple|airpods|vision pro|watchos'), ('samsung', r'samsung|galaxy|one ?ui|exynos'), ('android', r'android|pixel|xiaomi|redmi|huawei|honor|oneplus|oppo|realme|motorola|nothing phone|snapdragon'),
          ('google', r'\bgoogle\b|gemini|chrome|youtube|deepmind|waymo'), ('microsoft', r'microsoft|windows|copilot|xbox|azure|surface'), ('yz', r'yapay zek|chatgpt|openai|claude|anthropic|gemini|grok|deepseek|llm|\bai\b|artificial intelligence|midjourney|sora|copilot|mistral|perplexity'),
          ('telefon', r'telefon|smartphone|iphone|galaxy|pixel|katlanabilir|foldable'), ('bilgisayar', r'bilgisayar|laptop|macbook|notebook|\bpc\b|masaüstü|monitör'), ('cip', r'işlemci|yarı iletken|\bçip|chip|nvidia|\bamd\b|intel\b|qualcomm|tsmc|gpu|rtx|ryzen|snapdragon|dimensity'),
          ('siber', r'siber|güvenlik açığ|hack|ransomware|veri ihlali|malware|phishing'), ('sosyal', r'instagram|whatsapp|tiktok|x\.com|twitter|facebook|threads|snapchat|telegram|reddit|bluesky|sosyal medya|youtube'), ('uygulama', r'uygulama|\bapp\b|play store|app store|güncelleme|özellik|feature'),
          ('yazilim', r'yazılım|software|windows|macos|işletim sistemi'), ('oyun', r'oyun|playstation|xbox|nintendo|steam|gta|game|gaming|epic games'), ('oto-tekno', r'otonom|sürücüsüz|tesla|togg|elektrikli|autopilot|self-driving'),
          ('robotik', r'robot|insansı|humanoid|drone|boston dynamics|optimus'), ('giyilebilir', r'akıllı saat|giyilebilir|apple watch|galaxy watch|akıllı bileklik|smartwatch|wearable|airpods|kulaklık|smart ring'), ('ev', r'elektrikli araç|elektrikli otomobil|\bevs\b|\bev (charging|charger|battery|sales|maker|market|startup|range|tax|subsid)|şarj|batarya|battery')],
 'siyaset': [('tr-siyaset', r'erdoğan|chp\b|akp\b|mhp\b|dem parti|tbmm|meclis|özgür özel|bahçeli|belediye başkan|ekrem imamoğlu|türkiye siyaset|turkish politics'), ('abd', r'\babd\b|amerika|trump|biden|harris|kongre|senato|beyaz saray|washington|\bu\.?s\.?\b|congress|white house'), ('avrupa', r'avrupa|\bab\b|brüksel|almanya|fransa|macron|scholz|merz|ingiltere|starmer|european|\beu\b|brussels|germany|france|britain'),
          ('cin', r'\bçin\b|şi cinping|pekin|tayvan|china|beijing|taiwan|xi jinping'), ('rusya', r'rusya|putin|kremlin|moskova|ukrayna|zelen|russia|moscow|ukraine'), ('orta-dogu', r'orta doğu|suriye|\birak\b|\birak[\x27’]|\biran(?!\w)|\biran(lı|ian)|\biran[\x27’]|lübnan|yemen|körfez|suudi|katar|middle east|syria|iraq|lebanon|yemen|saudi|gulf'),
          ('israil-filistin', r'israil|filistin|gazze|hamas|hizbullah|netanyahu|batı şeria|israel|palestin|gaza|hezbollah|west bank'), ('nato', r'\bnato\b'), ('bm', r'birleşmiş milletler|\bbm\b|güvenlik konseyi|united nations|security council|\bun\b'), ('secim', r'seçim|oy\b|sandık|anket|referandum|election|poll\b|ballot|referendum|vote'),
          ('kriz', r'kriz|gerilim|büyükelçi|sınır|ateşkes|müzakere|crisis|tension|ambassador|ceasefire|negotiat'), ('yaptirim', r'yaptırım|ambargo|sanction|embargo|tariff|gümrük'), ('savunma', r'savunma|silah|füze|f-?35|f-?16|tank|donanma|hava kuvvetleri|baykar|aselsan|defen[cs]e|missile|fighter jet|navy|weapon|military')],
 'spor': [('futbol', r'futbol|süper lig|şampiyonlar ligi|avrupa ligi|premier league|la liga|serie a|bundesliga|football|soccer|champions league|galatasaray|fenerbahçe|beşiktaş|trabzonspor|teknik direktör|hakem|maç\b|gol\b'), ('basketbol', r'basketbol|nba|euroleague|basketball|a milli basketbol|tbf'), ('tenis', r'tenis|tennis|wimbledon|roland garros|us open|australian open|\batp\b|\bwta\b'), ('f1', r'formula ?1|\bf1\b|grand prix|verstappen|hamilton|leclerc'),
         ('motor', r'motogp|motorsport|ralli|\bwrc\b|superbike|nascar|indycar|sofuoğlu|tuncer'), ('voleybol', r'voleybol|volleyball|filenin sultanları|vakıfbank|eczacıbaşı|tvf'), ('olimpiyat', r'olimpiyat|olympic|paralimpik|paralympic'), ('dovus', r'ufc|boks|boxing|güreş|wrestling|mma|judo|karate|taekwondo'),
         ('espor', r'espor|e-spor|esports?|league of legends|valorant|counter-strike|dota'), ('transfer', r'transfer|bonservis|sözleşme imzaladı|kiralık|loan deal|signs? (a )?(contract|deal)|here we go'), ('kulup', r'galatasaray|fenerbahçe|beşiktaş|trabzonspor|başakşehir|real madrid|barcelona|manchester|liverpool|bayern|juventus|psg|arsenal|chelsea'), ('milli', r'milli takım|a milli|national team|türkiye milli')],
 'ekonomi': [('doviz', r'dolar|euro\b(?!\s?(20\d\d|cup|kupa|league|lig|elemeler))|kur\b|döviz|dollar|currency|forex'), ('altin', r'altın(?!\s?(madalya|top\b|gol|eldiven|krampon|küre|kelebek|portakal))|gram altın|\bons\b|\bgold\b(?!\s?medal)'), ('borsa', r'borsa|bist|hisse|wall street|nasdaq|stocks?\b|s&p|dow jones'), ('enflasyon', r'enflasyon|tüfe|üfe|inflation|cpi\b'), ('faiz', r'faiz|merkez bankası|tcmb|\bfed\b|ecb|interest rate|central bank'), ('kripto', r'bitcoin|kripto|ethereum|crypto|btc\b|stablecoin'),
             ('enerji', r'petrol|akaryakıt|benzin|motorin|doğalgaz|elektrik zammı|brent|oil|gas price|opec|energy'), ('istihdam', r'asgari ücret|maaş|işsizlik|emekli|zam\b|istihdam|unemployment|wages|jobs report'), ('sirket', r'bilanço|kâr|zarar|şirket|ihale|satın alma|birleşme|earnings|merger|acquisition|revenue|ipo\b'), ('ticaret', r'ihracat|ithalat|ticaret|gümrük|tariff|trade war|export|import'), ('konut', r'konut|kira|tapu|mortgage|housing|rent')],
 'bilim': [('uzay', r'nasa|uzay|gezegen|astronom|teleskop|asteroid|mars\b|ay\b|spacex|esa\b|space|planet|(?<!samsung )galax(y|ies)(?!\s?([szamf]\d|z (fold|flip)|tab|buds|watch|fold|flip|ring|book|ai\b|xr\b|unpacked|store|phone|series|ultra|edge|\d))|exoplanet|rocket|artemis|iss\b'), ('saglik', r'sağlık|kanser|aşı|ilaç|tedavi|virüs|salgın|health|cancer|vaccine|drug|disease|clinical|medicine|who\b'), ('iklim', r'iklim|küresel ısınma|sera gazı|buzul|kuraklık|climate|warming|emission|glacier|drought'), ('fizik', r'fizik|kuantum|parçacık|cern|physics|quantum|particle'), ('biyoloji', r'biyoloji|genetik|\bdna\b|fosil|evrim|hayvan|bitki|biology|genetic|fossil|species|evolution'), ('yz-arastirma', r'yapay zek|makine öğren|nöral|machine learning|neural|deep learning|arxiv|llm')],
 'siber': [('acik', r'güvenlik açığ|cve-\d|zero-?day|vulnerab|exploit|patch|yama'), ('fidye', r'fidye|ransomware'), ('veri-ihlali', r'veri ihlali|sızıntı|sızdı|data breach|leak'), ('oltalama', r'oltalama|phishing|dolandırıcı|scam|kimlik avı|smishing'), ('devlet-aktoru', r'apt\d|devlet destekli|state-sponsored|nation-state|lazarus|sandworm|çin bağlantılı|rus bağlantılı'), ('zararli', r'malware|zararlı|trojan|botnet|backdoor|stealer|spyware|casus yazılım')],
 'oto': [('elektrikli', r'elektrikli|\bevs\b|\bev (charging|charger|battery|sales|maker|market|startup|range|tax|subsid)|şarj|batarya|tesla|byd|togg|electric'), ('marka', r'bmw|mercedes|audi|volkswagen|porsche|ferrari|ford\b|fiat|renault|hyundai|toyota|honda|volvo|skoda|lamborghini|mclaren|nissan'), ('otonom', r'otonom|sürücüsüz|autopilot|fsd|self-driving|robotaxi|waymo'), ('ulasim', r'havalimanı|hızlı tren|metro|köprü|otoyol|thy\b|pegasus|havayolu|airline|flight|railway|airport|ulaşım'), ('yeni-model', r'yeni model|tanıtıldı|unveil|launch|debut|concept|facelift'), ('motorsporu', r'formula ?1|\bf1\b|motogp|ralli')],
 'yz': [('sohbet', r'chatgpt|claude|gemini|grok|copilot|perplexity|deepseek|chatbot|sohbet robotu'), ('yz-sirket', r'openai|anthropic|google deepmind|deepmind|xai\b|meta ai|mistral|nvidia|microsoft'),
        ('model', r'\bgpt-?\d|model|llm|dil modeli|benchmark|reasoning'), ('gorsel-video', r'sora|midjourney|\bveo\b|görsel üret|video üret|image gen|video gen|deepfake|nano banana'),
        ('duzenleme', r'yasa|düzenleme|regulation|ai act|telif|copyright|lawsuit|dava|yasak|ban\b|privacy|gizlilik'), ('donanim-yz', r'nvidia|gpu|çip|chip|veri merkez|data center|tpu'),
        ('is-hayati', r'işsiz|işten çıkar|layoff|jobs?\b|istihdam|meslek|workers?'), ('ajan', r'\bagent|ajan|otonom asistan|browser agent')],
 'savunma': [('yerli', r"aselsan|roketsan|tusaş|havelsan|baykar|bayraktar|\bmkek?\b|\bfnss\b|otokar|nurol|\bstm\b|kızılelma|kizilelma|\bkaan\b|hürjet|hurjet|altay|\btcg\b|milgem|akıncı|\bsiha\b|hisar|siper|korkut|tayfun|atmaca|(?<!tonluk )çelik kubbe(?!.{0,40}(vinç|cami))|\bssb\b|savunma sanayii başkan|yerli|milli|türk savunma|turkish defen[cs]e|türkiye"),
              ('hava', r"savaş uçağı|kızılelma|kizilelma|\bkaan\b|hürjet|hurjet|\bf-?(16|35|47)\b|eurofighter|rafale|hava kuvvetleri|helikopter|fighter|aircraft|air force|\bb-21\b|tusaş"),
              ('deniz', r"\btcg\b|donanma|fırkateyn|korvet|denizaltı|savaş gemisi|milgem|anadolu gemisi|deniz kuvvetleri|navy|warship|frigate|corvette|submarine|naval"),
              ('kara', r"altay|tank|zırhlı|obüs|kara kuvvetleri|\barmy\b|armou?red|artillery|howitzer|himars"),
              ('fuze-hava-savunma', r"füze|balistik|hava savunma|(?<!tonluk )çelik kubbe(?!.{0,40}(vinç|cami))|hisar|siper|korkut|tayfun|missile|ballistic|air defen[cs]e|iron dome|patriot|thaad|s-400|hypersonic|hipersonik"),
              ('iha', r"\b[sİi]?iha\b|\bsiha|insansız|bayraktar|akıncı|kızılelma|kizilelma|anka|\buav\b|\bucav\b|\bdrones?\b|loyal wingman"),
              ('ihracat-anlasma', r"ihracat|ihraç|sözleşme|anlaşma|sipariş|satış|tedarik|ihale|teslim|export|contract|deal\b|order|procurement|deliver"),
              ('uluslararasi', r"lockheed|raytheon|\brtx (corp|corporation)|northrop|general dynamics|bae systems|rheinmetall|\bsaab\b|dassault|eurofighter|thales|mbda|anduril|pentagon|\bnato\b|\babd\b|amerika|\bu\.?s\.?\b|ukrayna|ukraine|rusya|russia|israil|israel|\bçin\b|china|avrupa|europe|yunanistan|greece|hindistan|india|pakistan|tayvan|taiwan|japonya|japan|kore|korea")],
 'oyun': [('konsol', r'playstation|ps5|ps6|xbox|nintendo|switch 2'), ('pc-oyun', r'\bsteam\b|\bpc\b|epic games|gpu|ekran kart'), ('mobil-oyun', r'mobil oyun|mobile game|ios oyun|android oyun'),
          ('gta', r'\bgta\b|grand theft auto|rockstar'), ('cikis', r'çıkış tarihi|release date|launch|ertelendi|delay|fragman|trailer|duyuruldu|announced'),
          ('ucretsiz', r'ücretsiz|bedava|free\b|game pass|ps plus|epic games store'), ('sektor', r'işten çıkar|layoff|stüdyo|studio|satın al|acquisition|ubisoft|microsoft gaming'), ('espor-oyun', r'espor|e-spor|esports?|turnuva')],
 'eglence': [('film-dizi', r'dizi|film|sinema|fragman|gişe|yönetmen|netflix|disney|hbo|prime video|trailer|box office|movie|series|streaming|oscar|emmy'), ('muzik', r'şarkıcı|albüm|konser|müzik|billboard|grammy|spotify|album|singer|concert|tour\b'), ('kultur', r'sergi|tiyatro|kitap|festival|müze|edebiyat|exhibition|theater|museum|book|festival'), ('internet', r'viral|fenomen|trend|tiktok|youtube|meme|influencer|streamer'), ('anime', r'anime|manga|crunchyroll')],
}
ALT_RX = {a: [(k, re.compile(v, re.I)) for k, v in L] for a, L in ALT.items()}
ALT_AD = {'seyhan': 'Seyhan', 'cukurova': 'Çukurova', 'yuregir': 'Yüreğir', 'saricam': 'Sarıçam', 'ceyhan': 'Ceyhan', 'kozan': 'Kozan', 'imamoglu': 'İmamoğlu', 'karatas': 'Karataş', 'karaisali': 'Karaisalı', 'pozanti': 'Pozantı', 'yumurtalik': 'Yumurtalık', 'kuzey-ilceler': 'Kuzey ilçeler', 'asayis': 'Asayiş', 'belediye': 'Belediye ve kent', 'ekonomi-adana': 'Tarım ve ekonomi', 'spor-adana': 'Spor',
          'apple': 'Apple', 'samsung': 'Samsung', 'android': 'Android', 'google': 'Google', 'microsoft': 'Microsoft', 'yz': 'Yapay zekâ', 'telefon': 'Telefon', 'bilgisayar': 'Bilgisayar', 'cip': 'Çip', 'siber': 'Siber', 'sosyal': 'Sosyal medya', 'uygulama': 'Uygulama', 'yazilim': 'Yazılım', 'oyun': 'Oyun', 'oto-tekno': 'Otomobil teknolojisi', 'robotik': 'Robotik', 'giyilebilir': 'Giyilebilir', 'ev': 'Elektrikli araç/batarya',
          'tr-siyaset': 'Türkiye siyaseti', 'abd': 'ABD', 'avrupa': 'Avrupa', 'cin': 'Çin', 'rusya': 'Rusya-Ukrayna', 'orta-dogu': 'Orta Doğu', 'israil-filistin': 'İsrail-Filistin', 'nato': 'NATO', 'bm': 'BM', 'secim': 'Seçimler', 'kriz': 'Diplomatik kriz', 'yaptirim': 'Yaptırım ve ticaret', 'savunma': 'Savunma',
          'futbol': 'Futbol', 'basketbol': 'Basketbol', 'tenis': 'Tenis', 'f1': 'Formula 1', 'motor': 'Motor sporları', 'voleybol': 'Voleybol', 'olimpiyat': 'Olimpiyat', 'dovus': 'Dövüş sporları', 'espor': 'E-spor', 'transfer': 'Transfer', 'kulup': 'Kulüp', 'milli': 'Milli takımlar',
          'doviz': 'Döviz', 'altin': 'Altın', 'borsa': 'Borsa', 'enflasyon': 'Enflasyon', 'faiz': 'Faiz ve merkez bankaları', 'kripto': 'Kripto', 'enerji': 'Enerji', 'istihdam': 'Maaş ve istihdam', 'sirket': 'Şirket haberleri', 'ticaret': 'Dış ticaret', 'konut': 'Konut',
          'uzay': 'Uzay', 'saglik': 'Sağlık', 'iklim': 'İklim', 'fizik': 'Fizik', 'biyoloji': 'Biyoloji', 'yz-arastirma': 'Yapay zekâ araştırmaları', 'acik': 'Güvenlik açığı', 'fidye': 'Fidye yazılımı', 'veri-ihlali': 'Veri ihlali', 'oltalama': 'Dolandırıcılık/oltalama', 'devlet-aktoru': 'Devlet destekli', 'zararli': 'Zararlı yazılım',
          'elektrikli': 'Elektrikli', 'marka': 'Markalar', 'otonom': 'Otonom sürüş', 'ulasim': 'Ulaşım', 'yeni-model': 'Yeni model', 'motorsporu': 'Motor sporu', 'film-dizi': 'Film ve dizi', 'muzik': 'Müzik', 'kultur': 'Kültür-sanat', 'internet': 'İnternet fenomenleri', 'anime': 'Anime',
          'sohbet': 'Sohbet botları', 'yz-sirket': 'Yapay zekâ şirketleri', 'model': 'Modeller', 'gorsel-video': 'Görsel ve video üretimi', 'duzenleme': 'Hukuk ve düzenleme', 'donanim-yz': 'Çip ve veri merkezi', 'is-hayati': 'İş hayatı', 'ajan': 'Yapay zekâ ajanları',
          'yerli': 'Yerli projeler', 'hava': 'Hava', 'deniz': 'Deniz', 'kara': 'Kara', 'fuze-hava-savunma': 'Füze ve hava savunma', 'iha': 'İHA/SİHA', 'ihracat-anlasma': 'İhracat ve anlaşmalar', 'uluslararasi': 'Uluslararası',
          'konsol': 'Konsol', 'pc-oyun': 'PC', 'mobil-oyun': 'Mobil oyun', 'gta': 'GTA 6', 'cikis': 'Çıkış ve duyuru', 'ucretsiz': 'Ücretsiz ve abonelik', 'sektor': 'Sektör', 'espor-oyun': 'E-spor'}
GUNDEM_ALT = [('turkiye', 'Türkiye'), ('dunya', 'Dünya'), ('siyaset', 'Siyaset'), ('diplomasi', 'Diplomasi'), ('savas', 'Savaş ve güvenlik'), ('ekonomi', 'Ekonomi'), ('toplum', 'Toplum'), ('hukuk', 'Hukuk'), ('afet', 'Afet'), ('saglik', 'Sağlık'), ('egitim', 'Eğitim')]
RE_DIPLO = re.compile(r"diplomasi|diplomat|büyükelçi|zirve|müzakere|görüşme|dışişleri|ateşkes|anlaşma imza|summit|ambassador|talks|negotiat|treaty|foreign minister", re.I)

# ------------------------------------------------------------------ Reels puan kuralları (v2)
CARPICI = M.CARPICI
ETKI = re.compile(r"özellik|feature|geliyor|geldi|rolling out|gizli|hidden|ipucu|nasıl|ücretsiz|free\b|bedava|kapat|silin|dikkat|uyarı|warning|dolandır|scam|phishing|oltalama|güvenlik açığı|vulnerab|sızdı|sızıntı|leak|fiyat|zam\b|indirim|vergi|maaş|emekli|asgari ücret|kira|faiz|yasak|yasa\b|karar|düzenleme|zorunlu|erişim|çöktü|outage|kesinti|deprem|sel\b|uyarısı|alarm|kota|ceza|ehliyet|sınav|okul|tatil|akaryakıt|benzin|elektrik|doğalgaz|ban\b|law\b|rule|tax|price|salary|recall|geri çağır|cuts|layoff|işten çıkar", re.I)
TURKIYE = re.compile(r"türkiye|türk\b|türkiye'|togg|btk|imei|\btl\b|istanbul|ankara|izmir|baykar|aselsan|turkcell|vodafone tr|türk telekom|erdoğan|tbmm|\bmeb\b|yks|tcmb|bist|galatasaray|fenerbahçe|beşiktaş|trabzonspor|milli takım|turkey|turkish|türkiye'nin", re.I)
HIKAYE = re.compile(r"neden|nasıl|iddia|sızdı|kaçtı|çöktü|yıkıldı|karşı karşıya|kapışma|çatışma|istifa|tutuklan|yasaklandı|iflas|dönüş|sürpriz|beklenmedik|ilk kez|rekor|krizi|skandal|perde arkası|gerçek yüzü|revealed|why|how|fired|resign|banned|collapse|scandal|comeback|surprise|rivalry|feud|crackdown|ousted|secret", re.I)
IDDIA = re.compile(r"iddia|söylentiler?|sızıntı|sızdı|rumor|leak|reportedly|allegedly|claims?\b|unconfirmed|doğrulanmadı|kulis", re.I)
# Viral/iddialı: tuhaf, tartışmalı, "nasıl olur" dedirten konu. Yalnız Reels puanında; masa.py (TechTurco paneli) ortak kalıplarına dokunmaz.
VIRAL = re.compile(r"tuhaf|garip|gizemli|esrarengiz|viral oldu|sosyal medyada|tepki çekti|tepki yağdı|olay yarattı|tartışma yarattı|gündem oldu|dava açtı|milyarder|yapay zek[aâ]|robot|deepfake|uzaylı|ufo\b|antik|arkeolog|keşfedildi|dünyada ilk|ilk kez|yıl sonra|şaşırtan|şaşırtıcı|rekor|yasakladı|yasaklandı|para cezası|hackl|ifşa|itiraf|şaşkına|bilim insanları|araştırma(ya)? göre|"
                   r"\bweird|bizarre|strange|odd\b|mysterious|mystery|went viral|goes viral|viral\b|backlash|outrage|sparks? (anger|debate|fury)|controvers|conspiracy|lawsuit|\bsues?\b|sued\b|fined\b|billionaire|\bai\b|artificial intelligence|chatbot|robot|deepfake|alien|\bufo|ancient|archaeolog|discovered|scientists|study (finds|shows)|researchers|world'?s first|first[- ]ever|record[- ]breaking|banned|bans\b|hacked|exposed|caught|secretly|admits?\b|leaked|"
                   r"seltsam|kurios|verboten|erstmals|rekord|étrange|insolite|interdit|record\b|extraño|insólito|prohib", re.I)
# Hizmet/SEO sayfaları: her gün aynı kalıpla yazılan liste ve ilanlar. Gerçek deprem/sel haberi bu kalıplara girmez (yalnız "liste", "il il", "ne zaman" sayfaları).
SERVIS = re.compile(r"hava durumu (tahmin|il il)|saatlik hava durumu|bugün hava durumu|hava durumu (bugün|yarın|\d+ günlük)|il il hava|(hafta sonu|yarın) hava nasıl|namaz vakit|nöbetçi eczane|altın fiyatları (bugün|canlı)|döviz kurları bugün|(son )?depremler listesi|deprem(ler)? (listesi|canlı)|okul(lar)?(ın)? (açılış tarihi|ne zaman açıl)|ara tatil(i)? ne zaman|"
                    r"mahkemesinden\s*/?\s*başkanlığından|\bilan(ı)? ?:|kura sonuçları|tercih sonuçları (açıklandı|ne zaman)|"
                    r"weather forecast for|lottery (numbers|results)|powerball numbers|mega millions numbers|wordle (hint|answer)|connections hints?|crossword (answers|clue)|strands hints?", re.I)
HASSAS = re.compile(r"ölü|öldü|hayatını kaybet|cenaze|katliam|saldırı|bombalı|savaş|terör|tecavüz|taciz|istismar|intihar|killed|dead|massacre|attack|war\b|terror|rape|abuse|suicide", re.I)
RUTIN = M.RUTIN
ZAYIF = M.ZAYIF
# Büyük maç (derbi, Avrupa kupası, milli maç, final) ve skandal: rutin maç/transfer kuralları bunlara uygulanmaz.
BUYUK_MAC = re.compile(r"\b(derbi\w*|derby|el clasico|el clásico|şampiyonlar ligi|champions league|avrupa ligi|europa league|konferans ligi|conference league|\buefa\b|avrupa kupa\w*|"
                       r"milli (takım|maç)\w*|a milli|ay-yıldızlı\w*|national team|dünya kupası|world cup|\beuro 20\d\d|avrupa şampiyonası|\bfinal(i|de|e|inde)?\b|kupa finali|süper kupa)", re.I)
SKANDAL = re.compile(r"\b(skandal\w*|scandal\w*|olay (çıktı|yarattı)|kavga\w*|arbede\w*|saldırı\w*|şike\w*|bahis soruşturma\w*|soruşturma\w*|tepki\w*|istifa\w*|kırmızı kart\w*|hakem (hatası|skandalı|tepkisi)\w*|var (kararı|tartışma)\w*|tarihi (fark|yenilgi|galibiyet|zafer|skor)\w*|fined|banned|ban\b|protest\w*)", re.I)   # 'rekor' yok: maç özeti künyelerinde rutin ("Aslan rekor kırdı")
# Reels'e HİÇ girmeyenler (yalnız bunlar). Haber türü değil, içerik niteliği: spam/alışveriş/yayın rehberi ve özel kişilerin acısı.
ELE = [
 ('servis/SEO sayfasi', SERVIS),
 ('alisveris/indirim', re.compile(r"\b(deals?|coupon|promo code|black friday|prime day|\bsave \$?\d|\d+% off|indirim kodu|kupon|fırsat ürünleri)\b", re.I)),
 ('yayin rehberi', re.compile(r"canlı izle|nereden izlenir|hangi kanalda|şifresiz|how to watch|live stream|watch .{3,40} (for )?\W?(free|online)|ways? to watch|maç kadrosu|muhtemel 11|"
                             r"\b(ücretsiz|bedava) ve canlı\b|\bcanlı ve (ücretsiz|bedava)\b|\b(ücretsiz|bedava) izle\w*|\b(ücretsiz|canlı) yayınlan\w*|nerede yayınlan\w*|hangi kanal\w*|\btv'?(de|da) (ücretsiz|canlı)\b|\bstream(ing)? (for )?free\b|\bfree to (stream|watch)\b|where to stream|how to stream|\bstream .{3,50}\bfor free\b", re.I)),
 ('burc/kumar', re.compile(r"burç yorum|günlük burç|horoscope|bahis|casino|jackpot|iddaa tahmin|kesin kupon", re.I)),
 ('ozel kisi trajedisi', re.compile(r"tecavüz|cinsel istismar|taciz|çocuk istismarı|intihar etti|kadın cinayeti|cinayete kurban|cesedi bulundu|rape\b|child abuse|murdered (his|her) (wife|girlfriend|child)", re.I)),
 ('sponsorlu', re.compile(r"\bsponsored\b|işbirliğiyle|advertorial|ücretli içerik", re.I)),
 # 2026-11-18: Reels'e hiç uygun olmayan sayfa türleri (gerçek haber değil, rehber/ilan/canlı akış)
 ('resmi ilan', re.compile(r"mahkemesi(nden|ne)? (ilan|/)|icra (müdürlüğü|dairesi)(nden)? ilan|ihale ilanı|satış ilanı|satış icra dairesi|icra dairesi$|\bilan(ı)? (olunur|edilir)\b|t\.c\. .{0,40}(müdürlüğü|başkanlığı)ndan\b", re.I)),
 ('soru/SEO sayfasi', re.compile(r"nasıl (yapılır|iptal edilir|alınır|başvurulur|öğrenilir|sorgulanır|izlenir|açılır|kullanılır|indirilir|yüklenir)|ne zaman (yatacak|yatırılacak|açıklanacak|ödenecek|başlıyor|çıkacak)\??|ne kadar (olacak|oldu)\??|kaç (tl|lira)( olacak| oldu)?\??|saat kaçta|hangi gün|kimdir\??$|nerede oynanacak|how to (play|watch|get|download|fix|cancel)|what time (does|is)|release time|where to (buy|watch|preorder)|everything we know|all we know so far|kaç kaç bitti|kim yendi\??|maç sonucu|(yayınlandı|çıktı|başladı) mı\??|neden yok\??|yeni bölüm (ne zaman|fragman)", re.I)),
 # 2026-11-21 (tasarım-7 Reels kararı): rutin maç özeti/sonucu, tanıtım-fiyat sayfası, yerel kurs/deneme sınavı duyurusu girmez.
 # İstisna kalıbın başındaki (?!...) içinde: derbi, Avrupa kupası, milli maç, final ve skandal elenmez.
 ('rutin mac ozeti/sonucu', re.compile(r"^(?!.*" + BUYUK_MAC.pattern + r"|.*" + SKANDAL.pattern + r")"
                                      r".*(maç(ın)? özeti|geniş özet|\bhighlights\b|\bmaç sonucu\b|\bmaçı? (sona erdi|tamamlandı)\b|"
                                      r"\b\d{1,2}\s?[-–]\s?\d{1,2}\b.{0,50}\b(yendi|kazandı|mağlup|yenildi|berabere|geçti|devirdi|galip|beat|beats|defeat\w*|wins?|won|draw|drew|sinks?|edges?)\b|"
                                      r"\b(yendi|mağlup etti|yenildi|berabere kaldı|kazandı|beat|beats|defeated|won|drew)\b.{0,50}\b\d{1,2}\s?[-–]\s?\d{1,2}\b|"
                                      r"\b[A-ZÇĞİÖŞÜ][\wçğıöşüÇĞİÖŞÜ.']+\s\d{1,2}\s?[-–]\s?\d{1,2}\s[A-ZÇĞİÖŞÜ])", re.I | re.S)),
 ('urun tanitim/fiyat sayfasi', re.compile(r"^(?!.*" + SKANDAL.pattern + r"|.*\b(rekor\w*|record|en pahalı|most expensive|zam\w*|uçtu|el yakan|cep yakan|dudak uçuklat\w*|tepki\w*|backlash|outrage)\b)"
                                          r".*(özellikleri,? ve fiyatı|fiyatı ve özellikleri|özellikleri,? fiyatı|fiyatı belli oldu|(türkiye|tr) fiyatı (belli oldu|açıklandı)|"
                                          r"tanıtıldı[:!,]?\s*(işte )?(özellikleri|fiyatı|teknik)|(satışa|piyasaya) (sunuldu|çıktı)[:!,]?\s*(işte )?(fiyatı|özellikleri)|teknik özellikleri|"
                                          r"\bprice,? (and )?(specs|specifications|availability|release date)\b|\bspecs,? (and )?price\b|\bfull specs?\b|\bspecs and features\b|launch(es|ed)? with .{0,40}\bprice\b)", re.I | re.S)),
 ('yerel duyuru/kurs', re.compile(r"deneme sınav\w*|\bkurs(u|lar\w*|una|a)?\b.{0,40}\b(başladı|açıldı|kayıt\w*|başvuru\w*)|\b(ücretsiz|yeni) kurs\w*|\bkurs kayıt\w*|halk eğitim\w*|meslek edindirme|etüt merkez\w*|\beğitim desteği\b.{0,30}\bücretsiz|\bücretsiz\b.{0,30}\beğitim desteği", re.I)),
 ('canlı blog', re.compile(r"^(live|canlı|watch|izle)\s*[:|\-–]|live updates|liveblog|live blog|canlı (anlatım|blog)|son dakika gelişmeleri|minute[- ]by[- ]minute", re.I)),
]
ELE_ALAN = {'rutin mac ozeti/sonucu': {'spor'}, 'urun tanitim/fiyat sayfasi': {'tekno', 'oto', 'oyun', 'yz'}}
# Puan CEZASI (eleme değil): yalnız gerçekten düşük potansiyelli kalıplar. Siyaset bu listede değildir.
# 2026-11-21: spor için yalnız iki dar ceza var (sıradan transfer söylentisi, maç önü/hazırlık); derbi, büyük maç ve skandal CEZA_ISTISNA ile muaftır.
CEZA = [
 ('rutin sürüm/yama notu', RUTIN, 8, ('tekno', 'siber')),
 ('kurumsal finans dili', re.compile(r"\b(earnings|quarterly|funding round|raises \$|series [abc]\b|valuation|market cap|analyst|bilanço|piyasa değeri|hisse geri alım)\b", re.I), 10, ('tekno',)),
 ('ürün incelemesi/liste', re.compile(r"\breview:|incelemesi|\binceleme\b|\bbest .{0,30} (of|for)\b|en iyi \d+|haftanın|weekly roundup|podcast|newsletter", re.I), 8, ('tekno', 'oto', 'eglence')),
 ('sıradan hava/ulaşım duyurusu', re.compile(r"(sağanak|kuvvetli yağış|yağış|kar yağışı|kar|fırtına|rüzgar|don|sis) (uyarısı|alarmı|geliyor)|sarı kod|turuncu kod|meteoroloji(den)? uyar|hava durumu|sefer(ler)?(i)? iptal|seferleri durdur|vapur seferleri|uçuşlar(ı)? iptal|yollar kapandı|okullar tatil mi", re.I), 30, ('gundem', 'tekno', 'oto')),
 ('küçük deprem', re.compile(r"\b[1-4][.,]\d+ büyüklüğünde|magnitude[- ][1-4]\.\d|\bm[1-4]\.\d\b", re.I), 30, ('gundem',)),
 ('rutin adli süreç', re.compile(r"tutuklama talebiyle|hakimliğe sevk|adliyeye sevk|gözaltına alındı|gözaltı kararı|iddianame kabul|duruşma ertelendi|ifade verdi|kayyum atandı|kayyum atanan", re.I), 18, ('gundem', 'ekonomi')),
 ('magazin/dizi tanıtımı', re.compile(r"başrolde|kadrosuna katıldı|dizisi (geri dönüyor|başlıyor)|kırmızı halı|stil(i)?yle|kombin|premiere look|red carpet|casting", re.I), 14, ('gundem', 'eglence')),
 ('yalnızca yerel olay', re.compile(r"\b(mahallesinde|köyünde|ilçesinde|sokakta)\b.*\b(yaralandı|çarpıştı|kavga)\b|işçi servisi|servis aracı kaza", re.I), 10, ('gundem',)),
 ('sıradan transfer söylentisi', re.compile(r"\btransfer\w*\b.{0,50}\b(iddia\w*|söylenti\w*|gündem\w*|ilgileniyor|masada|radar\w*|listesi\w*|teklif\w*|görüşme\w*|bombası|sıcak gelişme)|"
                                           r"\b(ilgileniyor|gözünü dikti|radarına (aldı|girdi)|listesine (aldı|ekledi)|kancayı taktı|peşine düştü|transfer bombası|transferinde sıcak gelişme)\b|"
                                           r"\b(linked with|eyeing|monitoring|keen on|interested in signing|transfer (target|rumou?rs?|talks)|in talks to sign|set to sign|close to signing)\b", re.I), 15, ('spor',)),
 ('maç önü/hazırlık haberi', re.compile(r"maç hazırlık\w*|hazırlıklar\w* (sürdürdü|tamamladı|başladı)|\bantrenman\w*|kamp kadrosu|maçın hakemi|hakemleri açıklandı|ilk 11'?(i|leri)? belli oldu|kadro(su)? (açıklandı|belli oldu)|"
                                       r"\bmaç öncesi\b|\bpreview\b|predicted line-?ups?|team news|injury update", re.I), 15, ('spor',)),
 ('magazin dedikodusu', re.compile(r"aşk (yaşıyor|iddia\w*|bombası)|yeni sevgili\w*|sevgilisiyle|\bayrıldı(lar)?\b.{0,20}(ünlü|şarkıcı|oyuncu)|boşan(dı|ıyor|ma davası)\w*|dudak uçuklatan|tatilde görüntülen\w*|bikinili|paparazzi|imaj değişikliği|"
                                  r"estetik(li)? (operasyon|yaptırdı)|\bdating\b|split from|engaged to|baby bump|spotted with|\bburç\w*\b.{0,30}\b(özellikleri|uyumu)", re.I), 14, ('gundem', 'eglence')),
 ('rutin asayiş operasyonu', re.compile(r"\boperasyon\w*\b.{0,60}\b(gözaltı\w*|tutuklan\w*|yakalan\w*)|\bşüpheli\w*\b.{0,30}\b(yakalan\w*|tutuklan\w*|gözaltına)|\b\d+ (kişi|şüpheli|zanlı)\b.{0,30}\b(yakalan\w*|tutuklan\w*|gözaltına)", re.I), 12, ('gundem', 'tekno', 'siber')),
 # 2026-11-21: tekil trafik/kaza/asayiş haberi (bir sürücüye ceza, bir işçi göçük altında) gündem kotasını doldurmasın
 ('tekil trafik/kaza/asayiş', re.compile(r"\b(trafik|şerit|makas|drift|alkollü|ehliyetsiz|hız sınırı|yol verme|sürücü\w*|şoför\w*)\b.{0,70}\bceza\w*|\bceza\w*\b.{0,40}\b(sürücü\w*|şoför\w*)\b|"
                                         r"\bkaza(da|sında|yı|yla|ya)?\b.{0,40}\b(yaralandı|öldü|hayatını kaybetti|ceza\w*)|\bkaza yap(an|tı)\b|göçük altında|toprak kayması\w*.{0,20}\bişçi|"
                                         r"\b(kavga\w*|bıçakl\w*|silahl\w*|darp\w*)\b.{0,50}\b(yaralandı|gözaltı\w*|ceza\w*|tutuklan\w*)", re.I), 20, ('gundem', 'tekno')),
 ('yalnız ABD pazarı', re.compile(r"\b(us-only|only in the us|yalnızca abd|sadece abd|verizon|t-mobile|at&t|walmart|costco|best buy)\b", re.I), 8, ('tekno',)),
]
CEZA_ISTISNA = {'sıradan transfer söylentisi': re.compile(r"\b(rekor\w*|record|tarihi|en pahalı|most expensive|bedava|free transfer)\b|" + BUYUK_MAC.pattern, re.I),
                'maç önü/hazırlık haberi': re.compile(BUYUK_MAC.pattern + '|' + SKANDAL.pattern, re.I),
                'magazin dedikodusu': re.compile(r"\b(dava\w*|soruşturma\w*|tutuklan\w*|gözaltı\w*|lawsuit|sued|arrested)\b", re.I)}
# Ağırlıklar (toplam 100). Viral ve özgünlük (Türkçede henüz anlatılmamış yabancı konu) öne; Türkçe kaynak sayısı geri planda.
# 2026-11-21: 'iddiali' (14) eklendi; özgünlük, görsel, ilk 3 sn, güncellik, haber değeri, doğrulama ve hikâyeden alındı. Türkçe uygunluk ve hayata etki korunur
# (okangulesofficial verisi: cüzdan/gündem/Türkiye konuları kazandırıyor, yabancı şirket haberleri 1-2 B'de kalıyor).
KRITER = [('guncellik', 8, 'Güncellik'), ('haber', 8, 'Haber değeri'), ('etki', 10, 'Hayata etki'), ('ozgun', 5, 'Özgünlük'), ('saskin', 8, 'Şaşırtıcılık'), ('hikaye', 9, 'Hikâye potansiyeli'),
           ('gorsel', 4, 'Görsel malzeme'), ('dogrulama', 8, 'Çok kaynakta doğrulanma'), ('turk', 10, 'Türkçe izleyiciye uygunluk'), ('ilk3', 4, 'İlk 3 saniyede anlatılabilirlik'), ('viral', 12, 'Viral potansiyel'),
           ('iddiali', 14, 'İddialı konu')]

def cumle(s):
    s = re.sub(r'\s+', ' ', s or '').strip()
    m = re.match(r'^(.{25,220}?[.!?])(\s|$)', s)
    return m.group(1) if m else s[:200]

# ------------------------------------------------------------------ kümeleme
def kumele2(ogeler):
    """Haberleri olay kümelerine ayırır.
    Aynı dil: kelime benzerliği j>=.5, ya da j>=.3 ve ortak seyrek özel ad. Farklı dil: ortak varlık/sayı + zaman yakınlığı.
    Yeni haber kümenin ilk haberiyle karşılaştırılır (kayma olmasın)."""
    df = Counter(v for o in ogeler for v in o['var'])
    seyrek = {v for v, n in df.items() if n <= 25}
    ogeler.sort(key=lambda x: x['z'])
    kumeler, dizin = [], defaultdict(list)
    for o in ogeler:
        aday = Counter()
        for tk in o['tok'] | o['ent']:
            for c in dizin[tk][-40:]: aday[c] += 1
        en, enb = None, 0.0
        ov = o['var'] & seyrek
        for c, _ in aday.most_common(30):
            k = kumeler[c]
            if o['z'] - k['son'] > 36 * 3600: continue
            j = len(o['tok'] & k['ilk']) / max(1, len(o['tok'] | k['ilk']))
            ent = len(ov & k['ilkvar'])
            if (j >= .3 and ent >= 1) or j >= .5:
                skor = j + .15 * ent        # kelime benzerliği yeterli: dil etiketinden bağımsız (etiket yanlış olabilir)
            elif o['dil'] != k['ilkdil']:
                # çok dilli: ortak varlık sözlüğü + ortak sayı ya da çok seyrek ortak özel ad (df<=8).
                # Ülke/lider adları tek başına yetmez (Gazze haberlerinin hepsi eşleşirdi).
                ortak = o['ent'] & k['ilkent']
                sayi = {t for t in (o['tok'] & k['ilk']) if t.startswith('n:')}
                cok_seyrek = {v for v in (o['var'] & k['ilkvarall']) if not v.startswith('@') and df[v] <= 8}
                if abs(o['z'] - k['ilkz']) > 12 * 3600: continue
                if not (len(ortak) >= 2 and (sayi or len(cok_seyrek) >= 2)): continue
                skor = .2 * len(ortak) + .15 * len(cok_seyrek) + .3 * len(sayi)
            else:
                continue
            if skor > enb: en, enb = c, skor
        if en is None:
            en = len(kumeler)
            kumeler.append(dict(ogeler=[], tok=set(), son=o['z'], ilk=set(o['tok']), ilkvar=set(ov), ilkvarall=set(o['var']), ilkent=set(o['ent']), ilkdil=o['dil'], ilkz=o['z']))
            for tk in o['tok'] | o['ent']: dizin[tk].append(en)
        k = kumeler[en]
        k['ogeler'].append(o); k['tok'] |= o['tok']; k['son'] = max(k['son'], o['z'])
    return kumeler

def kumele_tam(ogeler):
    """kumele2 + ikinci geçiş: aynı olayı farklı başlıkla anlatan kümeler ortak SEYREK özel adlarla birleşir
    (masa.birlestir: zincirleme yok; üç ortak seyrek ad ya da kelime benzerliği ≥.35 ve ortak seyrek ad)."""
    ks = kumele2(ogeler)
    for o in ogeler: o['var_tam'] = o['var']; o['var'] = {v for v in o['var'] if not v.startswith('@')}   # sözlük jetonları (ülke/lider) ikinci geçişte sayılmaz
    try: return M.birlestir(ks)
    finally:
        for o in ogeler: o['var'] = o.pop('var_tam')

# ------------------------------------------------------------------ Akış'a özel üçüncü geçiş (2026-11-20)
# Büyük olaylar bölünüyordu: 'anthropic' 178 haberde geçince "seyrek" sayılmıyor, olayın onlarca kümesi birleşemiyordu.
# Tek ad yerine AD ÇİFTİ ayırt edicidir: anthropic+ipo, myanmar+rohingya. masa.birlestir (TechTurco paneli) değişmez.
KAVRAM = [('#ipo', re.compile(r"\bipo\b|halka arz|halka açıl|börsengang|introduction en bourse|public offering|goes public|went public|first day of trading|首次公开|上市", re.I)),
          ('#ipo', re.compile(r"stock market debut|nasdaq debut|market debut|wall street (listing|debut)|debut(s|ed)?\b.{0,20}(wall street|nasdaq|nyse)|goes to wall street|borsaya açıl|borsada işlem görmeye", re.I)),
          ('#soykirim', re.compile(r"soykırım|genocide|génocide|völkermord|genocidio|种族灭绝", re.I)),
          ('#ateskes', re.compile(r"ateşkes|ceasefire|cessez-le-feu|waffenruhe|停火", re.I))]
AD_GENEL = {'son dakika', 'breaking', 'video', 'canli', 'live', 'update', 'report', 'new', 'yeni', 'exclusive', 'ozel', 'haber', 'news', 'photo', 'foto', 'galeri', 'watch', 'izle',
            'ocak', 'subat', 'mart', 'nisan', 'mayis', 'haziran', 'temmuz', 'agustos', 'eylul', 'ekim', 'kasim', 'aralik', 'january', 'february', 'march', 'april', 'may', 'june', 'july',
            'august', 'september', 'october', 'november', 'december', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'pazartesi', 'sali', 'carsamba',
            'persembe', 'cuma', 'cumartesi', 'pazar', 'the', 'and', 'for', 'with', 'how', 'why', 'what', 'who', 'this', 'that', 'here', 'after', 'over', 'from', 'are', 'is', 'its', 'his', 'her',
            'ceo', 'cfo', 'cto', 'coo', 'ai', 'yz', 'ipo', 'us', 'uk', 'eu', 'tv', 'pc', 'app', 'apps', 'says', 'dr', 'prof', 'mr', 'mrs', 'sir', 'inc', 'ltd', 'co', 'corp',
            'baskan', 'bakan', 'genel', 'cumhurbaskani', 'president', 'minister', 'chief', 'lideri', 'sozcusu',
            'haberleri', 'haberler', 'gundem', 'spor', 'belediye', 'belediyesi', 'festival', 'festivali', 'universitesi', 'bakanligi', 'komisyonu', 'meclisi',
            'kupa', 'kupasi', 'lig', 'ligi', 'one', 'ultra', 'pro', 'max', 'plus', 'mini', 'air', 'edition', 'series', 'live', 'canli', 'son', 'dakika'}
SOZ_RX = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşüÀ-ÿ][\w\-\.]*", re.U)
ASCII_TR = str.maketrans('çğıöşüâîû', 'cgiosuaiu')
def _ad_kok(w):
    w = re.split(r"['’]", w)[0].strip('.-')
    return w.translate(M.TR).lower().translate(ASCII_TR) if w else ''
def baslik_bicimi(t):
    """'cumle' (yalnız özel adlar büyük harfli), 'baslik' (Title Case ya da TÜMÜ BÜYÜK). Title Case başlıkta sıradan kelimeler de büyük harfle başlar."""
    w = [x for x in SOZ_RX.findall(t) if len(x) >= 4]
    if not w: return 'cumle'
    buyuk = sum(1 for x in w if x[0].isupper())
    return 'baslik' if buyuk >= .6 * len(w) and len(w) >= 3 else 'cumle'
def ozel_ad_havuzu(basliklar):
    """Cümle biçimli başlıklarda cümle ortasında büyük harfle yazılan sözcükler: gerçek özel adlar (Title Case başlıklar için sözlük)."""
    say = Counter()
    for t in basliklar:
        if baslik_bicimi(t) != 'cumle': continue
        for i, w in enumerate(SOZ_RX.findall(t)):
            if i and w[0].isupper() and len(w) >= 3: say[_ad_kok(w)] += 1
    return {k for k, n in say.items() if n >= 2 and k not in AD_GENEL}
def adlar(t, havuz):
    """Başlıktaki özel adlar; ardışık büyük harfli sözcükler tek ad olur ('real madrid', 'iphone 20', 'dana white'). Kavramlar (#ipo) eklenir."""
    bic = baslik_bicimi(t)
    out = set()
    # noktalama (virgül, iki nokta, tire…) adı böler: "UAD, Myanmar'ı" iki ayrı ad; parçanın ilk sözcüğü cümle başı sayılır
    for parca in re.split(r"[,:;!?\"“”()\[\]|–—]+|\s-\s|\.\s", t):
        out |= _parca_adlari(parca, bic, havuz)
    out = {x for x in out if len(x) >= 3 and not x.isdigit() and x not in AD_GENEL and x not in M.STOP}
    for ad, rx in KAVRAM:
        if rx.search(t): out.add(ad)
    return out

def _parca_adlari(parca, bic, havuz):
    sozler = parca.split()
    out, cur = set(), []
    for i, w in enumerate(sozler):
        w = w.strip("'‘’`«»„.")
        if re.fullmatch(r"[^\W\d_]{3,}-[^\W\d_]{3,}(['’]\w+)?", w):     # Anthropic-Börsengang: iki ayrı sözcük
            out |= _parca_adlari(w.replace('-', ' '), bic, havuz) if not cur else set(); continue
        if not w: continue
        k = _ad_kok(w); temiz = re.sub(r"[^\w]", '', w)
        ad_mi = False
        if temiz and len(temiz) >= 2:
            if temiz.isdigit(): ad_mi = bool(cur) and len(temiz) <= 4         # 'iPhone 20', 'S27': yalnız adın devamı
            elif re.fullmatch(r'\d+(st|nd|rd|th|inci|ıncı|uncu|üncü|nci|ncı|ncu|ncü)', temiz.lower()): ad_mi = False   # 20th: sıra sayısı
            elif re.search(r'\d', temiz) and re.search(r'[A-Za-z]', temiz): ad_mi = True        # S27, GPT-6, F-35
            elif temiz.isupper() and len(temiz) >= 2 and bic == 'cumle': ad_mi = True           # IPO, NASA, KAAN
            elif w[0].islower() and any(ch.isupper() for ch in w[1:3]): ad_mi = True        # iPhone, eSIM
            elif w[0].isupper():
                ad_mi = (k in havuz) if (bic == 'baslik' or i == 0) else True
        if ad_mi and k not in AD_GENEL: cur.append(k)
        else:
            if cur: out.add(' '.join(cur)); cur = []
        if "'" in w or '’' in w:
            if cur: out.add(' '.join(cur)); cur = []
    if cur: out.add(' '.join(cur))
    # cümlede bitişik yazılan iki ad ('Adalet Divanı Myanmar'ı'): uçtaki sözcük tek başına bilinen bir adsa o da ayrıca sayılır
    for x in list(out):
        p = x.split()
        if len(p) >= 3: out |= {w for w in (p[0], p[-1]) if w in havuz}
    return out
def ad_ciftleri(ad):
    """Olay anahtarı: iki ad birlikte. İki ülke/lider/kavram çifti (trump+putin, abd+çin) olayı ayırt etmez, sayılmaz."""
    out = set()
    cok = [set(x.split()) for x in ad if ' ' in x]
    L = sorted(ad)
    for i in range(len(L)):
        for j in range(i + 1, len(L)):
            a, b = L[i], L[j]
            ca, cb = canon_bul(a), canon_bul(b)
            if ca and ca == cb: continue                                          # 'apple' + 'iphone': aynı varlık
            sa, sb = set(a.split()), set(b.split())
            if any((sa | sb) <= g for g in cok): continue                        # 'real' + 'madrid' / 'real madrid': tek ad
            genel = lambda x, c: x.startswith('#') or (c and c <= (ULKE | LIDER | {'ab', 'bm', 'nato'}))
            if genel(a, ca) and genel(b, cb): continue
            if ca and cb: continue                                                # iki sözlük varlığı (chatgpt+claude, trump+çin): karşılaştırma/konu, olay değil
            out.add((a, b))
    return out

def birlestir_akis(kumeler, havuz, pencere=36):
    """Üçüncü geçiş: ortak ad çifti olan kümeler (36 saat içinde) birleşir. Zincirleme yok: büyükten küçüğe, her küme en çok bir çapaya.
    Ek tanık şart: aynı dilde başlık benzerliği (j>=.3) ya da iki ayrı ortak çift; diller arası: ortak sayı (sürüm/yıl değil) ya da iki ortak çift;
    her iki durumda olay kavramı çifti (anthropic+#ipo) tek başına yeter."""
    for k in kumeler:
        k['_ad'] = [adlar(o['t'], havuz) for o in k['ogeler'][:30]]
        k['_tc'] = [ad_ciftleri(a) for a in k['_ad']]
        k['_cift'] = set().union(*k['_tc']) if k['_tc'] else set()
        # ortak sayı tanığı: yıl ve sürüm numarası gibi sayılar (One UI 9.5, iOS 27.3) sayılmaz; yoksa bir ürünün tüm haberleri birleşirdi
        k['_sayi'] = {t for o in k['ogeler'][:12] for t in o['tok'] if t.startswith('n:') and len(t) >= 5 and not re.match(r'n:(20\d\d|\d{1,2}\.\d)$', t)}
        k['_dil'] = Counter(o['dil'] for o in k['ogeler']).most_common(1)[0][0]
    # aşırı yaygın çift (ör. bir haftalık savaşın iki tarafı) aday dizinini şişirmesin; olay çiftleri bunun çok altında kalır
    df = Counter(c for k in kumeler for c in k['_cift'])
    tavan = max(60, len(kumeler) // 25)
    sirali = sorted(range(len(kumeler)), key=lambda i: (-len(kumeler[i]['ogeler']), kumeler[i]['son']))
    capalar, dizin = [], defaultdict(list)
    def benzer(a, b, ortak):
        # benzer başlık çifti ortak ad çiftini de taşımalı (aynı kalıplı farklı ürün sayfaları birleşmesin)
        for x, cx in zip(a['ogeler'][:30], a['_tc']):
            if not cx & ortak: continue
            for y, cy in zip(b['ogeler'][:30], b['_tc']):
                if not cx & cy & ortak: continue
                u = len(x['tok'] | y['tok'])
                if u and len(x['tok'] & y['tok']) / u >= .3: return True
        return False
    for i in sirali:
        k = kumeler[i]; hedef = None
        ciftler = {c for c in k['_cift'] if df[c] <= tavan}
        aday = Counter(ci for c in ciftler for ci in dizin[c])
        for ci, n in aday.most_common(20):
            capa = capalar[ci][0]
            if abs(capa['son'] - k['son']) > pencere * 3600: continue
            ortak = capa['_cift'] & ciftler
            sayi = capa['_sayi'] & k['_sayi']
            ortak_ad = set().union(*(set(x) for x in ortak))
            iki = len(ortak_ad) >= 3                                               # en az üç farklı ad iki çiftte buluşuyor
            # olay kavramı + özel ad çifti (anthropic+#ipo, myanmar+#soykirim) dilden bağımsız yeterli tanıktır
            kavram = any(x.startswith('#') != y.startswith('#') for x, y in ortak)
            if capa['_dil'] == k['_dil']: ok = benzer(capa, k, ortak) or iki or kavram
            else: ok = sayi or iki or kavram
            if ok: hedef = ci; break
        if hedef is None:
            capalar.append((k, [k]))
            for c in ciftler: dizin[c].append(len(capalar) - 1)
        else:
            capalar[hedef][1].append(k)
    sonuc = []
    for capa, uyeler in capalar:
        ana = dict(capa)
        if len(uyeler) > 1:
            g, og = set(), []
            for u in uyeler:
                for o in u['ogeler']:
                    if o['l'] not in g: g.add(o['l']); og.append(o)
            ana['ogeler'] = og
            ana['tok'] = set().union(*(u['tok'] for u in uyeler))
            ana['son'] = max(u['son'] for u in uyeler)
        for x in ('_ad', '_tc', '_cift', '_sayi', '_dil'): ana.pop(x, None)
        sonuc.append(ana)
    return sonuc

def kumele_akis(ogeler, havuz=None):
    """Akış kümelemesi: kumele_tam (masa ile ortak iki geçiş) + ad çifti geçişi."""
    if havuz is None: havuz = ozel_ad_havuzu([o['t'] for o in ogeler])
    return birlestir_akis(kumele_tam(ogeler), havuz)

def bagimsiz_say(og):
    """Bağımsız doğrulama sayısı: kurum başına 1; ajans kopyaları ve aynı bültenden türeyenler ilk yayıncıyla bir sayılır.
    Dönüş: (sayı, {öğe_id: kopya_oldugu_kurum})"""
    gor, grup, kopya = {}, {}, {}
    og = sorted(og, key=lambda o: o['z'])
    for o in og:
        k = o['org']
        ajans = k in AJANS_KURUM or bool(AJANS_ISARET.search(o['t'] + ' ' + o['s'][:80])) or 'ajans' in o['nit']
        kok_ = None
        for q in og:
            if q is o or q['z'] > o['z'] or q['org'] == k: continue
            if o['z'] - q['z'] > 6 * 3600: continue
            jj = len(o['tok'] & q['tok']) / max(1, len(o['tok'] | q['tok']))
            if jj >= .85 and len(o['tok']) >= 5:   # neredeyse aynı başlık: aynı bülten
                kok_ = q['org']; break
        if k in gor: continue
        if kok_ and (ajans or True) and kok_ in grup.values():
            kopya[o['id']] = kok_; gor[k] = True; continue
        gor[k] = True; grup[k] = k
    return len(grup), kopya

def alan_bul(og, bas_metin, say_cal):
    """Bir kümenin çalışma alanları: kaynak türü + içerik kuralı. Dönüş: sıralı alan listesi."""
    a = set()
    m = bas_metin
    kay = say_cal
    # kaynak odaklı alanlar (haber sitesinin bölümü / uzman kaynak)
    for k, rx in (('tekno', 'tekno_guclu'), ('bilim', 'bilim_guclu'), ('ekonomi', 'ekonomi_guclu'), ('spor', 'spor_guclu'), ('oto', 'oto_guclu'), ('eglence', 'eglence_guclu'), ('oyun', 'oyun_guclu'), ('yz', 'yz_guclu')):
        # YZ ve oyun yalnız başlıklardan sayılır (özet metnindeki tek 'AI'/'game' kelimesi alan açmasın)
        n_rx = len(KURAL[rx].findall(m if k not in ('yz', 'oyun') else ' '.join(o['t'] for o in og[:12]))); n_k = kay.get(k, 0)
        # YZ ve oyun haberini çoğunlukla genel teknoloji/eğlence siteleri verir: o bölümler de tanık sayılır
        if k == 'yz': n_k += kay.get('tekno', 0) + kay.get('bilim', 0)
        if k == 'oyun': n_k += kay.get('tekno', 0) + kay.get('eglence', 0)
        # kaynak bölümü ve içerik birlikte tanık olmalı: bölüm tek başına ya da tek bir kelime yetmez
        if (n_k >= 2 and n_rx >= 1) or (n_k >= 1 and n_rx >= 2) or n_rx >= 3 or (n_k >= 1 and n_rx >= 1 and k in ('spor', 'oto', 'bilim', 'eglence', 'oyun', 'yz')): a.add(k)
    # YZ ve oyun ek katmandır: Gündem kuralını ve boş-alan yedeğini etkilemesin diye burada ayrılır, sonda geri eklenir
    # Savunma sanayi (yz gibi katman): özel terim tek başına; genel terim iki tane ya da savunma kaynağıyla. Saldırı/ölüm haberi genel
    # terimle (füze saldırısı, drone strike) savunmaya girmez; savunma kaynağı ya da özel terim (şirket/ürün) gerekir.
    bas_t = ' '.join(o['t'] for o in og[:12])
    sv_o = len(KURAL['savunma_guclu'].findall(bas_t))
    sv_g = len({mm.group(0).lower() for mm in KURAL['savunma_genel'].finditer(bas_t)}) + len({mm.group(0).lower() for mm in KURAL['savunma_platform'].finditer(bas_t)})
    sv_p = bool(KURAL['savunma_platform'].search(bas_t))
    sv_k = kay.get('savunma', 0)
    saldiri = bool(KURAL['savunma_saldiri'].search(bas_t))
    # Yanlış birleşmiş büyük kümede (ör. iki bakanlığın bütçe görüşmesi) tek savunma başlığı tüm kümeyi Savunma'ya taşımasın
    sv_bas = sum(1 for o in og if KURAL['savunma_guclu'].search(o['t']) or KURAL['savunma_genel'].search(o['t']) or KURAL['savunma_platform'].search(o['t']))
    azinlik = len(og) >= 6 and max(sv_bas, sv_k) < .25 * len(og)
    if not azinlik and (sv_o >= 1 or (sv_k >= 1 and sv_g >= 1) or ((sv_g >= 2 or sv_p) and not saldiri)): a.add('savunma')
    # Spor bölümü baskın küme (en az 3 spor kaynağı, kaynakların %60'ı): içerik kelimesi aranmaz; teknoloji/oyun/eğlence de
    # yalnız kendi kaynak bölümüyle açılır (futbol metnindeki 'oyun', 'akıllı', 'uygulama' Teknoloji'ye düşürmesin)
    n_kay = sum(kay.values()) or 1
    if kay.get('spor', 0) >= 3 and kay.get('spor', 0) >= .6 * n_kay:
        a.add('spor')
        for k in ('tekno', 'oyun', 'eglence'):
            if k in a and not kay.get(k, 0): a.discard(k)
    katman = a & {'yz', 'oyun', 'savunma'}; a -= katman
    # Adana: metninde Adana (il, ilçe, kurum, kulüp) geçen haber. Yerel kaynak tek başına yetmez (yerel siteler ulusal haber de verir);
    # yerel kaynakta ayrıca başka anlamı olan ilçe adları da (Seyhan, Ceyhan, Kozan…) kabul edilir. Hava durumu/servis sayfaları girmez.
    if not SERVIS.search(m) and (KURAL['adana'].search(m) or (kay.get('adana') and KURAL['adana_ilce'].search(m))): a.add('adana')
    if KURAL['siber'].search(m): a.add('siber')
    if KURAL['siyaset'].search(m) and (kay.get('siyaset') or kay.get('gundem') or len(KURAL['siyaset'].findall(m)) >= 2): a.add('siyaset')
    # Gündem: genel haber akışı (teknoloji/spor/magazin dışı kalanlar dahil siyaset, toplum, hukuk...)
    gundem_kay = kay.get('gundem', 0) + kay.get('siyaset', 0)
    if gundem_kay and (a - {'siyaset', 'ekonomi', 'siber'} == set() or 'siyaset' in a or KURAL['gundem_guclu'].search(m) or KURAL['savas'].search(m)):
        a.add('gundem')
    if 'siyaset' in a and not (a & {'gundem'}) and gundem_kay: a.add('gundem')
    if not a and not ('savunma' in katman and kay.get('savunma')):   # savunma kaynağının savunma haberi yalnız Savunma'da kalabilir
        top = max(kay, key=kay.get) if kay else 'gundem'
        # Adana içerik kuralıyla girer; yerel sitenin Adana'yla ilgisiz haberi varsayılan olarak Gündem'e düşer
        # savunma kaynağının (ör. Google Haberler sorgusu) savunmayla ilgisiz haberi de Gündem'e düşer
        a.add('gundem' if top in ('adana', 'savunma') else top)
    a |= katman
    if 'yz' in a and not a & {'tekno', 'bilim'}: a.add('tekno')   # yapay zekâ haberi Teknoloji'de de görünür
    if 'oyun' in a and a == {'oyun', 'eglence'} and not KURAL['eglence_guclu'].search(m): a.discard('eglence')
    return [x for x in ALANLAR if x in a]

def alt_etiket(alan, m):
    return [k for k, rx in ALT_RX.get(alan, []) if rx.search(m)]

def gundem_alt(m, ulkeler, dil_tr):
    out = []
    if KURAL['siyaset'].search(m): out.append('siyaset')
    if RE_DIPLO.search(m): out.append('diplomasi')
    if KURAL['savas'].search(m): out.append('savas')
    if KURAL['ekonomi_guclu'].search(m): out.append('ekonomi')
    if RE_HUKUK.search(m): out.append('hukuk')
    if RE_AFET.search(m): out.append('afet')
    if RE_SAGLIK.search(m): out.append('saglik')
    if RE_EGITIM.search(m): out.append('egitim')
    if RE_TOPLUM.search(m): out.append('toplum')
    out.append('turkiye' if (TURKIYE.search(m) or 'turkiye' in ulkeler) else 'dunya')
    return out

def zaman_pencere(og, simdi, saat):
    """(son `saat` saatteki haber sayısı, bağımsız kurum sayısı, önceki aynı uzunluktaki pencerede haber sayısı)"""
    s = simdi - saat * 3600; p = simdi - 2 * saat * 3600
    ic = [o for o in og if o['z'] >= s]; onc = [o for o in og if p <= o['z'] < s]
    return len(ic), len({o['org'] for o in ic}), len(onc)

def kanit_etiketi(og):
    n = set()
    for o in og: n |= set(o['nit'])
    if 'on-calisma' in n: return 'on-calisma'
    if 'hakemli-dergi' in n or 'hakemli' in n: return 'hakemli'
    if 'basin-bulteni' in n: return 'basin-bulteni'
    return 'haber'

# ------------------------------------------------------------------ Reels
CARPICI_ZAYIF = re.compile(r"^(leak\w*|finally|surpris\w*|sızdı|sızıntı\w*)$", re.I)
def carpici_gercek(t):
    """Başlıkta 'leak', 'finally', 'surprise' dışında gerçek bir şaşırtıcılık kelimesi var mı (rutin sürüm cezası muafiyeti ve içerik kapısı için)."""
    return any(not CARPICI_ZAYIF.match(m.group(0)) for m in CARPICI.finditer(t))

# 2026-11-21: "iddialı" konu ölçütü. Yalnız BAŞLIĞA bakılır (özet/kaynak metni kategori açmaz). Kelime sınırlıdır: "zaman" zam, "çıkış tarihi" tarihi,
# "ceza sahası" ceza, "recorded" record, "band" ban sayılmaz. Sıra = `aci` şablon önceliği (cüzdan, hukuk, güvenlik önce; Türkiye en son, yalnız güçlendirici).
IDDIALI = [
 ('cep', 'Cebinize dokunuyor', 7, re.compile(
    r"\bzam(lar\w*|lı\w*|land\w*|mı|m[ıa])?\b|\bzamm\w*|\bvergi\w*|\bkdv\b|\bötv\b|\bharç(lar\w*|ı)?\b|\bmaaş\w*|\bemekli(ler|lere|ye|nin|lerin)?\b.{0,25}\b(maaş|zam|ikramiye|bayram|promosyon|artış|ödeme)\w*|\bemeklilik\w*|asgari ücret\w*|\bfaiz\w*|\bkira(sı|ları|lar|ya|da|nın)?\b|"
    r"\bakaryakıt\w*|\bbenzin\w*|\bmotorin\w*|doğal ?gaz\w*|\belektri(k|ğ)\w*\s+(zam|fatura|tarife)\w*|\benflasyon\w*|\bfatura\w*|\bcezası\b.{0,20}\b(tl|lira)\b|"
    r"\bfiyat\w*\b.{0,30}\b(art\w*|yüksel\w*|düş\w*|zam\w*|uçtu|ucuzla\w*|pahalılaş\w*|el yakıyor|cep yakıyor|rekor\w*|katına)|\b(art\w*|zam\w*|indirim\w*)\b.{0,20}\bfiyat\w*|\bfiyat\w*\b.{0,15}\b(sızdı|sızdırıldı|sızıntı\w*)|\b(akaryakıt|benzin|motorin|mazot|lpg|doğal ?gaz|elektri\w*)\b.{0,40}\b(indirim\w*|zam\w*|geriledi|düştü|ucuzla\w*)|\bindirim\w*\b.{0,30}\b(benzin|motorin|akaryakıt|doğal ?gaz|elektri\w*)|\bfiyat\w*\b.{0,40}\b\d[\d.,]*\s*(bin |milyon )?(tl|lira)\b|"
    r"\bprice (hikes?|increases?|rises?|jumps?|cuts?)\b|\bprices? (rise|rises|rose|jump\w*|soar\w*|surge\w*|hike\w*|double\w*)\b|\btax(es|ed)?\b|\btariffs?\b|\bsalar(y|ies)\b|\bwages?\b|\binterest rates?\b|\binflation\b|\brent (hike|increase)s?\b", re.I)),
 ('hukuk', 'Yasak ve dava gündemi', 7, re.compile(
    r"\byasa(k|ğ)\w*|\byasakla\w*|\bdava(sı|lar\w*|yı|ya|da|cı)?\b|\bdava aç\w*|\bsoruşturma\w*|\bkovuşturma\w*|\btutuklan\w*|\bhapis\w*|\bmahk[uû]m\w*|\biddianame\w*|"
    r"(?<!asliye )(?<!ağır )\bceza(?!\s*(sahas|mahkeme|alan|vuruş|puan))\w*|\bmühür\w*|\berişim engeli\w*|\bkapatıl(dı|acak)\b|"
    r"\bban(s|ned|ning)?\b|\bsue[sd]?\b|\blawsuits?\b|\bfined\b|\bfines?\b(?= of| for)|\bprobe[sd]?\b|\binvestigation\w*|\bindict\w*|\bantitrust\b|\bconvicted\b|\bsentenced\b|\bjail\w*|\barrested\b", re.I)),
 ('guvenlik', 'Güvenlik uyarısı', 7, re.compile(
    r"\bhack(?!athon)\w*|siber saldırı\w*|veri sızıntı\w*|\bveriler\w*\b.{0,25}\b(sızdı|sızdırıldı|çalındı|ele geçirildi|satışa)|\bgüvenlik açığı\w*|\bdolandırıc\w*|\boltalama\w*|\bfidye\w*|"
    r"\bcasus\w*|\bgizlilik\w*|\bkvkk\b|zararlı yazılım\w*|"
    r"\bdata breach\w*|\bbreach(es|ed)?\b|\bvulnerabilit\w*|\bzero[- ]day\b|\bransomware\b|\bmalware\b|\bspyware\b|\bphishing\b|\bscam\w*|\bprivacy\b|\bsurveillance\b|\bexploit(s|ed)?\b|\bcyber ?attack\w*", re.I)),
 ('tartisma', 'Tartışma büyüyor', 7, re.compile(
    r"\btepki\w*|\btartışma\w*|\bpolemik\w*|\bkriz\w*|\bskandal\w*|\bistifa\w*|\bkarşı çıktı\w*|\bsert (çıktı|yanıt|sözler)\w*|\bisyan\w*|\bboykot\w*|\bprotesto\w*|\byalanla\w*|\bsuçla\w*|\bifşa\w*|\bitiraf\w*|"
    r"\bbacklash\b|\boutrage\b|\bcontrovers\w*|\bslam(s|med)?\b|\bfury\b|\bscandal\w*|\bresign\w*|\bboycott\w*|\bprotest\w*|\bcritici[sz]\w*|\bfeud\b|\bclash\w*|\bdenies\b|\baccus\w*", re.I)),
 ('rekor', 'Rekor', 7, re.compile(
    r"\brekor\w*|\brecord(-breaking)?\b|\ball-time high\b|tarihi zirve\w*|\d[\d.,]*\s*(milyar|trilyon)\s*(dolar|tl|lira|euro|avro)\w*|\$\s?\d[\d.,]*\s*(billion|trillion|bn)\b|\b(billion|trillion)-dollar\b|"
    r"\btarihin(in)? en büyü\w*|\ben büyük (halka arz|yatırım|ihale|satın alma|anlaşma|zarar|ceza)\w*|\ben pahalı\b|\bbiggest ever\b|\blargest ever\b|\bmost expensive\b", re.I)),
 ('ilk', 'İlk kez', 7, re.compile(
    r"\bilk kez\b|\bilk defa\b|dünyada (bir )?ilk\b|\bbir ilk\b|\btarih(e|i) geçti\w*|\btarih yazdı\w*|\btarihi (karar|an|zafer|adım|anlaşma|zirve|gün|başarı|ilk|değişiklik|dönem)\w*|\btarihte (ilk|bir ilk)\b|"
    r"\beşi benzeri görülmemiş\b|\bfirst[- ]ever\b|\bworld'?s first\b|\bfor the first time\b|\bhistoric\b|\bunprecedented\b", re.I)),
 ('bilim', 'Şaşırtan gelişme', 6, re.compile(
    r"\b(bilim insanları|araştırmacılar)\b.{0,60}\b(buldu|keşfetti|şaşırt\w*|ortaya çıkardı|başardı)|\bkeşfedil\w*|\bkeşfetti\b|\bhipotez\w*|\bkuantum\w*|\bkara delik\w*|\bnükleer füzyon\w*|"
    r"\bscientists (discover\w*|find|found|reveal\w*)\b|\bdiscover(ed|y)\b|\bbreakthrough\b|\bstudy (finds|shows|reveals)\b|\bresearchers (find|found|discover\w*)\b|\bquantum\b|\bfusion\b|\bblack hole\b|\bexoplanet\w*", re.I)),
 ('buyuk_mac', 'Büyük maç', 6, BUYUK_MAC),      # yalnız spor alanında sayılır (iddiali_bul): "sezon finali", "Final Fantasy" maç değildir
 ('turkiye', "Türkiye'yi doğrudan ilgilendiriyor", 4, re.compile(
    r"\btürkiye\w*|\bturkey\b|\bturkish\b|\btürk (vatandaş|lirası|halkı|kullanıcı|öğrenci)\w*|\bbtk\b|\bimei\b|resm[iî] gazete\w*|rekabet kurul\w*|\btcmb\b|merkez bankası\w*|\bbddk\b|\bspk\b|\bepdk\b|\bsgk\b|\bmeb\b", re.I)),
]
IDDIALI_RX = {ad: rx for ad, _, _, rx in IDDIALI}
DEV_CATISMA = re.compile(r"\b(vs\.?|versus|karşı|rakib\w*|rakip\w*|savaş\w*|kapışma\w*|rekabet\w*|dava\w*|suçla\w*|tahtını|geride bıraktı|rival\w*|battle|war\b|feud|takes on|sues|against|beats|overtakes?|challenge\w*)\b", re.I)

def iddiali_bul(t, alanlar=(), ent=None):
    """Başlıktaki iddialı konu kategorileri (sıra IDDIALI ile aynı) ve 0-10 puan. Devlerin çatışması: 2+ büyük marka + çatışma kelimesi.
    Yalnız spor alanındaki 'ilk kez'/'rekor' istatistik dilidir (Süper Lig'de ilk kez Çoklu Top Sistemi): düşük puan alır."""
    t = t or ''
    kat = [(ad, p) for ad, _, p, rx in IDDIALI if rx.search(t)]
    ent = canon_bul(t) if ent is None else ent
    if len(ent & MARKA) >= 2 and DEV_CATISMA.search(t): kat.insert(0, ('devler', 7))
    if 'spor' not in alanlar: kat = [(ad, p) for ad, p in kat if ad != 'buyuk_mac']
    kat = [(ad, 9 if ad == 'cep' and ACI_GUCLU['cep'].search(t) else p) for ad, p in kat]      # Türkiye'de cebe dokunan (TL, akaryakıt, maaş, kira…) en güçlü konu
    sadece_spor = set(alanlar) and set(alanlar) <= {'spor'}
    if sadece_spor: kat = [(ad, 3 if ad in ('ilk', 'rekor', 'bilim', 'turkiye') else p) for ad, p in kat]
    if not kat: return [], 0
    pu = sorted((p for _, p in kat), reverse=True)
    return [ad for ad, _ in kat], min(10, pu[0] + sum(1.5 for x in pu[1:] if x >= 6) + sum(.5 for x in pu[1:] if x < 6))

def icerik_kapisi(c):
    """Reels içerik kapısı (2026-11-21, "daha az ve daha iddialı"): başlıkta iddialı konu (puan >= 6) şart.
    Hayata etki/viral/hikâye tek başına yetmez: bu ölçütler 'fiyat', 'ücretsiz', 'sınav', 'ilk kez' gibi rutin kelimelerle de açılıyor.
    İstisna (büyük olay): 4+ bağımsız kaynaklı siyaset/savunma/savaş/afet/diplomasi olayı ('dünya' tek başına değil: yabancı teknoloji haberleri de 'dunya' alır) ya da 10+ bağımsız kaynaklı her konu. Spor istisnası yok (derbi/büyük maç iddialı sayılır)."""
    if iddiali_bul(c['t'], c.get('alanlar') or ())[1] >= 6: return True
    a = set(c['alanlar']); ga = set(c.get('gundem_alt') or ())
    if c['kb'] >= 4 and (a & {'siyaset', 'savunma'} or ga & {'savas', 'afet', 'diplomasi'}): return True
    return c['kb'] >= 10

def reels_puanla(c, og, bas, metin, simdi, kay_ad):
    """c: küme özeti. Dönüş: (puan, kriter dict 0-10, gerekçe listesi, elenme nedeni|None, cezalar)"""
    t = bas['t']; yas = (simdi - c['son']) / 3600
    kr = {}
    kr['guncellik'] = 10 if yas <= 3 else 8.5 if yas <= 6 else 7 if yas <= 12 else 5 if yas <= 24 else 3 if yas <= 48 else 1.5
    kr['haber'] = min(10, c['h6'] * 1.6 + c['h24'] * .25 + (3 if c['kb'] >= 4 else 0) + (2 if c['resmi'] else 0))
    kr['etki'] = min(10, (6 if ETKI.search(t) else 0) + (3 if ETKI.search(metin) else 0) + (2 if 'turkiye' in c['gundem_alt'] and KURAL['gundem_guclu'].search(t) else 0))
    kr['ozgun'] = 5 + (4 if c['sadece_yabanci'] and c['kb'] >= 2 else 0) + (1.5 if c['n_tr'] <= 2 and c['kb'] >= 3 else 0) - (3 if RUTIN.search(t) else 0) - (1.5 if c['kb'] >= 8 else 0) + (1 if c['farkli'] else 0)
    vur = CARPICI.findall(metin)
    kr['saskin'] = min(10, (6 if CARPICI.search(t) else 0) + min(4, len(vur)) + (1 if re.search(r'\d{2,}', t) else 0))
    kr['hikaye'] = min(10, (5 if HIKAYE.search(t) else 0) + (2 if HIKAYE.search(metin) else 0) + min(3, len(og) / 3.0))
    kr['gorsel'] = (6 if c['i'] else 0) + (2 if any(o['plat'] == 'youtube' for o in og) else 0) + (2 if c['resmi'] or len([o for o in og if o['i']]) >= 3 else 0)
    kr['dogrulama'] = 9.5 if c['kb'] >= 4 else 8 if c['kb'] == 3 else 6 if c['kb'] == 2 else (4.5 if c['resmi'] else 1.5)
    kr['turk'] = min(10, (6 if TURKIYE.search(metin) else 0) + min(3, c['n_tr'] * 1.2) + (2 if c['alanlar'] and set(c['alanlar']) & {'tekno', 'ekonomi'} and c['n_tr'] else 0))
    kr['iddiali'] = iddiali_bul(t, c['alanlar'])[1]
    kr['ilk3'] = min(10, (3 if re.search(r'\d', t) else 0) + (3 if CARPICI.search(t) else 0) + (2 if 25 <= len(t) <= 95 else 0) + (2 if len(M.varlik(t)) >= 2 else 0))
    # Viral: yalnız en az 2 bağımsız kaynakta doğrulanan konu (tek kaynaklı sızıntı/iddia öne çıkmaz); ölüm/savaş dili viral sayılmaz.
    if c['kb'] >= 2 and not HASSAS.search(t):
        kat = set(c.get('kategoriler') or [])
        kr['viral'] = (5 if VIRAL.search(t) else 0) + min(2, len(VIRAL.findall(metin)) * .5) + (2 if kat & {'viral', 'cool', 'sci'} else 0) + (2 if c['sadece_yabanci'] else 0) + (1 if CARPICI.search(t) else 0)
    else:
        kr['viral'] = 0
    for a in kr: kr[a] = round(max(0, min(10, kr[a])), 1)
    p = sum(kr[k] * w for k, w, _ in KRITER) / 10.0
    # 2026-11-21: Türkiye'de cebe dokunan konu (akaryakıt, zam, indirim, vergi, maaş, faiz, kira, enerji fiyatı) Okan'ın en çok izlenen türü: ek +8
    if kr['iddiali'] >= 9 and 'cep' in iddiali_bul(t, c['alanlar'])[0]: p += CEP_EK
    ceza = []
    for ad, rx, d, alanlar in CEZA:
        if set(c['alanlar']) & set(alanlar) and rx.search(t) and not (ad.startswith('rutin') and carpici_gercek(t)) and not (ad in CEZA_ISTISNA and CEZA_ISTISNA[ad].search(t)):
            p -= d; ceza.append(ad)
    # Yalnız yabancı kaynaklı sızıntı/söylenti, Türkçe kaynağı olan eşdeğer konunun önüne geçmesin (hafif ceza; siyaset/spor rutinine ceza yok)
    if c['sadece_yabanci'] and IDDIA.search(t): p -= 4; ceza.append('yalnız yabancı kaynaklı sızıntı/söylenti')
    if c['kb'] < 2 and not c['resmi'] and c['plat_topluluk']: p -= 6; ceza.append('yalnız topluluk kaynağı (erken sinyal)')
    if c['kb'] < 2 and not c['resmi'] and not c['plat_topluluk']: p -= 3; ceza.append('tek bağımsız kaynak')
    # Türkiye izleyicisine uzak yabancı yerel haber: Türkçe kaynak yok, Türkiye geçmiyor, büyük ülke/lider/marka da yok
    genel = set(c['alanlar']) & {'tekno', 'yz', 'bilim', 'oyun', 'eglence', 'oto', 'siber'}
    if c['sadece_yabanci'] and not TURKIYE.search(metin) and not (c['ulkeler'] or c['liderler'] or c['markalar']) and not genel:
        p -= 15; ceza.append('Türkiye izleyicisine uzak yabancı yerel haber')
    if len(re.findall(r"\b[A-ZÇĞİÖŞÜ]{3,}\b", t)) >= 4 and len(re.findall(r"\b[A-ZÇĞİÖŞÜ]{3,}\b", t)) * 2 >= len(t.split()):
        p -= 10; ceza.append('büyük harfli tık tuzağı başlık')
    elen = None
    for ad, rx in ELE:
        if ad in ELE_ALAN and not set(c['alanlar']) & ELE_ALAN[ad]: continue      # maç sonucu yalnız sporda, tanıtım sayfası yalnız teknolojide elenir
        if rx.search(t): elen = ad; break
    return round(max(0, p), 1), kr, ceza, elen

REELS_ESIK = 48        # 2026-11-18: 38'den yükseltildi (187 aday 'aşırı' bulundu)
REELS_TOPLAM = 40      # 2026-11-21 (tasarım-7): daha az, daha iddialı; liste dolmazsa doldurulmaz
REELS_PROFIL = 15      # kesin sınır: bir kart dolu profile sayılmaz (kartın profil listesinden düşer)
REELS_GUC3, REELS_GUC2 = 65, 56
CEP_EK = 8
REELS_GENEL = {'apple', 'google', 'samsung', 'microsoft', 'yeni', 'new', 'turkiye', 'abd', 'trump', 'update', 'guncelleme', 'pro', 'max', 'ultra', 'son', 'dakika',
               'rusya', 'russia', 'cin', 'china', 'dunya', 'world', 'yapay', 'zeka', 'leak', 'design', 'report', 'first', 'erdogan', 'avrupa', 'europe', 'istanbul', 'ankara'}
def reels_anahtar(og, havuz=frozenset(), bas_t=''):
    """Kümenin hikâye anahtarı (2026-11-20): başlıklardaki özel adlar (Title Case ve TÜMÜ BÜYÜK başlıkların sıradan kelimeleri değil)
    ve ad çiftleri. Dönüş: (adlar, ad çiftleri). Tek ortak ad tekrar sayılmaz; ortak ad ÇİFTİ ya da ortak ad + benzer başlık sayılır."""
    ad, cift = set(), set()
    for t in ([bas_t] if bas_t else []) + [o['t'] for o in og[:8]]:
        a = {x for x in adlar(t, havuz) if x not in REELS_GENEL and not x.startswith('#')}
        a_k = a | {x for x in adlar(t, havuz) if x.startswith('#')}
        ad |= a; cift |= ad_ciftleri(a_k)
    return ad, cift

TURKIYE_SAVUNMA = re.compile(r"aselsan|roketsan|tusaş|havelsan|baykar|bayraktar|kızılelma|kizilelma|\bkaan\b|hürjet|hurjet|altay|\btcg\b|milgem|akıncı|\bsiha\b|\bİHA|(?<!tonluk )çelik kubbe(?!.{0,40}(vinç|cami))|\bssb\b|savunma sanayi|türk|turkish|turkey", re.I)
def profil_bul(c, m):
    pr = []
    a = set(c['alanlar'])
    # profil başlıkla doğrulanır: kaynağın bölümü tek başına profil açmaz
    if a & {'tekno', 'siber', 'yz', 'oyun'} and (KURAL['tekno_guclu'].search(m) or KURAL['siber'].search(m) or KURAL['yz_guclu'].search(m) or KURAL['oyun_guclu'].search(m)): pr.append('teknoloji')
    if 'gundem' in a or 'ekonomi' in a: pr.append('gundem')
    if 'siyaset' in a and KURAL['siyaset'].search(m): pr.append('siyaset')
    if 'spor' in a and KURAL['spor_guclu'].search(m): pr.append('spor')
    alt = []
    if 'bilim' in a: alt.append('bilim')
    if 'siber' in a: alt.append('siber')
    if 'yz' in a: alt.append('yz')
    if 'oyun' in a: alt.append('oyun')
    if 'oto' in a: alt.append('oto'); pr = pr or ['teknoloji']
    # savunma: yerli şirket/ürün haberi teknoloji, diğerleri (tedarik, uluslararası) gündem profiline
    if 'savunma' in a:
        alt.append('savunma')
        if not pr: pr = ['teknoloji'] if KURAL['savunma_guclu'].search(m) and TURKIYE_SAVUNMA.search(m) else ['gundem']
    if 'ekonomi' in a: alt.append('ekonomi')
    if 'eglence' in a and not pr: pr.append('gundem')
    if c['_kr']['saskin'] >= 7 and ('bilim' in a or 'eglence' in a or 'oto' in a or c['kb'] >= 3): alt.append('ilginc')
    if not pr: pr.append('gundem')
    return pr, alt

ACI = [
 (lambda c, m: 'siber' in c['alanlar'], 'Uyarı odaklı: ne oldu → kim etkileniyor → şimdi ne yapmalı (3 adım)'),
 (lambda c, m: bool(re.search(r'fiyat|zam\b|maaş|vergi|faiz|kira|akaryakıt|price|tax|salary', m, re.I)), 'Cebe etkisi: sayıyı ver → kimin cebini ne kadar etkiliyor → ne yapılabilir'),
 (lambda c, m: 'spor' in c['alanlar'], 'Anın hikâyesi: sonuç/karar önce → perde arkası → kimin kaybettiği/kazandığı'),
 (lambda c, m: 'siyaset' in c['alanlar'], 'Tarafsız özet: kim ne dedi → ne değişiyor → Türkiye için sonucu (yorumsuz, kaynaklı)'),
 (lambda c, m: 'tekno' in c['alanlar'] and 'yz' in c['alt'].get('tekno', []), 'Yapay zekâ neden önemli: tek çarpıcı örnek → gündelik hayata etkisi → riskler'),
 (lambda c, m: 'bilim' in c['alanlar'], 'Merak anlatısı: şaşırtıcı bulgu → nasıl bulundu → hâlâ bilinmeyenler'),
 (lambda c, m: bool(IDDIA.search(m)), 'Doğrulama odaklı: iddia → neyin kanıtlandığı → neyin henüz belli olmadığı'),
 (lambda c, m: True, 'Ters köşe: herkesin bildiği → şaşırtan ayrıntı → ne anlama geliyor'),
]
def kisa_baslik(t, n=62):
    t = re.sub(r'\s+', ' ', t).strip(' .')
    return t if len(t) <= n else t[:n - 1].rsplit(' ', 1)[0] + '…'

ACI_ON = {ad: on for ad, on, _, _ in IDDIALI}
ACI_ON['devler'] = 'Devler karşı karşıya'
# Başlık zaten aynı kelimeyi söylüyorsa ("Rekor: … rekor") ikinci önek kullanılır.
ACI_KELIME = {'rekor': re.compile(r"\brekor", re.I), 'ilk': re.compile(r"\bilk (kez|defa)\b", re.I), 'tartisma': re.compile(r"\btartışma", re.I), 'hukuk': re.compile(r"\byasa(k|ğ)|\bdava", re.I)}
ACI_ON2 = {'rekor': 'Kırılan eşik', 'ilk': 'Tarihî adım', 'tartisma': 'Gerilim yükseliyor', 'hukuk': 'Hukuki düğüm'}
# Güçlü önek yalnız kendi kelime sınıfı eşleşirse; yoksa daha yumuşak (başlıktan fazlasını iddia etmeyen) önek.
ACI_GUCLU = {'cep': re.compile(r"\b(tl|lira\w*|türkiye\w*|emekli\w*|asgari|memur\w*|sgk|akaryakıt\w*|benzin\w*|motorin\w*|mazot|lpg|doğal ?gaz\w*|elektri\w*|kira\w*|maaş\w*|zam\w*|kdv|ötv|harç\w*|fatura\w*)\b", re.I),
             'tartisma': re.compile(r"\b(tepki\w*|tartışma\w*|polemik\w*|skandal\w*|boykot\w*|protesto\w*|backlash|outrage|controvers\w*|fury|boycott\w*|protest\w*|slam(s|med)?)\b", re.I),
             'rekor': re.compile(r"\b(rekor\w*|record(-breaking)?|all-time high|tarihi zirve\w*|tarihin(in)? en büyü\w*|biggest ever|largest ever)\b", re.I)}
ACI_YUMUSAK = {'cep': 'Para gündemi', 'tartisma': 'Gerilimli gündem', 'rekor': 'Büyük para'}
ACI_SIRA = ['cep', 'hukuk', 'guvenlik', 'devler', 'tartisma', 'rekor', 'ilk', 'bilim', 'buyuk_mac', 'turkiye']
ACI_BAS = re.compile(r"^\s*(son dakika|flaş|flas|breaking|rekor|ilk kez|şok|sok|resmen|müjde|dikkat|uyarı)\s*[:!|\-–]+\s*", re.I)
ACI_SINIR = 90
def aci_temiz(t, kaynaklar=()):
    """Başlığı açı cümlesine hazırlar: kaynak eki (' - GSMArena.com news'), boru ile ayrılmış künye ve baştaki 'SON DAKİKA:' gibi etiket atılır. Yeni kelime/sayı eklenmez."""
    t = re.sub(r'\s+', ' ', t or '').strip()
    parca = re.split(r'\s+[|]\s+', t)
    t = parca[0] if len(parca[0]) >= 25 else ' | '.join(parca[:2])
    m = re.search(r'\s[-–—]\s([^-–—]{2,45})$', t)
    if m and (re.search(r'\.(com|net|org|tr)\b|\bnews\b|\bhaber', m.group(1), re.I) or any(k and k.lower() in m.group(1).lower() for k in kaynaklar)): t = t[:m.start()]
    for _ in range(2): t = ACI_BAS.sub('', t)
    return t.strip(' .:;,-–')

ACI_YETIM = re.compile(r"^(\d[\d.,]*%?|%\d[\d.,]*|yüzde|bin|milyon|milyar|trilyon|ve|ile|ama|için|da|de|ki|bir|the|and|of|to|a|an|in|on|for|with|after|as|by)$", re.I)
def aci_kisalt(t, n):
    """n karakteri aşan başlığı önce ':' / ',' / ' – ' sınırında keser (en az 30 karakter kalıyorsa), olmazsa kelimede; sonda sayı, birim ya da bağlaç yetim kalmaz."""
    for m in reversed(list(re.finditer(r'\s*[:;,–—]\s+|[.!?]\s+', t[:n + 1]))):
        if 30 <= m.start() <= n: return t[:m.start()].rstrip(' .:;,-–')
    w = t[:n - 1].split(' ')
    if len(w) > 1: w = w[:-1]
    while len(w) > 3 and ACI_YETIM.match(w[-1].strip('.,:;')): w.pop()
    return ' '.join(w).rstrip(' .:;,-–') + '…'

def aci_etiket_bul(c, bas):
    """Açının yalnız öneki (ör. 'Kırılan eşik', 'Cebinize dokunuyor'); kartta `aci_etiket` olarak da yazılır."""
    kat, _ = iddiali_bul(bas['t'], c['alanlar'])
    ad = next((a for a in ACI_SIRA if a in kat), None)
    if 'spor' in c['alanlar'] and 'buyuk_mac' in kat: ad = 'buyuk_mac'
    if ad in ACI_GUCLU and not ACI_GUCLU[ad].search(bas['t']): on = ACI_YUMUSAK[ad]
    elif ad: on = ACI_ON2[ad] if ad in ACI_ON2 and ACI_KELIME[ad].search(bas['t']) else ACI_ON[ad]
    elif c['kb'] >= 8: on = 'Neden herkes bunu konuşuyor'
    else: on = 'Gündemde'
    return on

def aci_konu(c):
    """Türkçe başlığı olmayan kart için kısa Türkçe konu adı: alt etiket adı (ALT_AD) ya da alan adı; varsa en çok 2 marka/kişi adı."""
    ad = next((ALT_AD[x] for a in c['alanlar'] for x in (c.get('alt') or {}).get(a, []) if x in ALT_AD), None) or next((ALAN_AD[a] for a in c['alanlar'] if a in ALAN_AD), 'Dünya gündemi')
    ozel = [x.title() for x in (c.get('markalar') or []) + (c.get('liderler') or [])][:2]
    return ad + (' (%s)' % ', '.join(ozel) if ozel else '')

def aci_uret(c, bas):
    """Tek, kısa, iddialı açı cümlesi (2026-11-21). Kategori ve metin yalnız kartın BAŞLIĞINDAN gelir; etiket + kısaltılmış başlık.
    Başlık Türkçe değilse (Türkçe kaynak yoksa baş haber de yabancıdır) gövde çevrilmez: etiket + Türkçe konu adı (aci_konu).
    Sayı uydurmaz: başlıkta olmayan sayı yazılmaz, kaynak sayısı gibi hesaplanan değerler de eklenmez. En çok ACI_SINIR karakter."""
    on = aci_etiket_bul(c, bas)
    if bas.get('dil', 'tr') != 'tr': return ('%s: %s' % (on, aci_konu(c)))[:ACI_SINIR]
    govde = aci_temiz(bas['t'], c.get('kaynaklar') or ())
    n = ACI_SINIR - len(on) - 2
    if len(govde) > n: govde = aci_kisalt(govde, n)
    return '%s: %s' % (on, govde)

def guc_bul(p):
    """Puan dilimi -> 1-3 (3 = en güçlü). Dilimler 21.11.2026 canlı veri dağılımına göre seçildi."""
    return 3 if p >= REELS_GUC3 else 2 if p >= REELS_GUC2 else 1

def hook_uret(c, bas, ayrinti):
    """3 açılış cümlesi (kural şablonu; taslaktır). Uydurma iddia içermez: yalnız kümeden hesaplanan değerleri kullanır."""
    t = kisa_baslik(bas['t'])
    sayi = re.search(r'(\d[\d.,]*)\s?(%|milyar|milyon|bin\b|TL\b|dolar|euro|kişi|yaralı|gün|yıl|km\b|GB\b|puan|gol)', bas['t'], re.I)
    h = []
    if sayi: h.append('Rakam bu: %s. %s' % (sayi.group(0).strip(), t))     # yalnız birimli sayı (tarih/sıra sayısı hook olmaz)
    else: h.append('3 saniyede özet: %s' % t)
    if ayrinti: h.append('Başlıkta yazmayan ayrıntı: %s' % (ayrinti[:90].rstrip(' .,') + ('…' if len(ayrinti) > 90 else '')))
    else: h.append('Bu haberde herkesin aynı şeyi yazmasının nedeni: %d farklı kaynak, aynı gelişme.' % c['kb'])
    h.append('%d kaynak yazdı ama Türkçede neredeyse kimse anlatmadı; sana ne etkisi var?' % c['kb'] if c['sadece_yabanci'] else '%d bağımsız kaynak aynı gelişmeyi yazıyor. Peki sana ne etkisi var?' % c['kb'])
    return h

def reels_kart(c, og, bas, simdi):
    metin = ' '.join(o['t'] + ' ' + o['s'][:100] for o in og)
    kr = c['_kr']; p = c['r']
    yas_saat = (simdi - c['ilk']) / 3600
    k_ad = lambda: ', '.join(c['kaynaklar'][:3])
    # çarpıcı ayrıntı: sayı/rekor/ilk içeren cümle; yoksa en farklı başlık
    bt = {M.kok(w) for w in M.sozcuk(bas['t'])}
    def yeni_mi(x):
        xt = {M.kok(w) for w in M.sozcuk(x)}
        return bool(xt) and len(xt & bt) / max(1, len(xt | bt)) < .5          # başlığı tekrarlayan cümle ayrıntı değildir
    aday = [cumle(o['s']) for o in og if o['s'] and (CARPICI.search(o['s']) or re.search(r'\d{2,}', o['s'])) and yeni_mi(cumle(o['s']))]
    aday = aday or [cumle(o['s']) for o in og if o['s'] and yeni_mi(cumle(o['s']))]
    ayrinti = aday[0] if aday else (c['farkli'][0]['t'] if c['farkli'] else '')
    ayrinti = re.sub(r'\b\d{1,2}[./]\d{1,2}[./]\d{4}\b', '', ayrinti)                       # akış künyesi: tarih
    ayrinti = re.sub(r'\s+', ' ', ayrinti).strip(' -–·')
    if len(ayrinti) < 25: ayrinti = ''
    neden = []
    neden.append('%d bağımsız kaynak yazdı' % c['kb'] if c['kb'] >= 2 else 'şu an tek kaynak var')
    if c['h6'] >= 2: neden.append('son 6 saatte %d haber' % c['h6'])
    if c['yog'] > 0: neden.append('yoğunluk önceki döneme göre +%d%%' % c['yog'])
    neden.append('ilk haber %s önce' % ('%d dk' % int(yas_saat * 60) if yas_saat < 1 else '%d saat' % yas_saat if yas_saat < 48 else '%d gün' % (yas_saat // 24)))
    tr = 'Türkiye\'yi doğrudan ilgilendiriyor' if TURKIYE.search(metin) else ('Türkçe kaynaklar da yazıyor (%d)' % c['n_tr'] if c['n_tr'] else 'Türkçede henüz yer almamış; ilk anlatan siz olabilirsiniz')
    if c['kb'] >= 2:
        dog = 'Doğrulandı: %d bağımsız kaynak (%s%s)' % (c['kb'], ', '.join(c['kaynaklar'][:4]), '…' if len(c['kaynaklar']) > 4 else '')
    elif c['resmi']:
        dog = 'Resmî kaynaktan; ikinci bağımsız haber bekleniyor'
    else:
        dog = 'DOĞRULANMADI: tek kaynak (%s)' % k_ad()
    gor = []
    if c['i']: gor.append('haber görseli var')
    yt = [o for o in og if o['plat'] == 'youtube']
    if yt: gor.append('YouTube videosu: %s' % yt[0]['kaynak'])
    if c['resmi']: gor.append('resmî kaynak görsel/video paylaşmış olabilir (lisansı kontrol edin)')
    if not gor: gor.append('hazır görsel yok; ekran kaydı, grafik veya stok malzeme gerekir')
    risk = []
    if c['kb'] < 2: risk.append('Tek kaynak: yayından önce ikinci kaynak bulun')
    if IDDIA.search(metin): risk.append('İddia/sızıntı dili: "iddia ediliyor" çerçevesi kullanın')
    if HASSAS.search(metin): risk.append('Hassas içerik (şiddet/ölüm): şiddet görüntüsü kullanmayın, mağdur kimliği vermeyin')
    if c['kanit'] == 'on-calisma': risk.append('Ön çalışma (hakem denetimi yok): kesin bulgu gibi sunmayın')
    if c['kanit'] == 'basin-bulteni': risk.append('Basın bülteni: kurumun kendi anlatımı, bağımsız doğrulama değil')
    if c['plat_topluluk']: risk.append('Topluluk kaynağı: doğrulanmış haber sayılmaz, erken sinyaldir')
    if c['sadece_yabanci'] and not TURKIYE.search(metin): risk.append('Türkiye bağlantısı zayıf: izleyiciye "neden önemli" bağını kurun')
    if not risk: risk.append('Belirgin risk yok; yine de yayından önce kaynak bağlantılarını açıp kontrol edin')
    anlatim = next(t for f, t in ACI if f(c, metin))      # eski 'aci' (anlatım kalıbı); 'aci' artık tek cümlelik iddialı açı
    oz = cumle(bas['s']) or bas['t']
    onerilen = bas['t'] if len(bas['t']) <= 72 else bas['t'][:69].rsplit(' ', 1)[0] + '…'
    en_iyi = sorted(kr.items(), key=lambda kv: -kv[1] * dict((k, w) for k, w, _ in KRITER)[kv[0]])[:3]
    gerekce = '%s: %s/10' % (', '.join(a for a in [dict((k, a) for k, _, a in KRITER)[k] for k, _ in en_iyi]), ' · '.join('%.0f' % v for _, v in en_iyi))
    return dict(oneri_baslik=onerilen, ozet=oz, neden_gundemde='; '.join(neden), carpici_ayrinti=ayrinti or 'Belirgin tek bir ayrıntı bulunamadı; kaynak başlıklarındaki farka bakın.',
                turk_onemi=tr, dogrulama=dog, gorsel_potansiyel='; '.join(gor), hooklar=hook_uret(c, bas, ayrinti), aci=aci_uret(c, bas), aci_etiket=aci_etiket_bul(c, bas), anlatim=anlatim, guc=guc_bul(p),
                puan_gerekce=gerekce, risk=risk)

def reels_sec(cikti, havuz, simdi):
    """Reels seçimi: eşik + içerik kapısı + tekrar/konu sınırı + profil kotası (en çok REELS_PROFIL) + toplam (en çok REELS_TOPLAM). Liste dolmazsa doldurulmaz."""
    reels = []
    gorulen = []; konu_say = Counter(); reels_disi = Counter()
    for c, og, bas in sorted(cikti, key=lambda x: -x[0]['r']):
        if c['r'] < REELS_ESIK or c['elen'] or c['kb'] < 1: continue
        if (simdi - c['son']) > 72 * 3600: continue
        if not icerik_kapisi(c): reels_disi['icerik kapisi'] += 1; continue
        # aynı olayın ikinci kartı: çok benzer başlık, ortak ad çifti (anthropic+ipo, myanmar+rohingya) ya da ortak ad + benzer başlık
        toks = [{M.kok(w) for w in M.sozcuk(o['t'])} for o in og[:6]]
        ad, cift = reels_anahtar(og, havuz, c['t'])
        # aynı iki liderin (Trump-Putin zirvesi) ikinci kartı da tekrardır; yalnız kartın kendi başlıklarına bakılır (büyük kümenin kıyısındaki haber sayılmaz)
        lider = set().union(*(canon_bul(t) for t in [c['t']] + [o['t'] for o in og[:4]])) & LIDER
        def ayni(q):
            qt, qad, qcift, qlider = q
            jmax = max((len(x & y) / max(1, len(x | y)) for x in toks for y in qt), default=0)
            oc = cift & qcift
            kavram = any(x.startswith('#') or y.startswith('#') for x, y in oc)
            # ortak olay kavramı çifti (anthropic+#ipo) dil farkında da yeter; diğer ortak çift ya da ad başlık benzerliği ister
            return (jmax >= .4 or kavram or (bool(oc) and jmax >= .2) or (bool(ad & qad) and jmax >= .25)
                    or (len(lider & qlider) >= 2 and (bool(ad & qad) or jmax >= .2)))
        if any(ayni(q) for q in gorulen): reels_disi['tekrar'] += 1; continue
        # tek konu (GTA 6, iPhone 20, Nvidia…) listeyi doldurmasın: en fazla 2 kart
        modeller = {v for v in ad if re.search(r'\d', v) or ' ' in v}
        if any(konu_say[v] >= 2 for v in modeller): reels_disi['konu siniri'] += 1; continue
        gorulen.append((toks, ad, cift, lider))
        for v in modeller: konu_say[v] += 1
        reels.append((c, og, bas))
    # çıktı: reels (profil dengeli: her profilden en fazla REELS_PROFIL)
    prof_say = Counter(); reels_son = []
    for c, og, bas in reels:
        kalan = [p for p in c['profil'] if prof_say[p] < REELS_PROFIL]      # kesin sınır: dolu profil karttan düşer
        if not kalan: reels_disi['profil dolu'] += 1; continue
        c['_reels_profil'] = kalan
        for p in kalan: prof_say[p] += 1
        reels_son.append((c, og, bas))
        if len(reels_son) >= REELS_TOPLAM: break
    return reels_son, reels_disi

# ------------------------------------------------------------------ ana akış
def durum_hesapla(s, d, simdi_iso, simdi, n72):
    """Kaynak durum etiketi: aktif | yavas | hata | guncellenmiyor | erisim-engelli | devre-disi | beklemede | bekliyor"""
    if s.get('aktif') is False: return 'devre-disi'
    dog = (s.get('dogrulama') or {}).get('durum')
    if not d or (not d.get('son_basari') and not d.get('son_kod')):
        return 'bekliyor' if dog == 'bekliyor' else 'beklemede'
    if d.get('bekle_kadar', '') > simdi_iso: return 'beklemede' if d.get('son_kod') == 429 else ('erisim-engelli' if d.get('son_kod') in (401, 403, 451) else 'hata')
    n = d.get('ardisik_basarisiz', 0)
    if n >= 3: return 'erisim-engelli' if d.get('son_kod') in (401, 403, 451) else 'hata'
    if n >= 1 and not d.get('son_basari'): return 'hata'
    sh = d.get('son_haber') or ''
    if sh:
        try:
            gun = (simdi - datetime.fromisoformat(sh).timestamp()) / 86400
            if gun > (14 if s.get('plat') in ('web', 'gnews') and s.get('oncelik', 2) <= 2 else 30): return 'guncellenmiyor'
        except Exception: pass
    if (d.get('ms') or 0) > 3000: return 'yavas'
    return 'aktif'

# Geliştirici/kod haberleri akışa girmez (kullanıcı isteği, 2026-11-18). Tüketiciyi ilgilendiren sürüm/beta haberleri (iOS beta, Chrome sürümü) dışarıda kalmaz.
GELISTIRICI = re.compile(r"\b(github|gitlab|stack ?overflow|npm\b|pypi|rustlang|\brust (\d|dili|language|compiler)|golang|\bgo \d\.\d|python \d|typescript|javascript|kotlin \d|swift \d|\.net \d|node\.?js|\bdeno\b|vue\.?js|react (\d|native)|webassembly|wasm\b|kubernetes|docker|devops|ci/cd|compiler|derleyici|codebase|kod taban|source code|kaynak kod|pull request|open[- ]source (library|framework|tool)|açık kaynak(lı)? (kütüphane|araç|yazılım projesi)|\bsdk\b|\bapi\b.{0,20}(deprecat|update|güncelle)|programlama|programming language|programmers?\b|yazılımcı|coding|kodlama|developer (tool|conference|preview)s?|geliştirici(ler)? (aracı|araçları|konferans|önizleme)|vs ?code|visual studio|xcode|android studio|linux (kernel|çekirde)|\bkernel \d|\bllvm\b|\bgcc\b|copilot (for|in) (vs|visual|github)|claude code|codex (cli|agent|app)|cursor (ai|ide|editor)|vibe[- ]cod|kotlin|flutter|unity engine|unreal engine \d|\bphp \d|\bcli\b|developer kit)", re.I)

# Kod terimi geçse de asıl konusu tüketici ürünü olan başlık kalır (ör. 'ChatGPT ve Codex yeni modelle güncellendi', telefonda yapay zekâyla uygulama).
TUKETICI = re.compile(r"chatgpt|\bgpt-\d|gemini (app|uygulama)|iphone|ipad|galaxy|xiaomi|pixel \d|playstation|xbox|nintendo|\bgta\b|whatsapp|instagram", re.I)

def ogeler_kur(j, src, simdi):
    """feeds.json -> tekilleştirilmiş haber öğeleri (kümelemeye girer). Dönüş: (ogeler, kaynak başına 72 sa sayaç)"""
    ogeler, gor = [], set()
    n72 = Counter()
    for sid, f in j['feeds'].items():
        s = src.get(sid, {})
        if sid.startswith('trends-'): continue
        if s.get('aktif') is False: continue   # kapatılan kaynağın eski kayıtları (feeds.json bir tur geriden gelir) akışa girmez   # Google Trends haber değil, arama sinyali: ayrı işlenir (ekler.trendler_uret)
        for it in f['items']:
            l = it.get('l'); t = (it.get('t') or '').strip()
            if not l or not t or not it.get('d'): continue
            if GELISTIRICI.search(t) and not TUKETICI.search(t): continue
            try: z = datetime.fromisoformat(it['d']).timestamp()
            except Exception: continue
            if simdi - z <= 72 * 3600 and z <= simdi + 300: n72[sid] += 1   # gerçekten son 72 saat (önce akıştaki tüm öğeler sayılıyordu)
            if simdi - z > SAAT * 3600 or z > simdi + 300: continue
            kl = kanonik(l) if 'news.google.com' not in l else l
            anahtar = kl if 'news.google.com' not in l else (re.sub(r'\W+', '', t.lower())[:60] + (it.get('p') or ''))
            if anahtar in gor: continue
            gor.add(anahtar)
            p = (it.get('p') or '').strip()
            if not p or p.startswith('http'): p = f['name']
            org = kurum(p, sid)
            # aynı kurumun aynı başlığı farklı adreslerle (bölüm/sürüm akışları) tek haber sayılır
            tek = (org, re.sub(r'\W+', '', t.lower())[:80])
            if tek in gor: continue
            gor.add(tek)
            cat = it.get('c') or f['cat']
            metin = t + ' ' + (it.get('s') or '')[:120]
            o = dict(id=hashlib.md5(l.encode()).hexdigest()[:10], t=t, l=l, z=z, s=(it.get('s') or '')[:220], i=it.get('i'), cat=cat, dil=f['lang'], kaynak=p, sid=sid, org=org,
                     plat=f.get('plat', 'web'), n=it.get('n'), tip=s.get('tip', 'ana akim'), nit=set(s.get('nitelik') or []), cal=s.get('calisma') or 'gundem', ulke=s.get('ulke', ''))
            o['tok'] = tok2(t); o['ent'] = canon_bul(t); o['var'] = M.varlik(t) | {'@' + e for e in o['ent']}
            ogeler.append(o)
    return ogeler, n72

def kumeler_kur(kumeler, simdi):
    """kumele_tam çıktısı -> (küme sözlüğü, öğeler, baş haber) listesi; puanlar dahil."""
    cikti = []
    for k in kumeler:
        og = sorted(k['ogeler'], key=lambda x: -x['z'])
        if len(og) > 40: og = og[:40]
        kb, kopya = bagimsiz_say(og)
        kaynaklar = list(dict.fromkeys(o['kaynak'] for o in og))
        say_cal = Counter(o['cal'] for o in og)
        tr_og = [o for o in og if o['dil'] == 'tr']
        adaylar = tr_og or og
        bas = max(adaylar, key=lambda o: (sum(len(o['tok'] & q['tok']) for q in og), -o['z']))
        metin_bas = bas['t'] + ' ' + bas['s']
        m_tum = ' '.join(o['t'] for o in og[:12]) + ' ' + bas['s']
        alanlar = alan_bul(og, m_tum, say_cal)
        ent_tum = set().union(*(o['ent'] for o in og))
        h1 = zaman_pencere(og, simdi, 1); h6 = zaman_pencere(og, simdi, 6); h24 = zaman_pencere(og, simdi, 24)
        yog = int(round(100 * (h6[0] - h6[2]) / max(1, h6[2]))) if (h6[0] or h6[2]) else 0
        yog = max(-100, min(900, yog))
        yog24 = int(round(100 * (h24[0] - h24[2]) / max(1, h24[2]))) if (h24[0] or h24[2]) else 0
        resmi = any('resmi' in o['nit'] for o in og)
        alt = {a: alt_etiket(a, metin_bas if a == 'adana' else m_tum) for a in alanlar if a in ALT_RX}
        gimg = bas.get('i') or next((o['i'] for o in sorted(og, key=lambda o: -len(o['tok'] & bas['tok'])) if o.get('i')), None)
        # farklı anlatılan ayrıntılar: ana başlıkla benzerliği düşük başlıklar
        farkli = []
        for o in og:
            if o is bas: continue
            jj = len(o['tok'] & bas['tok']) / max(1, len(o['tok'] | bas['tok']))
            if jj < .55 and len(farkli) < 4 and o['id'] not in kopya: farkli.append(dict(t=o['t'], p=o['kaynak']))
        c = dict(id=hashlib.md5(bas['l'].encode()).hexdigest()[:10], t=bas['t'], s=bas['s'], i=gimg, l=bas['l'], dil=bas['dil'],
                 diller=sorted({o['dil'] for o in og}), cat=bas['cat'], alanlar=alanlar, alt=alt, ks=len(kaynaklar), kb=kb,
                 ilk=int(min(o['z'] for o in og)), son=int(k['son']), h1=h1[0], h6=h6[0], h24=h24[0], k6=h6[1], k24=h24[1], yog=yog, yog24=yog24, h6o=h6[2], h24o=h24[2],
                 kaynaklar=kaynaklar, resmi=resmi, kanit=kanit_etiketi(og), farkli=farkli, n_tr=len(tr_og), sadece_yabanci=not tr_og,
                 plat_topluluk=all(o['plat'] in ('reddit', 'hn') or 'topluluk' in o['nit'] or 'erken-sinyal' in o['nit'] for o in og),
                 ulkeler=sorted(ent_tum & ULKE), liderler=sorted(ent_tum & LIDER), markalar=sorted(ent_tum & MARKA),
                 gundem_alt=gundem_alt(m_tum, ent_tum, bool(tr_og)), kategoriler=sorted({o['cat'] for o in og}))
        c['og'] = [dict(t=o['t'][:140], l=o['l'], p=o['kaynak'], z=int(o['z']), d=o['dil'], **({'kp': kopya[o['id']]} if o['id'] in kopya else {}))
                   for o in og[:10]]
        # Reels puanı
        p, kr, ceza, elen = reels_puanla(c, og, bas, m_tum, simdi, None)
        c['r'] = p; c['_kr'] = kr; c['_ceza'] = ceza; c['elen'] = elen
        # sıcaklık: yalnız çok kaynaklı konular "sıcak" sayılır
        for w, hh in (('1', h1), ('6', h6), ('24', h24)):
            c['sicak' + w] = round(hh[1] * 3 + hh[0] * .7, 1) if (kb >= 2 and hh[1] >= 1) else 0
        # yükselen: yoğunluk x çeşitlilik x ivme (hesap kullanıcıya gösterilir)
        yog_s = h6[0]; cesit = h6[1]; ivme = (h6[0] + 1) / (h6[2] + 1)
        c['yuk'] = dict(yogunluk=yog_s, cesit=cesit, ivme=round(ivme, 2), puan=round(math.log2(1 + yog_s) * math.log2(1 + cesit) * min(ivme, 6), 2) if (kb >= 2 and yog_s >= 2) else 0,
                        ilk_saat=round((simdi - c['ilk']) / 3600, 1))
        cikti.append((c, og, bas))
    return cikti

# ------------------------------------------------------------------ Videolar
VIDEO_SAAT = 72
VIDEO_SINIR = 150          # tür başına (tekno/turkiye/dunya/diger): yoğun haber kanalları teknolojiyi dışarı itmesin
VIDEO_SPOR = re.compile(r"maç özeti|geniş özet|\bgol(ler)?\b|uefa|süper lig|premier league|highlights|\bvs\.? ", re.I)
VIDEO_TEKNO = {'tech', 'samsung', 'ios', 'mac', 'mobil', 'win', 'auto', 'sci'}
def video_tur(o, c):
    """tekno | turkiye | dunya | diger. Kanal kategorisi önce; Türkçe gündem kanalı ya da Türkiye geçen konu 'turkiye'."""
    if VIDEO_SPOR.search(o['t']): return 'diger'
    if o['cat'] in VIDEO_TEKNO or set(c['alanlar']) & {'tekno', 'siber', 'bilim'} and o['cat'] not in ('sport', 'ent'): return 'tekno'
    if o['dil'] == 'tr' and o['cat'] in ('tr', 'eco', 'world') or TURKIYE.search(o['t']) and o['cat'] not in ('sport', 'ent'): return 'turkiye'
    if o['cat'] in ('world', 'eco'): return 'dunya'
    return 'diger'

def video_dil(t, dil):
    """Kanal dili yerine başlığın yazısı: Al Jazeera English gibi kanallar Arapça video da yükler."""
    for rx, d in ((r'[\u0600-\u06ff]', 'ar'), (r'[\u0400-\u04ff]', 'ru'), (r'[\u3040-\u30ff]', 'ja'), (r'[\uac00-\ud7af]', 'ko'), (r'[\u4e00-\u9fff]', 'zh')):
        if len(re.findall(rx, t)) >= 4: return d
    return dil

def video_saglik(src, dur, simdi):
    """Videolar başlığı için: etkin YouTube kanallarından kaçı son 3 saatte başarıyla çekildi."""
    yt = [s for s in src.values() if s.get('plat') == 'youtube' and 'youtube.com/feeds/' in s.get('url', '') and s.get('aktif') is not False]
    def zt(x):
        try: return datetime.fromisoformat(x).timestamp()
        except Exception: return 0
    guncel = sum(1 for s in yt if simdi - zt((dur.get(s['id']) or {}).get('son_basari', '')) <= 3 * 3600)
    son = max((zt((dur.get(s['id']) or {}).get('son_kontrol', '')) for s in yt), default=0)
    return dict(toplam=len(yt), guncel=guncel, son_deneme=int(son) or None)

def videolar_uret(cikti, simdi, generated, saglik=None):
    """YouTube kanallarının son 72 saatteki videoları. Video, ait olduğu haber kümesine bağlanır: kümede 2+ bağımsız kaynak
    varsa 'konu' alanı gündemdeki haberi gösterir (videonun konusu başka basında da yazılıyor)."""
    out = []
    for c, og, _ in cikti:
        for o in og:
            if o['plat'] != 'youtube' or simdi - o['z'] > VIDEO_SAAT * 3600: continue
            m = re.search(r'(?:[?&]v=|/shorts/)([\w-]{6,})', o['l'])
            d = dict(id='yt:' + (m.group(1) if m else o['id']), t=o['t'], l=o['l'], i=o['i'] or (m and 'https://i.ytimg.com/vi/%s/hqdefault.jpg' % m.group(1)), kanal=o['kaynak'], sid=o['sid'], dil=video_dil(o['t'], o['dil']), son=int(o['z']), tur=video_tur(o, c))
            if re.search(r'#shorts?\b|/shorts/', o['t'] + ' ' + o['l'], re.I): d['kisa'] = True
            if c['kb'] >= 2: d['konu'] = dict(id=c['id'], t=c['t'], kb=c['kb'])
            out.append(d)
    out.sort(key=lambda x: -x['son'])
    say = Counter(); sec = []
    for v in out:
        if say[v['tur']] < VIDEO_SINIR: say[v['tur']] += 1; sec.append(v)
    out = sec
    return dict(generated=generated, videolar=out, saglik=saglik or {}, kanallar=sorted({(v['sid'], v['kanal']) for v in out}),
                not_='Videolar kanalların kendi YouTube sayfasına bağlanır; içerik hakları kanallara aittir.')

def main():
    j = json.load(open('site/feeds.json', encoding='utf-8'))
    src = {s['id']: s for s in json.load(open('sources.json', encoding='utf-8'))}
    try: dur = json.load(open('site/kaynak-durum.json', encoding='utf-8'))
    except Exception: dur = {}
    simdi_dt = datetime.fromisoformat(j['generated']) if j.get('generated') else datetime.now(timezone.utc)
    simdi = simdi_dt.timestamp(); simdi_iso = simdi_dt.isoformat()
    ogeler, n72 = ogeler_kur(j, src, simdi)
    havuz = ozel_ad_havuzu([o['t'] for o in ogeler])
    kumeler = kumele_akis(ogeler, havuz)
    cikti = kumeler_kur(kumeler, simdi)
    # Reels alanı
    for c, og, bas in cikti:
        pr, alt = profil_bul(c, bas['t'])
        c['profil'] = pr; c['reels_alt'] = alt
    reels_son, reels_disi = reels_sec(cikti, havuz, simdi)
    elenen_say = Counter(c['elen'] for c, _, _ in cikti if c['elen'])
    reels_json = []
    for c, og, bas in reels_son:
        d = reels_kart(c, og, bas, simdi)
        reels_json.append(dict(id=c['id'], t=c['t'], i=c['i'], l=c['l'], profil=c.get('_reels_profil', c['profil']), alt=c['reels_alt'], alanlar=c['alanlar'], kb=c['kb'], ks=c['ks'], son=c['son'], ilk=c['ilk'], h6=c['h6'],
                               puan=c['r'], kriter=c['_kr'], yabanci=c['sadece_yabanci'], ceza=c['_ceza'], diller=c['diller'], kanit=c['kanit'], **d,
                               og=[dict(t=o['t'], l=o['l'], p=o['p'], z=o['z'], d=o['d']) for o in c['og'][:8]]))
    # kümeleri alanlara dağıt
    os.makedirs(CIKTI, exist_ok=True)
    # Arayüzün (index.tpl.html) okumadığı alanlar dosyalara yazılmaz (2026-11-20, hız raporu madde 7; grep ile doğrulandı).
    # Bellekteki küme (ekler.py, kisisel.py) bu alanları kullanmaya devam eder.
    OKUNMAYAN = {'cat', 'h1', 'h6', 'h24', 'h6o', 'h24o', 'k6', 'k24', 'sicak1', 'sicak6', 'sicak24', 'yog', 'yog24', 'resmi', 'reels_alt'}
    def sade(c):
        return {k: v for k, v in c.items() if not k.startswith('_') and k not in OKUNMAYAN and k not in ('yuk', 'r', 'elen', 'kategoriler', 'plat_topluluk', 'sadece_yabanci', 'n_tr', 'ulkeler', 'liderler', 'markalar')}
    alan_json = {}
    for a in ALANLAR:
        lst = [c for c, _, _ in cikti if a in c['alanlar']]
        lst.sort(key=lambda c: -(c['son'] / 3600.0 - 6 * max(0, 3 - c['kb']) / 3.0 * 0 + 0) if False else -c['son'])
        # alan içi sıralama: yakın zamanda güncellenen ve çok kaynaklı öne
        lst.sort(key=lambda c: -(min(c['kb'], 10) * 2 + c['h6'] * 1.5 + c['h24'] * .3) * math.exp(-(simdi - c['son']) / 3600 / 14))
        sec = lst[:KUME_ALAN_SINIR]
        var = {c['id'] for c in sec}
        ayrilan = Counter()
        for c in lst[KUME_ALAN_SINIR:]:
            if c['dil'] in ('tr', 'en') or ayrilan[c['dil']] >= DIL_AYRILAN or c['id'] in var: continue
            ayrilan[c['dil']] += 1; sec.append(c)
        alan_json[a] = sec
    def yaz(ad, nesne):
        with open(os.path.join(CIKTI, ad), 'w', encoding='utf-8') as f: json.dump(nesne, f, ensure_ascii=False, separators=(',', ':'))
    for a, lst in alan_json.items():
        yaz('kume-%s.json' % a, dict(generated=j['generated'], alan=a, ad=ALAN_AD[a], toplam=sum(1 for c, _, _ in cikti if a in c['alanlar']), kumeler=[sade(c) for c in lst]))
    yaz('reels.json', dict(generated=j['generated'], adaylar=reels_json, elenen=dict(elenen_say),
                           kriterler=[dict(k=k, w=w, ad=a) for k, w, a in KRITER],
                           not_='Tahmini editoryal değerlendirmedir (kural tabanlı), viral garantisi değildir.'))
    yaz('surum.json', dict(generated=j['generated']))   # arayüz tazelik yoklaması için (ozet.json 300 KB yerine birkaç bayt)
    yaz('videolar.json', videolar_uret(cikti, simdi, j['generated'], video_saglik(src, dur, simdi)))
    # ana ekran
    tum = [c for c, _, _ in cikti]
    def ozet_kume(c, w=None):
        d = dict(id=c['id'], t=c['t'], s=c['s'][:160], i=c['i'], l=c['l'], dil=c['dil'], ks=c['ks'], kb=c['kb'], ilk=c['ilk'], son=c['son'],
                 alanlar=c['alanlar'], gundem_alt=c['gundem_alt'], kaynaklar=c['kaynaklar'][:6], kanit=c['kanit'], diller=c['diller'])
        return d
    def tam(c, **ek):
        d = ozet_kume(c); d.update(og=c['og'], farkli=c['farkli'], s=c['s'][:220]); d.update(ek); return d
    sicak = {}
    for w in ('1', '6', '24'):
        lst = sorted([c for c in tum if c['sicak' + w] > 0], key=lambda c: -c['sicak' + w])[:12]
        sicak[w] = [tam(c, puan=c['sicak' + w]) for c in lst]
    yuk = [tam(c) for c in sorted([c for c in tum if c['yuk']['puan'] > 0 and c['yuk']['ilk_saat'] <= 48], key=lambda c: -c['yuk']['puan'])[:12]]
    son = [ozet_kume(c) for c in sorted(tum, key=lambda c: -c['son'])[:40]]   # Bugün ekranı 24 gösterir; arama indeksi aynı konuları zaten içerir
    # sayılar
    sayim = {a: dict(toplam=sum(1 for c in tum if a in c['alanlar']), son6=sum(1 for c in tum if a in c['alanlar'] and simdi - c['son'] < 6 * 3600), cok_kaynakli=sum(1 for c in tum if a in c['alanlar'] and c['kb'] >= 3)) for a in ALANLAR}
    # kaynaklar
    kay = []
    for sid, s in src.items():
        d = dur.get(sid) or {}
        durum = durum_hesapla(s, d, simdi_iso, simdi, n72)
        sb = d.get('son_basari')
        sessiz = int(simdi - datetime.fromisoformat(sb).timestamp()) if sb else None
        kay.append(dict(id=sid, ad=s['name'], calisma=s.get('calisma'), cat=s['cat'], dil=s['lang'], ulke=s.get('ulke'), tip=s.get('tip'), plat=s.get('plat'), url=s['url'], oncelik=s.get('oncelik'),
                        nitelik=s.get('nitelik', []), aktif=s.get('aktif', True), dogrulama=s.get('dogrulama'), pasif_neden=s.get('pasif_neden'),
                        son_kontrol=d.get('son_kontrol'), son_basari=sb, son_haber=d.get('son_haber'), son_hata=d.get('son_hata'), hata=d.get('hata'), kod=d.get('son_kod'),
                        ardisik=d.get('ardisik_basarisiz', 0), ms=d.get('ms'), haber72=n72.get(sid, 0), sessiz_sn=sessiz, durum=durum, bekle_kadar=d.get('bekle_kadar')))
    durum_say = Counter(k['durum'] for k in kay)
    yaz('kaynaklar.json', dict(generated=j['generated'], saglik=j.get('saglik', {}), kaynaklar=kay, durum_say=dict(durum_say)))
    # arama dizini
    idx = [dict(id=c['id'], t=c['t'], s=c['s'][:70], son=c['son'], kb=c['kb'], a=c['alanlar'], d=c['diller'], k=c['kaynaklar'][:5], e=sorted(set(c['liderler']) | set(c['markalar']) | set(c['ulkeler']))) for c in sorted(tum, key=lambda c: -c['son'])[:2600]]
    yaz('indeks.json', dict(generated=j['generated'], kayitlar=idx))
    # Akış 4: dil başına dosya (Dünya ekranı) ve dil özeti
    kay_dil = Counter(k['dil'] for k in kay if k['aktif'] and not k['id'].startswith('trends-'))
    dil_say = Counter(c['dil'] for c in tum)
    dil_ozet = []
    for d, n in dil_say.most_common():
        lst = sorted([c for c in tum if c['dil'] == d], key=lambda c: -(min(c['kb'], 10) * 2 + c['h6'] * 1.5 + c['h24'] * .3 + 1) * math.exp(-(simdi - c['son']) / 3600 / 10))[:DIL_DOSYA_SINIR]
        ad, tr_ad = DIL_AD.get(d, (d.upper(), d.upper()))
        alan_n = Counter(a for c in tum if c['dil'] == d for a in c['alanlar'])
        dil_ozet.append(dict(k=d, ad=ad, tr=tr_ad, n=n, n24=sum(1 for c in tum if c['dil'] == d and simdi - c['son'] < 86400), kaynak=kay_dil.get(d, 0),
                             alanlar=dict(alan_n), ilk=[dict(id=c['id'], t=c['t'], kb=c['kb'], son=c['son']) for c in lst[:3]]))
        yaz('dil-%s.json' % d, dict(generated=j['generated'], dil=d, ad=ad, tr=tr_ad, kumeler=[sade(c) for c in lst]))
    yaz('diller.json', dict(generated=j['generated'], diller=dil_ozet))
    # Akış 3 ekleri: Google Trends ve Güncelleme Radarı
    trend = E.trendler_uret(j['feeds'], tum, simdi)
    yaz('trendler.json', dict(generated=j['generated'], **trend))
    gunc = E.guncellemeler_uret(tum, simdi)
    yaz('guncellemeler.json', dict(generated=j['generated'], **gunc))
    tr_tr = (trend['ulkeler'].get('TR') or {}).get('trendler', [])
    ozet = dict(generated=j['generated'], uretim=datetime.now(timezone.utc).isoformat(), saglik=j.get('saglik', {}), kaynak_durum=dict(durum_say),
                sicak=sicak, yukselen=yuk, son=son, sayim=sayim, alanlar=[dict(k=a, ad=ALAN_AD[a]) for a in ALANLAR],
                alt_ad=dict(ALT_AD, **dict(GUNDEM_ALT)),
                trend_tr=[{k: v for k, v in x.items() if k not in ('hn', 'i')} | dict(hn=x['hn'][:1]) for x in tr_tr if x['aktif']][:15],
                guncelleme_ozet=[dict(k=u['k'], ad=u['ad'], n=u['n'], n24=u['n24'], son=u['son'], ilk=u['ogeler'][0]['t']) for u in gunc['urunler'][:12]],
                diller=[{k: v for k, v in x.items() if k != 'alanlar'} for x in dil_ozet],
                reels_ilk=[dict(id=r['id'], t=r['t'], puan=r['puan'], profil=r['profil'], kb=r['kb']) for r in reels_json[:6]],
                toplam=dict(haber=len(ogeler), kume=len(cikti), cok_kaynakli=sum(1 for c in tum if c['kb'] >= 3)),
                yontem=dict(
                    sicak='Sıcak konu: son 1/6/24 saatte haber yazan bağımsız kurum sayısı × 3 + o penceredeki haber sayısı × 0,7. En az 2 bağımsız kaynak şart; tek haberle konu sıcak sayılmaz. Ajans kopyaları ve aynı bültenden türeyen haberler tek kaynak sayılır.',
                    yukselen='Yükselen konu: log₂(1+haber yoğunluğu 6 sa) × log₂(1+bağımsız kurum 6 sa) × ivme (son 6 saatteki haber+1 / önceki 6 saatteki haber+1, en çok 6). En az 2 bağımsız kaynak, son 6 saatte en az 2 haber ve ilk haberi 48 saatten yeni olan konular girer.',
                    yogunluk='Yoğunluk değişimi: son penceredeki haber sayısı, bir önceki aynı uzunluktaki pencereyle karşılaştırılır.',
                    kume='Aynı olay: başlık/içerik kelime benzerliği ve ortak seyrek özel ad; farklı dillerde ortak varlık (ülke, lider, şirket) ve sayılar, 18 saat içinde. Yalnız başlık benzerliğiyle farklı olaylar birleştirilmez.'))
    yaz('ozet.json', ozet)
    boy = {f: os.path.getsize(os.path.join(CIKTI, f)) for f in sorted(os.listdir(CIKTI)) if f.endswith('.json')}
    print('oge', len(ogeler), 'kume', len(cikti), 'cok kaynakli(>=3 bagimsiz)', sum(1 for c in tum if c['kb'] >= 3), 'reels', len(reels_json), 'elenen', dict(elenen_say), 'reels disi', dict(reels_disi))
    print({a: v['toplam'] for a, v in sayim.items()})
    print({k: '%dKB' % (v / 1024) for k, v in boy.items()})

if __name__ == '__main__':
    main()
