import datetime as dt
import unittest

from django.utils import timezone

from discordtimerboard.parsing import parse_add_input


class TestParseAddInput(unittest.TestCase):
    def test_parse_timerboard_output_plain(self):
        """Copy-paste from timerboard channel without markdown link."""
        parsed = parse_add_input(
            "2026-04-23 19:15:59 CL6-ZG (Pure Blind) Microplastic of Pure Blind [INIT][ASTRA][FINAL] (5292)"
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "CL6-ZG")
        self.assertEqual(parsed.structure_name, "Microplastic of Pure Blind")
        self.assertEqual(parsed.tags, ["INIT", "ASTRA", "FINAL"])

    def test_parse_timerboard_output_with_markdown_link(self):
        """Copy-paste where Discord preserves the markdown link syntax."""
        parsed = parse_add_input(
            "2026-04-23 19:15:59 [CL6-ZG](<https://evemaps.dotlan.net/system/CL6-ZG>) (Pure Blind) Microplastic of Pure Blind [INIT][ASTRA][FINAL] (5292)"
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "CL6-ZG")
        self.assertEqual(parsed.structure_name, "Microplastic of Pure Blind")
        self.assertEqual(parsed.tags, ["INIT", "ASTRA", "FINAL"])

    def test_parse_timerboard_output_spaced_tags(self):
        """Tags with spaces between them as shown in the example."""
        parsed = parse_add_input(
            "2026-04-23 19:15:59 CL6-ZG (Pure Blind) Microplastic of Pure Blind [INIT] [ASTRA] [FINAL] (5292)"
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "CL6-ZG")
        self.assertEqual(parsed.structure_name, "Microplastic of Pure Blind")
        self.assertEqual(parsed.tags, ["INIT", "ASTRA", "FINAL"])

    def test_parse_timerboard_output_plain(self):
        parsed = parse_add_input(
            "2026-04-23 19:15:59 CL6-ZG (Pure Blind) Microplastic of Pure Blind [INIT][ASTRA][FINAL] (5292)"
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "CL6-ZG")
        self.assertEqual(parsed.structure_name, "Microplastic of Pure Blind")
        self.assertEqual(parsed.tags, ["INIT", "ASTRA", "FINAL"])

    def test_parse_timerboard_output_markdown_link(self):
        """Discord client preserves raw markdown link syntax on copy."""
        parsed = parse_add_input(
            "2026-04-23 19:15:59 [CL6-ZG](<https://evemaps.dotlan.net/system/CL6-ZG>) (Pure Blind) Microplastic of Pure Blind [INIT][ASTRA][FINAL] (5292)"
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "CL6-ZG")
        self.assertEqual(parsed.structure_name, "Microplastic of Pure Blind")
        self.assertEqual(parsed.tags, ["INIT", "ASTRA", "FINAL"])

    def test_parse_timerboard_output_spaced_tags(self):
        """Tags with spaces between them."""
        parsed = parse_add_input(
            "2026-04-23 19:15:59 CL6-ZG (Pure Blind) Microplastic of Pure Blind [INIT] [ASTRA] [FINAL] (5292)"
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "CL6-ZG")
        self.assertEqual(parsed.structure_name, "Microplastic of Pure Blind")
        self.assertEqual(parsed.tags, ["INIT", "ASTRA", "FINAL"])

    def test_parse_timerboard_output_no_region(self):
        """Timer with no region resolved."""
        parsed = parse_add_input(
            "2026-04-23 19:15:59 CL6-ZG Microplastic of Pure Blind [INIT][ASTRA][FINAL] (5292)"
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "CL6-ZG")
        self.assertEqual(parsed.structure_name, "Microplastic of Pure Blind")

    def test_parse_timerboard_output_no_id(self):
        """Timerboard line without trailing id (manually typed)."""
        parsed = parse_add_input(
            "2026-04-23 19:15:59 CL6-ZG (Pure Blind) Microplastic of Pure Blind [INIT][ASTRA][FINAL]"
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "CL6-ZG")
        self.assertEqual(parsed.structure_name, "Microplastic of Pure Blind")

    def test_parse_timerboard_output_ihub(self):
        """IHUB timer with no owner tag."""
        parsed = parse_add_input(
            "2026-04-23 19:15:59 CL6-ZG (Pure Blind) Infrastructure Hub [IHUB][FINAL] (100)"
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "CL6-ZG")
        self.assertEqual(parsed.structure_name, "Infrastructure Hub")
        self.assertEqual(parsed.tags, ["IHUB", "FINAL"])

    def test_parse_timerboard_output_mercenary_den(self):
        """Mercenary Den timer with multi-word structure tag."""
        parsed = parse_add_input(
            "2026-04-23 19:15:59 MQ-NPY (Pure Blind) Mercenary Den Planet I [NC][MERCENARY DEN][FINAL] (51)"
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "MQ-NPY")
        self.assertEqual(parsed.structure_name, "Mercenary Den Planet I")
        self.assertEqual(parsed.tags, ["NC", "MERCENARY DEN", "FINAL"])

    def test_parse_timerboard_output_skyhook(self):
        parsed = parse_add_input(
            "2026-04-24 10:01:36 MQ-NPY (Pure Blind) Orbital Skyhook [Best Friends Forever][Skyhook][FINAL] (50)"
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "MQ-NPY")
        self.assertEqual(parsed.structure_name, "Orbital Skyhook")
        self.assertEqual(parsed.tags, ["Best Friends Forever", "Skyhook", "FINAL"])

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

    def test_parse_ansiblex_multiline_reinforced(self):
        """Ansiblex gate pasted from in-game: the system must not be split on its hyphen.

        The gate name has no ' - ' between system and structure, so the dash rule used to
        backtrack into the hyphen of '6RCQ-V' and report 'Unknown solar system: 6RCQ'.
        """
        raw = "\n".join(
            [
                "6RCQ-V \u00bb 9-4RP2 - Edgy Ansiblex Name",
                "0 m",
                "Reinforced until 2026.08.25 19:53:31 [BDNUT][ANSIBLEX][HULL]",
            ]
        )
        parsed = parse_add_input(raw)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "6RCQ-V")
        self.assertEqual(parsed.structure_name, "6RCQ-V \u00bb 9-4RP2 - Edgy Ansiblex Name")
        self.assertEqual(parsed.tags, ["BDNUT", "ANSIBLEX", "HULL"])
        self.assertEqual(
            parsed.timer_time,
            timezone.make_aware(dt.datetime(2026, 8, 25, 19, 53, 31), dt.timezone.utc),
        )

    def test_parse_ansiblex_single_line_reinforced(self):
        parsed = parse_add_input(
            "6RCQ-V \u00bb 9-4RP2 - Edgy Ansiblex Name "
            "Reinforced until 2026.08.25 19:53:31 [BDNUT][ANSIBLEX][HULL]"
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "6RCQ-V")
        self.assertEqual(parsed.tags, ["BDNUT", "ANSIBLEX", "HULL"])

    def test_parse_ansiblex_ascii_arrow(self):
        """Some people type >> rather than the in-game » character."""
        raw = "\n".join(
            [
                "6RCQ-V >> 9-4RP2 - Edgy Ansiblex Name",
                "Reinforced until 2026.08.25 19:53:31 [BDNUT][ANSIBLEX][HULL]",
            ]
        )
        parsed = parse_add_input(raw)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "6RCQ-V")

    def test_parse_ansiblex_from_timerboard_copy_paste(self):
        """The board renders the gate name in full; pasting that line back must round-trip."""
        parsed = parse_add_input(
            "2026-08-25 19:53:31 [6RCQ-V](<https://evemaps.dotlan.net/system/6RCQ-V>) "
            "(Tenal) 6RCQ-V \u00bb 9-4RP2 - Edgy Ansiblex Name [BDNUT][ANSIBLEX][HULL] (51)"
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "6RCQ-V")
        self.assertEqual(parsed.structure_name, "6RCQ-V \u00bb 9-4RP2 - Edgy Ansiblex Name")
        self.assertEqual(parsed.tags, ["BDNUT", "ANSIBLEX", "HULL"])

    def test_dash_format_still_wins_for_hyphenated_systems(self):
        """The Ansiblex rule must not disturb the ordinary 'SYSTEM - STRUCTURE' form."""
        parsed = parse_add_input(
            "M-OEE8 - Some Structure - With Dashes "
            "Reinforced until 2026.08.25 19:53:31 [NC][FORT][ARMOR]"
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.system, "M-OEE8")
        self.assertEqual(parsed.structure_name, "Some Structure - With Dashes")
