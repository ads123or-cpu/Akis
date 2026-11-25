#!/usr/bin/env node
/**
 * Opaque-box headless Chrome CDP driver for Akis E2E suite.
 * Zero external npm dependencies (requires Node >= 22 for native WebSocket & fetch).
 * Reads newline-delimited JSON commands on stdin; writes newline-delimited JSON results on stdout.
 */
import { spawn } from 'node:child_process';
import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import { createServer } from 'node:net';
import os from 'node:os';
import path from 'node:path';
import readline from 'node:readline';

const sleep = ms => new Promise(r => setTimeout(r, ms));

function resolveChrome() {
  const envChrome = (process.env.CHROME || '').trim();
  if (envChrome) {
    if (!existsSync(envChrome)) {
      throw new Error(`CHROME_NOT_FOUND: Explicit CHROME path not found: ${envChrome}`);
    }
    return envChrome;
  }
  const candidates = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta',
    '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
  ];
  const pathDirs = (process.env.PATH || '').split(path.delimiter).filter(Boolean);
  for (const bin of ['google-chrome', 'chromium', 'chromium-browser', 'chrome']) {
    for (const dir of pathDirs) {
      candidates.push(path.join(dir, bin));
    }
  }
  for (const p of candidates) {
    if (p && existsSync(p)) return p;
  }
  throw new Error(
    'CHROME_NOT_FOUND: No Chrome/Chromium binary found. Checked /Applications/*.app and PATH.'
  );
}

function getFreePort() {
  return new Promise((resolve, reject) => {
    const srv = createServer();
    srv.unref();
    srv.on('error', reject);
    srv.listen(0, '127.0.0.1', () => {
      const addr = srv.address();
      const port = typeof addr === 'object' && addr ? addr.port : 0;
      srv.close(() => resolve(port));
    });
  });
}

function parseArgs(argv) {
  const out = { userDataDir: '', baseUrl: '' };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--user-data-dir' && argv[i + 1]) out.userDataDir = argv[++i];
    else if (a === '--base-url' && argv[i + 1]) out.baseUrl = argv[++i];
    else if (a === '--check-chrome') out.checkChrome = true;
  }
  return out;
}

class CdpSession {
  constructor({ userDataDir, baseUrl }) {
    this.baseUrl = (baseUrl || '').replace(/\/+$/, '');
    this.ownUserDataDir = !userDataDir;
    this.userDataDir = userDataDir || mkdtempSync(path.join(os.tmpdir(), 'akis-cdp-'));
    this.proc = null;
    this.ws = null;
    this.nextId = 0;
    this.pending = new Map();
    this.exceptions = [];
    this.httpErrors = [];
    this.requests = new Map();
    this.viewportWidth = 1440;
    this.viewportHeight = 1000;
    this.closed = false;
  }

