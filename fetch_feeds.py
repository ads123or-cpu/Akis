#!/usr/bin/env python3
"""sources.json içindeki RSS/Atom kaynaklarını çekip site/feeds.json dosyasına yazar."""
import json, re, html, gzip, concurrent.futures as cf, urllib.request, xml.etree.ElementTree as ET
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
GENERAL = re.compile(r"cinayet|gözaltı|tutuklandı|erdoğan|cumhurbaşkanı|bakan\b|belediye|savcılık|operasyon|kaza\b|yaralandı|hayatını kaybetti|polis|cezaevi|soruşturma|başkan\b|seçim|chp|akp|mhp|meclis|tbmm|savaş|gaza|ukrayna|israil|iran|rusya|putin|trump|biden|police|killed|arrested|election|war\b|president", re.I)

def classify(it, s):
    """Kategori kaynağın bölümünden farklıysa (ör. teknoloji bölümünde gündem haberi) madde bazında düzelt."""
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

def go(s):
    err = 'bos'
    for attempt in range(2):
        try:
            host_wait(s['url'])
            items = parse(fetch(s['url']))
            if items: return s, items, None
        except Exception as e:
            err = str(e)[:80]
    return s, [], err

def main():
    sources = json.load(open('sources.json'))
    try: old = json.load(open('site/feeds.json')).get('feeds', {})
    except Exception: old = {}
    now = datetime.now(timezone.utc).isoformat(); feeds = {}; failed = []
    with cf.ThreadPoolExecutor(24) as ex:
        for s, items, err in ex.map(go, sources):
            if items:
                lim = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
                items = [i for i in items if not i.get('d') or i['d'] >= lim]
                for i in items:
                    c = classify(i, s)
                    if c != s['cat']: i['c'] = c
                if not items: failed.append((s['id'], 'eski')); continue
                feeds[s['id']] = dict(name=s['name'], lang=s['lang'], cat=s['cat'], plat=s.get('plat') or 'web', url=s['url'], items=items, updated=now)
            else:
                failed.append((s['id'], err))
                if s['id'] in old: feeds[s['id']] = old[s['id']]   # eski haberleri koru
    import os; os.makedirs('site', exist_ok=True)
    json.dump(dict(generated=now, feeds=feeds), open('site/feeds.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    n = sum(len(f['items']) for f in feeds.values())
    print(f"{len(feeds)} kaynak, {n} haber, {len(failed)} başarısız", *failed, sep='\n  ')

if __name__ == '__main__': main()
