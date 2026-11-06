#!/usr/bin/env python3
"""site/feeds.json'dan masa verisi: ayni olayi anlatan haberleri kumeler, konu atar, Reels adaylarini siralar.

Puan yapay zeka degil, acik kuraldir. Her Reels adayi puani nasil aldigini "nedenler" ile soyler:
kac kaynak yazdi, ne kadar hizli yayildi, Google'da trend mi, Turkcede var mi, gorseli var mi.
"""
import json, re, math, hashlib
from collections import Counter, defaultdict
from datetime import datetime, timezone

SAAT = 72
KONULAR = [
    ('samsung', 'Samsung', r"\bsamsung\w*|\bgalaxy\b|\bone ?ui\b|\bexynos\b"),
    ('apple', 'Apple', r"\biphone\w*|\bipad\w*|\bmacbook\w*|\bimac\b|\bmacos\b|\bios ?\d*\b|\bapple\w*|\bairpods?\b|\bvision pro\b|\bwatchos\b"),
    ('android', 'Android', r"\bandroid\w*|\bpixel ?\d+\w*|\bxiaomi\w*|\bredmi\b|\bpoco\b|\bhyperos\b|\bhuawei\w*|\bhonor\b|\boneplus\b|\boppo\b|\bvivo\b|\brealme\b|\bnothing phone\b|\bmotorola\b|\bmoto [a-z]\d"),
    ('yz', 'Yapay Zekâ', r"yapay zek|\bchatgpt\b|\bopenai\b|\bclaude\b|\banthropic\b|\bgemini\b|\bgrok\b|\bcopilot\b|\bdeepseek\b|\bai (model|agent|chatbot|tool|startup|video)|\bartificial intelligence\b|\bllm\b|\bsam altman\b|\bmidjourney\b|\bsora\b"),
    ('oto', 'Otomobil', r"\btesla\w*|\btogg\w*|elektrikli (araç|otomobil|araba|suv|model)|\bevs?\b|\bbyd\b|\bbmw\b|\bmercedes\b|\baudi\b|\bvolkswagen\b|\bporsche\b|\bferrari\b|\botomobil\w*|\bhyundai\b|\btoyota\b|\brenault\b|\bfiat\b|\bcybertruck\b|\bsuv\b"),
    ('oyun', 'Oyun', r"\bplaystation\b|\bps[56]\b|\bxbox\b|\bnintendo\b|\bswitch 2\b|\bsteam\b|\bgta ?\d\w*|\bgaming\b|\bpc oyun\w*|\bmobil oyun\w*|\boyun konsol\w*|\bepic games\b|\bminecraft\b|\bfortnite\b|\broblox\b|\bvideo game"),
    ('donanim', 'Donanım', r"\bnvidia\w*|\bamd\b|\bintel\b|\brtx ?\d*|\bradeon\b|\bryzen\b|\bgeforce\b|\bsnapdragon\b|\btsmc\b|\bddr\d\b|\bssd\b|\bram\b|\bişlemci\w*|\bçip\w*|\bchip\w*|\bgpu\b|\bcpu\b"),
    ('yazilim', 'Yazılım ve Güvenlik', r"\bwindows\b|\blinux\b|\bmicrosoft\b|\bgoogle chrome\b|\bfirefox\b|\bsiber\b|\bhack\w*|\bsızıntı\w*|\bsızdı\b|\bdata breach\b|\bransomware\b|\bzero-?day\b|\bmalware\b|\bvirüs\w*|\bgüvenlik açığı\b|\bvulnerabilit\w*"),
    ('sosyal', 'Sosyal Medya', r"\binstagram\w*|\bwhatsapp\w*|\btiktok\w*|\byoutube\w*|\btelegram\w*|\bfacebook\w*|\bthreads\b|\bsnapchat\b|\bmeta\b|\bmusk\b|\breddit\b"),
    ('uzay', 'Uzay ve Bilim', r"\bnasa\b|\bspacex\b|\bstarship\b|\bartemis\b|\bmars\b|\bay'a\b|\bastronot\w*|\bastronaut\w*|\buzay\w*|\bjames webb\b|\bgezegen\w*|\bblack hole\b|\bkara delik\w*|\brobot\w*|\bhumanoid\b|\binsansı\b|\bquantum\b|\bkuantum\b"),
    ('savunma', 'Savunma', r"\bbaykar\b|\baselsan\b|\btusaş\b|\broketsan\b|\bkaan\b|\bkızılelma\b|\btb[23]\b|\bakıncı\b|\bsiha\b|\bf-?35\b|\bf-?16\b|\bhipersonik\b|\bhypersonic\b|\bdrone\w*|\bsavunma sanayi\w*"),
]
KONU_RX = [(k, ad, re.compile(r, re.I)) for k, ad, r in KONULAR]
# Teknoloji basini degilse konu kelimesi yetmez: "meta", "apple" genel haberde baska anlama gelebilir.
TEKNIK = {'tech', 'ios', 'mac', 'win', 'mobil', 'samsung', 'auto', 'sci', 'cool'}
GENEL_RED = re.compile(r"cinayet|gözaltı|tutuklan|erdoğan|cumhurbaşkan|bakan\b|belediye|savcı|operasyon|kaza\b|yaralan|hayatını kaybet|öldü|ölü\b|intihar|tecavüz|taciz|deprem|savaş|gazze|israil|killed|dies\b|shooting|murder|election|trump|biden|maç\b|gol\b|fenerbahçe|galatasaray|beşiktaş|süper lig|transfer|teknik direktör|ev hapsi|hapis|dava\b|mahkeme|alev alev|yangın|yandı|vize\b|emekli|maaş|how to watch|live stream|watch .{3,40} (free|online)|canlı izle", re.I)
ZAYIF = re.compile(r"\b(earnings|quarterly|hisse|bilanço|investor|funding round|raises \$|series [abc]\b|enterprise|b2b|kubernetes|sdk\b|api\b|developer preview|podcast|newsletter|review:|inceleme:|weekly|roundup|opinion)\b|haftanın|bu hafta", re.I)
RUTIN = re.compile(r"yama|güncelleme|beta\b|sürüm\b|patch|update|firmware|security fix", re.I)
CARPICI = re.compile(r"ilk kez|dünyanın ilk|tarihte|rekor|yasak|yasakla|sızdı|sızıntı|şok|inanılmaz|şaşırt|gizli|ortaya çık|bedava|ücretsiz|fiyatı|zam\b|iptal|kapanıyor|bitiyor|tehlike|uyarı|keşfed|keşfet|insansı|robot|world'?s first|first ever|record|banned?|bans?\b|leak|secret|shock|free\b|insane|surpris|cancel|shut(ting)? down|warning|discover|humanoid|finally|revealed|unbelievable", re.I)
TURKIYE = re.compile(r"türkiye|türk\b|togg|btk|imei|\btl\b|istanbul|ankara|baykar|aselsan|turkcell|vodafone tr|türk telekom", re.I)
TUKETICI = {'samsung', 'apple', 'android', 'yz', 'oto', 'oyun', 'sosyal', 'uzay'}

