#!/usr/bin/env python3
"""sources.json'u zenginlestirir (ek alanlar) ve test edilmis yeni kaynaklari ekler. Eski alanlar (id,name,lang,cat,url,plat) degismez.
Ek alanlar: calisma (calisma alani), tip, ulke, oncelik, nitelik (liste), aktif, dogrulama {durum, tarih, n, ms}.
Kullanim: python3 tools/kaynak_birlestir.py  (tools/kaynak_test_sonuc*.json ve adaylar*.py okunur)"""
import json, os, re, sys, importlib.util, urllib.parse
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAL = {'tr': 'gundem', 'world': 'gundem', 'tech': 'tekno', 'win': 'tekno', 'ios': 'tekno', 'mac': 'tekno', 'samsung': 'tekno', 'sci': 'bilim', 'eco': 'ekonomi', 'sport': 'spor', 'auto': 'oto', 'ent': 'eglence', 'cool': 'eglence', 'viral': 'eglence'}
SIRKET = set('openai nvidia-blog deepmind google-blog ms-blog apple-news aws-news meta-news spotify-newsroom mac-newsroom steam-news win-blog win-msedge yt-blog tumblr-staff hf-blog'.split())
AJANS = re.compile(r'^(aa|aa-.*|ntv-son)$')
BILIMSEL = set('nasa sciencedaily newscientist quanta nature livescience physorg smithsonian sciencealert bbc-sci guardian-sci the-decoder'.split())
UCRETLI = set('nyt nyt-tech nyt-world wapo economist bloomberg ft wsj-world wsj-tech theinformation haaretz foreignpolicy fortune'.split())
ONCELIK1 = set('aa trthaber bbc-tr dw-tr ntv cnnturk hurriyet sozcu haberturk cumhuriyet bianet medyascope bbc-world guardian nyt aljazeera npr sky dw-en france24-en politico axios techcrunch verge webrazzi donanimhaber nasa openai espn bbc-sport skysports androidauthority gsmarena macrumors 9to5mac 9to5google bleepingcomputer'.split())
TLD = {'bbc': 'GB', 'guardian': 'GB', 'sky': 'GB', 'independent': 'GB', 'dailymail': 'GB', 'newscientist': 'GB', 'economist': 'GB', 'theregister': 'GB', 'techradar': 'GB', 'dw': 'DE', 'france24': 'FR', 'euronews': 'EU', 'scmp': 'HK', 'japantimes': 'JP', 'ithome': 'CN', 'cnbeta': 'CN', 'mydrivers': 'CN', 'aljazeera': 'QA', 'toi': 'IN', 'thehindu': 'IN', 'ndtv-en': 'IN', 'indiatoday': 'IN', 'straitstimes': 'SG', 'abc-au': 'AU', 'mee': 'GB', 'dailysabah': 'TR', 'gsmarena': 'BG', 'xda': 'US'}
def ulke(s):
    if s['lang'] == 'tr' or s['id'].startswith(('gn-tr', 'gnq')): return 'TR'
    if s['lang'] == 'zh': return 'CN'
    for k, v in TLD.items():
        if s['id'] == k or s['id'].startswith(k + '-'): return v
    return 'US' if s['lang'] == 'en' else 'INT'
def tip(s):
    i, c, p = s['id'], s['cat'], s.get('plat')
    if p == 'gnews': return 'toplayici'
    if p == 'youtube': return 'video (YouTube)'
    if p in ('reddit', 'hn') or c == 'viral' and i.startswith(('trends', 'hn', 'lobsters')): return 'topluluk/trend'
    if i in SIRKET: return 'sirket duyurusu'
    if AJANS.match(i): return 'ajans'
    if i in BILIMSEL: return 'bilimsel'
    if c == 'sport': return 'spor'
    if c in ('tech', 'win', 'ios', 'mac', 'samsung') and s['lang'] == 'en' or i.startswith(('xda', 'y-', 'ios-', 'mac-', 'win-')): return 'uzman teknoloji'
    return 'ana akim'
