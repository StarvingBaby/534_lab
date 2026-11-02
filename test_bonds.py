"""Offline calculation/edge-case tests. Fixtures are synthetic test inputs only."""
import json
import math
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import fetch_bond_data as fetcher
from bond_math import align, discover_window, monthly_last, par_bond, window_metrics


class BondsTests(unittest.TestCase):
    def test_par_price_and_duration(self):
        for y in (0, 0.5, 2, 5, 10):
            price, duration = par_bond(y)
            self.assertAlmostEqual(price, 100, places=10)
            self.assertGreater(duration, 0)
            self.assertLessEqual(duration, 10)
        self.assertAlmostEqual(par_bond(0)[1], 10)
        self.assertGreater(par_bond(2)[1], par_bond(5)[1])

    def test_duration_independent_closed_form_and_shock(self):
        y = .04
        expected = (1 - (1 + y / 2) ** -20) / y
        duration = par_bond(4)[1]
        self.assertAlmostEqual(duration, expected, places=10)
        self.assertLess(-duration * .01, 0)
        # Reprice the original 4% coupon bond at 4.0001% (do not reset coupon).
        price = sum((2 + (100 if t == 20 else 0)) / (1 + .040001 / 2) ** t for t in range(1, 21))
        self.assertAlmostEqual((price / 100 - 1) / .000001, -duration, places=3)

    def test_invalid_yields(self):
        for y in (math.nan, math.inf, -200):
            with self.assertRaises(ValueError):
                par_bond(y)

    def test_month_end_no_fill_and_no_partial_month(self):
        result = monthly_last([('2024-01-30', 4), ('2024-01-31', 4.1),
                               ('2024-03-28', 4.2), ('2024-03-29', math.nan),
                               ('2024-04-01', 5)], date(2024, 4, 2))
        self.assertEqual(result, {'2024-01': ('2024-01-31', 4.1), '2024-03': ('2024-03-28', 4.2)})

    def test_align_preserves_distinct_dates_and_zero_premium(self):
        rows = align({'2024-03': ('2024-03-31', 0)}, {'2024-03': ('2024-03-28', 4)},
                     {'2024-03': ('2024-03-28', 200), '2024-02': ('2024-02-29', 190)})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['gld_price_date'], '2024-03-28')
        self.assertEqual(rows[0]['acm_term_premium_pct'], 0)
        self.assertEqual(align({}, {}, {}), [])
        with self.assertRaises(ValueError):
            align({'2024-03': ('2024-03-31', 0)}, {'2024-03': ('2024-03-28', 4)}, {'2024-03': ('2024-03-28', 0)})

    def test_metrics_units(self):
        m = window_metrics({'acm_term_premium_pct': -.4, 'gld_adjusted_close_usd': 200},
                           {'acm_term_premium_pct': .3, 'gld_adjusted_close_usd': 220})
        self.assertAlmostEqual(m['term_premium_change_bps'], 70)
        self.assertAlmostEqual(m['gld_return_pct'], 10)

    def test_discovery_ignores_gold_and_rejects_gaps(self):
        rows = [{'month': f'2024-{m:02d}', 'acm_term_premium_pct': m ** 2 / 100,
                 'gld_adjusted_close_usd': 200 + m} for m in range(1, 10)]
        self.assertEqual(discover_window(rows)['start_month'], '2024-03')
        self.assertEqual(discover_window(rows)['candidate_count'], 3)
        for r in rows:
            r['gld_adjusted_close_usd'] *= 10
        self.assertEqual(discover_window(rows)['start_month'], '2024-03')
        with self.assertRaises(ValueError):
            discover_window(rows[:3] + rows[4:])

    def test_fred_formats_and_missing_values(self):
        self.assertEqual(fetcher.parse_yields(b'observation_date,DGS10\n2024-01-01,.\n2024-01-02,4.0\n'), [('2024-01-02', 4.0)])
        self.assertEqual(fetcher.parse_yields(b'DATE,DGS10\n2024-01-02,0\n'), [('2024-01-02', 0)])
        with self.assertRaises(ValueError):
            fetcher.parse_yields(b'<html>error</html>')

    def test_failed_first_refresh_reports_error(self):
        with tempfile.TemporaryDirectory() as folder:
            status = Path(folder) / 'status.json'
            with patch.object(fetcher, 'OUT', Path(folder) / 'missing.json'), patch.object(fetcher, 'STATUS', status), patch.object(fetcher, 'download', side_effect=RuntimeError('test source unavailable')):
                with self.assertRaises(RuntimeError):
                    fetcher.main()
                self.assertFalse(json.loads(status.read_text())['ok'])

    def test_failed_refresh_keeps_cache_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            out, status = Path(folder) / 'bonds.json', Path(folder) / 'status.json'
            rows = [{'month': f'{2020 + i // 12}-{i % 12 + 1:02d}', 'acm_term_premium_pct': i / 100,
                     'gld_adjusted_close_usd': 200 + i} for i in range(37)]
            content = json.dumps({'observations': rows})
            out.write_text(content)
            with patch.object(fetcher, 'OUT', out), patch.object(fetcher, 'STATUS', status), patch.object(fetcher, 'download', side_effect=RuntimeError('test source unavailable')):
                fetcher.main()
            self.assertEqual(out.read_text(), content)
            self.assertFalse(json.loads(status.read_text())['ok'])


if __name__ == '__main__':
    unittest.main()
