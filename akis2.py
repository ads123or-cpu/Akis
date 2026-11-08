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
import masa as M   # sozcuk/kok yardımcıları ve STOP listesi eski hattan alınır

SAAT = 168                     # kümelemeye giren haber yaşı (saat)
CIKTI = 'site/data'
ALANLAR = ['gundem', 'tekno', 'siyaset', 'spor', 'ekonomi', 'bilim', 'siber', 'oto', 'eglence']
ALAN_AD = {'gundem': 'Gündem Radarı', 'tekno': 'Teknoloji Radarı', 'siyaset': 'Siyaset ve Jeopolitik', 'spor': 'Spor', 'ekonomi': 'Ekonomi ve Finans',
           'bilim': 'Bilim ve Uzay', 'siber': 'Siber Güvenlik', 'oto': 'Otomobil ve Ulaşım', 'eglence': 'Eğlence, Oyun, Kültür'}
KUME_ALAN_SINIR = 360          # alan başına dosyaya yazılan küme sayısı

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
    (r'anadolu|^aa$|\baa\b', 'aa'), (r'^trt|trt ', 'trt'), (r'^ntv|ntv ', 'ntv'), (r'hürriyet|hurriyet', 'hurriyet'), (r'milliyet', 'milliyet'),
    (r'sabah|a haber|ahaber|atv', 'sabah'), (r'sözcü|sozcu', 'sozcu'), (r'habertürk|haberturk', 'haberturk'), (r'cnn ?türk|cnnturk', 'cnnturk'),
    (r'bbc', 'bbc'), (r'\bdw\b|deutsche welle', 'dw'), (r'france ?24', 'france24'), (r'al ?jazeera|aljazeera', 'aljazeera'),
    (r'guardian', 'guardian'), (r'new york times|nytimes|^nyt', 'nyt'), (r'washington post|wapo', 'wapo'), (r'reuters', 'reuters'),
    (r'associated press|^ap$|ap news', 'ap'), (r'\bafp\b|agence france', 'afp'), (r'bloomberg', 'bloomberg'), (r'cnbc', 'cnbc'),
    (r'euronews', 'euronews'), (r'independent', 'independent'), (r'daily sabah', 'dailysabah'), (r'9to5mac|9to5google', '9to5'),
    (r'ars technica|arstechnica|ars$', 'ars'), (r'the verge|theverge|^verge', 'verge'), (r'google', 'googlehaber'), (r'youtube|^yt-', 'youtube'),
    (r'fanatik|a spor|aspor', 'sabah'),
]
ORG_RX = [(re.compile(a, re.I), b) for a, b in ORG_ALIAS]
AJANS_ISARET = re.compile(r'\((aa|dha|iha|ihlas|anka|reuters|afp|ap|apa|epa)\)|^(aa|dha|iha|reuters|afp|ap)\b|\b(reuters|afp|associated press)\b.{0,12}(reported|dedi|aktardı)', re.I)
AJANS_KURUM = {'aa', 'reuters', 'ap', 'afp', 'dha', 'iha', 'anka', 'xinhua', 'tass', 'yonhap'}
def kurum(p, sid):
    ad = re.sub(r'\.(com\.tr|com|net|org|info|tr|co\.uk|de|fr)$', '', (p or '').strip().lower().translate(M.TR))
    for rx, k in ORG_RX:
        if rx.search(ad): return k
    ad = ad.translate(str.maketrans('çğıöşü', 'cgiosu'))
    return re.sub(r'[^a-z0-9]+', '', ad)[:24] or sid

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
 'siyaset': re.compile(r"erdoğan|cumhurbaşkan|chp\b|akp\b|mhp\b|dem parti|tbmm|meclis|seçim|siyasi|muhalefet|iktidar|özgür özel|bahçeli|yaptırım|diplomasi|diplomat|zirve|büyükelçi|dışişleri|nato\b|birleşmiş milletler|güvenlik konseyi|trump|biden|harris|putin|zelen|netanyahu|macron|şi cinping|xi jinping|kongre|senato|beyaz saray|kremlin|brüksel|avrupa birliği|\bab\b|israil|filistin|gazze|hamas|hizbullah|iran|suriye|ukrayna|rusya|tayvan|savunma bakan|savunma sanayi|election|parliament|sanction|diplomat|summit|ambassador|president|prime minister|congress|senate|white house|kremlin|nato\b|united nations|security council|ceasefire|ateşkes|treaty|referendum|coalition|opposition party|defen[cs]e minister|sanctions", re.I),
 'savas': re.compile(r"savaş|çatışma|saldırı|füze|hava saldırısı|ateşkes|asker|ordu\b|cephe|işgal|bombardıman|silahlı|terör|drone saldırı|war\b|attack|missile|airstrike|strike|troops|frontline|invasion|military|ceasefire|offensive|bombing|terror", re.I),
 'siber': re.compile(r"siber|güvenlik açığ|sızıntı|veri ihlali|fidye|ransomware|zero-?day|malware|zararlı yazılım|oltalama|phishing|hacker|hack\b|saldırgan|cve-\d|vulnerab|data breach|botnet|exploit|backdoor|apt\d|cyberattack|cyber attack|ddos|kimlik avı|dolandırıcı", re.I),
 'spor_guclu': re.compile(r"maç|gol\b|futbol|basketbol|voleybol|süper lig|şampiyonlar ligi|teknik direktör|hakem|transfer|milli takım|nba|euroleague|uefa|fifa|olimpiyat|formula ?1|\bf1\b|motogp|tenis|wimbledon|grand slam|\batp\b|\bwta\b|ufc|boks|güreş|espor|e-spor|premier league|la liga|serie a|bundesliga|champions league|football|soccer|basketball|volleyball|tennis|coach|goal\b|stadium|tournament|athlete|olympic|grand prix|galatasaray|fenerbahçe|beşiktaş|trabzonspor", re.I),
 'ekonomi_guclu': re.compile(r"dolar|euro\b|altın|borsa|bist|enflasyon|faiz|merkez bankası|ekonomi|asgari ücret|emekli maaş|vergi|ihracat|ithalat|bütçe|petrol|akaryakıt|benzin|motorin|konut|kira artış|bitcoin|kripto|\bfed\b|inflation|interest rate|stocks?\b|wall street|gdp|tariff|oil price|currency|ticaret|piyasa|cari açık|işsizlik|unemployment|central bank|recession|ipo\b|nasdaq|s&p", re.I),
 'bilim_guclu': re.compile(r"nasa\b|uzay|gezegen|astronom|teleskop|asteroid|fosil|keşfetti|araştırmacılar|bilim insanları|genetik|\bdna\b|kanser tedavi|iklim değişikliği|kuantum|fizik|evren|mars\b|ay'a|space station|scientists|researchers|study finds|astronomers|physics|biology|quantum|exoplanet|galaxy|black hole|climate|vaccine|clinical trial|peer-reviewed", re.I),
 'oto_guclu': re.compile(r"otomobil|araba\b|otomotiv|elektrikli (araç|otomobil|araba|suv)|togg|tesla|bmw|mercedes|audi|volkswagen|porsche|ferrari|ford\b|fiat|renault|hyundai|toyota|byd\b|şarj istasyon|sürücüsüz|otonom|suv\b|sedan|electric vehicle|\bev\b|self-driving|autonomous|car maker|automaker|recall|lamborghini|mclaren|yeni model|raylı sistem|metro hattı|hızlı tren|havalimanı|thy\b|pegasus|ulaşım|trafik|köprü|otoyol|airline|flight", re.I),
 'tekno_guclu': re.compile(r"iphone|ipad|macbook|android|samsung|galaxy|xiaomi|huawei|google|pixel|microsoft|windows|openai|chatgpt|claude|gemini|anthropic|yapay zek|artificial intelligence|\bai\b|işlemci|ekran kart|nvidia|intel\b|amd\b|qualcomm|snapdragon|telefon|akıllı|bilgisayar|laptop|yazılım|uygulama|siber|robot|drone|oyun|playstation|xbox|steam|nintendo|teknoloji|whatsapp|instagram|tiktok|youtube|netflix|starlink|spacex|çip|yarı iletken|chip|startup|giyilebilir|akıllı saat|kulaklık|tablet|5g|bulut|veri merkezi|ios \d|one ui", re.I),
 'eglence_guclu': re.compile(r"dizi|film|sinema|oyuncu|şarkıcı|ünlü|konser|albüm|festival|oscar|gişe|fragman|yönetmen|survivor|masterchef|sanatçı|netflix dizisi|playstation|xbox|nintendo|steam|oyun|game|trailer|box office|movie|series|actor|singer|album|anime|hollywood|billboard|grammy|emmy|video game|viral|fenomen|tiktok", re.I),
 'gundem_guclu': re.compile(r"cinayet|gözaltı|tutuklandı|soruşturma|dava\b|mahkeme|savcılık|yargıtay|anayasa mahkemesi|hapis|ceza\b|belediye|valilik|yangın|sel\b|deprem|afet|kaza\b|yaralandı|hayatını kaybetti|okul|üniversite|sınav|yks|meb\b|öğrenci|hastane|sağlık bakan|salgın|aşı\b|ilaç|grip|zam\b|maaş|emekli|asgari ücret", re.I),
}
RE_HUKUK = re.compile(r"mahkeme|dava\b|savcı|yargıtay|anayasa mahkemesi|hakim|hâkim|tutuklan|beraat|iddianame|court|judge|lawsuit|indict|trial|verdict|sentenc", re.I)
RE_AFET = re.compile(r"deprem|sel\b|yangın|orman yangını|fırtına|hortum|çığ|heyelan|afet|afad|earthquake|flood|wildfire|storm|hurricane|tornado|landslide|tsunami|eruption|volkan", re.I)
RE_SAGLIK = re.compile(r"sağlık|hastane|salgın|aşı\b|ilaç|grip|kanser|tedavi|doktor|virüs|health|hospital|outbreak|vaccine|disease|cancer|virus|who\b", re.I)
RE_EGITIM = re.compile(r"okul|üniversite|sınav|yks|lgs|meb\b|öğrenci|öğretmen|eğitim|karne|school|university|exam|student|teacher|education", re.I)
RE_TOPLUM = re.compile(r"toplum|kadın|çocuk|göç|mülteci|yoksulluk|işsiz|emekli|asgari ücret|kira|barınma|şiddet|eşitlik|protesto|grev|society|migrant|refugee|poverty|protest|strike|housing", re.I)
ALT = {
 'tekno': [('apple', r'iphone|ipad|macbook|\bmac\b|ios \d|apple|airpods|vision pro|watchos'), ('samsung', r'samsung|galaxy|one ?ui|exynos'), ('android', r'android|pixel|xiaomi|redmi|huawei|honor|oneplus|oppo|realme|motorola|nothing phone|snapdragon'),
          ('google', r'\bgoogle\b|gemini|chrome|youtube|deepmind|waymo'), ('microsoft', r'microsoft|windows|copilot|xbox|azure|surface'), ('yz', r'yapay zek|chatgpt|openai|claude|anthropic|gemini|grok|deepseek|llm|\bai\b|artificial intelligence|midjourney|sora|copilot|mistral|perplexity'),
          ('telefon', r'telefon|smartphone|iphone|galaxy|pixel|katlanabilir|foldable'), ('bilgisayar', r'bilgisayar|laptop|macbook|notebook|\bpc\b|masaüstü|monitör'), ('cip', r'işlemci|yarı iletken|\bçip|chip|nvidia|\bamd\b|intel\b|qualcomm|tsmc|gpu|rtx|ryzen|snapdragon|dimensity'),
          ('siber', r'siber|güvenlik açığ|hack|ransomware|veri ihlali|malware|phishing'), ('sosyal', r'instagram|whatsapp|tiktok|x\.com|twitter|facebook|threads|snapchat|telegram|reddit|bluesky|sosyal medya|youtube'), ('uygulama', r'uygulama|\bapp\b|play store|app store|güncelleme|özellik|feature'),
          ('yazilim', r'yazılım|software|linux|github|windows|macos|\bapi\b|geliştirici|developer|open source|açık kaynak'), ('oyun', r'oyun|playstation|xbox|nintendo|steam|gta|game|gaming|epic games'), ('oto-tekno', r'otonom|sürücüsüz|tesla|togg|elektrikli|autopilot|self-driving'),
          ('robotik', r'robot|insansı|humanoid|drone|boston dynamics|optimus'), ('giyilebilir', r'akıllı saat|giyilebilir|apple watch|galaxy watch|akıllı bileklik|smartwatch|wearable|airpods|kulaklık|smart ring'), ('ev', r'elektrikli araç|elektrikli otomobil|\bev\b|şarj|batarya|battery')],
 'siyaset': [('tr-siyaset', r'erdoğan|chp\b|akp\b|mhp\b|dem parti|tbmm|meclis|özgür özel|bahçeli|belediye başkan|ekrem imamoğlu|türkiye siyaset|turkish politics'), ('abd', r'\babd\b|amerika|trump|biden|harris|kongre|senato|beyaz saray|washington|\bu\.?s\.?\b|congress|white house'), ('avrupa', r'avrupa|\bab\b|brüksel|almanya|fransa|macron|scholz|merz|ingiltere|starmer|european|\beu\b|brussels|germany|france|britain'),
          ('cin', r'\bçin\b|şi cinping|pekin|tayvan|china|beijing|taiwan|xi jinping'), ('rusya', r'rusya|putin|kremlin|moskova|ukrayna|zelen|russia|moscow|ukraine'), ('orta-dogu', r'orta doğu|suriye|irak|iran|lübnan|yemen|körfez|suudi|katar|middle east|syria|iraq|lebanon|yemen|saudi|gulf'),
          ('israil-filistin', r'israil|filistin|gazze|hamas|hizbullah|netanyahu|batı şeria|israel|palestin|gaza|hezbollah|west bank'), ('nato', r'\bnato\b'), ('bm', r'birleşmiş milletler|\bbm\b|güvenlik konseyi|united nations|security council|\bun\b'), ('secim', r'seçim|oy\b|sandık|anket|referandum|election|poll\b|ballot|referendum|vote'),
          ('kriz', r'kriz|gerilim|büyükelçi|sınır|ateşkes|müzakere|crisis|tension|ambassador|ceasefire|negotiat'), ('yaptirim', r'yaptırım|ambargo|sanction|embargo|tariff|gümrük'), ('savunma', r'savunma|silah|füze|f-?35|f-?16|tank|donanma|hava kuvvetleri|baykar|aselsan|defen[cs]e|missile|fighter jet|navy|weapon|military')],
 'spor': [('futbol', r'futbol|süper lig|şampiyonlar ligi|avrupa ligi|premier league|la liga|serie a|bundesliga|football|soccer|champions league|galatasaray|fenerbahçe|beşiktaş|trabzonspor|teknik direktör|hakem|maç\b|gol\b'), ('basketbol', r'basketbol|nba|euroleague|basketball|a milli basketbol|tbf'), ('tenis', r'tenis|tennis|wimbledon|roland garros|us open|australian open|\batp\b|\bwta\b'), ('f1', r'formula ?1|\bf1\b|grand prix|verstappen|hamilton|leclerc'),
         ('motor', r'motogp|motorsport|ralli|\bwrc\b|superbike|nascar|indycar|sofuoğlu|tuncer'), ('voleybol', r'voleybol|volleyball|filenin sultanları|vakıfbank|eczacıbaşı|tvf'), ('olimpiyat', r'olimpiyat|olympic|paralimpik|paralympic'), ('dovus', r'ufc|boks|boxing|güreş|wrestling|mma|judo|karate|taekwondo'),
         ('espor', r'espor|e-spor|esports?|league of legends|valorant|counter-strike|dota'), ('transfer', r'transfer|bonservis|sözleşme imzaladı|kiralık|loan deal|signs? (a )?(contract|deal)|here we go'), ('kulup', r'galatasaray|fenerbahçe|beşiktaş|trabzonspor|başakşehir|real madrid|barcelona|manchester|liverpool|bayern|juventus|psg|arsenal|chelsea'), ('milli', r'milli takım|a milli|national team|türkiye milli')],
 'ekonomi': [('doviz', r'dolar|euro\b|kur\b|döviz|dollar|currency|forex'), ('altin', r'altın|gram altın|ons|gold'), ('borsa', r'borsa|bist|hisse|wall street|nasdaq|stocks?\b|s&p|dow jones'), ('enflasyon', r'enflasyon|tüfe|üfe|inflation|cpi\b'), ('faiz', r'faiz|merkez bankası|tcmb|\bfed\b|ecb|interest rate|central bank'), ('kripto', r'bitcoin|kripto|ethereum|crypto|btc\b|stablecoin'),
             ('enerji', r'petrol|akaryakıt|benzin|motorin|doğalgaz|elektrik zammı|brent|oil|gas price|opec|energy'), ('istihdam', r'asgari ücret|maaş|işsizlik|emekli|zam\b|istihdam|unemployment|wages|jobs report'), ('sirket', r'bilanço|kâr|zarar|şirket|ihale|satın alma|birleşme|earnings|merger|acquisition|revenue|ipo\b'), ('ticaret', r'ihracat|ithalat|ticaret|gümrük|tariff|trade war|export|import'), ('konut', r'konut|kira|tapu|mortgage|housing|rent')],
 'bilim': [('uzay', r'nasa|uzay|gezegen|astronom|teleskop|asteroid|mars\b|ay\b|spacex|esa\b|space|planet|galaxy|exoplanet|rocket|artemis|iss\b'), ('saglik', r'sağlık|kanser|aşı|ilaç|tedavi|virüs|salgın|health|cancer|vaccine|drug|disease|clinical|medicine|who\b'), ('iklim', r'iklim|küresel ısınma|sera gazı|buzul|kuraklık|climate|warming|emission|glacier|drought'), ('fizik', r'fizik|kuantum|parçacık|cern|physics|quantum|particle'), ('biyoloji', r'biyoloji|genetik|\bdna\b|fosil|evrim|hayvan|bitki|biology|genetic|fossil|species|evolution'), ('yz-arastirma', r'yapay zek|makine öğren|nöral|machine learning|neural|deep learning|arxiv|llm')],
 'siber': [('acik', r'güvenlik açığ|cve-\d|zero-?day|vulnerab|exploit|patch|yama'), ('fidye', r'fidye|ransomware'), ('veri-ihlali', r'veri ihlali|sızıntı|sızdı|data breach|leak'), ('oltalama', r'oltalama|phishing|dolandırıcı|scam|kimlik avı|smishing'), ('devlet-aktoru', r'apt\d|devlet destekli|state-sponsored|nation-state|lazarus|sandworm|çin bağlantılı|rus bağlantılı'), ('zararli', r'malware|zararlı|trojan|botnet|backdoor|stealer|spyware|casus yazılım')],
 'oto': [('elektrikli', r'elektrikli|\bev\b|şarj|batarya|tesla|byd|togg|electric'), ('marka', r'bmw|mercedes|audi|volkswagen|porsche|ferrari|ford\b|fiat|renault|hyundai|toyota|honda|volvo|skoda|lamborghini|mclaren|nissan'), ('otonom', r'otonom|sürücüsüz|autopilot|fsd|self-driving|robotaxi|waymo'), ('ulasim', r'havalimanı|hızlı tren|metro|köprü|otoyol|thy\b|pegasus|havayolu|airline|flight|railway|airport|ulaşım'), ('yeni-model', r'yeni model|tanıtıldı|unveil|launch|debut|concept|facelift'), ('motorsporu', r'formula ?1|\bf1\b|motogp|ralli')],
 'eglence': [('oyun', r'oyun|playstation|xbox|nintendo|steam|gta|game|gaming|epic games|switch 2'), ('film-dizi', r'dizi|film|sinema|fragman|gişe|yönetmen|netflix|disney|hbo|prime video|trailer|box office|movie|series|streaming|oscar|emmy'), ('muzik', r'şarkıcı|albüm|konser|müzik|billboard|grammy|spotify|album|singer|concert|tour\b'), ('kultur', r'sergi|tiyatro|kitap|festival|müze|edebiyat|exhibition|theater|museum|book|festival'), ('internet', r'viral|fenomen|trend|tiktok|youtube|meme|influencer|streamer'), ('anime', r'anime|manga|crunchyroll')],
}
ALT_RX = {a: [(k, re.compile(v, re.I)) for k, v in L] for a, L in ALT.items()}
ALT_AD = {'apple': 'Apple', 'samsung': 'Samsung', 'android': 'Android', 'google': 'Google', 'microsoft': 'Microsoft', 'yz': 'Yapay zekâ', 'telefon': 'Telefon', 'bilgisayar': 'Bilgisayar', 'cip': 'Çip', 'siber': 'Siber', 'sosyal': 'Sosyal medya', 'uygulama': 'Uygulama', 'yazilim': 'Yazılım', 'oyun': 'Oyun', 'oto-tekno': 'Otomobil teknolojisi', 'robotik': 'Robotik', 'giyilebilir': 'Giyilebilir', 'ev': 'Elektrikli araç/batarya',
          'tr-siyaset': 'Türkiye siyaseti', 'abd': 'ABD', 'avrupa': 'Avrupa', 'cin': 'Çin', 'rusya': 'Rusya-Ukrayna', 'orta-dogu': 'Orta Doğu', 'israil-filistin': 'İsrail-Filistin', 'nato': 'NATO', 'bm': 'BM', 'secim': 'Seçimler', 'kriz': 'Diplomatik kriz', 'yaptirim': 'Yaptırım ve ticaret', 'savunma': 'Savunma',
          'futbol': 'Futbol', 'basketbol': 'Basketbol', 'tenis': 'Tenis', 'f1': 'Formula 1', 'motor': 'Motor sporları', 'voleybol': 'Voleybol', 'olimpiyat': 'Olimpiyat', 'dovus': 'Dövüş sporları', 'espor': 'E-spor', 'transfer': 'Transfer', 'kulup': 'Kulüp', 'milli': 'Milli takımlar',
          'doviz': 'Döviz', 'altin': 'Altın', 'borsa': 'Borsa', 'enflasyon': 'Enflasyon', 'faiz': 'Faiz ve merkez bankaları', 'kripto': 'Kripto', 'enerji': 'Enerji', 'istihdam': 'Maaş ve istihdam', 'sirket': 'Şirket haberleri', 'ticaret': 'Dış ticaret', 'konut': 'Konut',
          'uzay': 'Uzay', 'saglik': 'Sağlık', 'iklim': 'İklim', 'fizik': 'Fizik', 'biyoloji': 'Biyoloji', 'yz-arastirma': 'Yapay zekâ araştırmaları', 'acik': 'Güvenlik açığı', 'fidye': 'Fidye yazılımı', 'veri-ihlali': 'Veri ihlali', 'oltalama': 'Dolandırıcılık/oltalama', 'devlet-aktoru': 'Devlet destekli', 'zararli': 'Zararlı yazılım',
          'elektrikli': 'Elektrikli', 'marka': 'Markalar', 'otonom': 'Otonom sürüş', 'ulasim': 'Ulaşım', 'yeni-model': 'Yeni model', 'motorsporu': 'Motor sporu', 'film-dizi': 'Film ve dizi', 'muzik': 'Müzik', 'kultur': 'Kültür-sanat', 'internet': 'İnternet fenomenleri', 'anime': 'Anime'}
