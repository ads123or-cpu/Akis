"""GitHub Actions iş akışı: zincir kopmasın, test ve doğrulama sırası doğru olsun, geliştirme dalı yayın başlatmasın."""
import os, re, unittest
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Y = open(os.path.join(KOK, '.github', 'workflows', 'refresh.yml'), encoding='utf-8').read()
class IsAkisi(unittest.TestCase):
    def test_sira(self):
        sira = ['run: python -m unittest discover', 'run: python fetch_feeds.py', 'run: python masa.py', 'run: python akis2.py', 'run: python build.py', 'tests.test_sozlesme', 'git commit']
        konum = [Y.index(x) for x in sira]; self.assertEqual(konum, sorted(konum))
    def test_dogrulama_committen_once(self): self.assertLess(Y.index('tests.test_cikti'), Y.index('git commit'))
    def test_push_yalniz_main(self): self.assertRegex(Y, r'push:\s*\n\s*branches: \[main\]')
    def test_tetikleyen_dosyalar(self):
        for f in ('sources.json', 'fetch_feeds.py', 'masa.py', 'akis2.py', 'index.tpl.html', 'build.py'): self.assertIn(f, Y)
    def test_zincir_kopmaz(self):
        self.assertIn('if: ${{ !cancelled() }}', Y); self.assertIn('gh workflow run refresh.yml', Y); self.assertIn('cron: "*/30 * * * *"', Y)
    def test_es_zamanli_calisma_yok(self): self.assertIn('concurrency: refresh', Y)
    def test_pages_yalniz_site(self): self.assertIn('path: site', Y)
    def test_gizli_bilgi_yok(self):
        for dosya in ('index.tpl.html', 'fetch_feeds.py', 'akis2.py'):
            t = open(os.path.join(KOK, dosya), encoding='utf-8').read()
            self.assertNotRegex(t, r'(api[_-]?key|secret|token)\s*[:=]\s*["\'][A-Za-z0-9_\-]{16,}', dosya)
if __name__ == '__main__': unittest.main()
