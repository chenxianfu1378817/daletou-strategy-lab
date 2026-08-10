import tempfile
import unittest
from datetime import date
from pathlib import Path

from daletou_lab.backtest import HoldoutLock, _longest_losing_streak, _maximum_drawdown, summarize
from daletou_lab.database import Draw, connect, initialize
from daletou_lab.statistics import benjamini_hochberg, bootstrap_ci, permutation_test
from daletou_lab.simulation import PrizeScenarioEngine, uniform_draw
from daletou_lab.crowding import score_crowding
from daletou_lab.atomic import AtomicBet
from daletou_lab.rules import RuleRegistry
from daletou_lab.validation import validate_draws


def draw(issue="26014", front=(1, 2, 3, 4, 5), back=(1, 2), rule="rule_2026_26014"):
    return Draw(issue, "2026-02-02", front, back, rule_version=rule, source="test", fetched_at="now", verified=True)


class ValidationBacktestTests(unittest.TestCase):
    def test_valid_draw(self):
        self.assertEqual(validate_draws([draw()]), [])

    def test_duplicate_issue(self):
        warnings = validate_draws([draw(), draw()])
        self.assertIn("DUPLICATE_ISSUE", [item.code for item in warnings])

    def test_rule_mismatch(self):
        warnings = validate_draws([draw(rule="wrong")])
        self.assertIn("RULE_MISMATCH", [item.code for item in warnings])

    def test_invalid_numbers(self):
        warnings = validate_draws([draw(front=(1, 1, 3, 4, 5))])
        self.assertIn("INVALID_NUMBERS", [item.code for item in warnings])

    def test_drawdown(self):
        self.assertEqual(_maximum_drawdown([10, -3, -9, 4]), 12)

    def test_losing_streak(self):
        self.assertEqual(_longest_losing_streak([-1, -2, 3, -1]), 2)

    def test_holdout_once(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.db"
            initialize(path)
            lock = HoldoutLock(path)
            lock.lock("v1", "26070", "26089", "Ensemble_v1")
            lock.evaluate_once("v1", {"roi": -0.5})
            with self.assertRaises(RuntimeError):
                lock.evaluate_once("v1", {"roi": 1.0})

    def test_bootstrap_ci_order(self):
        low, high = bootstrap_ci([1, 2, 3, 4, 5], iterations=100, seed=1)
        self.assertLessEqual(low, high)

    def test_permutation_records_hypotheses(self):
        result = permutation_test([1, 2, 3], [0, 0, 0], iterations=100, hypotheses_tested=50)
        self.assertEqual(result.hypotheses_tested, 50)

    def test_bh_fdr(self):
        rejected = benjamini_hochberg([0.001, 0.02, 0.8])
        self.assertEqual(rejected, [True, True, False])

    def test_uniform_draw_matches_official_space(self):
        import random
        rule = RuleRegistry().current()
        front, back = uniform_draw(rule, random.Random(1))
        self.assertEqual((len(front), len(back)), (5, 2))
        self.assertTrue(all(1 <= number <= 35 for number in front))

    def test_prize_scenario_uses_supplied_history(self):
        import random
        engine = PrizeScenarioEngine([4_000_000, 5_000_000], [80_000])
        result = engine.sample(random.Random(1), {3: 5000})
        self.assertIn(result[1], (4_000_000, 5_000_000))
        self.assertEqual(result[2], 80_000)

    def test_crowding_is_proxy_only(self):
        result = score_crowding(AtomicBet((1, 2, 3, 4, 5), (6, 7)))
        self.assertTrue(result.arithmetic_sequence)
        self.assertIn("不代表真实投注人数", result.note)


if __name__ == "__main__":
    unittest.main()
