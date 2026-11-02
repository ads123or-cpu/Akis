import json
j=json.load(open('site/feeds.json',encoding='utf-8'))
# Gomulu kopya (sayfa ve panel ayni listeyi okur). Teknoloji ve genel ayri kotada:
# tek kotada genel haber hacmi teknolojiyi 30 habere dusuruyordu.
TEKNO = {'tech', 'samsung', 'ios', 'mac', 'mobil', 'win', 'auto'}
KOTA = 400
# Cince gibi kucuk dillerin haberleri teknoloji kotasinda yeni Turkce/Ingilizce haberin altinda kalip
# hic girmiyordu; kendi kotalari var.
KOTA_YABANCI = 60
tum = []
for k, f in j['feeds'].items():
    for it in f.get('items', []):
        tum.append((it.get('d') or '', k, it))
tum.sort(key=lambda x: x[0], reverse=True)
secili = {}
say = {True: 0, False: 0}
yabanci = 0
for _, k, it in tum:
    if j['feeds'][k].get('lang') not in ('tr', 'en'):
        if yabanci >= KOTA_YABANCI: continue
        yabanci += 1
    else:
        tek = (it.get('c') or j['feeds'][k]['cat']) in TEKNO
        if say[tek] >= KOTA: continue
        say[tek] += 1
    secili.setdefault(k, {**{a: b for a, b in j['feeds'][k].items() if a != 'items'}, 'items': []})['items'].append(it)
snap={'generated':j['generated'],'saglik':j.get('saglik',{}),'feeds':secili}
s=json.dumps(snap,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
t=open('index.tpl.html',encoding='utf-8').read()
open('site/index.html','w',encoding='utf-8').write(t.replace('/*SNAP*/',s))
print(len(t),len(s), sum(len(v['items']) for v in secili.values()), 'haber')
