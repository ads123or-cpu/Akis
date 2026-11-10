"""Akış 3 ekleri: Google Trends (geçmişli, haberle eşleşen) ve Güncelleme Radarı (işletim sistemi / uygulama / arayüz).
akis2.main() çağırır; ağ kullanmaz, site/feeds.json içinden okur."""
import json, os, re
from datetime import datetime
import masa as M

GECMIS = 'site/trend-gecmis.json'      # trendin ilk görüldüğü an, tepe hacmi, hacim serisi (commitlenir, küçük)
ULKE_AD = {'TR': 'Türkiye', 'US': 'ABD', 'GB': 'Birleşik Krallık', 'DE': 'Almanya', 'FR': 'Fransa', 'JP': 'Japonya', 'KR': 'Güney Kore'}
SPOR_TREND = re.compile(r"\s(vs\.?|–|-)\s|\bmaçı?\b|\bfc\b|\bspor\b|galatasaray|fenerbahçe|beşiktaş|trabzonspor|uefa|şampiyonlar ligi|uluslar ligi|süper lig|nba|nfl|premier league|la liga|serie a|bundesliga|f1|formula", re.I)


def _tok(t):
    return {M.kok(w) for w in M.sozcuk(t) if len(w) > 1}


def _anahtar(t):
    return re.sub(r'\s+', ' ', t.strip().lower())


def simdi_fark(c):
    return max(0, _SIMDI[0] - c['son'])


_SIMDI = [0]


def trend_eslestir(trend, kumeler):
    """Trend terimini ve trendi açıklayan haber başlıklarını kümelerle karşılaştırır. En iyi (küme, puan) döner."""
    kel = [w for w in M.sozcuk(trend['t']) if len(w) > 1]
    if not kel: return None, 0
    hn = [_tok(h['t']) for h in trend.get('hn') or []]
    gerek = len(kel) if len(kel) <= 2 else max(2, len(kel) - 1)
    en, en_p = None, 0
    for c in kumeler:
        ck = c['_kel']
        # Terimin sözcükleri kümenin başlıklarında geçmeli (Türkçe ek için en çok 5 harflik uzantıya izin)
        ortak = sum(1 for w in kel if w in ck or (len(w) >= 4 and any(x.startswith(w) and len(x) - len(w) <= 5 for x in ck)))
        if ortak < gerek: continue
        p = .7 + .3 * ortak / len(kel)
        # Trendi anlatan haber başlıkları kümedeki başlıklara benziyorsa güven artar
        for h in hn:
            if h: p = max(p, 1 + max((len(h & o) / max(1, len(h | o)) for o in c['_otok']), default=0))
        p2 = p + min(c['kb'], 10) * .01 - (simdi_fark(c) / 86400) * .05
        if p2 > en_p: en, en_p = c, p2
    return en, round(en_p, 2)


