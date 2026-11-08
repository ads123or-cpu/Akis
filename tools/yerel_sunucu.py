#!/usr/bin/env python3
"""Yerel önizleme sunucusu: GitHub Pages gibi gzip sıkıştırır ve önbellek başlığı (max-age=600) verir.
Kullanım: python3 tools/yerel_sunucu.py [port] [klasör]"""
import gzip, http.server, os, sys, functools
SIK = ('.html', '.json', '.js', '.css', '.svg', '.txt')
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def send_head(self):
        yol = self.translate_path(self.path.split('?')[0])
        if os.path.isdir(yol): yol = os.path.join(yol, 'index.html')
        if not os.path.isfile(yol): return super().send_head()
        veri = open(yol, 'rb').read()
        tur = self.guess_type(yol)
        self.send_response(200); self.send_header('Content-Type', tur + ('; charset=utf-8' if tur.startswith(('text/', 'application/json')) else ''))
        if yol.endswith(SIK) and 'gzip' in (self.headers.get('Accept-Encoding') or ''):
            veri = gzip.compress(veri, 6); self.send_header('Content-Encoding', 'gzip')
        self.send_header('Content-Length', str(len(veri))); self.send_header('Cache-Control', 'max-age=600'); self.end_headers()
        import io; return io.BytesIO(veri)
if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    kok = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else 'site')
    http.server.ThreadingHTTPServer(('127.0.0.1', port), functools.partial(H, directory=kok)).serve_forever()
