"""Diff the live model lists of each provider against catalog/models.json.

This is the thing to run after a model launch. It never edits the catalog:
a new model is reported as "not in catalog, price unknown" and a human adds
it with a price, a source URL and a date. Prices are not in these APIs.

Anthropic: GET /v1/models via the anthropic SDK if installed (it resolves
ANTHROPIC_API_KEY or an `ant auth login` profile), else urllib with
ANTHROPIC_API_KEY. OpenAI: GET /v1/models with OPENAI_API_KEY.

Usage: python3 discover.py [--stale-days 60] [--json]
Exit code 0 always; the report is the output.
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOG = HERE / 'models.json'


def anthropic_models():
    try:
        import anthropic  # noqa: F401
        client = anthropic.Anthropic()
        return [(m.id, getattr(m, 'display_name', ''), str(getattr(m, 'created_at', '')))
                for m in client.models.list()], None
    except ImportError:
        key = os.environ.get('ANTHROPIC_API_KEY')
        if not key:
            return [], 'no anthropic SDK and ANTHROPIC_API_KEY unset'
        req = urllib.request.Request(
            'https://api.anthropic.com/v1/models?limit=1000',
            headers={'x-api-key': key, 'anthropic-version': '2023-06-01'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        return [(m['id'], m.get('display_name', ''), m.get('created_at', ''))
                for m in data.get('data', [])], None
    except Exception as error:  # auth, network
        return [], f'{type(error).__name__}: {str(error)[:160]}'


def openai_models():
    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        return [], 'OPENAI_API_KEY unset'
    try:
        req = urllib.request.Request('https://api.openai.com/v1/models',
                                     headers={'Authorization': f'Bearer {key}'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        return [('openai:' + m['id'], '', str(m.get('created', '')))
                for m in data.get('data', [])], None
    except Exception as error:
        return [], f'{type(error).__name__}: {str(error)[:160]}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stale-days', type=int, default=60)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    catalog = json.loads(CATALOG.read_text())
    known = catalog['models']
    today = dt.date.today()
    report = {'date': today.isoformat(), 'providers': {}, 'new': [],
              'missing_live': [], 'stale': [], 'price_unknown': []}
    for provider, fetch in (('anthropic', anthropic_models), ('openai', openai_models)):
        live, error = fetch()
        report['providers'][provider] = {'listed': len(live), 'error': error}
        live_ids = {m[0] for m in live}
        for mid, name, created in sorted(live):
            if mid not in known:
                report['new'].append({'id': mid, 'display_name': name,
                                      'created': created, 'provider': provider})
        for mid, entry in known.items():
            if entry['provider'] == provider and live and mid not in live_ids:
                report['missing_live'].append(mid)
    for mid, entry in known.items():
        verified = dt.date.fromisoformat(entry['verified_date'])
        if (today - verified).days > args.stale_days:
            report['stale'].append({'id': mid, 'verified_date': entry['verified_date']})
        if entry.get('input_per_mtok') is None or entry.get('output_per_mtok') is None:
            report['price_unknown'].append(mid)
    if args.json:
        print(json.dumps(report, indent=1))
        return
    print(f"catalog: {len(known)} models, checked {report['date']}")
    for p, info in report['providers'].items():
        print(f"{p}: {'listed ' + str(info['listed']) if not info['error'] else 'not checked: ' + info['error']}")
    print(f"\nnew models not in catalog ({len(report['new'])}): price unknown, add by hand with source and date")
    for m in report['new']:
        print(f"  {m['id']}  {m['display_name']}  created {m['created']}")
    print(f"\ncatalog models no longer listed live ({len(report['missing_live'])}):")
    for mid in report['missing_live']:
        print(f"  {mid}")
    print(f"\ncatalog prices older than {args.stale_days} days ({len(report['stale'])}): reverify")
    for m in report['stale']:
        print(f"  {m['id']}  verified {m['verified_date']}")
    print(f"\ncatalog entries with no price ({len(report['price_unknown'])}): {', '.join(report['price_unknown']) or 'none'}")


if __name__ == '__main__':
    sys.exit(main())