def trendler_uret(feeds, kumeler, simdi):
    """feeds: feeds.json 'feeds'; kumeler: akis2 küme sözlükleri (t, og, kb, son, alanlar, id). simdi: epoch sn."""
    _SIMDI[0] = simdi
    try: gecmis = json.load(open(GECMIS, encoding='utf-8'))
    except Exception: gecmis = {}
    for c in kumeler:
        c['_otok'] = [_tok(o['t']) for o in c['og']]
        c['_kel'] = {w for o in c['og'] for w in M.sozcuk(o['t'])} | set(M.sozcuk(c['t']))
        c['_tok'] = set().union(*c['_otok']) if c['_otok'] else set()
    yakin = [c for c in kumeler if simdi - c['son'] < 72 * 3600]
    ulkeler = {}
    for sid, f in feeds.items():
        if not sid.startswith('trends-'): continue
        geo = sid.split('-')[-1].upper()
        g = gecmis.setdefault(geo, {})
        aktif = []
        for it in f.get('items', []):
            k = _anahtar(it['t'])
            try: bas_z = datetime.fromisoformat(it['d']).timestamp() if it.get('d') else simdi
            except Exception: bas_z = simdi
            h = g.get(k) or dict(t=it['t'], ilk=int(min(bas_z, simdi)), tepe=0, seri=[])
            n = it.get('n') or 0
            h.update(son=int(simdi), hn=(it.get('hn') or [])[:4], i=it.get('i'), tr=it.get('tr', ''), l=it['l'])
            h['tepe'] = max(h['tepe'], n)
            if not h['seri'] or h['seri'][-1][1] != n or simdi - h['seri'][-1][0] > 3 * 3600: h['seri'].append([int(simdi), n])
            h['seri'] = h['seri'][-24:]
            g[k] = h
            aktif.append(k)
        # eşleştir ve çıktı
        lst = []
        for k, h in g.items():
            if simdi - h['son'] > 48 * 3600: continue
            c, puan = trend_eslestir(h, yakin) if geo == 'TR' or geo in ('US', 'GB') else (None, 0)
            alan = (c['alanlar'][0] if c and c.get('alanlar') else ('spor' if SPOR_TREND.search(h['t'] + ' ' + ' '.join(x['t'] for x in h['hn'][:2])) else 'gundem'))
            onceki = h['seri'][-2][1] if len(h['seri']) > 1 else 0
            lst.append(dict(t=h['t'], tr=h.get('tr', ''), n=h['seri'][-1][1] if h['seri'] else 0, tepe=h['tepe'], ilk=h['ilk'], son=h['son'], aktif=k in aktif,
                            artis=(h['seri'][-1][1] > onceki > 0), seri=h['seri'][-12:], l=h['l'], i=h.get('i'), hn=h['hn'], alan=alan,
                            kume=dict(id=c['id'], t=c['t'], kb=c['kb'], son=c['son'], alanlar=c['alanlar']) if c else None, eslesme=puan,
                            firsat=(c is None or c['kb'] <= 1)))
        lst.sort(key=lambda x: (not x['aktif'], -x['n'], -x['ilk']))
        ulkeler[geo] = dict(ad=ULKE_AD.get(geo, geo), trendler=lst[:40], guncel=max((h['son'] for h in g.values()), default=0))
        # 48 saatten eski trendleri geçmişten at
        gecmis[geo] = {k: h for k, h in g.items() if simdi - h['son'] <= 48 * 3600}
    for c in kumeler: c.pop('_otok', None); c.pop('_tok', None); c.pop('_kel', None)
    os.makedirs(os.path.dirname(GECMIS), exist_ok=True)
    with open(GECMIS, 'w', encoding='utf-8') as f: json.dump(gecmis, f, ensure_ascii=False, separators=(',', ':'))
    sira = ['TR'] + sorted(k for k in ulkeler if k != 'TR')
    return dict(sira=[k for k in sira if k in ulkeler], ulkeler=ulkeler,
                not_='Google Trends günlük arama trendleri (RSS). Hacim yaklaşık değerdir. "Bizde yok" işareti: Akış kaynaklarında bu konuda en fazla 1 bağımsız haber var.')


