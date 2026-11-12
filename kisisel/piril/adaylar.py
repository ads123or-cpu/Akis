# -*- coding: utf-8 -*-
# Pırıl Cennet — Dünya masası: YALNIZ yabancı dilde dünya haberi kaynakları (2026-11-12).
# Ana akışın sources.json listesine GİRMEZ (kaynak_birlestir.py ile birleştirilmez). Kimlikler 'pc-' önekli.
# (id, ad, dil, ulke, cat, calisma, tip, url, nitelik)
import urllib.parse
GN = {'en': ('en-US', 'US', 'US:en'), 'en-GB': ('en-GB', 'GB', 'GB:en'), 'de': ('de', 'DE', 'DE:de'), 'fr': ('fr', 'FR', 'FR:fr'),
      'es': ('es', 'ES', 'ES:es'), 'es-MX': ('es-419', 'MX', 'MX:es-419'), 'it': ('it', 'IT', 'IT:it'), 'pt': ('pt-BR', 'BR', 'BR:pt-419'),
      'ru': ('ru', 'RU', 'RU:ru'), 'ar': ('ar', 'SA', 'SA:ar'), 'ja': ('ja', 'JP', 'JP:ja'), 'ko': ('ko', 'KR', 'KR:ko'),
      'zh': ('zh-TW', 'TW', 'TW:zh-Hant'), 'uk': ('uk', 'UA', 'UA:uk'), 'pl': ('pl', 'PL', 'PL:pl'), 'nl': ('nl', 'NL', 'NL:nl'),
      'he': ('he', 'IL', 'IL:he'), 'el': ('el', 'GR', 'GR:el'), 'fa': ('fa', 'IR', 'IR:fa')}
def gw(id_, ad, dil, ulke, yer):
    hl, gl, ceid = GN[yer]
    return (id_, 'Google News Dünya: ' + ad, dil, ulke, 'world', 'gundem', 'toplayici',
            'https://news.google.com/rss/headlines/section/topic/WORLD?hl=%s&gl=%s&ceid=%s' % (hl, gl, ceid), 'toplayici')
def gs(id_, ad, site, q=''):
    return (id_, ad + ' (Google News)', 'en', 'US', 'world', 'gundem', 'ajans',
            'https://news.google.com/rss/search?q=%s&hl=en-US&gl=US&ceid=US:en' % urllib.parse.quote('when:1d site:%s %s' % (site, q)).strip(), 'ajans')
def u(id_, ad, dil, ulke, url, tip='ana akim'):
    return (id_, ad, dil, ulke, 'world', 'gundem', tip, url, '')

