#!/usr/bin/env python3
"""sources.json içindeki RSS/Atom kaynaklarını çekip site/feeds.json dosyasına yazar."""
import json, re, html, gzip, random, concurrent.futures as cf, urllib.request, urllib.error, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta

class R(urllib.request.HTTPRedirectHandler):
    def http_error_308(self, req, fp, code, msg, headers):
        return self.http_error_302(req, fp, 302, msg, headers)
urllib.request.install_opener(urllib.request.build_opener(R))

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
MAX_ITEMS = 40

def strip(s):
    s = re.sub(r'<[^>]+>', ' ', s or ''); s = html.unescape(s)
    return re.sub(r'\s+', ' ', s).strip()

def ln(t): return t.split('}')[-1]

def pdate(s):
    if not s: return None
    s = s.strip()
    try: return parsedate_to_datetime(s).astimezone(timezone.utc).isoformat()
    except Exception: pass
    try: return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(timezone.utc).isoformat()
    except Exception: return None

def clean(data):
    s = data.decode('utf-8', 'ignore') if isinstance(data, bytes) else data
    s = s.lstrip('﻿ \r\n\t')
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)

def parse_et(data):
    root = ET.fromstring(clean(data).encode('utf-8')); out = []
    for it in root.iter():
        if ln(it.tag) not in ('item', 'entry'): continue
        d = {}; img = None; desc = ''
        for c in it:
            k = ln(c.tag); t = (c.text or '').strip()
            if k == 'title': d['t'] = strip(t)
            elif k == 'link':
                l = c.get('href') or t
                if l and c.get('rel') in (None, 'alternate'): d['l'] = d.get('l') or l
            elif k in ('pubDate', 'published', 'updated', 'date') and 'd' not in d: d['d'] = pdate(t)
            elif k == 'source' and t: d['p'] = strip(t)
            elif k in ('description', 'summary', 'content', 'encoded') and len(t) > len(desc): desc = t
            elif k in ('thumbnail', 'content') and c.get('url') and not img and (c.get('medium') in (None, 'image') or 'image' in (c.get('type') or 'image')): img = c.get('url')
            elif k == 'enclosure' and c.get('url') and 'image' in (c.get('type') or ''): img = c.get('url')
        if not img:
            m = re.search(r'<img[^>]+src=["\']([^"\']+)', html.unescape(desc))
            if m: img = m.group(1)
        d['s'] = '' if 'news.google.com' in d.get('l', '') else strip(desc)[:200]
        if img and img.startswith('http'): d['i'] = img
        if not d.get('t') and d.get('s'): d['t'] = d['s'][:110]
        if d.get('t') and d.get('l'): out.append(d)
    return out

def parse_re(data):
    """Bozuk XML için yedek: regex ile item/entry ayıkla."""
    s = clean(data); out = []
    for blk in re.findall(r'<(?:item|entry)[\s>].*?</(?:item|entry)>', s, re.S):
        def g(tag):
            m = re.search(r'<%s[^>]*>(.*?)</%s>' % (tag, tag), blk, re.S)
            if not m: return ''
            return re.sub(r'^<!\[CDATA\[(.*?)\]\]>$', r'\1', m.group(1).strip(), flags=re.S)
        t = strip(g('title'))
        l = g('link').strip() or (re.search(r'<link[^>]+href=["\']([^"\']+)', blk) or [None, ''])[1]
        d = pdate(g('pubDate') or g('published') or g('updated') or g('dc:date'))
        desc = g('description') or g('summary') or g('content:encoded')
        img = (re.search(r'<(?:media:thumbnail|media:content|enclosure)[^>]+url=["\']([^"\']+)', blk) or re.search(r'<img[^>]+src=["\']([^"\']+)', html.unescape(desc)) or [None, ''])[1]
        it = dict(t=t, l=html.unescape(l), d=d, s=strip(desc)[:200])
        if img.startswith('http'): it['i'] = html.unescape(img)
        if not it['t'] and it['s']: it['t'] = it['s'][:110]
        if it['t'] and it['l']: out.append(it)
    return out


import threading, time, unicodedata
_rl = threading.Lock()
def host_wait(url):
    if 'reddit.com' in url:
        with _rl: time.sleep(1.3)

