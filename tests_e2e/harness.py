"""Shared E2E test harness: local HTTP server, headless Chrome CDP bridge, repo/data helpers."""
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E2E_DIR = os.path.dirname(os.path.abspath(__file__))
CDP_DRIVER = os.path.join(E2E_DIR, 'cdp_driver.mjs')
SITE_DIR = os.path.join(KOK, 'site')
DATA_DIR = os.path.join(SITE_DIR, 'data')

TESTS = []


class HarnessError(RuntimeError):
    """Infrastructure / environment error (exit code 2)."""


def e2e_test(test_id, tier, feature, desc, gate='invariant'):
    def deco(fn):
        fn._e2e = {
            'id': test_id,
            'tier': int(tier),
            'feature': feature,
            'desc': desc,
            'gate': gate,
        }
        TESTS.append(fn)
        return fn
    return deco


def pick_free_port(preferred=8775):
    if preferred and int(preferred) > 0:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', int(preferred)))
            return int(preferred)
        except OSError as exc:
            raise HarnessError(f'Port {preferred} is unavailable: {exc}')
        finally:
            s.close()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]
    finally:
        s.close()


def check_node_version(min_major=22):
    try:
        out = subprocess.check_output(['node', '--version'], text=True, timeout=5).strip()
    except FileNotFoundError:
        raise HarnessError('node binary not found in PATH')
    except Exception as exc:
        raise HarnessError(f'Failed to run node --version: {exc}')
    m = re.match(r'^v?(\d+)\.', out)
    if not m or int(m.group(1)) < min_major:
        raise HarnessError(f'Node >= {min_major} required for built-in WebSocket; got {out}')
    return out