# ------------------------------------------------------------------ Güncelleme Radarı
URUN = [  # (anahtar, ad, grup, desen)
    ('ios', 'iOS / iPadOS', 'Apple', r"\bi(?:pad)?os\s?\d{2}|\bi(?:pad)?os (?:update|güncelle|beta)|iphone (?:update|güncelle)"),
    ('macos', 'macOS', 'Apple', r"\bmacos\b"),
    ('watchos', 'watchOS / visionOS', 'Apple', r"\bwatchos\b|\bvisionos\b|\btvos\b"),
    ('android', 'Android', 'Google', r"\bandroid\s?1\d\b|\bandroid (?:update|güncelle|beta|qpr)|pixel (?:drop|update|feature)|\bandroid'?(?:e|a|in|ın|un)? (?:yeni|gelen)"),
    ('oneui', 'Samsung One UI', 'Samsung', r"\bone ?ui\b|galaxy (?:update|güncelle)"),
    ('hyperos', 'Xiaomi HyperOS', 'Xiaomi', r"\bhyperos\b|\bmiui\b"),
    ('oxygenos', 'OnePlus / OPPO', 'Diğer Android', r"\boxygenos\b|\bcoloros\b|\bfuntouch\b|\borigin ?os\b|\bharmonyos\b|\bmagicos\b"),
    ('windows', 'Windows', 'Microsoft', r"\bwindows 1[01]\b|\bwindows update\b|\bwindows insider\b|\bwindows (?:güncelle|yeni özellik)"),
    ('office', 'Microsoft 365 / Copilot', 'Microsoft', r"\bcopilot\b|\bmicrosoft 365\b|\boffice\b.{0,20}(?:update|güncelle|feature|özellik)|\bteams\b.{0,20}(?:update|güncelle|feature|özellik)|\boutlook\b"),
    ('chrome', 'Chrome / tarayıcılar', 'Tarayıcı', r"\bchrome\b|\bfirefox\b|\bmicrosoft edge\b|\bedge (?:browser|tarayıcı)|\bsafari\b|\bopera\b|\bbrave\b|\barc browser\b"),
    ('whatsapp', 'WhatsApp', 'Meta', r"\bwhatsapp\b"),
    ('instagram', 'Instagram / Threads', 'Meta', r"\binstagram\b|\bthreads\b"),
    ('facebook', 'Facebook / Messenger', 'Meta', r"\bfacebook\b|\bmessenger\b"),
    ('x', 'X (Twitter)', 'Sosyal', r"\bx\.com\b|\btwitter\b|\bgrok\b|\bx'?(?:e|te|in|ın)? (?:yeni|gelen) özellik|\bx (?:adds|rolls|launches|update)"),
    ('tiktok', 'TikTok', 'Sosyal', r"\btiktok\b"),
    ('youtube', 'YouTube', 'Google', r"\byoutube\b"),
    ('telegram', 'Telegram / Signal', 'Sosyal', r"\btelegram\b|\bsignal app\b|\bsignal'?(?:e|in)\b"),
    ('google', 'Google uygulamaları', 'Google', r"\bgmail\b|google (?:maps|haritalar|photos|fotoğraflar|drive|docs|dokümanlar|workspace|play|wallet|cüzdan|search|arama|lens|keep|calendar|takvim|messages|mesajlar|tv)\b"),
    ('chatgpt', 'ChatGPT / OpenAI', 'Yapay zekâ', r"\bchatgpt\b|\bopenai\b|\bsora\b|\bgpt-?\d"),
    ('gemini', 'Gemini', 'Yapay zekâ', r"\bgemini\b"),
    ('claude', 'Claude', 'Yapay zekâ', r"\bclaude\b|\banthropic\b"),
    ('spotify', 'Spotify / Netflix', 'Eğlence', r"\bspotify\b|\bnetflix\b(?=.{0,30}(?:\bapp\b|uygulama|update|güncelle|test ediyor|testing|yeni özellik|new feature))|\bapple music\b|\byoutube music\b"),
    ('oyun', 'Oyun platformları', 'Oyun', r"(?:\bsteam\b|\bplaystation\b|\bps5\b|\bxbox\b|\bnintendo switch\b|\bswitch 2\b|\bepic games store\b)(?=.{0,40}(?:system (?:software|update)|sistem (?:yazılımı|güncelle)|firmware|update|güncelle|feature|özellik|arayüz|interface|redesign|beta))"),
    ('arac', 'Araç yazılımı', 'Otomobil', r"(?:tesla|togg|bmw|mercedes|volkswagen|byd|hyundai|ford).{0,40}(?:software update|ota|yazılım güncelle|yeni özellik|update)|\bcarplay\b|\bandroid auto\b"),
    ('edevlet', 'e-Devlet ve operatörler', 'Türkiye', r"e-?devlet|\bturkcell\b|\bvodafone\b|türk telekom|\bbip\b.{0,20}(?:özellik|güncelle)|\bpaycell\b|\bpapara\b"),
    ('linux', 'Linux', 'Diğer', r"\blinux\b|\bubuntu\b|\bfedora\b|\bgnome\b|\bkde\b"),
]
URUN_RX = [(k, ad, g, re.compile(d, re.I)) for k, ad, g, d in URUN]
GUNCEL = re.compile(r"güncelleme|update[sd]?\b|upgrade|özellik|feature|rolling out|rolls? out|kullanıma sun|beta\b|preview|insider|canary|sürüm|redesign|arayüz|tasarım|new (?:look|design|interface|ui|tab|button|option|setting)|changelog|patch|yama|ekledi|ekleniyor|geliyor|getiriyor|\badds?\b|\bgets?\b|test ediyor|testing|seçenek|sekme|widget|dağıtım|kararlı|stable|ota\b|firmware", re.I)
TUR = [  # ilk eşleşen kazanır
    ('guvenlik', 'Güvenlik yaması', re.compile(r"güvenlik (?:açı|yama|güncelle)|açıkları(?:nı)? kapat|açığı(?:nı)? kapat|security (?:update|patch|fix)|zero-?day|sıfırıncı gün|vulnerab|exploit|cve-\d|patch tuesday", re.I)),
    ('sizinti', 'Sızıntı / iddia', re.compile(r"sızdı|sızıntı|iddia|leak|rumou?r|reportedly|could|might|may (?:get|soon)|kodda|code (?:reveals|hints)|apk teardown|spotted", re.I)),
    ('beta', 'Beta / test', re.compile(r"\bbeta\b|preview|insider|canary|dev channel|test ediyor|testing|tests?\b|deneme sürümü|developer", re.I)),
    ('tasarim', 'Arayüz / tasarım', re.compile(r"redesign|yeni (?:arayüz|tasarım|görünüm)|new (?:look|design|interface|ui|layout)|arayüz|tasarım|interface|\bui\b|dark mode|karanlık mod|icon|ikon|widget", re.I)),
    ('yayinda', 'Yayında', re.compile(r"rolling out|rolls? out|kullanıma sun|yayınlandı|released?|now available|available now|is out|arrives|çıktı|stable|kararlı|indirmeye açıldı|herkese", re.I)),
    ('ozellik', 'Yeni özellik', re.compile(r"özellik|feature|adds?\b|ekledi|ekleniyor|geliyor|getiriyor|gets?\b|option|seçenek", re.I)),
]


