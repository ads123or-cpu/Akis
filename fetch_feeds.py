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
        if it['t'] and it['l']: out.append(it)
    return out

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
                feeds[s['id']] = dict(name=s['name'], lang=s['lang'], cat=s['cat'], url=s['url'], items=items, updated=now)
            else:
                failed.append((s['id'], err))
                if s['id'] in old: feeds[s['id']] = old[s['id']]   # eski haberleri koru
    json.dump(dict(generated=now, feeds=feeds), open('site/feeds.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    n = sum(len(f['items']) for f in feeds.values())
    print(f"{len(feeds)} kaynak, {n} haber, {len(failed)} başarısız", *failed, sep='\n  ')

if __name__ == '__main__': main()
