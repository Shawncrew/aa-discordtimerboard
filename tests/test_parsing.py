import datetime as dt
import unittest

from django.utils import timezone

from discordtimerboard.parsing import parse_add_input


class TestParseAddInput(unittest.TestCase):
    def test_parse_direct_format(self):
        parsed = parse_add_input(
            "2026-04-23 19:15:59 CL6-ZG - Microplastic of Pure Blind [INIT][ASTRA][FINAL]"
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "CL6-ZG")
        self.assertEqual(parsed.structure_name, "Microplastic of Pure Blind")
        self.assertEqual(parsed.tags, ["INIT", "ASTRA", "FINAL"])

    def test_parse_multiline_reinforced_format(self):
        raw = "\n".join(
            [
                "RD-G2R - Neutral States",
                "38.4 AU",
                "Reinforced until 2026.04.23 22:43:31 [INIT][FORT][ARMOR]",
            ]
        )
        parsed = parse_add_input(raw)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "RD-G2R")
        self.assertEqual(parsed.structure_name, "Neutral States")
        self.assertEqual(parsed.tags, ["INIT", "FORT", "ARMOR"])

    def test_parse_customs_office_line(self):
        raw = "\n".join(
            [
                "Customs Office (DT-TCD IX) [NC]",
                "5.1 AU",
                "Reinforced until 2026.04.24 10:01:00 [NC][POCO][FINAL]",
            ]
        )
        parsed = parse_add_input(raw)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "DT-TCD")
        self.assertEqual(parsed.structure_name, "Customs Office Planet IX")

    def test_parse_merc_den_relative_format(self):
        now_utc = timezone.make_aware(dt.datetime(2026, 4, 23, 10, 0, 0), dt.timezone.utc)
        parsed = parse_add_input(
            "Merc Den MQ-NPY Planet I 2 30 [NC]",
            now_utc=now_utc,
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "MQ-NPY")
        self.assertEqual(parsed.structure_name, "Mercenary Den Planet I")
        self.assertEqual(parsed.tags, ["NC", "MERCENARY DEN", "FINAL"])
        self.assertEqual(parsed.timer_time, now_utc + dt.timedelta(hours=2, minutes=30))
