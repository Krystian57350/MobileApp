"""Uruchomienie: python -m unittest discover -s raporty/tests -t .   (z folderu projektu)"""
import unittest
from datetime import date

from raporty.models import Subscription
from raporty.payments import charge_dates
from raporty.periods import build_buckets
from raporty.report import build_report
from raporty.stats import describe


def sub(name, cost, period="monthly", start=date(2025, 1, 5), nxt=None, cat="A", active=True, end=None):
    return Subscription(name, name, cost, period, nxt or start, cat, active, start, end)


class PeriodsTest(unittest.TestCase):
    def test_quarters_and_halves(self):
        q = build_buckets(date(2025, 2, 10), date(2025, 8, 1), "quarter")
        self.assertEqual([b.label for b in q], ["Q1 2025", "Q2 2025", "Q3 2025"])
        h = build_buckets(date(2025, 2, 10), date(2026, 1, 1), "half")
        self.assertEqual([b.label for b in h], ["I poł. 2025", "II poł. 2025", "I poł. 2026"])

    def test_bad_range(self):
        with self.assertRaises(ValueError):
            build_buckets(date(2025, 5, 1), date(2025, 1, 1), "month")


class PaymentsTest(unittest.TestCase):
    def test_day_31_is_clamped(self):
        s = sub("x", 10, start=date(2025, 1, 1), nxt=date(2025, 1, 31))
        days = [d for d in charge_dates(s, date(2025, 3, 31)) if d.month == 2]
        self.assertEqual(days, [date(2025, 2, 28)])

    def test_yearly_counts_once_per_year(self):
        s = sub("y", 120, "yearly", start=date(2024, 3, 1), nxt=date(2025, 6, 10))
        self.assertEqual(list(charge_dates(s, date(2026, 12, 31))), [date(2024, 6, 10), date(2025, 6, 10), date(2026, 6, 10)])

    def test_inactive_stops_at_end_date(self):
        s = sub("m", 10, start=date(2025, 1, 1), nxt=date(2025, 1, 10), active=False, end=date(2025, 3, 15))
        self.assertEqual(len(list(charge_dates(s, date(2025, 12, 31)))), 3)

    def test_inactive_without_end_is_skipped(self):
        self.assertEqual(list(charge_dates(sub("m", 10, active=False), date(2025, 12, 31))), [])


class StatsRulesTest(unittest.TestCase):
    def test_no_periods(self):
        r = describe([], [])
        self.assertIsNone(r["mean"]); self.assertTrue(r["notes"])

    def test_one_period_no_mean(self):
        r = describe([100], ["a"])
        self.assertIsNone(r["mean"]); self.assertEqual(r["total"], 100)

    def test_two_periods_mean_but_no_median(self):
        r = describe([100, 200], ["a", "b"])
        self.assertEqual(r["mean"], 150); self.assertIsNone(r["median"])

    def test_three_periods_full(self):
        r = describe([100, 100, 400], ["a", "b", "c"])
        self.assertEqual(r["mean"], 200); self.assertEqual(r["median"], 100)
        self.assertTrue(r["irregular"])        # roczna płatność zniekształca średnią
        self.assertIsNone(r["trend_per_period"])

    def test_trend_from_four(self):
        r = describe([10, 20, 30, 40], list("abcd"))
        self.assertEqual(r["trend_per_period"], 10)

    def test_all_zero_means_no_mean(self):
        self.assertIsNone(describe([0, 0, 0], list("abc"))["mean"])


class ReportTest(unittest.TestCase):
    TODAY = date(2026, 3, 20)

    def subs(self):
        return [sub("Netflix", 40, start=date(2025, 7, 3), cat="Wideo"),
                sub("HBO", 30, start=date(2025, 9, 3), cat="Wideo"),
                sub("Antywirus", 120, "yearly", start=date(2025, 7, 3), nxt=date(2026, 2, 14), cat="Aplikacje")]

    def test_monthly_report_excludes_partial_from_stats(self):
        r = build_report(self.subs(), "month", today=self.TODAY)
        labels = {b["label"]: b for b in r["buckets"]}
        self.assertEqual(r["buckets"][-1]["status"], "in_progress")
        self.assertFalse(labels["mar 2026"]["complete"])
        self.assertEqual(r["stats"]["n"], len([b for b in r["buckets"] if b["complete"]]))
        self.assertEqual(labels["lut 2026"]["total"], 190)           # 40 + 30 + 120 (płatność roczna)
        self.assertTrue(r["stats"]["irregular"])

    def test_change_pct_between_complete_neighbours(self):
        r = build_report(self.subs(), "month", today=self.TODAY)
        b = {x["label"]: x for x in r["buckets"]}
        self.assertEqual(b["wrz 2025"]["change_pct"], 75.0)          # 40 -> 70

    def test_custom_range(self):
        r = build_report(self.subs(), "quarter", date(2025, 10, 1), date(2026, 1, 31), self.TODAY)
        self.assertEqual([b["label"] for b in r["buckets"]], ["Q4 2025", "Q1 2026"])

    def test_custom_range_clips_partial_month_quarter_and_year(self):
        subscription = sub("Monthly", 10, start=date(2025, 1, 1), nxt=date(2025, 1, 10))
        date_from, date_to, today = date(2025, 2, 15), date(2025, 5, 15), date(2025, 6, 20)
        expected = {
            "month": ([0, 10, 10, 10], ["partial_range", "complete", "complete", "partial_range"], 2),
            "quarter": ([10, 20], ["partial_range", "partial_range"], 0),
            "year": ([30], ["partial_range"], 0),
        }

        for granularity, (totals, statuses, complete_periods) in expected.items():
            with self.subTest(granularity=granularity):
                report = build_report([subscription], granularity, date_from, date_to, today)
                self.assertEqual([b["total"] for b in report["buckets"]], totals)
                self.assertEqual([b["status"] for b in report["buckets"]], statuses)
                self.assertEqual(report["stats"]["n"], complete_periods)
                self.assertEqual(report["summary"]["total_range"], 30)

    def test_no_subscriptions(self):
        r = build_report([], "month", today=self.TODAY)
        self.assertEqual(r["buckets"], []); self.assertTrue(r["warnings"])

    def test_insights_overlap_detected(self):
        r = build_report(self.subs(), "month", today=self.TODAY)
        self.assertTrue(any("Wideo" in t and "2" in t for t in r["insights"]))


if __name__ == "__main__":
    unittest.main()
