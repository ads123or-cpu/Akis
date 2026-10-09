import json
j=json.load(open('site/feeds.json',encoding='utf-8'))
# gömülü kopya: her kaynaktan en yeni 8 haber (tam veri feeds.json'dan gelir)
snap={'generated':j['generated'],'feeds':{k:{**v,'items':v['items'][:8]} for k,v in j['feeds'].items()}}
s=json.dumps(snap,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
t=open('index.tpl.html',encoding='utf-8').read()
open('site/index.html','w',encoding='utf-8').write(t.replace('/*SNAP*/',s))
print(len(t),len(s))
