"""Pure calculations shared by ingestion and its offline tests."""
import math
from datetime import date


def par_bond(yield_pct):
    y = yield_pct / 100
    if not math.isfinite(y) or y <= -2:
        raise ValueError('Invalid annual yield')
    pv = [(100 * y / 2 + (100 if t == 20 else 0)) / (1 + y / 2) ** t
          for t in range(1, 21)]
    price = sum(pv)
    return price, sum((t / 2) * v for t, v in enumerate(pv, 1)) / price / (1 + y / 2)


def month_number(month):
    return int(month[:4]) * 12 + int(month[5:7])


def monthly_last(rows, today=None):
    """Keep last finite value per completed month; never forward-fill."""
    today = today or date.today()
    result = {}
    for day, value in sorted(rows):
        d = date.fromisoformat(day)
        if day[:7] >= today.strftime('%Y-%m') or not math.isfinite(value):
            continue
        result[day[:7]] = (d.isoformat(), value)
    return result


def align(acm, yields, gold):
    result = []
    for month in sorted(acm.keys() & yields.keys() & gold.keys()):
        ad, tp = acm[month]
        yd, y = yields[month]
        gd, g = gold[month]
        if g <= 0:
            raise ValueError('GLD adjusted price must be positive')
        result.append(dict(month=month, acm_date=ad, treasury_yield_date=yd,
                           acm_term_premium_pct=tp, treasury_10y_yield_pct=y,
                           modified_duration_years=par_bond(y)[1],
                           gld_price_date=gd, gld_adjusted_close_usd=g))
    return result


def window_metrics(a, b):
    return {'term_premium_change_bps': (b['acm_term_premium_pct'] - a['acm_term_premium_pct']) * 100,
            'gld_return_pct': (b['gld_adjusted_close_usd'] / a['gld_adjusted_close_usd'] - 1) * 100}


def discover_window(rows):
    """Largest absolute six-calendar-month ACM move; GLD does not affect selection."""
    candidates = []
    for i in range(len(rows) - 6):
        chunk = rows[i:i + 7]
        if all(month_number(b['month']) - month_number(a['month']) == 1
               for a, b in zip(chunk, chunk[1:])):
            candidates.append((i, i + 6))
    if not candidates:
        raise ValueError('Insufficient consecutive observations for a six-month finding')
    i, j = max(candidates, key=lambda pair: abs(window_metrics(rows[pair[0]], rows[pair[1]])['term_premium_change_bps']))
    return {'start_month': rows[i]['month'], 'end_month': rows[j]['month'],
            'candidate_count': len(candidates), **window_metrics(rows[i], rows[j])}