GUNDEM_ALT = [('turkiye', 'Türkiye'), ('dunya', 'Dünya'), ('siyaset', 'Siyaset'), ('diplomasi', 'Diplomasi'), ('savas', 'Savaş ve güvenlik'), ('ekonomi', 'Ekonomi'), ('toplum', 'Toplum'), ('hukuk', 'Hukuk'), ('afet', 'Afet'), ('saglik', 'Sağlık'), ('egitim', 'Eğitim')]
RE_DIPLO = re.compile(r"diplomasi|diplomat|büyükelçi|zirve|müzakere|görüşme|dışişleri|ateşkes|anlaşma imza|summit|ambassador|talks|negotiat|treaty|foreign minister", re.I)

# ------------------------------------------------------------------ Reels puan kuralları (v2)
CARPICI = M.CARPICI
ETKI = re.compile(r"özellik|feature|geliyor|geldi|rolling out|gizli|hidden|ipucu|nasıl|ücretsiz|free\b|bedava|kapat|silin|dikkat|uyarı|warning|dolandır|scam|phishing|oltalama|güvenlik açığı|vulnerab|sızdı|sızıntı|leak|fiyat|zam\b|indirim|vergi|maaş|emekli|asgari ücret|kira|faiz|yasak|yasa\b|karar|düzenleme|zorunlu|erişim|çöktü|outage|kesinti|deprem|sel\b|uyarısı|alarm|kota|ceza|ehliyet|sınav|okul|tatil|akaryakıt|benzin|elektrik|doğalgaz|ban\b|law\b|rule|tax|price|salary|recall|geri çağır|cuts|layoff|işten çıkar", re.I)
TURKIYE = re.compile(r"türkiye|türk\b|türkiye'|togg|btk|imei|\btl\b|istanbul|ankara|izmir|baykar|aselsan|turkcell|vodafone tr|türk telekom|erdoğan|tbmm|\bmeb\b|yks|tcmb|bist|galatasaray|fenerbahçe|beşiktaş|trabzonspor|milli takım|turkey|turkish|türkiye'nin", re.I)
HIKAYE = re.compile(r"neden|nasıl|iddia|sızdı|kaçtı|çöktü|yıkıldı|karşı karşıya|kapışma|çatışma|istifa|tutuklan|yasaklandı|iflas|dönüş|sürpriz|beklenmedik|ilk kez|rekor|krizi|skandal|perde arkası|gerçek yüzü|revealed|why|how|fired|resign|banned|collapse|scandal|comeback|surprise|rivalry|feud|crackdown|ousted|secret", re.I)
IDDIA = re.compile(r"iddia|söylentiler?|sızıntı|sızdı|rumor|leak|reportedly|allegedly|claims?\b|unconfirmed|doğrulanmadı|kulis", re.I)
HASSAS = re.compile(r"ölü|öldü|hayatını kaybet|cenaze|katliam|saldırı|bombalı|savaş|terör|tecavüz|taciz|istismar|intihar|killed|dead|massacre|attack|war\b|terror|rape|abuse|suicide", re.I)
RUTIN = M.RUTIN
ZAYIF = M.ZAYIF
# Reels'e HİÇ girmeyenler (yalnız bunlar). Haber türü değil, içerik niteliği: spam/alışveriş/yayın rehberi ve özel kişilerin acısı.
ELE = [
 ('alisveris/indirim', re.compile(r"\b(deals?|coupon|promo code|black friday|prime day|\bsave \$?\d|\d+% off|indirim kodu|kupon|fırsat ürünleri)\b", re.I)),
 ('yayin rehberi', re.compile(r"canlı izle|nereden izlenir|hangi kanalda|şifresiz|how to watch|live stream|watch .{3,40} (free|online)|maç kadrosu|muhtemel 11", re.I)),
 ('burc/kumar', re.compile(r"burç yorum|günlük burç|horoscope|bahis|casino|jackpot|iddaa tahmin|kesin kupon", re.I)),
 ('ozel kisi trajedisi', re.compile(r"tecavüz|cinsel istismar|taciz|çocuk istismarı|intihar etti|kadın cinayeti|cinayete kurban|cesedi bulundu|rape\b|child abuse|murdered (his|her) (wife|girlfriend|child)", re.I)),
 ('sponsorlu', re.compile(r"\bsponsored\b|işbirliğiyle|advertorial|ücretli içerik", re.I)),
]
# Puan CEZASI (eleme değil): yalnız gerçekten düşük potansiyelli kalıplar. Siyaset/spor/gündem bu listede değildir.
CEZA = [
 ('rutin sürüm/yama notu', RUTIN, 8, ('tekno', 'siber')),
 ('kurumsal finans dili', re.compile(r"\b(earnings|quarterly|funding round|raises \$|series [abc]\b|valuation|market cap|analyst|bilanço|piyasa değeri|hisse geri alım)\b", re.I), 10, ('tekno',)),
 ('ürün incelemesi/liste', re.compile(r"\breview:|incelemesi|\bbest .{0,30} (of|for)\b|en iyi \d+|haftanın|weekly roundup|podcast|newsletter", re.I), 8, ('tekno', 'oto', 'eglence')),
 ('yalnızca yerel olay', re.compile(r"\b(mahallesinde|köyünde|ilçesinde|sokakta)\b.*\b(yaralandı|çarpıştı|kavga)\b|işçi servisi|servis aracı kaza", re.I), 10, ('gundem',)),
 ('yalnız ABD pazarı', re.compile(r"\b(us-only|only in the us|yalnızca abd|sadece abd|verizon|t-mobile|at&t|walmart|costco|best buy)\b", re.I), 8, ('tekno',)),
]
KRITER = [('guncellik', 12, 'Güncellik'), ('haber', 12, 'Haber değeri'), ('etki', 12, 'Hayata etki'), ('ozgun', 8, 'Özgünlük'), ('saskin', 10, 'Şaşırtıcılık'), ('hikaye', 10, 'Hikâye potansiyeli'),
           ('gorsel', 8, 'Görsel malzeme'), ('dogrulama', 12, 'Çok kaynakta doğrulanma'), ('turk', 8, 'Türkçe izleyiciye uygunluk'), ('ilk3', 8, 'İlk 3 saniyede anlatılabilirlik')]

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
    for k, rx in (('tekno', 'tekno_guclu'), ('bilim', 'bilim_guclu'), ('ekonomi', 'ekonomi_guclu'), ('spor', 'spor_guclu'), ('oto', 'oto_guclu'), ('eglence', 'eglence_guclu')):
        n_rx = len(KURAL[rx].findall(m)); n_k = kay.get(k, 0)
        # kaynak bölümü ve içerik birlikte tanık olmalı: bölüm tek başına ya da tek bir kelime yetmez
        if (n_k >= 2 and n_rx >= 1) or (n_k >= 1 and n_rx >= 2) or n_rx >= 3 or (n_k >= 1 and n_rx >= 1 and k in ('spor', 'oto', 'bilim', 'eglence')): a.add(k)
    if KURAL['siber'].search(m): a.add('siber')
    if KURAL['siyaset'].search(m) and (kay.get('siyaset') or kay.get('gundem') or len(KURAL['siyaset'].findall(m)) >= 2): a.add('siyaset')
    # Gündem: genel haber akışı (teknoloji/spor/magazin dışı kalanlar dahil siyaset, toplum, hukuk...)
    gundem_kay = kay.get('gundem', 0) + kay.get('siyaset', 0)
    if gundem_kay and (a - {'siyaset', 'ekonomi', 'siber'} == set() or 'siyaset' in a or KURAL['gundem_guclu'].search(m) or KURAL['savas'].search(m)):
        a.add('gundem')
    if 'siyaset' in a and not (a & {'gundem'}) and gundem_kay: a.add('gundem')
    if not a:
        top = max(kay, key=kay.get) if kay else 'gundem'
        a.add(top)
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
def reels_puanla(c, og, bas, metin, simdi, kay_ad):
    """c: küme özeti. Dönüş: (puan, kriter dict 0-10, gerekçe listesi, elenme nedeni|None, cezalar)"""
    t = bas['t']; yas = (simdi - c['son']) / 3600
    kr = {}
    kr['guncellik'] = 10 if yas <= 3 else 8.5 if yas <= 6 else 7 if yas <= 12 else 5 if yas <= 24 else 3 if yas <= 48 else 1.5
    kr['haber'] = min(10, c['h6'] * 1.6 + c['h24'] * .25 + (3 if c['kb'] >= 4 else 0) + (2 if c['resmi'] else 0))
    kr['etki'] = min(10, (6 if ETKI.search(t) else 0) + (3 if ETKI.search(metin) else 0) + (2 if 'turkiye' in c['gundem_alt'] and KURAL['gundem_guclu'].search(t) else 0))
    kr['ozgun'] = 5 + (2 if c['sadece_yabanci'] and c['kb'] >= 2 else 0) + (1.5 if c['n_tr'] <= 2 and c['kb'] >= 3 else 0) - (3 if RUTIN.search(t) else 0) - (1.5 if c['kb'] >= 8 else 0) + (1 if c['farkli'] else 0)
    vur = CARPICI.findall(metin)
    kr['saskin'] = min(10, (6 if CARPICI.search(t) else 0) + min(4, len(vur)) + (1 if re.search(r'\d{2,}', t) else 0))
    kr['hikaye'] = min(10, (5 if HIKAYE.search(t) else 0) + (2 if HIKAYE.search(metin) else 0) + min(3, len(og) / 3.0))
    kr['gorsel'] = (6 if c['i'] else 0) + (2 if any(o['plat'] == 'youtube' for o in og) else 0) + (2 if c['resmi'] or len([o for o in og if o['i']]) >= 3 else 0)
    kr['dogrulama'] = 9.5 if c['kb'] >= 4 else 8 if c['kb'] == 3 else 6 if c['kb'] == 2 else (4.5 if c['resmi'] else 1.5)
    kr['turk'] = min(10, (6 if TURKIYE.search(metin) else 0) + min(3, c['n_tr'] * 1.2) + (2 if c['alanlar'] and set(c['alanlar']) & {'tekno', 'ekonomi'} and c['n_tr'] else 0))
    kr['ilk3'] = min(10, (3 if re.search(r'\d', t) else 0) + (3 if CARPICI.search(t) else 0) + (2 if 25 <= len(t) <= 95 else 0) + (2 if len(M.varlik(t)) >= 2 else 0))
    for a in kr: kr[a] = round(max(0, min(10, kr[a])), 1)
    p = sum(kr[k] * w for k, w, _ in KRITER) / 10.0
    ceza = []
    for ad, rx, d, alanlar in CEZA:
        if set(c['alanlar']) & set(alanlar) and rx.search(t) and not (kr['saskin'] >= 6 and ad.startswith('rutin')):
            p -= d; ceza.append(ad)
    if c['kb'] < 2 and not c['resmi'] and c['plat_topluluk']: p -= 6; ceza.append('yalnız topluluk kaynağı (erken sinyal)')
    if c['kb'] < 2 and not c['resmi'] and not c['plat_topluluk']: p -= 3; ceza.append('tek bağımsız kaynak')
    elen = None
    for ad, rx in ELE:
        if rx.search(t): elen = ad; break
    return round(max(0, p), 1), kr, ceza, elen

