import unittest
from datetime import date

from daletou_lab.atomic import AtomicBet, MultipleBet
from daletou_lab.prize import settle_atomic, settle_portfolio, tax_for_issue
from daletou_lab.rules import RuleRegistry


class PrizeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rule = RuleRegistry().current()
        cls.winning_front = (1, 2, 3, 4, 5)
        cls.winning_back = (1, 2)
        cls.realized = {1: 5_000_000, 2: 100_000, 3: 5000, 4: 300, 5: 150, 6: 15, 7: 5}

    def settle(self, front, back, additional=False, pool=100_000_000):
        return settle_atomic(AtomicBet(front, back, additional), self.winning_front, self.winning_back, self.rule, self.realized, pool)

    def test_first_prize(self):
        self.assertEqual(self.settle((1, 2, 3, 4, 5), (1, 2)).level, 1)

    def test_second_prize(self):
        self.assertEqual(self.settle((1, 2, 3, 4, 5), (1, 3)).level, 2)

    def test_third_prize_two_patterns(self):
        self.assertEqual(self.settle((1, 2, 3, 4, 5), (3, 4)).level, 3)
        self.assertEqual(self.settle((1, 2, 3, 4, 6), (1, 2)).level, 3)

    def test_fourth_prize(self):
        self.assertEqual(self.settle((1, 2, 3, 4, 6), (1, 3)).level, 4)

    def test_fifth_prize(self):
        self.assertEqual(self.settle((1, 2, 3, 4, 6), (3, 4)).level, 5)

    def test_sixth_prize(self):
        self.assertEqual(self.settle((1, 2, 3, 6, 7), (1, 3)).level, 6)

    def test_seventh_prize(self):
        self.assertEqual(self.settle((6, 7, 8, 9, 10), (1, 2)).level, 7)

    def test_no_prize(self):
        self.assertIsNone(self.settle((6, 7, 8, 9, 10), (3, 4)).level)

    def test_additional_only_float(self):
        first = self.settle((1, 2, 3, 4, 5), (1, 2), True)
        third = self.settle((1, 2, 3, 4, 5), (3, 4), True)
        self.assertEqual(first.additional_prize, 4_000_000)
        self.assertEqual(third.additional_prize, 0)

    def test_high_pool_fixed_amount(self):
        result = settle_atomic(
            AtomicBet((1, 2, 3, 4, 5), (3, 4)),
            self.winning_front,
            self.winning_back,
            self.rule,
            None,
            800_000_000,
        )
        self.assertEqual(result.base_prize, 6666)

    def test_tax_threshold(self):
        self.assertEqual(tax_for_issue(10_000, date(2026, 1, 1)), 0)
        self.assertEqual(tax_for_issue(10_001, date(2026, 1, 1)), 2000)

    def test_compound_multiple_awards(self):
        atoms = list(MultipleBet((1, 2, 3, 4, 5, 6), (1, 2, 3)).expand(self.rule))
        settled = settle_portfolio(atoms, self.winning_front, self.winning_back, self.rule, date(2026, 1, 1), self.realized)
        self.assertGreater(settled["gross_prize"], 5_000_000)


if __name__ == "__main__":
    unittest.main()

