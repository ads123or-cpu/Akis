# -*- coding: utf-8 -*-
"""Akış 5 kaynak adayları (2026-11-18): yapay zekâ, oyun, siber, ekonomi, spor, erişim engelli Türkçe kaynakların Google Haberler yedekleri,
tek kaynaklı diller (ro/hi/id). Geliştirici/kod odaklı kaynak bilerek yok (kullanıcı isteği)."""
G = 'https://news.google.com/rss/search?q=%s&hl=tr&gl=TR&ceid=TR:tr'
A = [
# yapay zekâ
('venturebeat-ai', 'VentureBeat AI', 'en', 'US', 'tech', 'yz', 'uzman teknoloji', 'https://venturebeat.com/category/ai/feed/', ''),
('mittr-ai', 'MIT Technology Review AI', 'en', 'US', 'tech', 'yz', 'uzman teknoloji', 'https://www.technologyreview.com/topic/artificial-intelligence/feed', ''),
('wired-ai', 'Wired AI', 'en', 'US', 'tech', 'yz', 'uzman teknoloji', 'https://www.wired.com/feed/tag/ai/latest/rss', ''),
('guardian-ai', 'Guardian AI', 'en', 'GB', 'tech', 'yz', 'ana akim', 'https://www.theguardian.com/technology/artificialintelligenceai/rss', ''),
('gn-tr-yz', 'Yapay zekâ (Google Haberler, TR)', 'tr', 'TR', 'tech', 'yz', 'toplayici', G % 'yapay%20zeka', 'toplayici'),
# oyun
('rps', 'Rock Paper Shotgun', 'en', 'GB', 'tech', 'oyun', 'uzman teknoloji', 'https://www.rockpapershotgun.com/feed', ''),
('pushsquare', 'Push Square', 'en', 'GB', 'tech', 'oyun', 'uzman teknoloji', 'https://www.pushsquare.com/feeds/latest', ''),
('nintendolife', 'Nintendo Life', 'en', 'GB', 'tech', 'oyun', 'uzman teknoloji', 'https://www.nintendolife.com/feeds/latest', ''),
('gamerant', 'Game Rant', 'en', 'US', 'tech', 'oyun', 'uzman teknoloji', 'https://gamerant.com/feed/', ''),
('bolumsonu', 'Bölüm Sonu Canavarı', 'tr', 'TR', 'tech', 'oyun', 'uzman teknoloji', 'https://www.bolumsonucanavari.com/rss', ''),
('gn-tr-oyun', 'Oyun dünyası (Google Haberler, TR)', 'tr', 'TR', 'tech', 'oyun', 'toplayici', G % '%22oyun%22%20(PlayStation%20OR%20Xbox%20OR%20Steam%20OR%20Nintendo)', 'toplayici'),
# siber
('therecord', 'The Record', 'en', 'US', 'tech', 'siber', 'uzman teknoloji', 'https://therecord.media/feed', ''),
('helpnetsec', 'Help Net Security', 'en', 'HR', 'tech', 'siber', 'uzman teknoloji', 'https://www.helpnetsecurity.com/feed/', ''),
('gn-tr-siber', 'Siber güvenlik (Google Haberler, TR)', 'tr', 'TR', 'tech', 'siber', 'toplayici', G % '%22siber%20sald%C4%B1r%C4%B1%22%20OR%20%22veri%20s%C4%B1z%C4%B1nt%C4%B1s%C4%B1%22%20OR%20doland%C4%B1r%C4%B1c%C4%B1l%C4%B1k', 'toplayici'),
# ekonomi
('paraanaliz', 'Paraanaliz', 'tr', 'TR', 'eco', 'ekonomi', 'ana akim', 'https://www.paraanaliz.com/feed/', ''),
('marketwatch', 'MarketWatch', 'en', 'US', 'eco', 'ekonomi', 'ana akim', 'https://feeds.marketwatch.com/marketwatch/topstories/', ''),
('yahoo-fin', 'Yahoo Finance', 'en', 'US', 'eco', 'ekonomi', 'ana akim', 'https://finance.yahoo.com/news/rssindex', ''),
# spor
('ajansspor', 'Ajansspor', 'tr', 'TR', 'sport', 'spor', 'spor', 'https://ajansspor.com/rss', ''),
('trtspor', 'TRT Spor', 'tr', 'TR', 'sport', 'spor', 'spor', 'https://www.trtspor.com.tr/rss/anasayfa.rss', 'kamu-yayincisi'),
('fanatik', 'Fanatik', 'tr', 'TR', 'sport', 'spor', 'spor', 'https://www.fanatik.com.tr/rss/anasayfa', ''),
# erişim engelli (403) Türkçe kaynakların toplayıcı yedekleri
('gn-site-halktv', 'Halk TV (Google Haberler)', 'tr', 'TR', 'tr', 'gundem', 'toplayici', G % 'site:halktv.com.tr', 'toplayici'),
('gn-site-t24', 'T24 (Google Haberler)', 'tr', 'TR', 'tr', 'gundem', 'toplayici', G % 'site:t24.com.tr', 'toplayici'),
('gn-site-duvar', 'Gazete Duvar (Google Haberler)', 'tr', 'TR', 'tr', 'gundem', 'toplayici', G % 'site:gazeteduvar.com.tr', 'toplayici'),
('gn-site-technopat', 'Technopat (Google Haberler)', 'tr', 'TR', 'tech', 'tekno', 'toplayici', G % 'site:technopat.net', 'toplayici'),
# tek kaynaklı diller
('ro-digi24', 'Digi24', 'ro', 'RO', 'world', 'gundem', 'ana akim', 'https://www.digi24.ro/rss', ''),
('ro-hotnews', 'HotNews', 'ro', 'RO', 'world', 'gundem', 'ana akim', 'https://www.hotnews.ro/rss', ''),
('hi-bbc', 'BBC Hindi', 'hi', 'IN', 'world', 'gundem', 'ana akim', 'https://feeds.bbci.co.uk/hindi/rss.xml', 'kamu-yayincisi'),
('id-bbc', 'BBC Indonesia', 'id', 'ID', 'world', 'gundem', 'ana akim', 'https://feeds.bbci.co.uk/indonesia/rss.xml', 'kamu-yayincisi'),
('id-detik', 'Detik', 'id', 'ID', 'world', 'gundem', 'ana akim', 'https://rss.detik.com/index.php/detikcom', ''),
]
