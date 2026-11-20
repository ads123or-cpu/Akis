# -*- coding: utf-8 -*-
"""Savunma sanayi adayları (2026-11-19): resmi kurum/şirket duyuruları, Türkçe savunma yayınları, uluslararası savunma basını."""
G = 'https://news.google.com/rss/search?q=%s&hl=tr&gl=TR&ceid=TR:tr'
GE = 'https://news.google.com/rss/search?q=%s&hl=en-US&gl=US&ceid=US:en'
A = [
# resmi kurum / şirket (doğrudan)
('ssb', 'SSB', 'tr', 'TR', 'tr', 'savunma', 'resmi kurum', 'https://www.ssb.gov.tr/rss.aspx', ''),
('msb', 'MSB', 'tr', 'TR', 'tr', 'savunma', 'resmi kurum', 'https://www.msb.gov.tr/rss', ''),
('aselsan', 'ASELSAN', 'tr', 'TR', 'tech', 'savunma', 'sirket duyurusu', 'https://www.aselsan.com/tr/rss', 'sirket-haberi'),
('roketsan', 'ROKETSAN', 'tr', 'TR', 'tech', 'savunma', 'sirket duyurusu', 'https://www.roketsan.com.tr/tr/rss', 'sirket-haberi'),
('tusas', 'TUSAŞ', 'tr', 'TR', 'tech', 'savunma', 'sirket duyurusu', 'https://www.tusas.com/rss', 'sirket-haberi'),
('baykar', 'Baykar', 'tr', 'TR', 'tech', 'savunma', 'sirket duyurusu', 'https://baykartech.com/tr/rss/', 'sirket-haberi'),
('baykar2', 'Baykar (feed)', 'tr', 'TR', 'tech', 'savunma', 'sirket duyurusu', 'https://baykartech.com/tr/feed/', 'sirket-haberi'),
('havelsan', 'HAVELSAN', 'tr', 'TR', 'tech', 'savunma', 'sirket duyurusu', 'https://www.havelsan.com/rss', 'sirket-haberi'),
# resmi kurum / şirket (Google Haberler site: yedeği)
('gn-site-ssb', 'SSB (Google Haberler)', 'tr', 'TR', 'tr', 'savunma', 'toplayici', G % 'site:ssb.gov.tr', 'toplayici'),
('gn-site-msb', 'MSB (Google Haberler)', 'tr', 'TR', 'tr', 'savunma', 'toplayici', G % 'site:msb.gov.tr', 'toplayici'),
('gn-site-aselsan', 'ASELSAN (Google Haberler)', 'tr', 'TR', 'tech', 'savunma', 'toplayici', G % 'site:aselsan.com', 'toplayici'),
('gn-site-roketsan', 'ROKETSAN (Google Haberler)', 'tr', 'TR', 'tech', 'savunma', 'toplayici', G % 'site:roketsan.com.tr', 'toplayici'),
('gn-site-tusas', 'TUSAŞ (Google Haberler)', 'tr', 'TR', 'tech', 'savunma', 'toplayici', G % 'site:tusas.com', 'toplayici'),
('gn-site-baykar', 'Baykar (Google Haberler)', 'tr', 'TR', 'tech', 'savunma', 'toplayici', G % 'site:baykartech.com', 'toplayici'),
# şirket adıyla haber araması
('gnq-aselsan', 'ASELSAN haberleri (GN)', 'tr', 'TR', 'tech', 'savunma', 'toplayici', G % 'ASELSAN%20when%3A2d', 'toplayici'),
('gnq-baykar', 'Baykar haberleri (GN)', 'tr', 'TR', 'tech', 'savunma', 'toplayici', G % 'Baykar%20OR%20Bayraktar%20OR%20K%C4%B1z%C4%B1lelma%20when%3A2d', 'toplayici'),
('gnq-tusas', 'TUSAŞ / KAAN haberleri (GN)', 'tr', 'TR', 'tech', 'savunma', 'toplayici', G % 'TUSA%C5%9E%20OR%20%22KAAN%22%20OR%20H%C3%BCrjet%20when%3A2d', 'toplayici'),
('gnq-roketsan', 'ROKETSAN haberleri (GN)', 'tr', 'TR', 'tech', 'savunma', 'toplayici', G % 'ROKETSAN%20OR%20%22%C3%87elik%20Kubbe%22%20when%3A2d', 'toplayici'),
('gnq-ssb', 'SSB / MSB haberleri (GN)', 'tr', 'TR', 'tr', 'savunma', 'toplayici', G % '%22Savunma%20Sanayii%20Ba%C5%9Fkanl%C4%B1%C4%9F%C4%B1%22%20OR%20%22Mill%C3%AE%20Savunma%20Bakanl%C4%B1%C4%9F%C4%B1%22%20when%3A2d', 'toplayici'),
# Türkçe savunma yayınları
('savunmatr', 'SavunmaTR', 'tr', 'TR', 'tech', 'savunma', 'uzman teknoloji', 'https://www.savunmatr.com/feed/', ''),
('defensehere-tr', 'DefenseHere', 'tr', 'TR', 'tech', 'savunma', 'uzman teknoloji', 'https://www.defensehere.com/tr/rss', ''),
('turdef-tr', 'TurDef (TR)', 'tr', 'TR', 'tech', 'savunma', 'uzman teknoloji', 'https://www.turdef.com/tr/rss', ''),
('turdef', 'TurDef', 'en', 'TR', 'tech', 'savunma', 'uzman teknoloji', 'https://turdef.com/rss', ''),
('siyahgribeyaz', 'SavunmaHaber', 'tr', 'TR', 'tech', 'savunma', 'uzman teknoloji', 'https://www.savunmahaber.com/feed/', ''),
('c4defence', 'C4Defence', 'tr', 'TR', 'tech', 'savunma', 'uzman teknoloji', 'https://www.c4defence.com/feed/', ''),
('msi-dergi', 'MSI Dergisi', 'tr', 'TR', 'tech', 'savunma', 'uzman teknoloji', 'https://www.savunmahaber.com/rss', ''),
('defenceturkey', 'Defence Turkey', 'en', 'TR', 'tech', 'savunma', 'uzman teknoloji', 'https://www.defenceturkey.com/rss', ''),
('aa-savunma', 'AA Savunma (GN)', 'tr', 'TR', 'tr', 'savunma', 'toplayici', G % 'site:aa.com.tr%20savunma%20sanayii', 'toplayici'),
('turkiyetoday-def', 'Türkiye Today Defense (GN)', 'en', 'TR', 'world', 'savunma', 'toplayici', GE % 'Turkish%20defense%20industry%20when%3A3d', 'toplayici'),
# uluslararası
('defensenews', 'Defense News', 'en', 'US', 'world', 'savunma', 'uzman teknoloji', 'https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml', ''),
('defenseone', 'Defense One', 'en', 'US', 'world', 'savunma', 'uzman teknoloji', 'https://www.defenseone.com/rss/all/', ''),
('navalnews', 'Naval News', 'en', 'FR', 'world', 'savunma', 'uzman teknoloji', 'https://www.navalnews.com/feed/', ''),
('armyrecognition', 'Army Recognition', 'en', 'BE', 'world', 'savunma', 'uzman teknoloji', 'https://www.armyrecognition.com/news?format=feed&type=rss', ''),
('armyrecognition2', 'Army Recognition (feed)', 'en', 'BE', 'world', 'savunma', 'uzman teknoloji', 'https://armyrecognition.com/feed', ''),
('janes', 'Janes', 'en', 'GB', 'world', 'savunma', 'uzman teknoloji', 'https://www.janes.com/osint-insights/defence-news/rss', ''),
('ukdj', 'UK Defence Journal', 'en', 'GB', 'world', 'savunma', 'uzman teknoloji', 'https://ukdefencejournal.org.uk/feed/', ''),
('defence-blog', 'Defence Blog', 'en', 'US', 'world', 'savunma', 'uzman teknoloji', 'https://defence-blog.com/feed/', ''),
('thedefensepost', 'The Defense Post', 'en', 'US', 'world', 'savunma', 'uzman teknoloji', 'https://thedefensepost.com/feed/', ''),
('aviationist', 'The Aviationist', 'en', 'IT', 'world', 'savunma', 'uzman teknoloji', 'https://theaviationist.com/feed/', ''),
('airforcetimes', 'Air & Space Forces Magazine', 'en', 'US', 'world', 'savunma', 'uzman teknoloji', 'https://www.airandspaceforces.com/feed/', ''),
('warontherocks', 'War on the Rocks', 'en', 'US', 'world', 'savunma', 'uzman teknoloji', 'https://warontherocks.com/feed/', ''),
('eda-news', 'Avrupa Savunma Ajansı', 'en', 'EU', 'world', 'savunma', 'uluslararasi kurum', 'https://eda.europa.eu/rss', ''),
('nato-news', 'NATO', 'en', 'INT', 'world', 'savunma', 'uluslararasi kurum', 'https://www.nato.int/cps/rss/en/natohq/rssFeed.xsl/rssFeed.xml', ''),
('militarytimes', 'Military Times', 'en', 'US', 'world', 'savunma', 'uzman teknoloji', 'https://www.militarytimes.com/arc/outboundfeeds/rss/?outputType=xml', ''),
('c4isrnet', 'C4ISRNET', 'en', 'US', 'world', 'savunma', 'uzman teknoloji', 'https://www.c4isrnet.com/arc/outboundfeeds/rss/?outputType=xml', ''),
('opex360', 'Zone Militaire', 'fr', 'FR', 'world', 'savunma', 'uzman teknoloji', 'https://www.opex360.com/feed/', ''),
('esut', 'ESUT', 'de', 'DE', 'world', 'savunma', 'uzman teknoloji', 'https://esut.de/feed/', ''),
('gn-en-turkdef', 'Bayraktar/KAAN (Google News EN)', 'en', 'US', 'world', 'savunma', 'toplayici', GE % 'Bayraktar%20OR%20Baykar%20OR%20%22KAAN%20fighter%22%20OR%20Aselsan%20when%3A3d', 'toplayici'),
]