TRUST = set("""webrazzi shiftdelete donanimhaber webtekno technopat log teknoseyir chip-tr tamindir hn verge techcrunch ars wired engadget gizmodo 9to5mac 9to5google macrumors mit-tr cnet zdnet techmeme theregister androidauthority tomshardware thenextweb hackaday producthunt xda gsmarena sammobile appleinsider bleepingcomputer krebs merlin donanimarsivi techinside electrek eurogamer the-decoder hf-blog openai nasa sciencedaily newscientist quanta nature livescience physorg smithsonian bilimgenc fizikist evrim sciencealert bloomberght ekonomim dunya-gzt cnbc bloomberg marketwatch coindesk cointelegraph economist fortune variety thr deadline rollingstone pitchfork polygon ign kotaku pcgamer tmz eonline espn bbc-sport skysports guardian-football fotomac aspor bbc-football aa-spor trthaber-spor atlas boingboing goodnews futurism kottke oddity vice mashable buzzfeed knowyourmeme theonion onedio gnq-gs gnq-fb gnq-bjk gnq-ts gnq-milli gnq-basket gnqe-nfl gnqe-celeb gnqe-crypto gnq-kripto gnq-dolar gnq-ekonomi gnq-ai gnqe-ai gnq-iphone gnq-oyun gnqe-ev gnqe-space gnq-uzay anthropic-gn""".split())
MIXED = set("""hurriyet-tek milliyet-tek sabah-tek haberturk-tek sozcu-tek aa-bilim trthaber-bilim ntv-tek cnnturk-tek hurriyet-eko milliyet-eko sabah-eko haberturk-eko sozcu-eko aa-eko trthaber-eko cumhuriyet-eko""".split())
KW = {
 'tech': r"iphone|ipad|macbook|android|samsung|galaxy|xiaomi|huawei|apple|google|microsoft|windows|linux|openai|chatgpt|claude|gemini|anthropic|yapay zek|artificial intel|\bai\b|işlemci|ekran kart|nvidia|intel|amd|qualcomm|telefon|akıllı|bilgisayar|laptop|yazılım|uygulama|siber|hack|güvenlik açığ|robot|drone|tesla|elektrikli|togg|otomobil|oyun|playstation|xbox|steam|nintendo|teknoloji|teknofest|internet|5g|chip|çip|startup|girişim|güncelleme|whatsapp|instagram|tiktok|youtube|netflix|spotify|starlink|spacex|roket|uydu|bulut|veri|algoritma|kripto cüzdan|batarya|şarj|kamera|tablet|kulaklık|monitör|ssd|ram",
 'sport': r"maç|gol\b|futbol|basketbol|voleybol|lig\b|süper lig|şampiyon|transfer|teknik direktör|hakem|galatasaray|fenerbahçe|beşiktaş|trabzonspor|başakşehir|milli takım|euroleague|nba|nfl|uefa|fifa|olimpiyat|formula|f1\b|tenis|güreş|boks|ufc|premier league|champions|football|soccer|goal|coach|match|tournament|cup\b|stadyum|kupa",
 'eco': r"dolar|euro|altın|borsa|bist|enflasyon|faiz|merkez bankası|ekonomi|zam\b|maaş|asgari ücret|emekli|vergi|ihracat|ithalat|bütçe|kredi|banka|yatırım|hisse|petrol|akaryakıt|benzin|motorin|konut|kira|bitcoin|kripto|ethereum|fed\b|inflation|stock|market|economy|gdp|earnings|bank|tariff|oil|currency|sanayi|şirket|ticaret|piyasa",
 'sci': r"nasa|uzay|gezegen|astronom|bilim|araştırma|keşfetti|fosil|iklim|deprem|kanser|tedavi|hastalık|aşı|vitamin|beslenme|sağlık|doktor|ilaç|genetik|dna|evren|teleskop|asteroid|study|scientists|researchers|climate|vaccine|disease|health|planet|space|physics|biology|quantum|güneş|mars",
 'ent': r"dizi|film|sinema|oyuncu|şarkıcı|ünlü|magazin|konser|albüm|festival|ödül|oscar|netflix|gişe|fragman|yönetmen|survivor|masterchef|sanatçı|aktris|aktör|celebrity|movie|series|actor|actress|singer|album|box office|trailer|hollywood|streaming",
}
KWC = {k: re.compile(v, re.I) for k, v in KW.items()}
SUB = {
 'samsung': re.compile(r"\bsamsung\b|\bgalaxy\b|\bone\s?ui\b|\bexynos\b|\bsammobile\b", re.I),
 'mac': re.compile(r"\bmacos|macbook|\bimac\b|mac mini|mac studio|mac pro|apple silicon|\bm[1-5] (?:pro|max|ultra|chip|çip)|\bmacs?\b", re.I),
 'ios': re.compile(r"\biphone|\bios ?\d*\b|\bipados|\bwatchos|\bairpods|apple watch|\bipad\b|vision pro|\bapple\b|app store", re.I),
 'win': re.compile(r"\bwindows\b|\bwin ?1[01]\b|copilot\+? ?pc|surface (?:pro|laptop|go)|microsoft edge|\bnotepad\b|microsoft 365", re.I),
 'auto': re.compile(r"otomobil|\baraba|otomotiv|elektrikli (?:araç|otomobil|araba|suv|model)|\btogg\b|\btesla\b|\bbmw\b|mercedes|\baudi\b|volkswagen|porsche|ferrari|\bford\b|\bfiat\b|renault|hyundai|toyota|\bhonda\b|\bopel\b|peugeot|citro|skoda|\bkia\b|volvo|\bbyd\b|tofaş|\begea\b|\bsuv\b|sedan|hatchback|electric (?:car|vehicle|suv)|\bcars?\b|motor show|lamborghini|mclaren|nissan|mazda|suzuki|leapmotor|chery|xpeng|lucid|rivian|\bjeep\b|dacia|paris otomobil|yeni model", re.I),
}
SUB_ORDER = ('samsung', 'mac', 'ios', 'win', 'auto')
def subclass(it):
    title = it.get('t', ''); summ = it.get('s', '')[:140]
    best, bs = None, 0
    for k in SUB_ORDER:
        sc = 3 * len(SUB[k].findall(title)) + len(SUB[k].findall(summ))
        if sc > bs: best, bs = k, sc
    return best if bs >= 3 else None