def profil_bul(c, m):
    pr = []
    a = set(c['alanlar'])
    if 'tekno' in a or 'siber' in a: pr.append('teknoloji')
    if 'gundem' in a or 'ekonomi' in a: pr.append('gundem')
    if 'siyaset' in a: pr.append('siyaset')
    if 'spor' in a: pr.append('spor')
    alt = []
    if 'bilim' in a: alt.append('bilim')
    if 'siber' in a: alt.append('siber')
    if 'oto' in a: alt.append('oto'); pr = pr or ['teknoloji']
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

def hook_uret(c, bas, ayrinti):
    """3 açılış cümlesi (kural şablonu; taslaktır). Uydurma iddia içermez: yalnız kümeden hesaplanan değerleri kullanır."""
    t = kisa_baslik(bas['t'])
    sayi = re.search(r'\d[\d.,]*\s?(?:%|milyar|milyon|bin|TL|dolar|euro|gün|yıl|saat|dakika|km|GB|MP|mAh|kişi)?', bas['t'])
    h = []
    if sayi and sayi.group(0).strip(): h.append('%s sayısı bugün gündemin ortasında: %s' % (sayi.group(0).strip(), t))
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
    aci = next(t for f, t in ACI if f(c, metin))
    oz = cumle(bas['s']) or bas['t']
    onerilen = bas['t'] if len(bas['t']) <= 72 else bas['t'][:69].rsplit(' ', 1)[0] + '…'
    en_iyi = sorted(kr.items(), key=lambda kv: -kv[1] * dict((k, w) for k, w, _ in KRITER)[kv[0]])[:3]
    gerekce = '%s: %s/10' % (', '.join(a for a in [dict((k, a) for k, _, a in KRITER)[k] for k, _ in en_iyi]), ' · '.join('%.0f' % v for _, v in en_iyi))
    return dict(oneri_baslik=onerilen, ozet=oz, neden_gundemde='; '.join(neden), carpici_ayrinti=ayrinti or 'Belirgin tek bir ayrıntı bulunamadı; kaynak başlıklarındaki farka bakın.',
                turk_onemi=tr, dogrulama=dog, gorsel_potansiyel='; '.join(gor), hooklar=hook_uret(c, bas, ayrinti), aci=aci,
                puan_gerekce=gerekce, risk=risk)

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