def nitelik(s):
    n = []; i, p = s['id'], s.get('plat')
    if p == 'gnews': n.append('toplayici')
    if p in ('reddit', 'hn') or i in ('trends-tr', 'trends-us', 'trends-gb'): n += ['erken-sinyal', 'topluluk']
    if p == 'youtube': n.append('video')
    if i in UCRETLI: n.append('ucretli-duvar')
    if i in SIRKET: n.append('sirket-haberi')
    if AJANS.match(i): n.append('ajans')
    if i in BILIMSEL: n.append('bilimsel')
    return n
def oncelik(s):
    if s['id'] in ONCELIK1: return 1
    if s.get('plat') in ('gnews', 'youtube', 'reddit') or s['cat'] in ('viral', 'cool'): return 3
    return 2

def zenginlestir(s):
    s.setdefault('calisma', CAL.get(s['cat'], 'gundem'))
    s.setdefault('tip', tip(s)); s.setdefault('ulke', ulke(s)); s.setdefault('oncelik', oncelik(s))
    s.setdefault('nitelik', nitelik(s)); s.setdefault('aktif', True)
    return s

def main():
    yol = os.path.join(KOK, 'sources.json')
    src = json.load(open(yol, encoding='utf-8'))
    for s in src: zenginlestir(s)
    for s in src:
        if s['id'] == 'yt-spacex': s['aktif'] = False; s['pasif_neden'] = 'YouTube kanal akisi 404 (kanal kimligi gecersiz); 5 ardisik hata'
    mevcut_id = {s['id'] for s in src}; mevcut_url = {s['url'] for s in src}
    # Aday listeleri ve test sonuclari
    adaylar = {}
    for f in ('adaylar.py', 'adaylar2.py'):
        sp = importlib.util.spec_from_file_location('a', os.path.join(KOK, 'tools', f)); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
        for a in m.A: adaylar[a[0]] = a
    sonuc = {}
    for f in ('kaynak_test_sonuc.json', 'kaynak_test_sonuc2.json'):
        for r in json.load(open(os.path.join(KOK, 'tools', f), encoding='utf-8')): sonuc[r['id']] = r
    RED = set(open(os.path.join(KOK, 'tools', 'kaynak_red.txt')).read().split()) if os.path.exists(os.path.join(KOK, 'tools', 'kaynak_red.txt')) else set()
    # Agdan erisilemedigi icin test edilemeyen ama bilinen RSS adresleri: aktif eklenir, durum 'bekliyor' (Actions ilk cekisi dogrular)
    BEKLIYOR = {'t24', 'turkishminute', 'wsj-world', 'wsj-tech'}
    eklenen, atlanan = [], []
    for id_, a in adaylar.items():
        r = sonuc.get(id_)
        if id_ in RED or id_ in mevcut_id or a[7] in mevcut_url or not r: continue
        _, ad, dil, ulk, cat, cal, tp, url, nit = a
        if r['ok']: dog = dict(durum='gecti', tarih=r['tarih'], n=r['n'], ms=r['ms'])
        elif id_ in BEKLIYOR: dog = dict(durum='bekliyor', tarih=r['tarih'], not_='Gelistirme ortamindan agla erisilemedi; ilk Actions cekisi dogrular')
        else: atlanan.append((id_, r.get('neden'))); continue
        plat = 'gnews' if 'news.google.com' in url else ('youtube' if 'youtube.com' in url else 'web')
        yeni = dict(id=id_, name=ad, lang=dil, cat=cat, url=url, plat=plat, calisma=cal, tip=tp, ulke=ulk, oncelik=1 if tp in ('resmi kurum', 'ajans', 'dogrulama', 'uluslararasi kurum') else 2 if tp != 'toplayici' else 3,
                    nitelik=[x for x in nit.split(',') if x], aktif=True, dogrulama=dog)
        src.append(yeni); eklenen.append(id_)
    json.dump(src, open(yol, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('toplam', len(src), 'eklenen', len(eklenen)); print('atlanan', *atlanan, sep='\n  ')
    json.dump(dict(eklenen=eklenen, atlanan=atlanan), open(os.path.join(KOK, 'tools', 'kaynak_birlestir_rapor.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
if __name__ == '__main__': main()