ACCIDENT = re.compile(r"kaza|yaralan|yaralı|hayatını kaybet|çarpış|şarampol|cinayet|gözaltı|tutuklan|devrildi|ölü|crash kills|killed|dies", re.I)
GENERAL = re.compile(r"cinayet|gözaltı|tutuklandı|erdoğan|cumhurbaşkanı|bakan\b|belediye|savcılık|operasyon|kaza\b|yaralandı|hayatını kaybetti|polis|cezaevi|soruşturma|başkan\b|seçim|chp|akp|mhp|meclis|tbmm|savaş|gaza|ukrayna|israil|iran|rusya|putin|trump|biden|police|killed|arrested|election|war\b|president", re.I)

def classify(it, s):
    """Kategori kaynağın bölümünden farklıysa (ör. teknoloji bölümünde gündem haberi) madde bazında düzelt."""
    c = _classify(it, s)
    if c == 'tech' and s['lang'] in ('tr', 'en'):
        sub = subclass(it)
        if sub: return sub
    return c

def _classify(it, s):
    c = s['cat']
    if c not in KWC or s['lang'] not in ('tr', 'en'): return c
    if not (s['id'] in MIXED or s['id'].startswith('gn-')): return c
    text = (it.get('t', '') + ' ' + it.get('s', '')[:120])
    if KWC[c].search(text): return c
    best, bn = None, 0
    for k, rx in KWC.items():
        if k == c: continue
        n = len(rx.findall(text))
        if n > bn: best, bn = k, n
    if best and bn >= 1 and not GENERAL.search(text): return best
    return 'tr' if s['lang'] == 'tr' else 'world'

def fix_future(items):
    """Yerel saati GMT diye işaretleyen kaynakları (ör. CNN Türk) düzelt."""
    now = datetime.now(timezone.utc)
    for it in items:
        if not it.get('d'): continue
        d = datetime.fromisoformat(it['d'])
        if d > now + timedelta(minutes=2):
            sh = d - timedelta(hours=3)
            it['d'] = (sh if sh <= now + timedelta(minutes=2) else now).isoformat()
    return items

