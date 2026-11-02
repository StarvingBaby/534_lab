"""Fetch official monthly ACM + daily 10-year yields; reuse adjusted GLD data.

No silent source changes. Failure preserves the last verified artifact and records
an explicit refresh-error sidecar. The first fetch failure fails the build.
"""
import csv
import io
import json
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bond_math import align, discover_window, monthly_last

ROOT = Path(__file__).resolve().parent
ACM_URL = 'https://www.newyorkfed.org/medialibrary/media/research/data_indicators/ACMTermPremium.xls'
FRED_URL = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10&cosd=2004-01-01'
TREASURY_URL = ('https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml'
                '?data=daily_treasury_yield_curve&field_tdr_date_value={year}')
OUT = ROOT / 'bond_data.json'
STATUS = ROOT / 'bond_refresh_status.json'


def download(url, attempts=3):
    """Bounded retries for transient network errors, with source-specific logs."""
    for attempt in range(1, attempts + 1):
        print(f'Downloading {url} (attempt {attempt}/{attempts})', flush=True)
        try:
            with urlopen(Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; AurumLab academic research)',
                    'Accept': '*/*'}), timeout=25) as response:
                raw = response.read()
            if not raw:
                raise ValueError(f'Empty response from {url}')
            return raw
        except (HTTPError, URLError, TimeoutError, ConnectionError) as exc:
            if isinstance(exc, HTTPError) and exc.code not in (408, 429, 500, 502, 503, 504):
                raise
            if attempt == attempts:
                raise RuntimeError(f'Download failed after {attempts} attempts: {url}: {exc}') from exc
            print(f'WARNING: {url}: {exc}; retrying', flush=True)
            time.sleep(2 ** attempt)


def parse_acm(raw):
    import pandas as pd
    book = pd.ExcelFile(io.BytesIO(raw), engine='calamine')
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


def parse_treasury(raw):
    """Official Treasury Atom/OData feed: NEW_DATE and BC_10YEAR, percent."""
    root = ET.fromstring(raw)
    rows = []
    for properties in root.findall('.//{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}properties'):
        values = {node.tag.split('}')[-1]: node.text for node in properties}
        if 'NEW_DATE' not in values or 'BC_10YEAR' not in values:
            raise ValueError('Treasury XML schema changed: expected NEW_DATE and BC_10YEAR')
        if values['BC_10YEAR'] not in (None, '', 'N/A'):
            rows.append((values['NEW_DATE'][:10], float(values['BC_10YEAR'])))
    if not rows:
        raise ValueError('Treasury XML contains no daily 10-year yields')
    return rows


def fetch_yields(gold, today):
    """Use one complete provider per refresh; never blend feeds or fill gaps."""
    try:
        yields = monthly_last(parse_yields(download(FRED_URL)), today)
        if len(yields.keys() & gold.keys()) < 37:
            raise ValueError('FRED returned insufficient GLD-overlapping yield history')
        return yields, {'url': FRED_URL, 'name': 'FRED DGS10', 'columns': ['observation_date or DATE', 'DGS10']}
    except Exception as exc:
        reason = str(exc)
        print(f'WARNING: FRED unavailable: {reason}. Trying official Treasury daily par yields.', flush=True)
    # Treasury publishes the 10-year constant-maturity par yield directly.
    # This is an explicit alternative source, not a relabelled FRED response.
    years = sorted({int(month[:4]) for month in gold})
    raw_rows, urls = [], []
    for year in years:
        url = TREASURY_URL.format(year=year)
        urls.append(url)
        raw_rows.extend(parse_treasury(download(url)))
    yields = monthly_last(raw_rows, today)
    if len(yields.keys() & gold.keys()) < 37:
        raise ValueError('Treasury fallback returned insufficient GLD-overlapping yield history')
    return yields, {'url': 'https://home.treasury.gov/resource-center-data-chart-center/interest-rates',
                    'urls': urls, 'name': 'U.S. Treasury daily 10-year par yield',
                    'columns': ['NEW_DATE', 'BC_10YEAR'], 'fallback_reason': reason,
                    'note': 'Official Treasury alternative to FRED DGS10; not a FRED download. No mixing of providers.'}


def write_json(path, payload):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def main():
    now = datetime.now(timezone.utc)
    try:
        # Inspect actual source schemas on every refresh; fail rather than guess.
        acm = monthly_last(parse_acm(download(ACM_URL)), now.date())
        prices = json.loads((ROOT / 'data.json').read_text(encoding='utf-8'))
        gold = monthly_last([(r['date'], float(r['gld'])) for r in prices['prices']], now.date())
        if len(gold) < 37:
            raise ValueError('Insufficient completed-month GLD price history')
        yields, yield_source = fetch_yields(gold, now.date())
        observations = align(acm, yields, gold)
        if len(observations) < 37:
            raise ValueError(f'Insufficient aligned history: {len(observations)} months')
        finding = discover_window(observations)
        payload = {
            'schema_version': 1, 'generated_at': now.isoformat(timespec='seconds'),
            'last_observation_date': observations[-1]['acm_date'],
            'frequency': 'Completed calendar months; last available observation; inner join on month',
            'sources': {'acm': {'url': ACM_URL, 'sheet': 'ACM Monthly', 'columns': ['DATE', 'ACMTP10']},
                        'yield': yield_source,
                        'gold': {'file': 'data.json', 'source': prices['source'], 'fetched_at': prices['fetched_at']}},
            'definitions': {'acm_term_premium_pct': 'NY Fed ACM estimated 10-year term premium, percent annualized',
                            'modified_duration_years': 'Hypothetical fresh 10-year semiannual par Treasury; years',
                            'gld_adjusted_close_usd': 'GLD ETF adjusted close, USD; not spot gold'},
            'assumptions': ['Face 100; 20 half-year cash flows; annual coupon equals selected 10-year yield / 100.',
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
