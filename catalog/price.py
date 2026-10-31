"""Price a receipt's token usage from catalog/models.json.

cost = input * in + output * out + cache_read * cr + cache_write_5m * in * 1.25
       + cache_write_1h * in * 2.0, all per million tokens. `cr` is the catalog's
cache_read_per_mtok, or in * 0.1 when the catalog has not verified it (the
providers' published rule). Receipts carry the token counts, so a price change
means editing the catalog and re-running report.py, not re-running the tasks.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_CATALOG = None


def catalog(path=None):
    global _CATALOG
    if path is not None:
        return json.loads(Path(path).read_text())
    if _CATALOG is None:
        _CATALOG = json.loads((HERE / 'models.json').read_text())
    return _CATALOG


def model_entry(model, cat=None):
    cat = cat or catalog()
    models = cat['models']
    if model in models:
        return models[model]
    for k, v in models.items():  # 'openai:gpt-x' keyed with a provider prefix
        if k.split(':', 1)[-1] == model:
            return v
    return None


def rates(entry):
    """Per-token rates (USD) for one catalog entry, or None when a price is unknown."""
    inp, out = entry.get('input_per_mtok'), entry.get('output_per_mtok')
    if inp is None or out is None:
        return None
    cr = entry.get('cache_read_per_mtok')
    mult = entry.get('cache_write_multipliers') or {'5m': 1.25, '1h': 2.0}
    return {'in': inp / 1e6, 'out': out / 1e6,
            'cache_read': (cr if cr is not None else inp * 0.1) / 1e6,
            'write_5m': inp * mult.get('5m', 1.25) / 1e6, 'write_1h': inp * mult.get('1h', 2.0) / 1e6}


def price_usage(usage, entry):
    """USD for one receipt's `usage` block under the given catalog entry, or None."""
    r = rates(entry)
    if r is None or not usage:
        return None
    cc = usage.get('cache_creation') or {}
    w5, w1 = cc.get('ephemeral_5m_input_tokens'), cc.get('ephemeral_1h_input_tokens')
    if w5 is None and w1 is None:  # no breakdown: assume the CLI's default 1h cache
        w5, w1 = 0, usage.get('cache_creation_input_tokens', 0) or 0
    return (usage.get('input_tokens', 0) * r['in'] + usage.get('output_tokens', 0) * r['out']
            + usage.get('cache_read_input_tokens', 0) * r['cache_read']
            + (w5 or 0) * r['write_5m'] + (w1 or 0) * r['write_1h'])


def price_record(record, cat=None):
    entry = model_entry(record.get('model_requested') or record.get('model') or '', cat)
    return price_usage(record.get('usage'), entry) if entry else None