def parse(data):
    try: items = parse_et(data)
    except Exception: items = []
    if not items: items = parse_re(data)
    items = fix_future(items)
    items.sort(key=lambda x: x.get('d') or '', reverse=True)
    return items[:MAX_ITEMS]

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/rss+xml,application/atom+xml,application/xml,text/xml,*/*', 'Accept-Encoding': 'gzip'})
    r = urllib.request.urlopen(req, timeout=25); data = r.read()
    if r.headers.get('Content-Encoding') == 'gzip' or data[:2] == b'\x1f\x8b': data = gzip.decompress(data)
    return data


def fetch_x(handle):
    """X (Twitter) herkese açık gömme zaman tünelinden gönderileri çeker (giriş gerektirmez; X engellerse boş döner)."""
    u = 'https://syndication.twitter.com/srv/timeline-profile/screen-name/' + handle
    req = urllib.request.Request(u, headers={'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'})
    raw = urllib.request.urlopen(req, timeout=25).read().decode('utf-8', 'ignore')
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', raw, re.S)
    if not m: return []
    j = json.loads(m.group(1)); out = []
    for e in j.get('props', {}).get('pageProps', {}).get('timeline', {}).get('entries', []):
        tw = (e.get('content') or {}).get('tweet') or {}
        txt = html.unescape(tw.get('full_text') or tw.get('text') or '')
        if not txt or tw.get('in_reply_to_status_id_str'): continue
        txt = re.sub(r'https://t\.co/\w+', '', txt).strip()
        link = 'https://x.com' + (tw.get('permalink') or '/%s/status/%s' % (handle, tw.get('id_str')))
        media = ((tw.get('entities') or {}).get('media') or [{}])[0].get('media_url_https')
        it = dict(t=txt[:140], l=link, d=pdate(tw.get('created_at')), s=txt[:200])
        if media: it['i'] = media
        out.append(it)
    out.sort(key=lambda x: x.get('d') or '', reverse=True)
    return out[:MAX_ITEMS]

def go(s):
    """(kaynak, haberler, hata, http_kodu, retry_after_sn). 429'da ayni turda tekrar denenmez."""
    err = 'bos'; kod = None; bekle = None
    for attempt in range(2):
        try:
            host_wait(s['url'])
            items = fetch_x(s['url'][4:]) if s['url'].startswith('x://') else parse(fetch(s['url']))
            if items: return s, items, None, 200, None
        except urllib.error.HTTPError as e:
            err = str(e)[:80]; kod = e.code
            bekle = retry_after(e.headers.get('Retry-After') if e.headers else None)
            if e.code == 429: break   # hemen tekrar denemek yalnizca sinirin uzamasina yol acar
        except Exception as e:
            err = str(e)[:80]
    return s, [], err, kod, bekle


def retry_after(deger):
    """Retry-After basligi: saniye ya da HTTP tarihi. Okunamazsa None."""
    if not deger: return None
    deger = deger.strip()
    if deger.isdigit(): return int(deger)
    try: return max(0, int((parsedate_to_datetime(deger) - datetime.now(timezone.utc)).total_seconds()))
    except Exception: return None


# --- Devre kesici (27.10.2026) -----------------------------------------
# X ve Reddit kaynaklari her turda 429 aliyordu; her tur yeniden istek atmak
# sinirin surmesine yol aciyor ve tur suresini uzatiyordu. Kaynak durumu
# site/kaynak-durum.json'da turlar arasi saklanir (is akisi site/ klasorunu
# commit ediyor). 429 ya da ardisik 3 hatada kaynak bir sure atlanir:
# min(2^(n-1) x 30 dk, 24 sa) + rastgele pay; Retry-After varsa o kullanilir.
DURUM_DOSYASI = 'site/kaynak-durum.json'
TABAN_DK = 30
TAVAN_SN = 24 * 3600

def bekleme_suresi(ardisik, retry_sn):
    if retry_sn: return min(retry_sn, TAVAN_SN)
    sn = min(TABAN_DK * 60 * (2 ** max(0, ardisik - 1)), TAVAN_SN)
    return int(sn * random.uniform(1.0, 1.2))

def durum_guncelle(durum, sid, basarili, kod, hata, retry_sn, simdi):
    d = durum.setdefault(sid, {})
    if basarili:
        durum[sid] = {'ardisik_basarisiz': 0, 'son_basari': simdi.isoformat(), 'son_kod': 200}
        return
    n = d.get('ardisik_basarisiz', 0) + 1
    d.update(ardisik_basarisiz=n, son_hata=simdi.isoformat(), son_kod=kod, hata=hata)
    if kod == 429 or n >= 3:
        d['bekle_kadar'] = (simdi + timedelta(seconds=bekleme_suresi(n, retry_sn))).isoformat()
    else:
        d.pop('bekle_kadar', None)


# --- Spam süzgeci (14.10.2026) -------------------------------------------
# Ele geçirilmiş üniversite/kurum sitelerinden gelen bahis-izle spam'i ve
# sembol yığını başlıklar akışı kirletiyordu (ör. uco.es "canlı izle" başlıkları).
SPAM_KELIME = re.compile(r'(canlı\s*izle|şifresiz|bedava|bahis|casino|jackpot|selçuk\s*sport|taraftarium|justin\s*tv|izle\b.*\b(maç|film))', re.I)
SPAM_ALAN = re.compile(r'(\.edu(\.[a-z]{2})?$|\.ac\.[a-z]{2}$|(^|\.)uco\.es$|\.gov(\.[a-z]{2})?$)', re.I)
def spam_mi(it):
    t = it.get('t', '') or ''
    l = it.get('l', '') or ''
    host = re.sub(r'^https?://([^/]+).*$', r'\1', l).lower()
    sembol = len(re.findall(r'[^\w\s\-\.,:;!?\'"()%/&]', t))
    yayinci = it.get('p', '') or ''
    kurum = SPAM_ALAN.search(host) or re.search(r'(universidad|university|üniversite|college|\.edu\b)', yayinci, re.I)
    if kurum and re.search(r'(izle|canlı|maç|bahis|bedava|şifresiz|bein|trt\s*1)', t, re.I):
        return True
    if sembol >= 5 and SPAM_KELIME.search(t):
        return True
    return False

def main():
    sources = json.load(open('sources.json'))
    try: old = json.load(open('site/feeds.json')).get('feeds', {})
    except Exception: old = {}
    try: durum = json.load(open(DURUM_DOSYASI))
    except Exception: durum = {}
    simdi = datetime.now(timezone.utc)
    now = simdi.isoformat(); feeds = {}; failed = []
    # Beklemedeki kaynaklar bu tur cekilmez; eski verisi asagidaki 12 saat kuralina tabidir.
    beklemede = {s['id'] for s in sources if (durum.get(s['id']) or {}).get('bekle_kadar', '') > now}
    cekilecek = [s for s in sources if s['id'] not in beklemede]
    sonuclar = [(s, [], 'beklemede', None, None) for s in sources if s['id'] in beklemede]
    with cf.ThreadPoolExecutor(24) as ex:
        sonuclar += list(ex.map(go, cekilecek))
    for s, items, err, kod, retry_sn in sonuclar:
            if s['id'] not in beklemede:
                durum_guncelle(durum, s['id'], bool(items), kod, err, retry_sn, simdi)
            if items:
                lim = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
                items = [i for i in items if not i.get('d') or i['d'] >= lim]
                for i in items:
                    c = classify(i, s)
                    if c != s['cat']: i['c'] = c
                if s['cat'] == 'auto': items = [i for i in items if not ACCIDENT.search(i.get('t', ''))]
                items = [i for i in items if not spam_mi(i)]
                if not items: failed.append((s['id'], 'eski')); continue
                feeds[s['id']] = dict(name=s['name'], lang=s['lang'], cat=s['cat'], plat=s.get('plat') or 'web', url=s['url'], items=items, updated=now)
            else:
                failed.append((s['id'], err))
                # Bayat kopya 12 saatten eskiyse dusurulur: kaynak yanit vermediginde
                # eski haber 'yeni' gibi akisa dolmasin.
                lim12 = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
                if s['id'] in old:
                    taze = [i for i in old[s['id']].get('items', []) if i.get('d') and i['d'] >= lim12]
                    if taze: feeds[s['id']] = {**old[s['id']], 'items': taze, 'bayat': True}
    import os; os.makedirs('site', exist_ok=True)
    n = sum(len(f['items']) for f in feeds.values())
    saglik = dict(kaynak=len(sources), basarili=len(feeds) - sum(1 for f in feeds.values() if f.get('bayat')), bayat=sum(1 for f in feeds.values() if f.get('bayat')), basarisiz=sum(1 for _, e in failed if e != 'beklemede'), beklemede=len(beklemede))
    gecerli = {s['id'] for s in sources}
    json.dump({k: v for k, v in durum.items() if k in gecerli}, open(DURUM_DOSYASI, 'w'), ensure_ascii=False, indent=1, sort_keys=True)
    json.dump(dict(generated=now, saglik=saglik, feeds=feeds), open('site/feeds.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f"{len(feeds)} kaynak, {n} haber, {len(failed)} başarısız", *failed, sep='\n  ')

if __name__ == '__main__': main()
