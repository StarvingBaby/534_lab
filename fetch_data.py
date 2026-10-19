"""Fetch adjusted daily prices for SPY/GLD and publish aligned monthly closes.
Run with: python fetch_data.py
"""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

OUT = Path(__file__).with_name('data.json')
SYMBOLS = ('SPY', 'GLD')


def get_adjusted_daily(symbol):
    df = yf.download(symbol, period='6y', interval='1d', auto_adjust=True,
                     progress=False, threads=False, multi_level_index=False, timeout=25)
    if df is None or df.empty or 'Close' not in df.columns:
        raise RuntimeError(f'{symbol}: no prices returned')
    series = pd.to_numeric(df['Close'], errors='coerce').dropna()
    series.index = pd.to_datetime(series.index).tz_localize(None).normalize()
    if len(series) < 300:
        raise RuntimeError(f'{symbol}: insufficient daily history ({len(series)})')
    return series


def main():
    try:
        prices = pd.concat({s: get_adjusted_daily(s) for s in SYMBOLS}, axis=1).dropna()
        # Align month-end on the *same trading day* shared by both ETFs.
        month_keys = prices.index.to_period('M')
        monthly = prices.groupby(month_keys).tail(1).tail(73)
        if len(monthly) < 61:
            raise RuntimeError(f'Insufficient aligned months: {len(monthly)}')
        records = [
            {'date': dt.date().isoformat(), 'spy': round(float(row['SPY']), 5),
             'gld': round(float(row['GLD']), 5)}
            for dt, row in monthly.iterrows()
            if all(math.isfinite(float(row[s])) and float(row[s]) > 0 for s in SYMBOLS)
        ]
        if len(records) < 61:
            raise RuntimeError('Too few valid price observations')
        payload = {
            'source': 'Yahoo Finance via yfinance',
            'price_type': 'Adjusted closing prices (auto_adjust=True)',
            'frequency': 'Monthly last common trading date',
            'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'symbols': {'spy': 'SPY - SPDR S&P 500 ETF Trust',
                        'gld': 'GLD - SPDR Gold Shares'},
            'prices': records,
        }
        OUT.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
        print(f'Updated {OUT}: {len(records)} months, {records[0]["date"]} - {records[-1]["date"]}')
    except Exception as exc:
        if OUT.exists():
            try:
                old = json.loads(OUT.read_text(encoding='utf-8'))
                if len(old.get('prices', [])) >= 61:
                    print(f'WARNING: refresh failed ({exc}); retaining previously verified data.json')
                    return
            except Exception:
                pass
        raise RuntimeError(f'Unable to update data and no valid cache exists: {exc}') from exc


if __name__ == '__main__':
    main()
