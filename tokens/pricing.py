"""Optional caller-supplied flat rates. Never fetches prices or billing data."""
import json
import math

COUNTERS=('input','output','cache_read','cache_write')


def load_rates(path):
    if path.stat().st_size>65536:raise ValueError('Rate file must be at most 64 KiB')
    rates=json.loads(path.read_text())
    if not isinstance(rates,dict) or len(rates)>200:raise ValueError('Rates must map model names to per-million counter rates')
    for name,values in rates.items():
        if not isinstance(name,str) or not 1<=len(name)<=120 or not isinstance(values,dict):raise ValueError('Invalid model rates')
        for counter,value in values.items():
            if counter not in COUNTERS or isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
                raise ValueError('Rates must be finite nonnegative numbers for input, output, cache_read or cache_write')
    return rates


def estimate_usage(payload,rates):
    rows=[]
    for row in payload['rows']:
        known=rates.get(row['model'],{});estimate=0;unpriced=0
        for key in COUNTERS:
            if key in known:estimate+=row[key]*known[key]/1_000_000
            else:unpriced+=row[key]
        rows.append(dict(row,estimated_usd=estimate,unpriced_tokens=unpriced))
    return dict(payload,rows=rows,pricing={'basis':'Illustrative fictional demo rates' if payload.get('synthetic') else 'User-supplied flat rates per million tokens' if rates else 'No rates configured',
        'money_paid':None,'limits':'API-equivalent estimate only. No invoices, subscriptions, long-context tiers or provider billing adjustments are read or inferred.'})
