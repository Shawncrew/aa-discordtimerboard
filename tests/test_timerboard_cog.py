import datetime as dt
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.utils import timezone

from discordtimerboard.cogs.timerboard import DiscordTimerBoard
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


class TestDiscordTimerboardCog(unittest.TestCase):
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

    def test_extract_allowed_role_ids(self):
        ids = self.cog._extract_allowed_role_ids({"required_role_ids": "123, 456, abc,789"})
        self.assertEqual(ids, {123, 456, 789})

    def test_author_has_required_role(self):
        author = SimpleNamespace(roles=[SimpleNamespace(id=123), SimpleNamespace(id=999)])
        ctx = SimpleNamespace(author=author)
        cfg = {"required_role_ids": "555,123"}
        self.assertTrue(self.cog._author_has_required_role(ctx, cfg))
        cfg = {"required_role_ids": "555,777"}
        self.assertFalse(self.cog._author_has_required_role(ctx, cfg))