A = [
    gs('pc-reuters', 'Reuters World', 'reuters.com/world'), gs('pc-ap', 'AP World', 'apnews.com'),
    gw('pc-gnw-us', 'ABD (EN)', 'en', 'US', 'en'), gw('pc-gnw-gb', 'Birleşik Krallık (EN)', 'en', 'GB', 'en-GB'),
    gw('pc-gnw-de', 'Almanya', 'de', 'DE', 'de'), gw('pc-gnw-fr', 'Fransa', 'fr', 'FR', 'fr'), gw('pc-gnw-es', 'İspanya', 'es', 'ES', 'es'),
    gw('pc-gnw-mx', 'Latin Amerika', 'es', 'MX', 'es-MX'), gw('pc-gnw-it', 'İtalya', 'it', 'IT', 'it'), gw('pc-gnw-br', 'Brezilya', 'pt', 'BR', 'pt'),
    gw('pc-gnw-ru', 'Rusya', 'ru', 'RU', 'ru'), gw('pc-gnw-ar', 'Arap dünyası', 'ar', 'SA', 'ar'), gw('pc-gnw-jp', 'Japonya', 'ja', 'JP', 'ja'),
    gw('pc-gnw-kr', 'Güney Kore', 'ko', 'KR', 'ko'), gw('pc-gnw-tw', 'Tayvan', 'zh', 'TW', 'zh'), gw('pc-gnw-ua', 'Ukrayna', 'uk', 'UA', 'uk'),
    gw('pc-gnw-pl', 'Polonya', 'pl', 'PL', 'pl'), gw('pc-gnw-nl', 'Hollanda', 'nl', 'NL', 'nl'), gw('pc-gnw-il', 'İsrail', 'he', 'IL', 'he'),
    gw('pc-gnw-gr', 'Yunanistan', 'el', 'GR', 'el'),
    # İspanyolca
    u('pc-bbc-mundo', 'BBC Mundo', 'es', 'GB', 'https://feeds.bbci.co.uk/mundo/rss.xml'),
    u('pc-elmundo', 'El Mundo Internacional', 'es', 'ES', 'https://e00-elmundo.uecdn.es/elmundo/rss/internacional.xml'),
    u('pc-elpais-int', 'El País Internacional', 'es', 'ES', 'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada'),
    u('pc-cnn-es', 'CNN en Español', 'es', 'US', 'https://cnnespanol.cnn.com/feed/'),
    u('pc-infobae', 'Infobae', 'es', 'AR', 'https://www.infobae.com/arc/outboundfeeds/rss/'),
    u('pc-dw-es', 'DW Español', 'es', 'DE', 'https://rss.dw.com/rdf/rss-sp-all'),
    u('pc-france24-es', 'France 24 Español', 'es', 'FR', 'https://www.france24.com/es/rss'),
    # İtalyanca
    u('pc-ansa', 'ANSA Mondo', 'it', 'IT', 'https://www.ansa.it/sito/notizie/mondo/mondo_rss.xml', 'ajans'),
    u('pc-corriere', 'Corriere Esteri', 'it', 'IT', 'https://xml2.corriereobjects.it/rss/esteri.xml'),
    u('pc-repubblica', 'la Repubblica Esteri', 'it', 'IT', 'https://www.repubblica.it/rss/esteri/rss2.0.xml'),
    # Portekizce
    u('pc-bbc-br', 'BBC News Brasil', 'pt', 'GB', 'https://feeds.bbci.co.uk/portuguese/rss.xml'),
    u('pc-folha', 'Folha Mundo', 'pt', 'BR', 'https://feeds.folha.uol.com.br/mundo/rss091.xml'),
    u('pc-dw-br', 'DW Brasil', 'pt', 'DE', 'https://rss.dw.com/rdf/rss-br-all'),
    # Rusça / Ukraynaca / Farsça / Hintçe
    u('pc-bbc-ru', 'BBC Русская служба', 'ru', 'GB', 'https://feeds.bbci.co.uk/russian/rss.xml'),
    u('pc-meduza', 'Meduza', 'ru', 'LV', 'https://meduza.io/rss/all'),
    u('pc-dw-ru', 'DW на русском', 'ru', 'DE', 'https://rss.dw.com/rdf/rss-ru-all'),
    u('pc-kommersant', 'Коммерсантъ Мир', 'ru', 'RU', 'https://www.kommersant.ru/RSS/section-world.xml'),
    u('pc-bbc-ua', 'BBC News Україна', 'uk', 'GB', 'https://feeds.bbci.co.uk/ukrainian/rss.xml'),
    u('pc-pravda-ua', 'Українська правда', 'uk', 'UA', 'https://www.pravda.com.ua/rss/'),
    u('pc-bbc-fa', 'BBC فارسی', 'fa', 'GB', 'https://feeds.bbci.co.uk/persian/rss.xml'),
    u('pc-bbc-hi', 'BBC हिंदी', 'hi', 'GB', 'https://feeds.bbci.co.uk/hindi/rss.xml'),
    # Almanca
    u('pc-spiegel-ausland', 'Spiegel Ausland', 'de', 'DE', 'https://www.spiegel.de/ausland/index.rss'),
    u('pc-faz', 'FAZ Politik', 'de', 'DE', 'https://www.faz.net/rss/aktuell/politik/'),
    u('pc-sz', 'Süddeutsche Politik', 'de', 'DE', 'https://rss.sueddeutsche.de/rss/Politik'),
    u('pc-nzz', 'NZZ International', 'de', 'CH', 'https://www.nzz.ch/international.rss'),
    # Fransızca
    u('pc-lemonde-int', 'Le Monde International', 'fr', 'FR', 'https://www.lemonde.fr/international/rss_full.xml'),
    u('pc-figaro', 'Le Figaro International', 'fr', 'FR', 'https://www.lefigaro.fr/rss/figaro_international.xml'),
    u('pc-rfi', 'RFI', 'fr', 'FR', 'https://www.rfi.fr/fr/rss'),
    u('pc-liberation', 'Libération Monde', 'fr', 'FR', 'https://www.liberation.fr/arc/outboundfeeds/rss-all/category/international/?outputType=xml'),
    # Arapça
    u('pc-alarabiya', 'العربية', 'ar', 'AE', 'https://www.alarabiya.net/feed/rss2/ar.xml'),
    u('pc-skynewsarabia', 'سكاي نيوز عربية', 'ar', 'AE', 'https://www.skynewsarabia.com/rss'),
    u('pc-aawsat', 'الشرق الأوسط', 'ar', 'GB', 'https://aawsat.com/feed'),
    # Asya
    u('pc-nhk', 'NHK 国際', 'ja', 'JP', 'https://www3.nhk.or.jp/rss/news/cat6.xml'),
    u('pc-asahi', '朝日新聞', 'ja', 'JP', 'https://www.asahi.com/rss/asahi/newsheadlines.rdf'),
    u('pc-yna-int', '연합뉴스 국제', 'ko', 'KR', 'https://www.yna.co.kr/rss/international.xml', 'ajans'),
    u('pc-hani-int', '한겨레 국제', 'ko', 'KR', 'https://www.hani.co.kr/rss/international/'),
    u('pc-rfi-zh', 'RFI 中文', 'zh', 'FR', 'https://www.rfi.fr/cn/rss'),
    u('pc-nyt-zh', '纽约时报中文网', 'zh', 'US', 'https://cn.nytimes.com/rss/'),
    # Diğer Avrupa / Orta Doğu
    u('pc-kathimerini', 'Καθημερινή', 'el', 'GR', 'https://www.kathimerini.gr/infeeds/rss/nx-rss-feed.xml'),
    u('pc-tvn24', 'TVN24 Świat', 'pl', 'PL', 'https://tvn24.pl/swiat.xml'),
    u('pc-nos', 'NOS Buitenland', 'nl', 'NL', 'https://feeds.nos.nl/nosnieuwsbuitenland'),
    u('pc-ynet', 'ynet', 'he', 'IL', 'https://www.ynet.co.il/Integration/StoryRss2.xml'),
]