# --- Reels alaka kurallari (kanal: Turkce tuketici teknolojisi; izleyen telefon, uygulama, guvenlik, yapay zeka kullanicisi) ---
# Konu agirligi: kullanicinin elindeki cihaz ve uygulamalar one, otomobil/uzay/oyun geri.
KONU_AGIRLIK = {'sosyal': 9, 'samsung': 8, 'apple': 8, 'android': 8, 'yz': 8, 'yazilim': 5, 'donanim': 3, 'oyun': 3, 'oto': 2, 'uzay': 2, 'savunma': -4}
KITLE = re.compile(r"whatsapp|instagram|tiktok|youtube|telegram|threads|snapchat|iphone|\bios ?\d|galaxy|samsung|one ?ui|android|xiaomi|redmi|pixel|oneplus|honor|chatgpt|gemini|claude|grok|copilot|netflix|spotify|starlink|turkcell|vodafone|türk telekom|google (haritalar|maps|fotoğraflar|photos)|gmail|chrome|windows ?1[01]|airpods|apple watch|playstation|ps5|xbox|steam|epic games|nintendo switch", re.I)
ETKI = re.compile(r"özellik|feature|geliyor|geldi|rolling out|gizli|hidden|trick|ipucu|nasıl|how to|ücretsiz|free\b|bedava|kapat|silin|dikkat|uyarı|dolandır|scam|phishing|oltalama|güvenlik açığı|vulnerab|sızdı|sızıntı|leak|fiyat|zam\b|indirim|yasak|erişim|çöktü|outage|kesinti|güncelleme", re.I)
# Reels'e hic girmez (Gundem ve Son haberler'de durur): kaza, dizi/film, borsa-yatirim, yabanci ulke kampanyasi.
REELS_RED = re.compile(r"protesters?|\bsues?\b|lawsuit|airbnb|\baws\b|yaralı|yaralandı|çarpış|kaza\b|işçi servisi|servis aracı|cenaze|milli takım|futbolcu|süper lig|şampiyonlar ligi|abd genelinde|abd'de satışa|abd pazar|yalnızca abd|sadece abd|\bdizi\b|\bfilm\b|prime video|disney\\+|premieres? on|season \d+|box office|episode\b|fragman|gişe|\bdizisi\b|\bfilmi\b|\bipo\b|valuation|market cap|piyasa değeri|earnings|quarterly|revenue|raises \$|funding|hisse|bilanço|analyst|\bin the us\b|u\.s\.-only|us-only|verizon|t-mobile|at&t|best buy|walmart|costco|prime day|black friday|\bdeals?\b|coupon", re.I)
# Reels'te ceza: kurumsal hukuk/siyaset, kullaniciya dogrudan dokunmayan konular.
REELS_CEZA = re.compile(r"\breview\b|incelemesi|\$\d{2,4}\b|protesters?|lawsuit|sues?\b|court|\bftc\b|\bdoj\b|antitrust|fined|ab'?den|avrupa birliği|\bceza\b|regulator|senate|congress", re.I)
REELS_TOPLAM = 60
REELS_KONU_UST = 12

