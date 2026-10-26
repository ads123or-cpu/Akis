import json
j=json.load(open('site/feeds.json',encoding='utf-8'))
# Gomulu kopya: tum kaynaklardan en yeni 600 haber (sayfa ve panel ayni taze listeyi okur).
# Eskiden her kaynaktan 6 haber gomuluyordu; yogun kaynaklar bosluk birakiyor, akis bayatliyordu.
EN_COK = 600
tum = []
for k, f in j['feeds'].items():
    for it in f.get('items', []):
        tum.append((it.get('d') or '', k, it))
tum.sort(key=lambda x: x[0], reverse=True)
secili = {}
for _, k, it in tum[:EN_COK]:
    secili.setdefault(k, {**{a: b for a, b in j['feeds'][k].items() if a != 'items'}, 'items': []})['items'].append(it)
snap={'generated':j['generated'],'saglik':j.get('saglik',{}),'feeds':secili}
s=json.dumps(snap,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
t=open('index.tpl.html',encoding='utf-8').read()
open('site/index.html','w',encoding='utf-8').write(t.replace('/*SNAP*/',s))
print(len(t),len(s), sum(len(v['items']) for v in secili.values()), 'haber')
