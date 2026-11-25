#!/usr/bin/env python3
"""E2E Test Runner for Akis (Tiers 1–4, Features E1–E8).

Usage:
  python3 tests_e2e/run_e2e.py [--tier 1|2|3|4] [--feature E1..E8] [--port 8775] [--json <path>]

Exit codes:
  0 = all selected tests passed
  1 = >=1 test assertion failed
  2 = harness / infrastructure error
"""
import argparse
import json
import os
import sys
import time
import traceback

E2E_DIR = os.path.dirname(os.path.abspath(__file__))
if E2E_DIR not in sys.path:
    sys.path.insert(0, E2E_DIR)

from harness import BrowserClient, HarnessError, LocalServer, TESTS  # noqa: E402
import tier1_features  # noqa: E402, F401
import tier2_boundaries  # noqa: E402, F401
import tier3_pairwise  # noqa: E402, F401
import tier4_scenarios  # noqa: E402, F401


class RunContext:
    def __init__(self, port):
        self.port = port
        self._server = None
        self._browser = None
        self.health = {
            'server_url': None,
            'chrome_path': None,
            'node_version': None,
            'browser_started': False,
        }

    @property
    def browser(self):
        if self._browser is None:
            if self._server is None:
                self._server = LocalServer(port=self.port)
                self._server.__enter__()
                self.health['server_url'] = self._server.base_url
            self._browser = BrowserClient(self._server.base_url)
            self._browser.__enter__()
            self.health['chrome_path'] = self._browser.chrome_path
            self.health['node_version'] = self._browser.node_version
            self.health['browser_started'] = True
        return self._browser

    def close(self):
        errs = []
        if self._browser is not None:
            try:
                self._browser.__exit__(None, None, None)
            except Exception as exc:
                errs.append(f'Browser cleanup error: {exc}')
            self._browser = None
        if self._server is not None:
            try:
                self._server.__exit__(None, None, None)
            except Exception as exc:
                errs.append(f'Server cleanup error: {exc}')
            self._server = None
        return errs


def main():
    ap = argparse.ArgumentParser(description='Akis 4-Tier Opaque-Box E2E Runner')
    ap.add_argument('--tier', type=int, choices=[1, 2, 3, 4], action='append',
                    help='Run only specified tier(s)')
    ap.add_argument('--feature', choices=[f'E{i}' for i in range(1, 9)], action='append',
                    help='Run only specified feature(s)')
    ap.add_argument('--port', type=int, default=int(os.environ.get('E2E_PORT', '8775')),
                    help='Local server port (default 8775; 0 for ephemeral free port)')
    ap.add_argument('--json', dest='json_path', default='', help='Write JSON report to path')
    args = ap.parse_args()

    selected = [
        fn for fn in TESTS
        if (not args.tier or fn._e2e['tier'] in args.tier)
        and (not args.feature or fn._e2e['feature'] in args.feature)
    ]
    if not selected:
        print('No tests matched the given filters.', file=sys.stderr)
        return 2

    t0 = time.time()
    ctx = RunContext(args.port)
    results = []
    infra_error = None

    try:
        for fn in selected:
            meta = fn._e2e
            st = time.time()
            status = 'PASS'
            msg = ''
            try:
                fn(ctx)
            except AssertionError as exc:
                status = 'FAIL'
                msg = str(exc) or 'Assertion failed'
            except HarnessError as exc:
                status = 'INFRA_ERROR'
                msg = str(exc)
                infra_error = msg
            except Exception as exc:
                status = 'FAIL'
                msg = f'{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=3).strip()}'

            dur = round(time.time() - st, 3)
            results.append({
                'id': meta['id'],
                'tier': meta['tier'],
                'feature': meta['feature'],
                'desc': meta['desc'],
                'gate': meta['gate'],
                'status': status,
                'duration_s': dur,
                'message': msg,
            })
            mark = 'PASS' if status == 'PASS' else status
            short = f" — {msg.splitlines()[0][:110]}" if msg else ''
            print(f"[{mark:4s}] T{meta['tier']} {meta['feature']} {meta['id']}: {meta['desc']} ({dur:.2f}s){short}", flush=True)
            if infra_error:
                break
    finally:
        cleanup_errs = ctx.close()
        if cleanup_errs and not infra_error:
            infra_error = '; '.join(cleanup_errs)

    total_dur = round(time.time() - t0, 2)
    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    infra = sum(1 for r in results if r['status'] == 'INFRA_ERROR')

    by_tier = {}
    for t in (1, 2, 3, 4):
        sub = [r for r in results if r['tier'] == t]
        if sub:
            by_tier[f'T{t}'] = {
                'total': len(sub),
                'pass': sum(1 for r in sub if r['status'] == 'PASS'),
                'fail': sum(1 for r in sub if r['status'] != 'PASS'),
            }

    by_feature = {}
    for f_name in [f'E{i}' for i in range(1, 9)]:
        sub = [r for r in results if r['feature'] == f_name]
        if sub:
            by_feature[f_name] = {
                'total': len(sub),
                'pass': sum(1 for r in sub if r['status'] == 'PASS'),
                'fail': sum(1 for r in sub if r['status'] != 'PASS'),
            }

    summary = {
        'total_selected': len(selected),
        'executed': len(results),
        'passed': passed,
        'failed': failed,
        'infra_errors': infra,
        'duration_s': total_dur,
        'health': ctx.health,
        'by_tier': by_tier,
        'by_feature': by_feature,
        'results': results,
    }

    print('\n=== E2E SUMMARY ===')
    print(f"Health   : server={ctx.health['server_url']} node={ctx.health['node_version']} chrome={ctx.health['chrome_path']}")
    print(f"Totals   : {passed}/{len(results)} PASS, {failed} FAIL, {infra} INFRA_ERROR ({total_dur}s)")
    print('By Tier  : ' + ' | '.join(f"{k}: {v['pass']}/{v['total']}" for k, v in by_tier.items()))
    print('By Feat  : ' + ' | '.join(f"{k}: {v['pass']}/{v['total']}" for k, v in by_feature.items()))

    if args.json_path:
        out_dir = os.path.dirname(os.path.abspath(args.json_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.json_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f'JSON     : {args.json_path}')

    if infra_error or infra > 0:
        return 2
    if failed > 0:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
