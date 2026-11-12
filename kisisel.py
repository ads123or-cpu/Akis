#!/usr/bin/env python3
"""Kişisel alanlar (Akış içinde ayrı masa). Şu an: Pırıl Cennet — Dünya masası.

Kişinin kendi kaynak listesi (kisisel/<profil>/sources.json) ayrı çekilir (fetch_feeds.py --profil <profil>)
ve burada ayrı kümelenir. Ana akışın dosyalarına (sources.json, site/feeds.json, site/data/kume-*, dil-*, ozet)
ne okunur ne yazılır; ana akışın kaynakları da buraya karışmaz.

Kural: Dünya masasına YALNIZ yabancı dilde (Türkçe dışı) haber girer.
Çıktı: site/data/kisisel/<profil>.json"""
import json, math, os, sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import akis2 as A
import fetch_feeds as F

PROFILLER = {'piril': dict(ad='Pırıl Cennet', masa='Dünya masası')}
SINIR = 500          # dosyaya yazılan küme
CIKTI = os.path.join(A.CIKTI, 'kisisel')


def uret(profil):
    y = F.profil_yollari(profil)
    j = json.load(open(y['cikti'], encoding='utf-8'))
    src = {s['id']: s for s in json.load(open(y['kaynak'], encoding='utf-8'))}
    try: dur = json.load(open(y['durum'], encoding='utf-8'))
    except Exception: dur = {}
    simdi_dt = datetime.fromisoformat(j['generated']) if j.get('generated') else datetime.now(timezone.utc)
    simdi = simdi_dt.timestamp()
    # yalnız yabancı dil: Türkçe akışlar ve Türkçe etiketli öğeler hiç girmez
    j = dict(j, feeds={k: v for k, v in j['feeds'].items() if k in src and v.get('lang') != 'tr' and src[k].get('lang') != 'tr'})
    ogeler, n72 = A.ogeler_kur(j, src, simdi)
    ogeler = [o for o in ogeler if o['dil'] != 'tr']
    cikti = A.kumeler_kur(A.kumele_tam(ogeler), simdi)
    tum = [c for c, _, _ in cikti]

    def puan(c):
        return (min(c['kb'], 10) * 2 + c['h6'] * 1.5 + c['h24'] * .3 + 1) * math.exp(-(simdi - c['son']) / 3600 / 12)

    def kart(c):
        return dict(id=c['id'], t=c['t'], s=c['s'][:220], i=c['i'], l=c['l'], dil=c['dil'], diller=c['diller'], ks=c['ks'], kb=c['kb'],
                    ilk=c['ilk'], son=c['son'], h1=c['h1'], h6=c['h6'], h24=c['h24'], yog=c['yog'], kaynaklar=c['kaynaklar'][:8],
                    konu=[k for k in c['gundem_alt'] if k not in ('turkiye', 'dunya')], tr_ilgili='turkiye' in c['gundem_alt'],
                    ul=c['ulkeler'], ld=c['liderler'], resmi=c['resmi'], kanit=c['kanit'], farkli=c['farkli'], og=c['og'], alanlar=c['alanlar'])
    secili = sorted(tum, key=lambda c: -puan(c))[:SINIR]
    dil_n = Counter(c['dil'] for c in tum)
    diller = [dict(k=d, ad=A.DIL_AD.get(d, (d.upper(), d.upper()))[0], tr=A.DIL_AD.get(d, (d.upper(), d.upper()))[1], n=n,
                   n24=sum(1 for c in tum if c['dil'] == d and simdi - c['son'] < 86400)) for d, n in dil_n.most_common()]
    konu_n = Counter(k for c in secili for k in c['gundem_alt'] if k not in ('dunya',))
    simdi_iso = simdi_dt.isoformat()
    kay = []
    for sid, s in src.items():
        d = dur.get(sid) or {}
        kay.append(dict(id=sid, ad=s['name'], dil=s['lang'], ulke=s.get('ulke'), tip=s.get('tip'), url=s['url'],
                        durum=A.durum_hesapla(s, d, simdi_iso, simdi, n72), haber72=n72.get(sid, 0), son_haber=d.get('son_haber')))
    kay.sort(key=lambda k: (k['dil'], k['ad'].lower()))
    p = PROFILLER[profil]
    out = dict(generated=j['generated'], profil=profil, ad=p['ad'], masa=p['masa'], kural='Yalnız yabancı dilde (Türkçe dışı) haberler.',
               toplam=dict(haber=len(ogeler), kume=len(tum), kaynak=len(src), cok_kaynakli=sum(1 for c in tum if c['kb'] >= 3)),
               diller=diller, konular=[dict(k=k, ad=dict(A.GUNDEM_ALT).get(k, k), n=n) for k, n in konu_n.most_common()],
               kumeler=[kart(c) for c in secili], kaynaklar=kay, durum_say=dict(Counter(k['durum'] for k in kay)))
    os.makedirs(CIKTI, exist_ok=True)
    yol = os.path.join(CIKTI, profil + '.json')
    with open(yol, 'w', encoding='utf-8') as f: json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(profil, 'oge', len(ogeler), 'kume', len(tum), 'yazilan', len(secili), '%dKB' % (os.path.getsize(yol) / 1024), dict(dil_n.most_common(8)))


if __name__ == '__main__':
    for p in (sys.argv[1:] or PROFILLER):
        uret(p)
