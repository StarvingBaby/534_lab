"""Fetch official monthly ACM + daily DGS10; reuse existing adjusted GLD data.

No series substitution. Failure preserves the last verified artifact and records
an explicit refresh-error sidecar. The first fetch failure fails the build.
"""
import csv
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from bond_math import align, discover_window, monthly_last

ROOT = Path(__file__).resolve().parent
ACM_URL = 'https://www.newyorkfed.org/medialibrary/media/research/data_indicators/ACMTermPremium.xls'
FRED_URL = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10&cosd=2004-01-01'
OUT = ROOT / 'bond_data.json'
STATUS = ROOT / 'bond_refresh_status.json'


def download(url):
    with urlopen(Request(url, headers={'User-Agent': 'AurumLab academic research'}), timeout=60) as response:
        return response.read()


def parse_acm(raw):
    import pandas as pd
    book = pd.ExcelFile(io.BytesIO(raw))
    if 'ACM Monthly' not in book.sheet_names:
        raise ValueError(f'Official workbook missing ACM Monthly; found {book.sheet_names}')
    frame = pd.read_excel(book, sheet_name='ACM Monthly')
    if not {'DATE', 'ACMTP10'}.issubset(frame.columns):
        raise ValueError(f'ACM schema changed: expected DATE/ACMTP10, found {list(frame.columns)}')
    dates = pd.to_datetime(frame['DATE'], errors='raise')
    values = pd.to_numeric(frame['ACMTP10'], errors='coerce')
    rows = [(d.date().isoformat(), float(v)) for d, v in zip(dates, values)]
    if len({d[:7] for d, _ in rows}) != len(rows):
        raise ValueError('Duplicate months in official ACM monthly sheet')
    return rows


def parse_yields(raw):
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    columns = reader.fieldnames or []
    day_column = 'observation_date' if 'observation_date' in columns else 'DATE'
    if day_column not in columns or 'DGS10' not in columns:
        raise ValueError(f'FRED schema changed: {columns}')
    return [(r[day_column], float(r['DGS10'])) for r in reader if r['DGS10'] not in ('', '.')]


def write_json(path, payload):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def main():
    now = datetime.now(timezone.utc)
    try:
        # Inspect actual source schemas on every refresh; fail rather than guess.
        acm = monthly_last(parse_acm(download(ACM_URL)), now.date())
        yields = monthly_last(parse_yields(download(FRED_URL)), now.date())
        prices = json.loads((ROOT / 'data.json').read_text(encoding='utf-8'))
        gold = monthly_last([(r['date'], float(r['gld'])) for r in prices['prices']], now.date())
        observations = align(acm, yields, gold)
        if len(observations) < 37:
            raise ValueError(f'Insufficient aligned history: {len(observations)} months')
        finding = discover_window(observations)
        payload = {
            'schema_version': 1, 'generated_at': now.isoformat(timespec='seconds'),
            'last_observation_date': observations[-1]['acm_date'],
            'frequency': 'Completed calendar months; last available observation; inner join on month',
            'sources': {'acm': {'url': ACM_URL, 'sheet': 'ACM Monthly', 'columns': ['DATE', 'ACMTP10']},
                        'yield': {'url': FRED_URL, 'columns': ['observation_date or DATE', 'DGS10']},
                        'gold': {'file': 'data.json', 'source': prices['source'], 'fetched_at': prices['fetched_at']}},
            'definitions': {'acm_term_premium_pct': 'NY Fed ACM estimated 10-year term premium, percent annualized',
                            'modified_duration_years': 'Hypothetical fresh 10-year semiannual par Treasury; years',
                            'gld_adjusted_close_usd': 'GLD ETF adjusted close, USD; not spot gold'},
            'assumptions': ['Face 100; 20 half-year cash flows; annual coupon equals DGS10 yield / 100.',
                            'Reset maturity to 10 years each month; no aging CUSIP.',
                            'No forward filling. Source-specific endpoint dates may differ within a month.',
                            'Partial current month excluded. ACM estimates may be revised.'],
            'selection_rule': 'Largest absolute ACM change across all consecutive six-calendar-month windows; earliest tie; GLD return not used.',
            'default_window': finding, 'observations': observations}
        write_json(OUT, payload)
        write_json(STATUS, {'ok': True, 'attempted_at': now.isoformat(), 'error': None})
        print(f'Updated {len(observations)} months; default finding: {finding}')
    except Exception as exc:
        write_json(STATUS, {'ok': False, 'attempted_at': now.isoformat(), 'error': str(exc)})
        if OUT.exists():
            old = json.loads(OUT.read_text(encoding='utf-8'))
            if len(old.get('observations', [])) >= 37:
                discover_window(old['observations'])
                print(f'WARNING: bond refresh failed; retaining dated cache: {exc}')
                return
        raise RuntimeError(f'No verified bond cache; refresh failed: {exc}') from exc


if __name__ == '__main__':
    main()