STOP = set("""ve ile için bir bu da de ne mi mı daha en çok gibi olarak olan oldu olacak kadar sonra önce yeni son ama var yok her hem ya
the a an of to in on for and or is are was were with from at by as it its that this be has have had will how why what you your new now after over into about more than can may not""".split())
TR = str.maketrans({'İ': 'i', 'I': 'ı'})

def sozcuk(t):
    return [w for w in re.findall(r"[a-zçğıöşü0-9][a-zçğıöşü0-9\-\.]*", t.translate(TR).lower()) if w not in STOP and len(w) > 1]
def kok(w):
    return w if w[0].isdigit() or len(w) <= 5 else w[:6]
def varlik(t):
    """Ozel ad ve model: 'Galaxy S26', 'One UI 9'. Diller arasi eslesme bunlarla yapilir."""
    o = set()
    for w in re.findall(r"[A-ZÇĞİÖŞÜ][\w\-]{2,}|\b[A-Za-z]{0,3}\d{1,4}[A-Za-z]{0,3}\b", t):
        o.add(kok(w.translate(TR).lower().split("'")[0]))
    return o - {kok(x) for x in STOP}

def konu_bul(t, ozet, cat):
    puan = Counter()
    for k, _, rx in KONU_RX:
        n = len(rx.findall(t))
        if n: puan[k] += 3 * n
        elif cat in TEKNIK and rx.search(ozet or ''): puan[k] += 1
    if not puan: return None
    k, p = puan.most_common(1)[0]
    return k if p >= 3 else None