def guncellemeler_uret(kumeler, simdi, gun=7):
    out = {}
    for c in kumeler:
        if simdi - c['son'] > gun * 86400: continue
        basliklar = [c['t']] + [o['t'] for o in c['og'][:8]]
        metin = ' '.join(basliklar)
        # Ürün: başlıkta ürün adı ve ürün adının 60 karakter çevresinde güncelleme ifadesi (ana başlıkta ya da en az 2 başlıkta)
        urun = None
        for k, ad, g, rx in URUN_RX:
            def yakin(b):
                m = rx.search(b)
                return bool(m) and bool(GUNCEL.search(b[max(0, m.start() - 60):m.end() + 60]))
            if yakin(c['t']) or sum(1 for b in basliklar[1:] if yakin(b)) >= 2: urun = (k, ad, g); break
        if not urun: continue
        tur = next((k for k, ad, rx in TUR if rx.search(c['t'])), None) or next((k for k, ad, rx in TUR if rx.search(metin)), 'ozellik')
        out.setdefault(urun[0], dict(k=urun[0], ad=urun[1], grup=urun[2], ogeler=[]))['ogeler'].append(dict(
            id=c['id'], t=c['t'], s=(c.get('s') or '')[:180], l=c['l'], i=c.get('i'), son=c['son'], ilk=c['ilk'], kb=c['kb'], ks=c['ks'], tur=tur,
            dil=c['dil'], kaynaklar=c['kaynaklar'][:5], og=[dict(t=o['t'], l=o['l'], p=o['p'], z=o['z'], d=o['d']) for o in c['og'][:6]]))
    urunler = []
    for u in out.values():
        u['ogeler'].sort(key=lambda x: -x['son'])
        u['ogeler'] = u['ogeler'][:30]
        u['son'] = u['ogeler'][0]['son']; u['n'] = len(u['ogeler']); u['n24'] = sum(1 for x in u['ogeler'] if simdi - x['son'] < 86400)
        urunler.append(u)
    urunler.sort(key=lambda u: (-u['n24'], -u['son']))
    return dict(urunler=urunler, turler=[dict(k=k, ad=ad) for k, ad, _ in TUR], gun=gun,
                not_='Son %d günde işletim sistemi, uygulama ve arayüz güncellemesi anlatan konular. Tür, başlıktaki ifadelerden kural tabanlı çıkarılır.' % gun)
