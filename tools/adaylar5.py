# -*- coding: utf-8 -*-
# Akış 4: dünya dillerinden popüler teknoloji kaynakları (Çince, Japonca, Korece, Almanca, Fransızca, İspanyolca,
# İtalyanca, Rusça, Portekizce, Hintçe/Hindistan, Vietnamca, Endonezyaca, Lehçe, Hollandaca) ve Google News teknoloji başlıkları (2026-11-12).
# (id, ad, dil, ulke, cat, calisma, tip, url, nitelik)
GN_YER = {  # dil: (hl, gl, ceid)
    'zh-CN': ('zh-CN', 'CN', 'CN:zh-Hans'), 'zh-TW': ('zh-TW', 'TW', 'TW:zh-Hant'), 'zh-HK': ('zh-HK', 'HK', 'HK:zh-Hant'),
    'ja': ('ja', 'JP', 'JP:ja'), 'ko': ('ko', 'KR', 'KR:ko'), 'de': ('de', 'DE', 'DE:de'), 'fr': ('fr', 'FR', 'FR:fr'),
    'es': ('es', 'ES', 'ES:es'), 'es-MX': ('es-419', 'MX', 'MX:es-419'), 'it': ('it', 'IT', 'IT:it'), 'ru': ('ru', 'RU', 'RU:ru'),
    'pt-BR': ('pt-BR', 'BR', 'BR:pt-419'), 'hi': ('hi', 'IN', 'IN:hi'), 'en-IN': ('en-IN', 'IN', 'IN:en'), 'vi': ('vi', 'VN', 'VN:vi'),
    'id': ('id', 'ID', 'ID:id'), 'pl': ('pl', 'PL', 'PL:pl'), 'nl': ('nl', 'NL', 'NL:nl'), 'ar': ('ar', 'SA', 'SA:ar'),
    'en-GB': ('en-GB', 'GB', 'GB:en'), 'tr': ('tr', 'TR', 'TR:tr'), 'uk': ('uk', 'UA', 'UA:uk'),
}
def gn_konu(yer):
    hl, gl, ceid = GN_YER[yer]
    return 'https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=%s&gl=%s&ceid=%s' % (hl, gl, ceid)
def gn_ara(q, yer):
    import urllib.parse
    hl, gl, ceid = GN_YER[yer]
    return 'https://news.google.com/rss/search?q=%s&hl=%s&gl=%s&ceid=%s' % (urllib.parse.quote(q), hl, gl, ceid)

def u(id_, ad, dil, ulke, url, cat='tech', tip='uzman teknoloji', nit=''):
    return (id_, ad, dil, ulke, cat, 'tekno', tip, url, nit)
def gk(id_, ad, dil, ulke, yer):
    return (id_, 'Google News Teknoloji: ' + ad, dil, ulke, 'tech', 'tekno', 'toplayici', gn_konu(yer), 'toplayici')
def ga(id_, ad, dil, ulke, q, yer, cat='tech'):
    return (id_, ad + ' (Google News)', dil, ulke, cat, 'tekno', 'toplayici', gn_ara(q, yer), 'toplayici')