def main():
    j = json.load(open('site/feeds.json', encoding='utf-8'))
    src = {s['id']: s for s in json.load(open('sources.json', encoding='utf-8'))}
    try: dur = json.load(open('site/kaynak-durum.json', encoding='utf-8'))
    except Exception: dur = {}
    simdi_dt = datetime.fromisoformat(j['generated']) if j.get('generated') else datetime.now(timezone.utc)
    simdi = simdi_dt.timestamp(); simdi_iso = simdi_dt.isoformat()
    ogeler, gor = [], set()
    n72 = Counter()
    for sid, f in j['feeds'].items():
        s = src.get(sid, {})
        if s.get('nitelik') and 'erken-sinyal' in s['nitelik'] and 'trends' in sid: continue   # trend sayfaları ayrı (Reels trendleri)
        for it in f['items']:
            l = it.get('l'); t = (it.get('t') or '').strip()
            if not l or not t or not it.get('d'): continue
            try: z = datetime.fromisoformat(it['d']).timestamp()
            except Exception: continue
            n72[sid] += 1
            if simdi - z > SAAT * 3600 or z > simdi + 300: continue
            kl = kanonik(l) if 'news.google.com' not in l else l
            anahtar = kl if 'news.google.com' not in l else (re.sub(r'\W+', '', t.lower())[:60] + (it.get('p') or ''))
            if anahtar in gor: continue
            gor.add(anahtar)
            p = (it.get('p') or '').strip()
            if not p or p.startswith('http'): p = f['name']
            org = kurum(p, sid)
            cat = it.get('c') or f['cat']
            metin = t + ' ' + (it.get('s') or '')[:120]
            o = dict(id=hashlib.md5(l.encode()).hexdigest()[:10], t=t, l=l, z=z, s=(it.get('s') or '')[:220], i=it.get('i'), cat=cat, dil=f['lang'], kaynak=p, sid=sid, org=org,
                     plat=f.get('plat', 'web'), n=it.get('n'), tip=s.get('tip', 'ana akim'), nit=set(s.get('nitelik') or []), cal=s.get('calisma') or 'gundem', ulke=s.get('ulke', ''))
            o['tok'] = tok2(t); o['ent'] = canon_bul(t); o['var'] = M.varlik(t) | {'@' + e for e in o['ent']}
            ogeler.append(o)
    kumeler = kumele2(ogeler)
    # Büyük kümeleri ve olay bütünlüğünü korumak için: çok büyük kümelerde (>40 haber) yalnız en yakın 40 haber tutulur.
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
        alt = {a: alt_etiket(a, m_tum) for a in alanlar if a in ALT_RX}
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
        c['og'] = [dict(t=o['t'][:140], l=o['l'], p=o['kaynak'], z=int(o['z']), d=o['dil'], tp=o['tip'], **({'kp': kopya[o['id']]} if o['id'] in kopya else {}))
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
    # Reels alanı
    for c, og, bas in cikti:
        pr, alt = profil_bul(c, bas['t'])
        c['profil'] = pr; c['reels_alt'] = alt
    reels = []
    gorulen_tok = []
    for c, og, bas in sorted(cikti, key=lambda x: -x[0]['r']):
        if c['r'] < 38 or c['elen'] or c['kb'] < 1: continue
        if (simdi - c['son']) > 72 * 3600: continue
        # aynı olayın ikinci kartı: kümeler zaten birleşik; yine de çok benzer başlık varsa atla
        tk = M.sozcuk(c['t']); tks = {M.kok(w) for w in tk}
        if any(len(tks & q) / max(1, len(tks | q)) >= .5 for q in gorulen_tok[-80:]): continue
        gorulen_tok.append(tks)
        reels.append((c, og, bas))
    # çıktı: reels (profil dengeli: her profilden en fazla 60)
    prof_say = Counter(); reels_son = []
    for c, og, bas in reels:
        if all(prof_say[p] >= 60 for p in c['profil']): continue
        for p in c['profil']: prof_say[p] += 1
        reels_son.append((c, og, bas))
        if len(reels_son) >= 220: break
    elenen_say = Counter(c['elen'] for c, _, _ in cikti if c['elen'])
    reels_json = []
    for c, og, bas in reels_son:
        d = reels_kart(c, og, bas, simdi)
        reels_json.append(dict(id=c['id'], t=c['t'], i=c['i'], l=c['l'], profil=c['profil'], alt=c['reels_alt'], alanlar=c['alanlar'], kb=c['kb'], ks=c['ks'], son=c['son'], ilk=c['ilk'], h6=c['h6'],
                               puan=c['r'], kriter=c['_kr'], ceza=c['_ceza'], diller=c['diller'], kanit=c['kanit'], **d,
                               og=[dict(t=o['t'], l=o['l'], p=o['p'], z=o['z'], d=o['d']) for o in c['og'][:8]]))
    # kümeleri alanlara dağıt
    os.makedirs(CIKTI, exist_ok=True)
    def sade(c):
        d = {k: v for k, v in c.items() if not k.startswith('_') and k not in ('yuk', 'r', 'elen', 'kategoriler', 'plat_topluluk', 'sadece_yabanci', 'n_tr', 'ulkeler', 'liderler', 'markalar')}
        d['ul'] = c['ulkeler']; d['ld'] = c['liderler']; d['mk'] = c['markalar']
        d['yuk'] = c['yuk']['puan']
        return d
    alan_json = {}
    for a in ALANLAR:
        lst = [c for c, _, _ in cikti if a in c['alanlar']]
        lst.sort(key=lambda c: -(c['son'] / 3600.0 - 6 * max(0, 3 - c['kb']) / 3.0 * 0 + 0) if False else -c['son'])
        # alan içi sıralama: yakın zamanda güncellenen ve çok kaynaklı öne
        lst.sort(key=lambda c: -(min(c['kb'], 10) * 2 + c['h6'] * 1.5 + c['h24'] * .3) * math.exp(-(simdi - c['son']) / 3600 / 14))
        sec = lst[:KUME_ALAN_SINIR]
        alan_json[a] = sec
    def yaz(ad, nesne):
        with open(os.path.join(CIKTI, ad), 'w', encoding='utf-8') as f: json.dump(nesne, f, ensure_ascii=False, separators=(',', ':'))
    for a, lst in alan_json.items():
        yaz('kume-%s.json' % a, dict(generated=j['generated'], alan=a, ad=ALAN_AD[a], toplam=sum(1 for c, _, _ in cikti if a in c['alanlar']), kumeler=[sade(c) for c in lst]))
    yaz('reels.json', dict(generated=j['generated'], adaylar=reels_json, elenen=dict(elenen_say),
                           kriterler=[dict(k=k, w=w, ad=a) for k, w, a in KRITER],
                           not_='Tahmini editoryal değerlendirmedir (kural tabanlı), viral garantisi değildir.'))
    # ana ekran
    tum = [c for c, _, _ in cikti]
    def ozet_kume(c, w=None):
        d = dict(id=c['id'], t=c['t'], s=c['s'][:160], i=c['i'], l=c['l'], dil=c['dil'], ks=c['ks'], kb=c['kb'], ilk=c['ilk'], son=c['son'], h1=c['h1'], h6=c['h6'], h24=c['h24'], yog=c['yog'], yog24=c['yog24'], h6o=c['h6o'], h24o=c['h24o'],
                 alanlar=c['alanlar'], cat=c['cat'], gundem_alt=c['gundem_alt'], kaynaklar=c['kaynaklar'][:6], resmi=c['resmi'], kanit=c['kanit'], diller=c['diller'])
        return d
    def tam(c, **ek):
        d = ozet_kume(c); d.update(og=c['og'], farkli=c['farkli'], ul=c['ulkeler'], ld=c['liderler'], mk=c['markalar'], h6o=c['h6o'], h24o=c['h24o'], s=c['s'][:220]); d.update(ek); return d
    sicak = {}
    for w in ('1', '6', '24'):
        lst = sorted([c for c in tum if c['sicak' + w] > 0], key=lambda c: -c['sicak' + w])[:12]
        sicak[w] = [tam(c, puan=c['sicak' + w]) for c in lst]
    yuk = [tam(c, yuk=c['yuk']) for c in sorted([c for c in tum if c['yuk']['puan'] > 0 and c['yuk']['ilk_saat'] <= 48], key=lambda c: -c['yuk']['puan'])[:12]]
    son = [ozet_kume(c) for c in sorted(tum, key=lambda c: -c['son'])[:120]]
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
    idx = [dict(id=c['id'], t=c['t'], s=c['s'][:70], son=c['son'], kb=c['kb'], a=c['alanlar'], d=c['diller'], k=c['kaynaklar'][:5], e=sorted(set(c['liderler']) | set(c['markalar']) | set(c['ulkeler'])), cat=c['cat']) for c in sorted(tum, key=lambda c: -c['son'])[:2600]]
    yaz('indeks.json', dict(generated=j['generated'], kayitlar=idx))
    ozet = dict(generated=j['generated'], uretim=datetime.now(timezone.utc).isoformat(), saglik=j.get('saglik', {}), kaynak_durum=dict(durum_say),
                sicak=sicak, yukselen=yuk, son=son, sayim=sayim, alanlar=[dict(k=a, ad=ALAN_AD[a]) for a in ALANLAR],
                reels_ilk=[dict(id=r['id'], t=r['t'], puan=r['puan'], profil=r['profil'], kb=r['kb']) for r in reels_json[:6]],
                toplam=dict(haber=len(ogeler), kume=len(cikti), cok_kaynakli=sum(1 for c in tum if c['kb'] >= 3)),
                yontem=dict(
                    sicak='Sıcak konu: son 1/6/24 saatte haber yazan bağımsız kurum sayısı × 3 + o penceredeki haber sayısı × 0,7. En az 2 bağımsız kaynak şart; tek haberle konu sıcak sayılmaz. Ajans kopyaları ve aynı bültenden türeyen haberler tek kaynak sayılır.',
                    yukselen='Yükselen konu: log₂(1+haber yoğunluğu 6 sa) × log₂(1+bağımsız kurum 6 sa) × ivme (son 6 saatteki haber+1 / önceki 6 saatteki haber+1, en çok 6). En az 2 bağımsız kaynak, son 6 saatte en az 2 haber ve ilk haberi 48 saatten yeni olan konular girer.',
                    yogunluk='Yoğunluk değişimi: son penceredeki haber sayısı, bir önceki aynı uzunluktaki pencereyle karşılaştırılır.',
                    kume='Aynı olay: başlık/içerik kelime benzerliği ve ortak seyrek özel ad; farklı dillerde ortak varlık (ülke, lider, şirket) ve sayılar, 18 saat içinde. Yalnız başlık benzerliğiyle farklı olaylar birleştirilmez.'))
    yaz('ozet.json', ozet)
    boy = {f: os.path.getsize(os.path.join(CIKTI, f)) for f in sorted(os.listdir(CIKTI))}
    print('oge', len(ogeler), 'kume', len(cikti), 'cok kaynakli(>=3 bagimsiz)', sum(1 for c in tum if c['kb'] >= 3), 'reels', len(reels_json), 'elenen', dict(elenen_say))
    print({a: v['toplam'] for a, v in sayim.items()})
    print({k: '%dKB' % (v / 1024) for k, v in boy.items()})

if __name__ == '__main__':
    main()