  async start() {
    const chrome = resolveChrome();
    this.chromePath = chrome;
    const cdpPort = await getFreePort();
    const args = [
      '--headless=new',
      '--disable-gpu',
      '--no-sandbox',
      '--hide-scrollbars',
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-background-networking',
      '--disable-extensions',
      `--remote-debugging-port=${cdpPort}`,
      `--user-data-dir=${this.userDataDir}`,
      'about:blank',
    ];
    this.proc = spawn(chrome, args, { stdio: ['ignore', 'ignore', 'pipe'] });
    let stderrBuf = '';
    this.proc.stderr.on('data', d => {
      if (stderrBuf.length < 4096) stderrBuf += d.toString();
    });

    let target = null;
    for (let i = 0; i < 60; i++) {
      if (this.proc.exitCode !== null) {
        throw new Error(`CHROME_EXIT: Chrome exited early (${this.proc.exitCode}): ${stderrBuf.trim()}`);
      }
      try {
        const res = await fetch(`http://127.0.0.1:${cdpPort}/json`);
        if (res.ok) {
          const list = await res.json();
          target = list.find(x => x.type === 'page' && x.webSocketDebuggerUrl);
          if (target) break;
        }
      } catch {
        // retry
      }
      await sleep(150);
    }
    if (!target) {
      await this.close();
      throw new Error(`CDP_TIMEOUT: Timed out waiting for Chrome DevTools target on port ${cdpPort}`);
    }

    this.ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('WS_TIMEOUT: CDP WebSocket connect timeout')), 10000);
      this.ws.onopen = () => {
        clearTimeout(timer);
        resolve();
      };
      this.ws.onerror = err => {
        clearTimeout(timer);
        reject(new Error(`WS_ERROR: ${err?.message || 'WebSocket connection failed'}`));
      };
    });

    this.ws.onmessage = evt => {
      let msg;
      try {
        msg = JSON.parse(evt.data);
      } catch {
        return;
      }
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject, timer } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        clearTimeout(timer);
        if (msg.error) {
          reject(new Error(`CDP_${msg.error.code || 'ERR'}: ${msg.error.message}`));
        } else {
          resolve(msg.result || {});
        }
      } else if (msg.method) {
        this.handleEvent(msg.method, msg.params || {});
      }
    };

    this.ws.onclose = () => {
      for (const [, p] of this.pending) {
        clearTimeout(p.timer);
        p.reject(new Error('WS_CLOSED'));
      }
      this.pending.clear();
    };

    await this.cmd('Page.enable');
    await this.cmd('Runtime.enable');
    await this.cmd('Network.enable');
    await this.cmd('Network.setCacheDisabled', { cacheDisabled: true });
    await this.setDesktop();
    return { chromePath: this.chromePath, cdpPort };
  }

  handleEvent(method, params) {
    if (method === 'Runtime.exceptionThrown') {
      const d = params.exceptionDetails || {};
      const desc = d.exception?.description || d.text || 'Uncaught JS exception';
      this.exceptions.push({
        text: desc,
        url: d.url || '',
        line: d.lineNumber ?? null,
      });
    } else if (method === 'Network.requestWillBeSent') {
      this.requests.set(params.requestId, {
        url: params.request?.url || '',
        type: params.type || '',
      });
    } else if (method === 'Network.responseReceived') {
      const r = params.response || {};
      const u = r.url || '';
      if (this.isLocalAssetUrl(u) && r.status >= 400) {
        this.httpErrors.push({
          url: u,
          status: r.status,
          type: params.type || '',
        });
      }
    } else if (method === 'Network.loadingFailed') {
      const info = this.requests.get(params.requestId);
      if (info && this.isLocalAssetUrl(info.url) && !params.canceled) {
        this.httpErrors.push({
          url: info.url,
          status: 0,
          errorText: params.errorText || 'loadingFailed',
          type: info.type,
        });
      }
    }
  }

  isLocalAssetUrl(url) {
    if (!url) return false;
    if (this.baseUrl && url.startsWith(this.baseUrl)) return true;
    return /^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//i.test(url);
  }

  cmd(method, params = {}, timeoutMs = 15000) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return Promise.reject(new Error('CDP_NOT_CONNECTED'));
    }
    const id = ++this.nextId;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`CDP_CMD_TIMEOUT: ${method} timed out after ${timeoutMs}ms`));
      }, timeoutMs);
      this.pending.set(id, { resolve, reject, timer });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async evalJs(expression, awaitPromise = true) {
    const res = await this.cmd('Runtime.evaluate', {
      expression,
      awaitPromise,
      returnByValue: true,
    });
    if (res.exceptionDetails) {
      const d = res.exceptionDetails;
      throw new Error(`JS_EVAL_ERROR: ${d.exception?.description || d.text || 'Evaluation failed'}`);
    }
    return res.result ? res.result.value : undefined;
  }

  clearDiagnostics() {
    this.exceptions.length = 0;
    this.httpErrors.length = 0;
    this.requests.clear();
  }

  async setViewport(width, height, mobile, dpr) {
    const isMobile = !!mobile;
    this.viewportWidth = Number(width) || 0;
    this.viewportHeight = Number(height) || 0;
    await this.cmd('Emulation.setDeviceMetricsOverride', {
      width,
      height,
      deviceScaleFactor: dpr || (isMobile ? 2 : 1),
      mobile: isMobile,
    });
    await this.cmd('Emulation.setTouchEmulationEnabled', {
      enabled: isMobile,
      maxTouchPoints: isMobile ? 5 : 1,
    });
  }

  async setMobile() {
    await this.setViewport(390, 844, true, 2);
  }

  async setDesktop() {
    await this.setViewport(1440, 1000, false, 1);
  }

  async setMedia({ colorScheme = '', reducedMotion = false } = {}) {
    const features = [];
    if (colorScheme) features.push({ name: 'prefers-color-scheme', value: colorScheme });
    if (reducedMotion) features.push({ name: 'prefers-reduced-motion', value: 'reduce' });
    await this.cmd('Emulation.setEmulatedMedia', { features });
  }

  async waitForReady(timeoutMs = 10000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const state = await this.evalJs(`(() => {
        if (document.readyState !== 'complete') return { ready: false };
        const ana = document.getElementById('ana');
        if (!ana) return { ready: false };
        const skel = ana.querySelectorAll('.iskelet').length;
        const hasContent = ana.children.length > 0 && ana.textContent.trim().length > 0;
        return { ready: skel === 0 && hasContent, skel };
      })()`);
      if (state && state.ready) {
        await sleep(80);
        return true;
      }
      await sleep(80);
    }
    throw new Error('PAGE_READY_TIMEOUT: #ana did not finish rendering within timeout');
  }

  async waitFor(expression, timeoutMs = 6000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const ok = await this.evalJs(`Boolean(${expression})`);
      if (ok) return true;
      await sleep(70);
    }
    throw new Error(`WAIT_TIMEOUT: Condition did not become truthy: ${expression.slice(0, 120)}`);
  }

  async navigate(urlOrHash, { resetStorage = false, preStorage = null, colorScheme = '', reducedMotion = false, interceptWindowOpen = false, waitReady = true } = {}) {
    const target = urlOrHash.startsWith('http')
      ? urlOrHash
      : `${this.baseUrl}/${urlOrHash.replace(/^\/+/, '')}`;

    await this.setMedia({ colorScheme, reducedMotion });
    await this.cmd('Page.navigate', { url: 'about:blank' });
    await sleep(60);

    if (resetStorage || (preStorage && Object.keys(preStorage).length > 0)) {
      const originUrl = `${this.baseUrl}/data/surum.json`;
      await this.cmd('Page.navigate', { url: originUrl });
      await sleep(60);
      await this.evalJs(`(() => {
        ${resetStorage ? 'localStorage.clear();' : ''}
        const pre = ${JSON.stringify(preStorage || {})};
        for (const [k, v] of Object.entries(pre)) {
          if (v === null) localStorage.removeItem(k);
          else localStorage.setItem(k, typeof v === 'string' ? v : JSON.stringify(v));
        }
      })()`, false);
      await this.cmd('Page.navigate', { url: 'about:blank' });
      await sleep(50);
    }

    this.clearDiagnostics();
    await this.cmd('Page.navigate', { url: target });
    if (waitReady) {
      await this.waitForReady();
    } else {
      await sleep(250);
    }
    if (interceptWindowOpen) {
      await this.installWindowOpenSpy();
    }
    return {
      url: await this.evalJs('location.href', false),
      hash: await this.evalJs('location.hash', false),
      exceptions: [...this.exceptions],
      httpErrors: [...this.httpErrors],
    };
  }

  async reload({ waitReady = true, interceptWindowOpen = false } = {}) {
    this.clearDiagnostics();
    await this.cmd('Page.reload', { ignoreCache: true });
    if (waitReady) {
      await this.waitForReady();
    } else {
      await sleep(250);
    }
    if (interceptWindowOpen) {
      await this.installWindowOpenSpy();
    }
    return {
      url: await this.evalJs('location.href', false),
      hash: await this.evalJs('location.hash', false),
      exceptions: [...this.exceptions],
      httpErrors: [...this.httpErrors],
    };
  }

  async setHash(hash, { waitReady = true } = {}) {
    const h = hash.startsWith('#') ? hash : `#${hash}`;
    await this.evalJs(`location.hash = ${JSON.stringify(h)}`, false);
    await sleep(100);
    if (waitReady) await this.waitForReady();
    return {
      hash: await this.evalJs('location.hash', false),
      exceptions: [...this.exceptions],
      httpErrors: [...this.httpErrors],
    };
  }

  async installWindowOpenSpy() {
    await this.evalJs(`(() => {
      if (!window.__e2eOpenSpy) {
        window.__openedUrls = [];
        window.__e2eOrigOpen = window.open;
        window.open = function(url, target, features) {
          window.__openedUrls.push({ url: String(url || ''), target: String(target || ''), features: String(features || '') });
          return { opener: window, focus() {}, close() {} };
        };
        window.__e2eOpenSpy = true;
      }
      return true;
    })()`, false);
  }

  async click(selector, { index = 0 } = {}) {
    const found = await this.evalJs(`(() => {
      const els = Array.from(document.querySelectorAll(${JSON.stringify(selector)}))
        .filter(el => {
          const st = getComputedStyle(el);
          if (st.display === 'none' || st.visibility === 'hidden') return false;
          const r = el.getBoundingClientRect();
          return r.width > 0 && r.height > 0;
        });
      const el = els[${index}];
      if (!el) return null;
      el.scrollIntoView({ block: 'center', inline: 'center' });
      el.click();
      return { tag: el.tagName, text: (el.textContent || '').trim().slice(0, 80) };
    })()`, false);
    if (!found) {
      throw new Error(`ELEMENT_NOT_FOUND: ${selector} [${index}]`);
    }
    await sleep(120);
    return found;
  }

  async pressKey(key) {
    await this.cmd('Input.dispatchKeyEvent', { type: 'keyDown', key });
    await this.cmd('Input.dispatchKeyEvent', { type: 'keyUp', key });
    await sleep(100);
  }

  async inspectLayout() {
    return await this.evalJs(`(() => {
      const iw = window.innerWidth;
      const ih = window.innerHeight;
      const maxW = ${Number(this.viewportWidth) || 0} || iw;
      const docSW = document.documentElement.scrollWidth;
      const bodySW = document.body ? document.body.scrollWidth : 0;

      function inVisibleDialog(el) {
        const dlg = el.closest('dialog');
        if (dlg && !dlg.hasAttribute('open')) return false;
        const pop = el.closest('[popover]');
        if (pop && !pop.matches(':popover-open')) return false;
        const det = el.closest('details');
        if (det && !det.hasAttribute('open') && !el.closest('summary')) return false;
        return true;
      }

      function clippedRect(el) {
        let r = el.getBoundingClientRect();
        let left = r.left, top = r.top, right = r.right, bottom = r.bottom;
        let cur = el.parentElement;
        while (cur && cur !== document.body && cur !== document.documentElement) {
          const st = getComputedStyle(cur);
          if (st.overflowX === 'hidden' || st.overflowX === 'auto' || st.overflowX === 'scroll' ||
              st.overflowY === 'hidden' || st.overflowY === 'auto' || st.overflowY === 'scroll') {
            const cr = cur.getBoundingClientRect();
            left = Math.max(left, cr.left);
            top = Math.max(top, cr.top);
            right = Math.min(right, cr.right);
            bottom = Math.min(bottom, cr.bottom);
          }
          cur = cur.parentElement;
        }
        return { left, top, right, bottom, width: Math.max(0, right - left), height: Math.max(0, bottom - top) };
      }

      function isVisible(el) {
        if (!inVisibleDialog(el)) return false;
        if (el.closest('[hidden]')) return false;
        let cur = el;
        while (cur && cur !== document.documentElement) {
          const st = getComputedStyle(cur);
          if (st.display === 'none' || st.visibility === 'hidden' || parseFloat(st.opacity) === 0) return false;
          cur = cur.parentElement;
        }
        const r = el.getBoundingClientRect();
        return r.width > 0.5 && r.height > 0.5;
      }

      function hasHScrollAncestor(el) {
        let cur = el.parentElement;
        while (cur && cur !== document.body && cur !== document.documentElement) {
          const st = getComputedStyle(cur);
          if ((st.overflowX === 'auto' || st.overflowX === 'scroll') && cur.scrollWidth > cur.clientWidth + 2) {
            const cr = cur.getBoundingClientRect();
            if (cr.left >= -2 && cr.right <= maxW + 2) return cur;
          }
          cur = cur.parentElement;
        }
        return null;
      }

      function layerOf(el) {
        if (el.closest('dialog[open]')) {
          const d = el.closest('dialog[open]');
          return 'dialog:' + (d.id || 'anon');
        }
        if (el.closest('[popover]:popover-open')) return 'popover';
        let cur = el;
        while (cur && cur !== document.body) {
          const st = getComputedStyle(cur);
          if (st.position === 'fixed') return 'fixed:' + (cur.id || cur.className || cur.tagName);
          cur = cur.parentElement;
        }
        return 'flow';
      }

      const controls = Array.from(document.querySelectorAll('a, button, input, select, textarea, summary, [role="button"], [role="tab"]'))
        .filter(isVisible);

      const clipped = [];
      const items = [];
      for (const el of controls) {
        const r = el.getBoundingClientRect();
        const scroller = hasHScrollAncestor(el);
        if (!scroller && (r.left < -1.5 || r.right > maxW + 1.5)) {
          clipped.push({
            tag: el.tagName,
            text: (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 50),
            left: Math.round(r.left * 10) / 10,
            right: Math.round(r.right * 10) / 10,
            innerWidth: iw,
            viewportWidth: maxW,
          });
        }
        // Only check overlaps for controls that are actually inside or near the viewport
        if (r.bottom > 0 && r.top < ih && r.right > 0 && r.left < maxW) {
          items.push({ el, r, layer: layerOf(el), scroller });
        }
      }

      const overlaps = [];
      for (let i = 0; i < items.length; i++) {
        for (let j = i + 1; j < items.length; j++) {
          const A = items[i], B = items[j];
          if (A.el.contains(B.el) || B.el.contains(A.el)) continue;
          if (A.layer !== B.layer) continue; // separate fixed/dialog layers handled separately
          const ix = Math.max(0, Math.min(A.r.right, B.r.right) - Math.max(A.r.left, B.r.left));
          const iy = Math.max(0, Math.min(A.r.bottom, B.r.bottom) - Math.max(A.r.top, B.r.top));
          if (ix * iy > 4) {
            overlaps.push({
              a: (A.el.textContent || A.el.getAttribute('aria-label') || A.el.tagName).trim().slice(0, 40),
              b: (B.el.textContent || B.el.getAttribute('aria-label') || B.el.tagName).trim().slice(0, 40),
              area: Math.round(ix * iy),
            });
          }
        }
      }

      // Check non-modal desktop side #panel overlap against #ana content/controls
      const panel = document.getElementById('panel');
      const panelOverlaps = [];
      if (panel && panel.hasAttribute('open') && !panel.matches(':modal')) {
        const pr = panel.getBoundingClientRect();
        if (pr.width > 0 && pr.height > 0) {
          const ana = document.getElementById('ana');
          if (ana) {
            const anaTargets = ana.querySelectorAll('.kutu, .sat, .manset, .rk, a, button');
            for (const el of anaTargets) {
              if (!isVisible(el)) continue;
              const r = clippedRect(el);
              if (r.width <= 1 || r.height <= 1) continue;
              if (r.bottom <= 0 || r.top >= ih) continue;
              const ix = Math.max(0, Math.min(pr.right, r.right) - Math.max(pr.left, r.left));
              const iy = Math.max(0, Math.min(pr.bottom, r.bottom) - Math.max(pr.top, r.top));
              if (ix * iy > 4) {
                panelOverlaps.push({
                  target: (el.className || el.tagName) + ':' + (el.textContent || '').trim().slice(0, 35),
                  area: Math.round(ix * iy),
                });
              }
            }
          }
        }
      }

      return {
        viewportWidth: maxW,
        innerWidth: iw,
        innerHeight: ih,
        docScrollWidth: docSW,
        bodyScrollWidth: bodySW,
        horizontalOverflow: docSW > maxW + 1 || bodySW > maxW + 1 || iw > maxW + 1,
        clippedCount: clipped.length,
        clipped: clipped.slice(0, 10),
        overlapCount: overlaps.length,
        overlaps: overlaps.slice(0, 10),
        panelOverlapCount: panelOverlaps.length,
        panelOverlaps: panelOverlaps.slice(0, 10),
      };
    })()`, false);
  }

  async inspectTouchTargets(minPx = 44) {
    return await this.evalJs(`(() => {
      const min = ${Number(minPx)};
      const iw = window.innerWidth;
      const ih = window.innerHeight;
      function isVisible(el) {
        const dlg = el.closest('dialog');
        if (dlg && !dlg.hasAttribute('open')) return false;
        const pop = el.closest('[popover]');
        if (pop && !pop.matches(':popover-open')) return false;
        const det = el.closest('details');
        if (det && !det.hasAttribute('open') && !el.closest('summary')) return false;
        if (el.closest('[hidden]')) return false;
        let cur = el;
        while (cur && cur !== document.documentElement) {
          const st = getComputedStyle(cur);
          if (st.display === 'none' || st.visibility === 'hidden' || parseFloat(st.opacity) === 0) return false;
          cur = cur.parentElement;
        }
        const r = el.getBoundingClientRect();
        return r.width > 0.5 && r.height > 0.5;
      }

      function pseudoExpand(el, pseudo) {
        const st = getComputedStyle(el, pseudo);
        if (!st || st.content === 'none' || st.position !== 'absolute' || st.pointerEvents === 'none') return { dw: 0, dh: 0 };
        const px = v => (v && v.endsWith('px')) ? parseFloat(v) : 0;
        const top = px(st.top), right = px(st.right), bottom = px(st.bottom), left = px(st.left);
        return {
          dw: (left < 0 ? -left : 0) + (right < 0 ? -right : 0),
          dh: (top < 0 ? -top : 0) + (bottom < 0 ? -bottom : 0),
        };
      }

      const controls = Array.from(document.querySelectorAll('a, button, input, select, textarea, summary, [role="button"], [role="tab"]'))
        .filter(isVisible)
        .filter(el => {
          // Inline text headline links inside clickable rows/cards are prose links, not standalone hit buttons
          if (el.tagName === 'A' && el.closest('h1, h2, h3, p, .sat-t, .tr-t, .dk-t, .rk-t')) return false;
          // Exclude visually hidden skip/sr links
          const r = el.getBoundingClientRect();
          if (r.left < -500 || r.right > iw + 2000) return false;
          return true;
        });

      const undersized = [];
      for (const el of controls) {
        const r = el.getBoundingClientRect();
        if (r.bottom < 0 || r.top > ih + 400) continue; // check visible and first screen fold
        const a = pseudoExpand(el, '::after');
        const b = pseudoExpand(el, '::before');
        const effW = Math.round((r.width + Math.max(a.dw, b.dw)) * 10) / 10;
        const effH = Math.round((r.height + Math.max(a.dh, b.dh)) * 10) / 10;
        if (effW < min - 0.5 || effH < min - 0.5) {
          undersized.push({
            tag: el.tagName,
            act: el.dataset?.act || '',
            cls: typeof el.className === 'string' ? el.className : '',
            text: (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 45),
            w: Math.round(r.width * 10) / 10,
            h: Math.round(r.height * 10) / 10,
            effW,
            effH,
          });
        }
      }
      return {
        checked: controls.length,
        undersizedCount: undersized.length,
        undersized: undersized.slice(0, 20),
      };
    })()`, false);
  }

  async inspectTheme() {
    return await this.evalJs(`(() => {
      function parseRgb(str) {
        const m = String(str || '').match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
        if (!m) return [255, 255, 255];
        return [+m[1], +m[2], +m[3]];
      }
      function relLum([r, g, b]) {
        const f = c => {
          c /= 255;
          return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
        };
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
      }
      const st = getComputedStyle(document.body);
      const bg = parseRgb(st.backgroundColor);
      const fg = parseRgb(st.color);
      const bgLum = relLum(bg);
      const fgLum = relLum(fg);
      const contrast = (Math.max(bgLum, fgLum) + 0.05) / (Math.min(bgLum, fgLum) + 0.05);
      return {
        tema: document.documentElement.dataset.tema || '',
        bg: st.backgroundColor,
        fg: st.color,
        bgLum: Math.round(bgLum * 1000) / 1000,
        fgLum: Math.round(fgLum * 1000) / 1000,
        contrast: Math.round(contrast * 100) / 100,
      };
    })()`, false);
  }

  async inspectRtl() {
    return await this.evalJs(`(() => {
      const rtlRx = /[\\u0590-\\u08FF\\uFB50-\\uFDFF\\uFE70-\\uFEFF]/;
      const nodes = Array.from(document.querySelectorAll('#ana a, #ana h2, #ana h3, #ana p, #ana b, #ana span, #panel h2, #panel a'));
      const findings = [];
      let rtlCount = 0;
      for (const el of nodes) {
        const txt = (el.textContent || '').trim();
        if (!txt || !rtlRx.test(txt)) continue;
        // Skip container if a direct child already carries the text
        if (Array.from(el.children).some(ch => rtlRx.test(ch.textContent || ''))) continue;
        rtlCount++;
        const st = getComputedStyle(el);
        const hasDir = el.getAttribute('dir') === 'auto' || el.closest('[dir="auto"]') !== null;
        const hasIsolate = st.unicodeBidi === 'isolate' || st.unicodeBidi === 'plaintext';
        if (!hasDir && !hasIsolate) {
          findings.push({
            tag: el.tagName,
            cls: typeof el.className === 'string' ? el.className : '',
            text: txt.slice(0, 40),
            dir: el.getAttribute('dir') || '',
            unicodeBidi: st.unicodeBidi,
          });
        }
      }
      return {
        rtlCount,
        unprotectedCount: findings.length,
        unprotected: findings.slice(0, 15),
      };
    })()`, false);
  }

  async close() {
    if (this.closed) return;
    this.closed = true;
    try {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        await Promise.race([this.cmd('Browser.close', {}, 2000), sleep(500)]);
      }
    } catch {
      // ignore
    }
    try {
      if (this.ws) this.ws.close();
    } catch {
      // ignore
    }
    if (this.proc && this.proc.exitCode === null) {
      this.proc.kill('SIGTERM');
      await sleep(300);
      if (this.proc.exitCode === null) {
        try {
          this.proc.kill('SIGKILL');
        } catch {
          // ignore
        }
      }
    }
    if (this.ownUserDataDir && this.userDataDir && existsSync(this.userDataDir)) {
      try {
        rmSync(this.userDataDir, { recursive: true, force: true });
      } catch {
        // ignore
      }
    }
  }
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.checkChrome) {
    const p = resolveChrome();
    process.stdout.write(JSON.stringify({ ok: true, chromePath: p }) + '\n');
    return;
  }

  const session = new CdpSession({
    userDataDir: args.userDataDir,
    baseUrl: args.baseUrl,
  });

  const cleanup = async () => {
    await session.close();
  };
  process.on('SIGINT', async () => { await cleanup(); process.exit(0); });
  process.on('SIGTERM', async () => { await cleanup(); process.exit(0); });

  try {
    const info = await session.start();
    process.stdout.write(JSON.stringify({ ok: true, ready: true, ...info }) + '\n');
  } catch (err) {
    process.stdout.write(JSON.stringify({ ok: false, error: err.message, harnessError: true }) + '\n');
    await cleanup();
    process.exit(2);
  }

  const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
  for await (const line of rl) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    let req;
    try {
      req = JSON.parse(trimmed);
    } catch (e) {
      process.stdout.write(JSON.stringify({ ok: false, error: `INVALID_JSON: ${e.message}` }) + '\n');
      continue;
    }

    if (req.cmd === 'shutdown') {
      await cleanup();
      process.stdout.write(JSON.stringify({ ok: true, closed: true }) + '\n');
      break;
    }

    try {
      let result;
      switch (req.cmd) {
        case 'setMobile':
          await session.setMobile();
          result = { ok: true };
          break;
        case 'setDesktop':
          await session.setDesktop();
          result = { ok: true };
          break;
        case 'setViewport':
          await session.setViewport(req.width, req.height, req.mobile, req.dpr);
          result = { ok: true };
          break;
        case 'setMedia':
          await session.setMedia(req.params || {});
          result = { ok: true };
          break;
        case 'navigate':
          result = await session.navigate(req.target || '', req.options || {});
          break;
        case 'reload':
          result = await session.reload(req.options || {});
          break;
        case 'setHash':
          result = await session.setHash(req.hash || '', req.options || {});
          break;
        case 'eval':
          result = { value: await session.evalJs(req.expression, req.awaitPromise !== false) };
          break;
        case 'click':
          result = await session.click(req.selector, req.options || {});
          break;
        case 'pressKey':
          await session.pressKey(req.key);
          result = { ok: true };
          break;
        case 'waitFor':
          await session.waitFor(req.expression, req.timeoutMs || 6000);
          result = { ok: true };
          break;
        case 'waitForReady':
          await session.waitForReady(req.timeoutMs || 10000);
          result = { ok: true };
          break;
        case 'clearDiagnostics':
          session.clearDiagnostics();
          result = { ok: true };
          break;
        case 'getDiagnostics':
          result = {
            exceptions: [...session.exceptions],
            httpErrors: [...session.httpErrors],
          };
          break;
        case 'inspectLayout':
          result = await session.inspectLayout();
          break;
        case 'inspectTouchTargets':
          result = await session.inspectTouchTargets(req.minPx || 44);
          break;
        case 'inspectTheme':
          result = await session.inspectTheme();
          break;
        case 'inspectRtl':
          result = await session.inspectRtl();
          break;
        default:
          throw new Error(`UNKNOWN_CMD: ${req.cmd}`);
      }
      process.stdout.write(JSON.stringify({ ok: true, result }) + '\n');
    } catch (err) {
      const msg = err?.message || String(err);
      const isInfra = /^(CDP_|WS_|CHROME_|PAGE_READY_TIMEOUT)/.test(msg);
      process.stdout.write(JSON.stringify({ ok: false, error: msg, harnessError: isInfra }) + '\n');
    }
  }
  await cleanup();
}

main().catch(err => {
  process.stdout.write(JSON.stringify({ ok: false, error: err?.message || String(err), harnessError: true }) + '\n');
  process.exit(2);
});
