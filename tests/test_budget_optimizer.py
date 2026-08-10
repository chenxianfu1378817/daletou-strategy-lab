import unittest

from daletou_lab.budget import decide
from daletou_lab.models import ModelScores
from daletou_lab.optimizer import build_plan, overlap
from daletou_lab.rules import RuleRegistry


class BudgetOptimizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rule = RuleRegistry().current()
        cls.scores = ModelScores(
            front={n: n / 35 for n in range(1, 36)},
            back={n: n / 12 for n in range(1, 13)},
            uncertainty=0.7,
            diagnostics={},
        )

    def test_all_budgets_all_modes_never_exceed(self):
        for budget in (0, 20, 30, 40, 50, 60, 70, 80, 90, 100):
            for mode in ("智能推荐", "单式", "复式", "混合"):
                with self.subTest(budget=budget, mode=mode):
                    plan = build_plan(self.scores, self.rule, budget, mode, 42)
                    self.assertLessEqual(plan.cost, budget)
                    self.assertEqual(plan.cost + plan.unused_budget, budget)

    def test_invalid_negative_budget(self):
        with self.assertRaises(ValueError):
            build_plan(self.scores, self.rule, -1)

    def test_invalid_over_budget(self):
        with self.assertRaises(ValueError):
            build_plan(self.scores, self.rule, 101)

    def test_budget_is_cap_not_target(self):
        decision = decide(self.scores, self.rule, 100, evidence={})
        self.assertEqual(decision.decision, "SKIP")
        self.assertEqual(decision.suggested_amount, 0)

    def test_no_chasing_losses_input(self):
        decision = decide(self.scores, self.rule, 100, evidence={"loss_streak": 99})
        self.assertEqual(decision.suggested_amount, 0)

    def test_overlap_identity(self):
        plan = build_plan(self.scores, self.rule, 20, "单式", 1)
        self.assertTrue(overlap(plan.atomic_bets[0], plan.atomic_bets[0])["atomic_equal"])

    def test_coverage_uses_unique_atomic_bets(self):
        plan = build_plan(self.scores, self.rule, 100, "单式", 1)
        self.assertEqual(len(plan.atomic_bets), len(set(plan.atomic_bets)))


if __name__ == "__main__":
    unittest.main()