def kumele(ogeler):
    """Yeni haber kumenin ILK haberiyle karsilastirilir: kume buyudukce konu kaymasin.
    Apple, Google gibi her yerde gecen adlar benzerlik saymaz, yalniz seyrek adlar sayar."""
    df = Counter()
    for o in ogeler:
        for v in o['var']: df[v] += 1
    seyrek = {v for v, n in df.items() if n <= 25}
    ogeler.sort(key=lambda x: x['z'])
    kumeler, dizin = [], defaultdict(list)
    for o in ogeler:
        aday = Counter()
        for tk in o['tok']:
            for c in dizin[tk][-40:]: aday[c] += 1
        en, enb = None, 0
        ov = o['var'] & seyrek
        for c, _ in aday.most_common(30):
            k = kumeler[c]
            if o['z'] - k['son'] > 36 * 3600: continue
            bir = o['tok'] & k['ilk']
            j = len(bir) / max(1, len(o['tok'] | k['ilk']))
            ent = len(ov & k['ilkvar'])
            uygun = (o['dil'] == k['ilkdil'] and ((j >= .3 and ent >= 1) or j >= .5)) or (o['dil'] != k['ilkdil'] and ent >= 2)
            if uygun and j + .15 * ent > enb: en, enb = c, j + .15 * ent
        if en is None:
            en = len(kumeler)
            kumeler.append(dict(ogeler=[], tok=set(), son=o['z'], ilk=set(o['tok']), ilkvar=set(ov), ilkdil=o['dil']))
        k = kumeler[en]
        k['ogeler'].append(o); k['tok'] |= o['tok']; k['son'] = max(k['son'], o['z'])
        if en == len(kumeler) - 1 and len(k['ogeler']) == 1:
            for tk in o['tok']: dizin[tk].append(en)
    return kumeler

def birlestir(kumeler):
    """Ayni olayi ayri kumelere bolen kopuklugu giderir (dil farki, farkli anlatim).
    Zincirleme birlesme YOK: kumeler buyukten kucuge siralanir, her kume en fazla bir "capa" kumeye baglanir.
    Baglanma sarti: ikisinden birer haber arasinda kelime benzerligi >= .35 VE ortak seyrek ozel ad (en cok 10
    kumede gecen), ya da en az uc ortak seyrek ozel ad. Tek ortak ad (ornek 'iPhone Duo') yetmez."""
    for k in kumeler:
        k['v'] = set().union(*(o['var'] for o in k['ogeler']))
    df = Counter(v for k in kumeler for v in k['v'])
    nadir = {v for v, n in df.items() if n <= 10}
    sirali = sorted(range(len(kumeler)), key=lambda i: -len(kumeler[i]['ogeler']))
    capalar = []                       # (kume, uyeler)
    dizin = defaultdict(list)          # seyrek ad -> capa sirasi
    def benzer(a, b):
        for x in a['ogeler'][:12]:
            for y in b['ogeler'][:12]:
                if not (x['var'] & y['var'] & nadir): continue
                u = len(x['tok'] | y['tok'])
                if u and len(x['tok'] & y['tok']) / u >= .35: return True
        return False
    for i in sirali:
        k = kumeler[i]; hedef = None
        adaylar = Counter(c for v in k['v'] & nadir for c in dizin[v])
        for c, _ in adaylar.most_common(8):
            capa = capalar[c][0]
            if abs(capa['son'] - k['son']) > 48 * 3600: continue
            if len(capa['v'] & k['v'] & nadir) >= 3 or benzer(capa, k): hedef = c; break
        if hedef is None:
            capalar.append((k, [k]))
            for v in k['v'] & nadir: dizin[v].append(len(capalar) - 1)
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
        sonuc.append(ana)
    return sonuc

def trendler(feeds):
    o = []
    for k, f in feeds.items():
        if 'trends' not in k: continue
        for it in f['items']:
            if ' - ' in it['t'] or ' vs ' in it['t'].lower() or GENEL_RED.search(it['t']): continue   # mac ve gundem trendi Reels'e yaramaz
            if not (konu_bul(it['t'], '', 'tech') or KITLE.search(it['t'])): continue                  # teknoloji ya da kullanici urunu degilse trend gosterme
            o.append(dict(t=it['t'], l=it['l'], ulke=k.split('-')[-1].upper(), i=it.get('i')))
    return o

