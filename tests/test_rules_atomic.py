import unittest

from daletou_lab.atomic import AtomicBet, MultipleBet, portfolio_cost
from daletou_lab.rules import RuleRegistry, validate_numbers


class RuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = RuleRegistry()
        cls.old = cls.registry.for_issue("25001")
        cls.current = cls.registry.for_issue("26014")

    def test_rule_switches_at_26014(self):
        self.assertEqual(self.registry.for_issue("26013").rule_version, "rule_2019_19019")
        self.assertEqual(self.current.rule_version, "rule_2026_26014")

    def test_official_number_space(self):
        self.assertEqual((self.current.front_pool, self.current.front_pick), (35, 5))
        self.assertEqual((self.current.back_pool, self.current.back_pick), (12, 2))

    def test_prices(self):
        self.assertEqual(self.current.base_price, 2)
        self.assertEqual(self.current.additional_price, 1)

    def test_valid_numbers(self):
        validate_numbers((1, 2, 3, 4, 35), (1, 12), self.current)

    def test_front_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_numbers((0, 2, 3, 4, 5), (1, 2), self.current)

    def test_back_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_numbers((1, 2, 3, 4, 5), (1, 13), self.current)

    def test_duplicates_rejected(self):
        with self.assertRaises(ValueError):
            validate_numbers((1, 1, 3, 4, 5), (1, 2), self.current)

    def test_new_level_mapping(self):
        self.assertEqual(self.current.prize_level_for(5, 0).level, 3)
        self.assertEqual(self.current.prize_level_for(4, 2).level, 3)
        self.assertEqual(self.current.prize_level_for(0, 2).level, 7)

    def test_old_level_mapping(self):
        self.assertEqual(self.old.prize_level_for(5, 0).level, 3)
        self.assertEqual(self.old.prize_level_for(4, 2).level, 4)
        self.assertEqual(self.old.prize_level_for(0, 2).level, 9)


class AtomicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rule = RuleRegistry().current()

    def test_atomic_sorting(self):
        bet = AtomicBet((5, 1, 4, 2, 3), (12, 1))
        self.assertEqual(bet.front, (1, 2, 3, 4, 5))
        self.assertEqual(bet.back, (1, 12))

    def test_base_cost(self):
        self.assertEqual(AtomicBet((1, 2, 3, 4, 5), (1, 2)).cost(self.rule), 2)

    def test_additional_cost(self):
        self.assertEqual(AtomicBet((1, 2, 3, 4, 5), (1, 2), True).cost(self.rule), 3)

    def test_front_multiple_count(self):
        self.assertEqual(MultipleBet((1, 2, 3, 4, 5, 6), (1, 2)).atomic_count(self.rule), 6)

    def test_back_multiple_count(self):
        self.assertEqual(MultipleBet((1, 2, 3, 4, 5), (1, 2, 3)).atomic_count(self.rule), 3)

    def test_double_multiple_count(self):
        self.assertEqual(MultipleBet((1, 2, 3, 4, 5, 6), (1, 2, 3)).atomic_count(self.rule), 18)

    def test_expand_unique(self):
        atoms = list(MultipleBet((1, 2, 3, 4, 5, 6), (1, 2, 3)).expand(self.rule))
        self.assertEqual(len(atoms), len(set(atoms)))

    def test_multiple_cost_matches_atomic(self):
        multiple = MultipleBet((1, 2, 3, 4, 5, 6), (1, 2, 3))
        self.assertEqual(multiple.cost(self.rule), portfolio_cost(multiple.expand(self.rule), self.rule))


if __name__ == "__main__":
    unittest.main()

