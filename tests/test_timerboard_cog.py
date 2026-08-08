import datetime as dt
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.utils import timezone

from discordtimerboard.cogs.timerboard import (
    HELP_TOPICS,
    STRUCTURE_ALIAS_TO_EVE_TYPE_NAME,
    TIMER_TYPE_TAG_TO_MODEL,
    DiscordTimerBoard,
    build_help_text,
    split_for_discord,
)
from discordtimerboard.parsing import ParsedTimerInput


class _FakeTimerModel:
    class Objective:
        UNDEFINED = "UN"

    class Visibility:
        UNRESTRICTED = "UN"

    objects = MagicMock()

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.pk = 9999
        self.user = None
        self.eve_character = None
        self.eve_corporation = None
        self.eve_alliance = None

    def save(self):
        return None


class TestDiscordTimerboardCog(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.cog = DiscordTimerBoard.__new__(DiscordTimerBoard)
        self.cog.bot = MagicMock()

    @patch("discordtimerboard.cogs.timerboard.timezone.localtime", side_effect=lambda x: x)
    def test_format_line(self, _mock_localtime):
        fake_region = SimpleNamespace(name="Pure Blind")
        fake_const = SimpleNamespace(eve_region=fake_region)
        fake_system = SimpleNamespace(name="CL6-ZG", eve_constellation=fake_const)
        fake_type = SimpleNamespace(name="Astrahus")
        fake_timer = SimpleNamespace(
            date=timezone.make_aware(dt.datetime(2026, 4, 23, 19, 15, 59), dt.timezone.utc),
            eve_solar_system_id=30000001,
            eve_solar_system=fake_system,
            structure_name="Microplastic of Pure Blind",
            structure_type=fake_type,
            structure_type_id=35832,
            owner_name="INIT",
            timer_type="FI",
            pk=5292,
            get_timer_type_display=lambda: "Final",
        )
        line = self.cog._format_line(fake_timer)
        self.assertIn("2026-04-23 19:15:59", line)
        self.assertIn("CL6-ZG (Pure Blind) Microplastic of Pure Blind", line)
        self.assertIn("[INIT][ASTRA][FINAL] (5292)", line)

    @patch("discordtimerboard.cogs.timerboard.get_auth_user", side_effect=Exception("no auth"))
    @patch("discordtimerboard.cogs.timerboard.apps.get_model", return_value=_FakeTimerModel)
    @patch("discordtimerboard.cogs.timerboard.EveSolarSystem")
    def test_create_timer_from_parsed(self, mock_system_model, _mock_get_model, _mock_auth):
        _FakeTimerModel.objects.reset_mock()
        _FakeTimerModel.objects.filter.return_value.first.return_value = None
        mock_system_model.objects.filter.return_value.first.return_value = SimpleNamespace(name="CL6-ZG")
        self.cog._resolve_structure_type = MagicMock(return_value=SimpleNamespace(name="Astrahus"))

        parsed = ParsedTimerInput(
            timer_time=timezone.make_aware(dt.datetime(2026, 4, 23, 19, 15, 59), dt.timezone.utc),
            system="CL6-ZG",
            structure_name="Microplastic of Pure Blind",
            tags=["INIT", "ASTRA", "FINAL"],
        )
        ctx = SimpleNamespace(author=SimpleNamespace(), guild=SimpleNamespace())

        timer, created, error = self.cog._create_timer_from_parsed(ctx, parsed)
        self.assertIsNone(error)
        self.assertTrue(created)
        self.assertIsNotNone(timer)
        self.assertEqual(timer.kwargs["owner_name"], "INIT")
        self.assertEqual(timer.kwargs["timer_type"], "FI")

    @patch("discordtimerboard.cogs.timerboard.apps.get_model", return_value=_FakeTimerModel)
    @patch("discordtimerboard.cogs.timerboard.EveSolarSystem")
    def test_create_timer_duplicate_short_circuit(self, mock_system_model, _mock_get_model):
        _FakeTimerModel.objects.reset_mock()
        existing = SimpleNamespace(pk=1234)
        _FakeTimerModel.objects.filter.return_value.first.return_value = existing
        mock_system_model.objects.filter.return_value.first.return_value = SimpleNamespace(name="CL6-ZG")
        self.cog._resolve_structure_type = MagicMock(return_value=SimpleNamespace(name="Astrahus"))

        parsed = ParsedTimerInput(
            timer_time=timezone.make_aware(dt.datetime(2026, 4, 23, 19, 15, 59), dt.timezone.utc),
            system="CL6-ZG",
            structure_name="Microplastic of Pure Blind",
            tags=["INIT", "ASTRA", "FINAL"],
        )
        ctx = SimpleNamespace(author=SimpleNamespace(), guild=SimpleNamespace())
        timer, created, error = self.cog._create_timer_from_parsed(ctx, parsed)

        self.assertIsNone(error)
        self.assertFalse(created)
        self.assertEqual(timer.pk, 1234)

    @patch("discordtimerboard.cogs.timerboard.get_auth_user")
    async def test_check_add_perm_uses_structuretimers_permission(self, mock_get_auth_user):
        mock_get_auth_user.return_value = SimpleNamespace(
            has_perm=MagicMock(return_value=True)
        )
        ctx = SimpleNamespace(author=SimpleNamespace(), guild=SimpleNamespace())
        self.assertTrue(await self.cog._check_add_perm(ctx))


class TestHelpText(unittest.TestCase):
    def test_every_topic_renders(self):
        for topic in HELP_TOPICS:
            text = build_help_text(topic)
            self.assertTrue(text)
            self.assertEqual(text.count("```") % 2, 0, f"unbalanced code fence in {topic}")

    def test_all_topic_includes_every_section(self):
        text = build_help_text("all")
        for topic in HELP_TOPICS:
            self.assertIn(build_help_text(topic), text)

    def test_default_topic_is_add_formats(self):
        text = build_help_text()
        self.assertIn("Merc Den MQ-NPY Planet I 2 30 [NC]", text)
        self.assertIn("Reinforced until", text)

    def test_topic_aliases(self):
        self.assertEqual(build_help_text("formats"), build_help_text("add"))
        self.assertEqual(build_help_text("TAGS "), build_help_text("tags"))

    def test_unknown_topic_lists_available_topics(self):
        text = build_help_text("nonsense")
        self.assertIn("Unknown help topic", text)
        for topic in HELP_TOPICS:
            self.assertIn(f"`{topic}`", text)

    def test_tag_help_is_derived_from_alias_tables(self):
        """Adding an alias to the lookup tables must show up in help automatically."""
        text = build_help_text("tags")
        for alias in STRUCTURE_ALIAS_TO_EVE_TYPE_NAME:
            self.assertIn(f"`{alias}`", text)
        for tag in TIMER_TYPE_TAG_TO_MODEL:
            self.assertIn(f"`{tag}`", text)


class TestSplitForDiscord(unittest.TestCase):
    def test_short_text_is_one_chunk(self):
        self.assertEqual(split_for_discord("hello"), ["hello"])
        self.assertEqual(split_for_discord(""), [])

    def test_chunks_respect_limit_and_keep_fences_balanced(self):
        text = build_help_text("all")
        for limit in (2000, 900, 400, 120):
            chunks = split_for_discord(text, limit)
            for chunk in chunks:
                self.assertLessEqual(len(chunk), limit)
                self.assertEqual(chunk.count("```") % 2, 0)

    def test_no_content_is_lost(self):
        text = build_help_text("all")
        chunks = split_for_discord(text, 400)
        stripped = "".join(chunks).replace("```", "").replace("\n", "")
        self.assertEqual(stripped, text.replace("```", "").replace("\n", ""))

    def test_overlong_single_line_is_hard_split(self):
        line = "x" * 500
        chunks = split_for_discord(f"a\n{line}\nb", 100)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 100)
        self.assertEqual("".join(chunks).replace("\n", ""), f"a{line}b")

    def test_split_inside_code_block_reopens_fence(self):
        body = "\n".join(f"line {i}" for i in range(60))
        chunks = split_for_discord(f"intro\n```\n{body}\n```\nouttro", 200)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(chunks[0].endswith("```"))
        self.assertTrue(chunks[1].startswith("```"))