def main():
    j = json.load(open('site/feeds.json', encoding='utf-8'))
    simdi = datetime.now(timezone.utc).timestamp()
    ogeler, gorulen = [], set()
    for sid, f in j['feeds'].items():
        if 'trends' in sid or f.get('lang') not in ('tr', 'en'): continue
        for it in f['items']:
            l = it.get('l'); t = (it.get('t') or '').strip()
            if not l or not t or l in gorulen or not it.get('d'): continue
            try: z = datetime.fromisoformat(it['d']).timestamp()
            except Exception: continue
            if simdi - z > SAAT * 3600 or z > simdi + 300: continue
            cat = it.get('c') or f['cat']
            konu = konu_bul(t, it.get('s', ''), cat)
            if GENEL_RED.search(t): continue                 # suc, siyaset, spor, yayin rehberi masaya girmez
            if not konu and (cat not in TEKNIK or cat == 'auto'): continue   # genel haber Son haberler'de durur
            if f.get('plat') == 'reddit' and len(t) < 25: continue
            gorulen.add(l)
            kayak = (it.get('p') or '').strip()
            if not kayak or kayak.startswith('http'): kayak = f['name']
            ogeler.append(dict(t=t, l=l, z=z, s=(it.get('s') or '')[:180], i=it.get('i'), k=konu, cat=cat, dil=f['lang'], kaynak=kayak,
                               plat=f.get('plat', 'web'), n=it.get('n'), tok={kok(w) for w in sozcuk(t)}, var=varlik(t)))
    kumeler = birlestir(kumele(ogeler))
    _df = Counter(v for k in kumeler for v in set().union(*(o['var'] for o in k['ogeler'])))
    NADIR_GLOBAL = {v for v, n in _df.items() if n <= 10}
    tr = trendler(j['feeds'])
    tr_tok = [(x, {kok(w) for w in sozcuk(x['t'])}) for x in tr]
    cikti = []
    for k in kumeler:
        og = sorted(k['ogeler'], key=lambda x: -x['z'])
        kaynaklar = list(dict.fromkeys(o['kaynak'] for o in og))
        ks = len(kaynaklar)
        konu = Counter(o['k'] for o in og if o['k']).most_common(1)
        konu = konu[0][0] if konu else 'genel'
        tr_og = [o for o in og if o['dil'] == 'tr']; en_og = [o for o in og if o['dil'] == 'en']
        # Baslik: Turkcesi varsa Turkce, kaynak basligi aynen; gorsel: kumede ilk bulunan.
        adaylar = tr_og or og
        bas = max(adaylar, key=lambda o: (sum(len(o['tok'] & q['tok']) for q in og), -o['z']))   # kumenin merkezindeki baslik: diger haberlerle en cok ortak kelime
        gorsel = bas.get('i') or next((o['i'] for o in sorted(og, key=lambda o: -len(o['tok'] & bas['tok'])) if o.get('i')), None)
        yas = (simdi - k['son']) / 3600
        ilk = min(o['z'] for o in og)
        hiz = sum(1 for o in og if simdi - o['z'] < 6 * 3600)
        metin = ' '.join(o['t'] for o in og)
        trend = next((x for x, ts in tr_tok if len(ts) >= 2 and sum(1 for w in ts if w in k['tok']) >= math.ceil(len(ts) * .75)), None)
        hn = max([o['n'] or 0 for o in og] or [0])
        # --- Reels puani: her satir bir neden ---
        p, ned = 0.0, []
        if ks >= 2: p += min(ks, 10) * 3; ned.append(f"{ks} kaynak yazdı")
        if hiz >= 2: p += min(hiz, 8) * 2; ned.append(f"Son 6 saatte {hiz} haber")
        if trend: p += 14; ned.append(f"Google'da trend ({trend['ulke']})")
        if hn >= 100: p += 8 + min(hn, 800) / 100; ned.append(f"Hacker News'te {hn} puan")
        vur = CARPICI.findall(metin)
        if CARPICI.search(bas['t']) or len(vur) >= 2: p += 8; ned.append('Merak uyandıran konu')
        kitle = KITLE.search(bas['t']) or KITLE.search(metin)
        etki = ETKI.search(bas['t'])
        elen = bool(REELS_RED.search(bas['t'])) or (konu == 'genel' and not kitle)
        if konu == 'genel': p -= 12
        else: p += KONU_AGIRLIK.get(konu, 0)
        if KITLE.search(bas['t']):
            p += 9; ned.insert(0, f"{KITLE.search(bas['t']).group(0).title()} kullanıcısını ilgilendiriyor")
        elif kitle: p += 4
        if etki: p += 6; ned.insert(1 if kitle else 0, 'Kullanıcıyı doğrudan etkiliyor')
        if REELS_CEZA.search(bas['t']): p -= 10
        if gorsel: p += 3
        else: p -= 8
        if en_og and not tr_og and ks >= 2: p += 6; ned.append('Türkçede henüz yok')
        if en_og and not tr_og and ks < 4 and not TURKIYE.search(metin) and not trend: p -= 6
        tr_ilgi = bool(TURKIYE.search(metin))
        if tr_ilgi: p += 7; ned.append("Türkiye'yi ilgilendiriyor")
        if RUTIN.search(bas['t']): p -= 12
        if ZAYIF.search(bas['t']): p -= 25
        elif ZAYIF.search(metin): p -= 8
        p *= math.exp(-yas / 40)
        tur = []
        if p >= 30 and ks >= 4 and gorsel: tur.append('kesin')
        if ks >= 3: tur.append('gundem')
        if tr_ilgi: tur.append('turkiye')
        if en_og and not tr_og: tur.append('yurtdisi')
        if CARPICI.search(bas['t']): tur.append('carpici')
        cikti.append(dict(
            id=hashlib.md5(bas['l'].encode()).hexdigest()[:10],
            t=bas['t'], s=bas['s'], i=gorsel, k=konu, cat=bas['cat'], dil='tr' if tr_og else 'en',
            l=bas['l'], ks=ks, son=int(k['son']), ilk=int(ilk), hiz=hiz, r=round(p, 1), ned=ned[:4], tur=tur, elen=elen,
            _tok={kok(w) for w in sozcuk(bas['t'])}, _var=varlik(bas['t']),
            og=[dict(t=o['t'], l=o['l'], p=o['kaynak'], z=int(o['z']), d=o['dil']) for o in og[:12]],
        ))
    cikti.sort(key=lambda c: -(min(c['ks'], 12) * 3 + c['hiz'] * 1.5 + (2 if c['i'] else 0)) * math.exp(-(simdi - c['son']) / 3600 / 18))
    gundem = cikti[:450]
    reels, konu_say, secilen = [], Counter(), []
    for c in sorted([c for c in cikti if c['r'] >= 20 and not c['elen']], key=lambda c: -c['r']):
        if konu_say[c['k']] >= REELS_KONU_UST: continue      # tek konu listeyi doldurmasin
        # Ayni olayin ikinci karti: secilmis bir adayla kelime benzerligi yuksekse ya da iki seyrek ozel ad ortaksa atla.
        if any(len(c['_tok'] & t) / max(1, len(c['_tok'] | t)) >= .3 or len(c['_var'] & v & NADIR_GLOBAL) >= 2 for t, v in secilen): continue
        konu_say[c['k']] += 1; reels.append(c); secilen.append((c['_tok'], c['_var']))
        if len(reels) >= REELS_TOPLAM: break
    goruld = {c['id'] for c in gundem}
    gundem += [c for c in reels if c['id'] not in goruld]
    konular = [dict(k=k, ad=ad) for k, ad, _ in KONULAR] + [dict(k='genel', ad='Teknoloji genel')]
    durum = []
    for sid, f in j['feeds'].items():
        ts = [i.get('d') or '' for i in f['items']]
        durum.append(dict(id=sid, ad=f['name'], cat=f['cat'], dil=f['lang'], plat=f.get('plat', 'web'), son=max(ts) if ts else '', bayat=bool(f.get('bayat')), n=len(ts)))
    for c in cikti: c.pop('_tok', None); c.pop('_var', None)
    masa = dict(generated=j['generated'], saglik=j.get('saglik', {}), konular=konular, kumeler=gundem, reels=[c['id'] for c in reels], trendler=tr[:30], kaynaklar=durum)
    json.dump(masa, open('site/masa.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('oge', len(ogeler), 'kume', len(cikti), 'cok kaynakli', sum(1 for c in cikti if c['ks'] >= 3), 'reels', len(reels), 'gorselli', round(sum(1 for c in gundem if c['i']) / max(1, len(gundem)) * 100), '%')
    for c in sorted(cikti, key=lambda c: -c['r'])[:14]:
        print(round(c['r'], 1), c['k'], c['ks'], '|', c['t'][:76], '|', c['tur'])
        if __import__('os').environ.get('AYRINTI'):
            for o in c['og'][:7]: print('      ', o['p'][:14], '|', o['t'][:90])

if __name__ == '__main__':
    main()
