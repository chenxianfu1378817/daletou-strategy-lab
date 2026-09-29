import unittest

from daletou_lab.rules import RuleRegistry
from daletou_lab.source import SHANGHAI_SOURCE, _parse_shanghai_draw, parse_item


DRAW_26090 = {
    "ret": True,
    "data": {
        "lotId": "dlt",
        "issueNo": "26090",
        "bonusCode": "09,14,17,19,24#02,09",
        "bonusDate": "2026-08-10",
        "bonusList": [
            {"name": "一等奖", "amount": "2", "money": "10,000,000"},
            {"name": "一等奖追加", "amount": "0", "money": ""},
            {"name": "二等奖", "amount": "93", "money": "155,846"},
            {"name": "二等奖追加", "amount": "32", "money": "124,677"},
            {"name": "三等奖", "amount": "1169", "money": "6,666"},
            {"name": "四等奖", "amount": "16783", "money": "380"},
            {"name": "五等奖", "amount": "66157", "money": "200"},
            {"name": "六等奖", "amount": "818960", "money": "18"},
            {"name": "七等奖", "amount": "8260921", "money": "7"},
        ],
    },
}


class ShanghaiSourceTests(unittest.TestCase):
    def test_real_official_draw_preserves_numbers_and_all_prizes(self):
        item = _parse_shanghai_draw("26090", DRAW_26090)
        draw, prizes = parse_item(item, RuleRegistry(), "2026-09-29T00:00:00+00:00")
        self.assertEqual(draw.front, (9, 14, 17, 19, 24))
        self.assertEqual(draw.back, (2, 9))
        self.assertEqual(draw.source, SHANGHAI_SOURCE)
        self.assertIsNone(draw.sales_amount)
        self.assertEqual(len(prizes), 9)
        self.assertEqual((prizes[0]["winning_count"], prizes[0]["prize_per_ticket"]), (2, 10_000_000))
        self.assertEqual((prizes[1]["additional"], prizes[1]["winning_count"], prizes[1]["prize_per_ticket"]), (True, 0, 0))

    def test_rejects_wrong_issue_and_malformed_numbers(self):
        with self.assertRaisesRegex(ValueError, "does not match issue"):
            _parse_shanghai_draw("26091", DRAW_26090)
        bad = {"ret": True, "data": {**DRAW_26090["data"], "bonusCode": "09,09,17,19,24#02,09"}}
        with self.assertRaisesRegex(ValueError, "invalid winning numbers"):
            _parse_shanghai_draw("26090", bad)


if __name__ == "__main__":
    unittest.main()