class LocalServer:
    """Starts tools/yerel_sunucu.py <port> <site_dir> and shuts it down cleanly."""

    def __init__(self, port=8775, site_dir=SITE_DIR):
        self.requested_port = int(port)
        self.site_dir = site_dir
        self.port = None
        self.base_url = None
        self.proc = None

    def __enter__(self):
        if not os.path.isfile(os.path.join(self.site_dir, 'index.html')):
            raise HarnessError(f'Missing {os.path.join(self.site_dir, "index.html")}')
        self.port = pick_free_port(self.requested_port)
        self.base_url = f'http://127.0.0.1:{self.port}'
        cmd = [
            sys.executable,
            os.path.join(KOK, 'tools', 'yerel_sunucu.py'),
            str(self.port),
            self.site_dir,
        ]
        self.proc = subprocess.Popen(
            cmd,
            cwd=KOK,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.time() + 6.0
        last_err = None
        while time.time() < deadline:
            if self.proc.poll() is not None:
                err = self.proc.stderr.read() if self.proc.stderr else ''
                raise HarnessError(f'yerel_sunucu.py exited early ({self.proc.returncode}): {err.strip()}')
            for path in ('/data/surum.json', '/'):
                try:
                    req = urllib.request.Request(self.base_url + path, method='GET')
                    with urllib.request.urlopen(req, timeout=1.0) as resp:
                        if resp.status == 200:
                            return self
                except Exception as exc:
                    last_err = exc
            time.sleep(0.1)
        self.__exit__(None, None, None)
        raise HarnessError(f'Local server failed to respond on {self.base_url}: {last_err}')

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.proc is not None:
            if self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait(timeout=2)
            if self.proc.stderr:
                try:
                    self.proc.stderr.close()
                except Exception:
                    pass
            self.proc = None


class BrowserClient:
    """Persistent headless Chrome CDP session over tests_e2e/cdp_driver.mjs."""

    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self._tmp = None
        self.proc = None
        self.chrome_path = None
        self.node_version = None

    def __enter__(self):
        self.node_version = check_node_version(22)
        if not os.path.isfile(CDP_DRIVER):
            raise HarnessError(f'Missing CDP driver: {CDP_DRIVER}')
        self._tmp = tempfile.TemporaryDirectory(prefix='akis_e2e_')
        self.proc = subprocess.Popen(
            ['node', CDP_DRIVER, '--user-data-dir', self._tmp.name, '--base-url', self.base_url],
            cwd=KOK,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        line = self.proc.stdout.readline()
        if not line:
            err = self.proc.stderr.read() if self.proc.stderr else ''
            raise HarnessError(f'cdp_driver.mjs failed to start: {err.strip()}')
        try:
            init = json.loads(line)
        except json.JSONDecodeError as exc:
            raise HarnessError(f'Invalid startup JSON from cdp_driver.mjs: {line!r} ({exc})')
        if not init.get('ok'):
            raise HarnessError(init.get('error', 'cdp_driver.mjs startup failed'))
        self.chrome_path = init.get('chromePath')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.proc is not None:
            try:
                if self.proc.poll() is None and self.proc.stdin:
                    self.proc.stdin.write(json.dumps({'cmd': 'shutdown'}) + '\n')
                    self.proc.stdin.flush()
                    self.proc.wait(timeout=4)
            except Exception:
                try:
                    self.proc.terminate()
                    self.proc.wait(timeout=2)
                except Exception:
                    try:
                        self.proc.kill()
                    except Exception:
                        pass
            for s in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
                if s:
                    try:
                        s.close()
                    except Exception:
                        pass
            self.proc = None
        if self._tmp is not None:
            try:
                self._tmp.cleanup()
            except Exception:
                pass
            self._tmp = None

    def call(self, cmd, **kwargs):
        if not self.proc or self.proc.poll() is not None:
            raise HarnessError('CDP driver process is not running')
        payload = {'cmd': cmd, **kwargs}
        try:
            self.proc.stdin.write(json.dumps(payload) + '\n')
            self.proc.stdin.flush()
        except Exception as exc:
            raise HarnessError(f'Failed writing command {cmd} to cdp_driver: {exc}')
        line = self.proc.stdout.readline()
        if not line:
            err = self.proc.stderr.read() if self.proc.stderr else ''
            raise HarnessError(f'cdp_driver closed unexpectedly on {cmd}: {err.strip()}')
        resp = json.loads(line)
        if not resp.get('ok'):
            msg = resp.get('error', f'{cmd} failed')
            if resp.get('harnessError'):
                raise HarnessError(msg)
            raise RuntimeError(msg)
        return resp.get('result')

    def set_mobile(self):
        return self.call('setMobile')

    def set_desktop(self):
        return self.call('setDesktop')

    def set_viewport(self, width, height, mobile=False, dpr=None):
        return self.call('setViewport', width=width, height=height, mobile=mobile, dpr=dpr)

    def navigate(self, target='#/bugun', reset_storage=True, pre_storage=None,
                 color_scheme='', reduced_motion=False, intercept_window_open=False, wait_ready=True):
        return self.call(
            'navigate',
            target=target,
            options={
                'resetStorage': reset_storage,
                'preStorage': pre_storage or {},
                'colorScheme': color_scheme,
                'reducedMotion': reduced_motion,
                'interceptWindowOpen': intercept_window_open,
                'waitReady': wait_ready,
            },
        )

    def reload(self, wait_ready=True, intercept_window_open=False):
        return self.call('reload', options={
            'waitReady': wait_ready,
            'interceptWindowOpen': intercept_window_open,
        })

    def set_hash(self, hash_str, wait_ready=True):
        return self.call('setHash', hash=hash_str, options={'waitReady': wait_ready})

    def eval(self, expression, await_promise=True):
        res = self.call('eval', expression=expression, awaitPromise=await_promise)
        return res.get('value')

    def click(self, selector, index=0):
        return self.call('click', selector=selector, options={'index': index})

    def press_key(self, key):
        return self.call('pressKey', key=key)

    def wait_for(self, expression, timeout_ms=6000):
        return self.call('waitFor', expression=expression, timeoutMs=timeout_ms)

    def wait_ready(self, timeout_ms=10000):
        return self.call('waitForReady', timeoutMs=timeout_ms)

    def clear_diagnostics(self):
        return self.call('clearDiagnostics')

    def diagnostics(self):
        return self.call('getDiagnostics')

    def inspect_layout(self):
        return self.call('inspectLayout')

    def inspect_touch_targets(self, min_px=44):
        return self.call('inspectTouchTargets', minPx=min_px)

    def inspect_theme(self):
        return self.call('inspectTheme')

    def inspect_rtl(self):
        return self.call('inspectRtl')


def assert_clean_nav(nav_result, allowed_http_404_suffixes=()):
    ex = nav_result.get('exceptions') or []
    assert not ex, f'Uncaught JS exceptions: {ex}'
    errs = []
    for e in nav_result.get('httpErrors') or []:
        url = e.get('url', '')
        status = e.get('status')
        if status == 404 and any(url.split('?')[0].endswith(s) for s in allowed_http_404_suffixes):
            continue
        errs.append(e)
    assert not errs, f'Unexpected local HTTP errors: {errs}'


def assert_clean_diag(browser, allowed_http_404_suffixes=()):
    d = browser.diagnostics()
    assert_clean_nav(d, allowed_http_404_suffixes=allowed_http_404_suffixes)


def ensure_akis_rows(browser):
    """If default 24h window has 0 rows (e.g. stale local data), switch to Tüm zamanlar (0)."""
    cnt = browser.eval("document.querySelectorAll('#ana [data-id]').length")
    if cnt and cnt > 0:
        return cnt
    browser.eval("""(() => {
      const suz = document.querySelector('[data-act="suzAc"][aria-expanded="false"]');
      if (suz) suz.click();
      const z0 = document.querySelector('[data-act="zaman"][data-v="0"]');
      if (z0) z0.click();
    })()""")
    browser.wait_for("document.querySelectorAll('#ana [data-id]').length > 0", timeout_ms=4000)
    return browser.eval("document.querySelectorAll('#ana [data-id]').length")


def visible_okx_count(browser):
    """Count Okan-only controls currently visible (excluding closed dialogs/popovers)."""
    return browser.eval("""(() => {
      const els = document.querySelectorAll(
        '[data-act="okxOto"], [data-act="okxAc"], [data-act="mOkx"], a[href*="reels-sablonu"]'
      );
      return Array.from(els).filter(el => {
        if (el.closest('[hidden]')) return false;
        const d = el.closest('dialog');
        if (d && !d.open) return false;
        const p = el.closest('[popover]');
        if (p && !p.matches(':popover-open')) return false;
        return true;
      }).length;
    })()""")


def load_json(rel_path):
    p = os.path.join(KOK, rel_path)
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def file_size(rel_path):
    return os.path.getsize(os.path.join(KOK, rel_path))


def parse_snap(html):
    idx = html.find('id="snap"')
    assert idx >= 0, 'id="snap" missing'
    bas = html.find('>', idx)
    son = html.find('</script>', bas)
    assert bas >= 0 and son >= 0, 'id="snap" script closing tag missing'
    return json.loads(html[bas + 1:son])


def git_cmd(*args):
    res = subprocess.run(
        ['git', '-C', KOK, *args],
        capture_output=True,
        text=True,
        timeout=15,
    )
    return res.returncode, res.stdout, res.stderr
