#!/usr/bin/env node
// Chrome DevTools Protocol ile ekran görüntüsü ve performans ölçümü (ek bağımlılık yok; Node >= 22).
// Kullanım: node tools/ekran.mjs ekran <cikti-klasoru> | node tools/ekran.mjs olcum
import { spawn } from 'node:child_process'; import { mkdirSync, writeFileSync } from 'node:fs';
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const B = process.env.TABAN || 'http://localhost:8765';
const bekle = ms => new Promise(r => setTimeout(r, ms));
async function ac() {
  const port = 9300 + Math.floor(Math.random() * 500);
  const p = spawn(CHROME, ['--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars', `--remote-debugging-port=${port}`, '--user-data-dir=/tmp/akis-chrome-' + port, 'about:blank'], { stdio: 'ignore' });
  let hedef; for (let i = 0; i < 50; i++) { try { const l = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); hedef = l.find(x => x.type === 'page'); if (hedef) break } catch {} await bekle(200) }
  const ws = new WebSocket(hedef.webSocketDebuggerUrl); await new Promise(r => ws.onopen = r);
  let id = 0; const bek = new Map(), olay = [];
  ws.onmessage = m => { const j = JSON.parse(m.data); if (j.id && bek.has(j.id)) { bek.get(j.id)(j); bek.delete(j.id) } else if (j.method) olay.push(j) };
  const cmd = (method, params = {}) => new Promise(r => { const i = ++id; bek.set(i, r); ws.send(JSON.stringify({ id: i, method, params })) });
  return { cmd, olay, kapat: () => { try { ws.close() } catch {} p.kill() } };
}
const MOBIL = { width: 390, height: 844, deviceScaleFactor: 2, mobile: true };
const MASA = { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false };
async function git(c, url, ol, bekleMs = 4500) {
  await c.cmd('Emulation.setDeviceMetricsOverride', ol); await c.cmd('Page.enable'); await c.cmd('Network.enable'); await c.cmd('Network.setCacheDisabled', { cacheDisabled: true });
  c.olay.length = 0; await c.cmd('Page.navigate', { url }); await bekle(bekleMs)
}
const calis = async (c, js) => (await c.cmd('Runtime.evaluate', { expression: js, awaitPromise: true, returnByValue: true })).result?.result?.value;
const mod = process.argv[2];
if (mod === 'ekran') {
  const dizin = process.argv[3] || 'docs/ekran'; mkdirSync(dizin, { recursive: true });
  const isler = JSON.parse(process.argv[4]);
  const c = await ac();
  for (const j of isler) {
    await git(c, B + j.url, j.mobil ? MOBIL : { ...MASA, height: j.h || 1000 }, j.bekle || 4500);
    if (j.js) { await calis(c, j.js); await bekle(900) }
    const r = await c.cmd('Page.captureScreenshot', { format: 'png', captureBeyondViewport: !!j.tam });
    writeFileSync(`${dizin}/${j.ad}.png`, Buffer.from(r.result.data, 'base64')); console.log('ok', j.ad);
  }
  c.kapat();
} else if (mod === 'olcum') {
  const c = await ac(); const sonuc = {};
  for (const [ad, ol, cpu, ag, url] of [['masaustu', MASA, 1, null, '/#/merkez'], ['mobil-4x-cpu-4g', MOBIL, 4, { latency: 150, downloadThroughput: 1.6e6 / 8, uploadThroughput: 0.75e6 / 8 }, '/#/merkez'], ['mobil-reels', MOBIL, 4, { latency: 150, downloadThroughput: 1.6e6 / 8, uploadThroughput: 0.75e6 / 8 }, '/#/reels']]) {
    await c.cmd('Network.enable'); await c.cmd('Emulation.setCPUThrottlingRate', { rate: cpu });
    await c.cmd('Network.emulateNetworkConditions', ag ? { offline: false, ...ag } : { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
    await git(c, B + url, ol, 9000);
    const bayt = c.olay.filter(o => o.method === 'Network.loadingFinished').reduce((a, o) => a + (o.params.encodedDataLength || 0), 0);
    const istek = c.olay.filter(o => o.method === 'Network.requestWillBeSent').length;
    const m = await calis(c, `JSON.stringify({fcp:(performance.getEntriesByName('first-contentful-paint')[0]||{}).startTime,dcl:performance.timing.domContentLoadedEventEnd-performance.timing.navigationStart,load:performance.timing.loadEventEnd-performance.timing.navigationStart,icerik:document.querySelectorAll('.sk,.sat,.rk').length,dom:document.getElementsByTagName('*').length})`);
    sonuc[ad] = { ...JSON.parse(m), aktarilan_kb: Math.round(bayt / 1024), istek }; await c.cmd('Emulation.setCPUThrottlingRate', { rate: 1 });
  }
  console.log(JSON.stringify(sonuc, null, 1)); c.kapat();
}
process.exit(0);