A = [
    # --- Google News teknoloji başlıkları (her ülkenin en çok okunan teknoloji haberleri)
    gk('gnt-cn', 'Çin', 'zh', 'CN', 'zh-CN'), gk('gnt-tw', 'Tayvan', 'zh', 'TW', 'zh-TW'), gk('gnt-hk', 'Hong Kong', 'zh', 'HK', 'zh-HK'),
    gk('gnt-jp', 'Japonya', 'ja', 'JP', 'ja'), gk('gnt-kr', 'Güney Kore', 'ko', 'KR', 'ko'), gk('gnt-de', 'Almanya', 'de', 'DE', 'de'),
    gk('gnt-fr', 'Fransa', 'fr', 'FR', 'fr'), gk('gnt-es', 'İspanya', 'es', 'ES', 'es'), gk('gnt-mx', 'Latin Amerika', 'es', 'MX', 'es-MX'),
    gk('gnt-it', 'İtalya', 'it', 'IT', 'it'), gk('gnt-ru', 'Rusya', 'ru', 'RU', 'ru'), gk('gnt-br', 'Brezilya', 'pt', 'BR', 'pt-BR'),
    gk('gnt-in-hi', 'Hindistan (Hintçe)', 'hi', 'IN', 'hi'), gk('gnt-in', 'Hindistan', 'en', 'IN', 'en-IN'), gk('gnt-vn', 'Vietnam', 'vi', 'VN', 'vi'),
    gk('gnt-id', 'Endonezya', 'id', 'ID', 'id'), gk('gnt-pl', 'Polonya', 'pl', 'PL', 'pl'), gk('gnt-nl', 'Hollanda', 'nl', 'NL', 'nl'),
    gk('gnt-ar', 'Arap dünyası', 'ar', 'SA', 'ar'), gk('gnt-gb', 'Birleşik Krallık', 'en', 'GB', 'en-GB'), gk('gnt-tr', 'Türkiye', 'tr', 'TR', 'tr'),
    gk('gnt-ua', 'Ukrayna', 'uk', 'UA', 'uk'),
    # --- Çin anakarası
    u('cn-36kr', '36氪', 'zh', 'CN', 'https://36kr.com/feed'),
    u('cn-ifanr', '爱范儿 ifanr', 'zh', 'CN', 'https://www.ifanr.com/feed'),
    u('cn-sspai', '少数派 sspai', 'zh', 'CN', 'https://sspai.com/feed'),
    u('cn-huxiu', '虎嗅', 'zh', 'CN', 'https://www.huxiu.com/rss/0.xml'),
    u('cn-tmtpost', '钛媒体', 'zh', 'CN', 'https://www.tmtpost.com/rss.xml'),
    u('cn-geekpark', '极客公园', 'zh', 'CN', 'https://www.geekpark.net/rss'),
    u('cn-solidot', 'Solidot', 'zh', 'CN', 'https://www.solidot.org/index.rss'),
    u('cn-qbitai', '量子位', 'zh', 'CN', 'https://www.qbitai.com/feed'),
    u('cn-jiqizhixin', '机器之心', 'zh', 'CN', 'https://www.jiqizhixin.com/rss'),
    u('cn-leiphone', '雷峰网', 'zh', 'CN', 'https://www.leiphone.com/feed'),
    u('cn-pingwest', '品玩 PingWest', 'zh', 'CN', 'https://www.pingwest.com/feed'),
    u('cn-oschina', '开源中国', 'zh', 'CN', 'https://www.oschina.net/news/rss'),
    u('cn-infoq', 'InfoQ 中国', 'zh', 'CN', 'https://www.infoq.cn/feed'),
    u('cn-appinn', '小众软件', 'zh', 'CN', 'https://www.appinn.com/feed/'),
    u('cn-iplaysoft', '异次元软件世界', 'zh', 'CN', 'https://feed.iplaysoft.com/'),
    u('cn-dgtle', '数字尾巴', 'zh', 'CN', 'https://www.dgtle.com/rss/dgtle.xml'),
    u('cn-v2ex', 'V2EX', 'zh', 'CN', 'https://www.v2ex.com/index.xml', tip='topluluk/trend'),
    u('cn-sina-tech', '新浪科技', 'zh', 'CN', 'https://rss.sina.com.cn/tech/rollnews.xml'),
    u('cn-ithome-it', 'IT之家 IT资讯', 'zh', 'CN', 'https://www.ithome.com/rss/'),
    u('cn-gamersky', '游民星空', 'zh', 'CN', 'https://www.gamersky.com/rss/news.xml', cat='ent'),
    u('cn-chinaz', '站长之家 AI', 'zh', 'CN', 'https://www.chinaz.com/rss/news.xml'),
    u('cn-ruanyifeng', '阮一峰 科技爱好者周刊', 'zh', 'CN', 'https://www.ruanyifeng.com/blog/atom.xml', tip='uzman teknoloji'),
    ga('gn-cn-huawei', '华为 HarmonyOS', 'zh', 'CN', '华为 鸿蒙 OR HarmonyOS', 'zh-CN'),
    ga('gn-cn-xiaomi', '小米 澎湃OS', 'zh', 'CN', '小米 澎湃OS OR 小米手机', 'zh-CN'),
    ga('gn-cn-ai', '中国 AI 大模型', 'zh', 'CN', '大模型 DeepSeek OR 通义千问 OR 豆包 OR Kimi', 'zh-CN'),
    ga('gn-cn-iphone', 'iPhone (Çince)', 'zh', 'CN', 'iPhone iOS 更新', 'zh-CN', cat='ios'),
    # --- Tayvan / Hong Kong
    u('tw-ithome', 'iThome 台灣', 'zh', 'TW', 'https://www.ithome.com.tw/rss'),
    u('tw-techbang', 'T客邦', 'zh', 'TW', 'https://www.techbang.com/posts.rss'),
    u('tw-kocpc', '電腦王阿達', 'zh', 'TW', 'https://www.kocpc.com.tw/feed'),
    u('tw-inside', 'INSIDE 硬塞', 'zh', 'TW', 'https://www.inside.com.tw/feed/rss'),
    u('tw-technews', '科技新報 TechNews', 'zh', 'TW', 'https://technews.tw/feed/'),
    u('tw-cool3c', '癮科技 Cool3c', 'zh', 'TW', 'https://www.cool3c.com/rss'),
    u('tw-applealmond', '蘋果仁', 'zh', 'TW', 'https://applealmond.com/feed', cat='ios'),
    u('tw-sogi', 'SOGI 手機王', 'zh', 'TW', 'https://www.sogi.com.tw/rss/news_rss.xml'),
    u('tw-eprice', 'ePrice 比價王', 'zh', 'TW', 'https://www.eprice.com.tw/news/rss.xml'),
    u('hk-unwire', 'unwire.hk 流動日報', 'zh', 'HK', 'https://unwire.hk/feed/'),
    u('hk-unwirepro', 'Unwire.pro', 'zh', 'HK', 'https://unwire.pro/feed/'),
    u('hk-ezone', 'ezone.hk', 'zh', 'HK', 'https://ezone.hk/rss'),
    # --- Japonya
    u('jp-itmedia', 'ITmedia NEWS', 'ja', 'JP', 'https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml'),
    u('jp-itmedia-mobile', 'ITmedia Mobile', 'ja', 'JP', 'https://rss.itmedia.co.jp/rss/2.0/mobile.xml'),
    u('jp-gigazine', 'GIGAZINE', 'ja', 'JP', 'https://gigazine.net/news/rss_2.0/'),
    u('jp-impress-iw', 'INTERNET Watch', 'ja', 'JP', 'https://internet.watch.impress.co.jp/data/rss/1.0/iw/feed.rdf'),
    u('jp-impress-ktw', 'ケータイ Watch', 'ja', 'JP', 'https://k-tai.watch.impress.co.jp/data/rss/1.0/ktw/feed.rdf'),
    u('jp-impress-pcw', 'PC Watch', 'ja', 'JP', 'https://pc.watch.impress.co.jp/data/rss/1.0/pcw/feed.rdf'),
    u('jp-gizmodo', 'ギズモード・ジャパン', 'ja', 'JP', 'https://www.gizmodo.jp/index.xml'),
    u('jp-gori', 'gori.me', 'ja', 'JP', 'https://gori.me/feed', cat='ios'),
    u('jp-iphonemania', 'iPhone Mania', 'ja', 'JP', 'https://iphone-mania.jp/feed/', cat='ios'),
    u('jp-mynavi', 'マイナビ TECH+', 'ja', 'JP', 'https://news.mynavi.jp/techplus/rss/index'),
    u('jp-gadget-gate', 'Gadget Gate', 'ja', 'JP', 'https://gadget-gate.com/feed/'),
    u('jp-ascii', 'ASCII.jp', 'ja', 'JP', 'https://ascii.jp/rss.xml'),
    u('jp-publickey', 'Publickey', 'ja', 'JP', 'https://www.publickey1.jp/atom.xml'),
    u('jp-sumahoinfo', 'すまほん!!', 'ja', 'JP', 'https://smhn.info/feed'),
    # --- Güney Kore
    u('kr-zdnet', 'ZDNet Korea', 'ko', 'KR', 'https://feeds.feedburner.com/zdkorea'),
    u('kr-bloter', '블로터', 'ko', 'KR', 'https://www.bloter.net/rss/allArticle.xml'),
    u('kr-etnews', '전자신문', 'ko', 'KR', 'https://rss.etnews.com/Section901.xml'),
    u('kr-ddaily', '디지털데일리', 'ko', 'KR', 'https://www.ddaily.co.kr/rss/allArticle.xml'),
    u('kr-itworld', 'ITWorld Korea', 'ko', 'KR', 'https://www.itworld.co.kr/feed/'),
    u('kr-aitimes', 'AI타임스', 'ko', 'KR', 'https://www.aitimes.com/rss/allArticle.xml'),
    u('kr-byline', '바이라인네트워크', 'ko', 'KR', 'https://byline.network/feed/'),
    u('kr-theelec', '디일렉', 'ko', 'KR', 'https://www.thelec.kr/rss/allArticle.xml'),
    ga('gn-kr-galaxy', '갤럭시 One UI', 'ko', 'KR', '갤럭시 OR 원UI', 'ko', cat='samsung'),
    # --- Almanca
    u('de-heise', 'heise online', 'de', 'DE', 'https://www.heise.de/rss/heise-atom.xml'),
    u('de-golem', 'Golem.de', 'de', 'DE', 'https://rss.golem.de/rss.php?feed=RSS2.0'),
    u('de-computerbase', 'ComputerBase', 'de', 'DE', 'https://www.computerbase.de/rss/news.xml'),
    u('de-caschy', 'Caschys Blog', 'de', 'DE', 'https://stadt-bremerhaven.de/feed/'),
    u('de-winfuture', 'WinFuture', 'de', 'DE', 'https://static.winfuture.de/feeds/WinFuture-News-rss2.0.xml'),
    u('de-mobiflip', 'Mobiflip', 'de', 'DE', 'https://www.mobiflip.de/feed/'),
    u('de-iphoneticker', 'iphone-ticker.de', 'de', 'DE', 'https://www.iphone-ticker.de/feed/', cat='ios'),
    u('de-macerkopf', 'Macerkopf', 'de', 'DE', 'https://www.macerkopf.de/feed/', cat='ios'),
    u('de-allaboutsamsung', 'All About Samsung', 'de', 'DE', 'https://www.allaboutsamsung.de/feed/', cat='samsung'),
    u('de-t3n', 't3n', 'de', 'DE', 'https://t3n.de/rss.xml'),
    u('de-netzpolitik', 'netzpolitik.org', 'de', 'DE', 'https://netzpolitik.org/feed/'),
    # --- Fransızca
    u('fr-frandroid', 'Frandroid', 'fr', 'FR', 'https://www.frandroid.com/feed'),
    u('fr-numerama', 'Numerama', 'fr', 'FR', 'https://www.numerama.com/feed/'),
    u('fr-01net', '01net', 'fr', 'FR', 'https://www.01net.com/feed/'),
    u('fr-igen', 'iGeneration', 'fr', 'FR', 'https://www.igen.fr/rss', cat='ios'),
    u('fr-macg', 'MacGeneration', 'fr', 'FR', 'https://rss.macg.co', cat='mac'),
    u('fr-jdg', 'Journal du Geek', 'fr', 'FR', 'https://www.journaldugeek.com/feed/'),
    u('fr-clubic', 'Clubic', 'fr', 'FR', 'https://www.clubic.com/feed/news.rss'),
    u('fr-presse-citron', 'Presse-citron', 'fr', 'FR', 'https://www.presse-citron.net/feed/'),
    u('fr-phonandroid', 'Phonandroid', 'fr', 'FR', 'https://www.phonandroid.com/feed'),
    # --- İspanyolca
    u('es-xataka', 'Xataka', 'es', 'ES', 'https://feeds.weblogssl.com/xataka2'),
    u('es-xatakandroid', 'Xataka Android', 'es', 'ES', 'https://feeds.weblogssl.com/xatakandroid'),
    u('es-applesfera', 'Applesfera', 'es', 'ES', 'https://feeds.weblogssl.com/applesfera', cat='ios'),
    u('es-genbeta', 'Genbeta', 'es', 'ES', 'https://feeds.weblogssl.com/genbeta'),
    u('es-hipertextual', 'Hipertextual', 'es', 'ES', 'https://hipertextual.com/feed'),
    u('es-andro4all', 'Andro4all', 'es', 'ES', 'https://andro4all.com/feed'),
    u('es-xatakamx', 'Xataka México', 'es', 'MX', 'https://feeds.weblogssl.com/xatakamx'),
    # --- İtalyanca
    u('it-hdblog', 'HDblog', 'it', 'IT', 'https://www.hdblog.it/feed/'),
    u('it-hwupgrade', 'Hardware Upgrade', 'it', 'IT', 'https://www.hwupgrade.it/rss_hwup.xml'),
    u('it-macitynet', 'Macitynet', 'it', 'IT', 'https://www.macitynet.it/feed/', cat='ios'),
    u('it-ispazio', 'iSpazio', 'it', 'IT', 'https://www.ispazio.net/feed', cat='ios'),
    u('it-tuttoandroid', 'TuttoAndroid', 'it', 'IT', 'https://www.tuttoandroid.net/feed/'),
    # --- Rusça / Ukraynaca
    u('ru-habr', 'Хабр', 'ru', 'RU', 'https://habr.com/ru/rss/news/?fl=ru'),
    u('ru-ixbt', 'iXBT.com', 'ru', 'RU', 'https://www.ixbt.com/export/news.rss'),
    u('ru-3dnews', '3DNews', 'ru', 'RU', 'https://3dnews.ru/news/rss/'),
    u('ru-ferra', 'Ferra.ru', 'ru', 'RU', 'https://www.ferra.ru/exports/rss.xml'),
    u('ru-appleinsider', 'AppleInsider.ru', 'ru', 'RU', 'https://appleinsider.ru/feed', cat='ios'),
    u('ru-androidinsider', 'AndroidInsider.ru', 'ru', 'RU', 'https://androidinsider.ru/feed'),
    u('ua-itc', 'ITC.ua', 'uk', 'UA', 'https://itc.ua/feed/'),
    u('ua-dou', 'DOU', 'uk', 'UA', 'https://dou.ua/feed/'),
    # --- Portekizce (Brezilya)
    u('br-tecnoblog', 'Tecnoblog', 'pt', 'BR', 'https://tecnoblog.net/feed/'),
    u('br-tecmundo', 'TecMundo', 'pt', 'BR', 'https://rss.tecmundo.com.br/feed'),
    u('br-olhardigital', 'Olhar Digital', 'pt', 'BR', 'https://olhardigital.com.br/feed/'),
    u('br-macmagazine', 'MacMagazine', 'pt', 'BR', 'https://macmagazine.com.br/feed/', cat='ios'),
    u('br-canaltech', 'Canaltech', 'pt', 'BR', 'https://canaltech.com.br/rss/'),
    u('br-tudocelular', 'TudoCelular', 'pt', 'BR', 'https://www.tudocelular.com/feed/'),
    # --- Hindistan
    u('in-gadgets360', 'Gadgets 360', 'en', 'IN', 'https://feeds.feedburner.com/gadgets360-latest'),
    u('in-91mobiles', '91mobiles', 'en', 'IN', 'https://www.91mobiles.com/hub/feed/'),
    u('in-beebom', 'Beebom', 'en', 'IN', 'https://beebom.com/feed/'),
    u('in-gizbot', 'Gizbot', 'en', 'IN', 'https://www.gizbot.com/rss/gizbot-fb.xml'),
    u('in-digit', 'Digit', 'en', 'IN', 'https://www.digit.in/rss-feed/'),
    u('in-medianama', 'MediaNama', 'en', 'IN', 'https://www.medianama.com/feed/'),
    # --- Güneydoğu Asya / diğer
    u('vn-tinhte', 'Tinh tế', 'vi', 'VN', 'https://tinhte.vn/rss'),
    u('vn-genk', 'GenK', 'vi', 'VN', 'https://genk.vn/rss/home.rss'),
    u('id-detikinet', 'detikINET', 'id', 'ID', 'https://rss.detik.com/index.php/inet'),
    u('id-kompastekno', 'Kompas Tekno', 'id', 'ID', 'https://tekno.kompas.com/rss'),
    u('pl-antyweb', 'Antyweb', 'pl', 'PL', 'https://antyweb.pl/feed'),
    u('pl-spidersweb', "Spider's Web", 'pl', 'PL', 'https://spidersweb.pl/feed'),
    u('nl-tweakers', 'Tweakers', 'nl', 'NL', 'https://tweakers.net/feeds/mixed.xml'),
    u('nl-androidplanet', 'Android Planet', 'nl', 'NL', 'https://www.androidplanet.nl/feed/'),
    u('ar-aitnews', 'البوابة العربية للأخبار التقنية', 'ar', 'SA', 'https://aitnews.com/feed/'),
    u('ar-unlimit', 'عالم التقنية', 'ar', 'SA', 'https://www.tech-wd.com/wd/feed/'),
]
