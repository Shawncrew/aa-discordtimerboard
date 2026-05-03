import datetime as dt
import logging
from typing import Optional

import discord

from aadiscordbot.utils.auth import get_auth_user
try:
    from discord import option
except Exception:
    def option(*args, **kwargs):
        def _decorator(func):
            return func
        return _decorator
from discord.ext import commands, tasks

from django.apps import apps
from django.db.models import Count, Max
from django.utils import timezone
from eveuniverse.models import EveSolarSystem, EveType

from .. import app_settings
from ..parsing import ParsedTimerInput, parse_add_input, parse_bulk_input

logger = logging.getLogger(__name__)


STRUCTURE_ALIAS_TO_EVE_TYPE_NAME = {
    "ASTRA": "Astrahus",
    "ASTR": "Astrahus",
    "ASTRAHUS": "Astrahus",
    "FORT": "Fortizar",
    "FORTI": "Fortizar",
    "FZ": "Fortizar",
    "FORTIZAR": "Fortizar",
    "KEEP": "Keepstar",
    "KEEPSTAR": "Keepstar",
    "AZBEL": "Azbel",
    "ATHANOR": "Athanor",
    "RAITARU": "Raitaru",
    "SOTIYO": "Sotiyo",
    "ANSI": "Ansiblex Jump Gate",
    "ANSIBLEX": "Ansiblex Jump Gate",
    "SKYHOOK": "Orbital Skyhook",
    "SKY": "Orbital Skyhook",
    "ORBITAL SKYHOOK": "Orbital Skyhook",
    "POCO": "Customs Office",
    "CUSTOMS": "Customs Office",
    "CUSTOMS OFFICE": "Customs Office",
    "IHUB": "Infrastructure Hub",
    "MERCENARY DEN": "Mercenary Den",
    "MERC DEN": "Mercenary Den",
    "MERC": "Mercenary Den",
    "METENOX": "Metenox Moon Drill",
    "METANOX": "Metenox Moon Drill",
}

STRUCTURE_DISPLAY_TAG = {
    "Astrahus": "ASTRA",
    "Fortizar": "FORT",
    "Keepstar": "KEEPSTAR",
    "Azbel": "AZBEL",
    "Athanor": "ATHANOR",
    "Raitaru": "RAITARU",
    "Sotiyo": "SOTIYO",
    "Ansiblex Jump Gate": "ANSI",
    "Orbital Skyhook": "Skyhook",
    "Customs Office": "POCO",
    "Infrastructure Hub": "IHUB",
    "Mercenary Den": "MERCENARY DEN",
    "Metenox Moon Drill": "METENOX",
}

TIMER_TYPE_TAG_TO_MODEL = {
    "ARMOR": "AR",
    "HULL": "HL",
    "FINAL": "FI",
    "ANCHORING": "AN",
    "UNANCHORING": "UA",
    "MOON": "MM",
    "MOONMINING": "MM",
    "THEFT": "TF",
    "PRELIMINARY": "PL",
}

MODEL_TIMER_TO_TAG = {
    "NO": "NONE",
    "AR": "ARMOR",
    "HL": "HULL",
    "FI": "FINAL",
    "AN": "ANCHORING",
    "UA": "UNANCHORING",
    "MM": "MOON",
    "TF": "THEFT",
    "PL": "PRELIMINARY",
}


_REFRESH_COOLDOWN_SECONDS = 30


class DiscordTimerBoard(commands.Cog):
    _alliance_ticker_cache: dict[int, str] = {}

    def __init__(self, bot):
        self.bot = bot
        self._last_timer_state = None
        self._last_manual_refresh: dict[int, dt.datetime] = {}
        # Maps commands_channel_id -> set of timer PKs already notified (in-memory cache).
        self._notified_warning: dict[int, set[int]] = {}
        self._notified_start: dict[int, set[int]] = {}
        self._notified_sov_warning: dict[int, set[int]] = {}
        self._notified_sov_start: dict[int, set[int]] = {}
        if not self.refresh_boards.is_running():
            self.refresh_boards.start()

    def cog_unload(self):
        if self.refresh_boards.is_running():
            self.refresh_boards.cancel()

    @staticmethod
    def _structuretimers_available() -> bool:
        return apps.is_installed("structuretimers")

    @staticmethod
    def _sovtimer_available() -> bool:
        return apps.is_installed("sovtimer")

    @staticmethod
    def _iter_server_configs():
        yield from app_settings.get_server_configs()

    def _get_command_config_for_channel(self, channel_id: int):
        for cfg in self._iter_server_configs():
            if channel_id == cfg.get("commands"):
                return cfg
        return None

    async def _check_add_perm(self, ctx_or_interaction) -> bool:
        author = getattr(ctx_or_interaction, "author", None) or getattr(
            ctx_or_interaction, "user", None
        )
        guild = getattr(ctx_or_interaction, "guild", None)
        try:
            auth_user = get_auth_user(author, guild=guild)
        except Exception as e:
            logger.warning("Permission check failed for user=%s guild=%s: %s", author, guild, e)
            return False
        return auth_user.has_perm("structuretimers.add_timer")

    @tasks.loop(seconds=app_settings.DISCORDTIMERBOARD_UPDATE_INTERVAL)
    async def refresh_boards(self):
        if not self._structuretimers_available():
            return
        await self.update_all_timerboards()
        await self._send_timer_notifications()
        self._archive_expired_timers()

    @refresh_boards.before_loop
    async def _before_refresh_boards(self):
        await self.bot.wait_until_ready()
        self._load_sent_notifications()

    def _load_sent_notifications(self):
        """Populate in-memory notification cache from DB so reboots don't re-alert."""
        try:
            SentNotification = apps.get_model("discordtimerboard", "SentNotification")
            for notif in SentNotification.objects.all():
                ch = notif.commands_channel_id
                tid = notif.timer_id
                if notif.timer_type == SentNotification.STRUCTURE:
                    if notif.notification_type == SentNotification.WARNING:
                        self._notified_warning.setdefault(ch, set()).add(tid)
                    else:
                        self._notified_start.setdefault(ch, set()).add(tid)
                else:
                    if notif.notification_type == SentNotification.WARNING:
                        self._notified_sov_warning.setdefault(ch, set()).add(tid)
                    else:
                        self._notified_sov_start.setdefault(ch, set()).add(tid)
        except Exception as e:
            logger.warning("Failed to load sent notifications from DB: %s", e)

    def _archive_expired_timers(self):
        """Archive and delete structure timers whose strikethrough window has passed."""
        if not self._structuretimers_available():
            return
        configs = list(self._iter_server_configs())
        if not configs:
            return
        # Use the smallest strikethrough_minutes across configs as the cutoff.
        min_strikethrough = min(cfg.get("strikethrough_minutes", 5) for cfg in configs)
        cutoff = timezone.now() - dt.timedelta(minutes=min_strikethrough)
        try:
            Timer = apps.get_model("structuretimers", "Timer")
            ArchivedTimer = apps.get_model("discordtimerboard", "ArchivedTimer")
            expired = Timer.objects.select_related(
                "eve_solar_system", "structure_type"
            ).filter(date__isnull=False, date__lt=cutoff).exclude(timer_type="MM")
            for timer in expired:
                try:
                    ArchivedTimer.objects.create(
                        original_id=timer.pk,
                        timer_date=timer.date,
                        system_name=timer.eve_solar_system.name if timer.eve_solar_system_id else "",
                        structure_type_name=timer.structure_type.name if timer.structure_type_id else "",
                        structure_name=(timer.structure_name or "").strip(),
                        owner_name=(timer.owner_name or "").strip(),
                        timer_type=timer.timer_type or "",
                        archived_by="auto",
                    )
                    timer.delete()
                except Exception as e:
                    logger.error("Failed to auto-archive timer pk=%s: %s", timer.pk, e)
        except Exception as e:
            logger.error("Error in _archive_expired_timers: %s", e)

    def _query_upcoming_timers(self, lookahead_minutes: int):
        Timer = apps.get_model("structuretimers", "Timer")
        now = timezone.now()
        cutoff_past = now - dt.timedelta(
            minutes=app_settings.DISCORDTIMERBOARD_PAST_GRACE_MINUTES
        )
        cutoff_future = now + dt.timedelta(minutes=lookahead_minutes)
        return list(
            Timer.objects.select_related(
                "eve_solar_system",
                "structure_type",
            )
            .filter(date__isnull=False, date__gte=cutoff_past, date__lte=cutoff_future)
            .exclude(timer_type="MM")
        )

    async def _send_timer_notifications(self):
        configs = list(self._iter_server_configs())
        if not configs:
            return

        # Determine the widest lookahead needed across all configs.
        max_warning_minutes = max(
            cfg.get("warning_minutes", 60)
            for cfg in configs
            if cfg.get("warning_notifications_enabled", True)
        ) if any(cfg.get("warning_notifications_enabled", True) for cfg in configs) else 0

        timers = self._query_upcoming_timers(max_warning_minutes)
        now = timezone.now()

        try:
            SentNotification = apps.get_model("discordtimerboard", "SentNotification")
        except LookupError:
            SentNotification = None

        # Prune in-memory cache to active timer PKs only.
        active_pks = {t.pk for t in timers}
        for ch_id in list(self._notified_warning):
            self._notified_warning[ch_id] &= active_pks
        for ch_id in list(self._notified_start):
            self._notified_start[ch_id] &= active_pks

        for cfg in configs:
            commands_channel_id = cfg.get("commands")
            if not commands_channel_id:
                continue
            warning_enabled = cfg.get("warning_notifications_enabled", True)
            start_enabled = cfg.get("start_notifications_enabled", True)
            if not warning_enabled and not start_enabled:
                continue

            warning_minutes = cfg.get("warning_minutes", 60)

            channel = self.bot.get_channel(commands_channel_id)
            if channel is None:
                logger.warning("Commands channel not found for id=%s", commands_channel_id)
                continue

            warned = self._notified_warning.setdefault(commands_channel_id, set())
            started = self._notified_start.setdefault(commands_channel_id, set())

            for timer in timers:
                minutes_until = (timer.date - now).total_seconds() / 60

                if warning_enabled and timer.pk not in warned and 0 < minutes_until <= warning_minutes:
                    msg = f":warning: **Timer warning ({warning_minutes}m):** {self._format_line(timer)}"
                    try:
                        await channel.send(msg)
                        warned.add(timer.pk)
                        if SentNotification:
                            SentNotification.objects.get_or_create(
                                timer_type=SentNotification.STRUCTURE,
                                timer_id=timer.pk,
                                notification_type=SentNotification.WARNING,
                                commands_channel_id=commands_channel_id,
                            )
                    except discord.errors.Forbidden:
                        logger.error("No permission to send to commands channel id=%s", commands_channel_id)

                if start_enabled and timer.pk not in started and minutes_until <= 0:
                    msg = f":alarm_clock: **Timer starting now:** {self._format_line(timer)}"
                    try:
                        await channel.send(msg)
                        started.add(timer.pk)
                        if SentNotification:
                            SentNotification.objects.get_or_create(
                                timer_type=SentNotification.STRUCTURE,
                                timer_id=timer.pk,
                                notification_type=SentNotification.START,
                                commands_channel_id=commands_channel_id,
                            )
                    except discord.errors.Forbidden:
                        logger.error("No permission to send to commands channel id=%s", commands_channel_id)

            if not cfg.get("sov_notifications_enabled"):
                continue
            sov_alliance_ids = cfg.get("sov_alliance_ids") or []
            sov_campaigns = self._query_sov_campaigns(sov_alliance_ids)
            sov_active_pks = {c.campaign_id for c in sov_campaigns}
            self._notified_sov_warning.setdefault(commands_channel_id, set())
            self._notified_sov_start.setdefault(commands_channel_id, set())
            self._notified_sov_warning[commands_channel_id] &= sov_active_pks
            self._notified_sov_start[commands_channel_id] &= sov_active_pks
            sov_warned = self._notified_sov_warning[commands_channel_id]
            sov_started = self._notified_sov_start[commands_channel_id]

            for campaign in sov_campaigns:
                structure = campaign.structure
                end_time = (structure.vulnerable_end_time if structure else None) or campaign.start_time
                if end_time is None:
                    continue
                minutes_until = (end_time - now).total_seconds() / 60

                if warning_enabled and campaign.campaign_id not in sov_warned and 0 < minutes_until <= warning_minutes:
                    msg = f":warning: **Sov timer warning ({warning_minutes}m):** {self._format_sov_line(campaign)}"
                    try:
                        await channel.send(msg)
                        sov_warned.add(campaign.campaign_id)
                        if SentNotification:
                            SentNotification.objects.get_or_create(
                                timer_type=SentNotification.SOV,
                                timer_id=campaign.campaign_id,
                                notification_type=SentNotification.WARNING,
                                commands_channel_id=commands_channel_id,
                            )
                    except discord.errors.Forbidden:
                        logger.error("No permission to send to commands channel id=%s", commands_channel_id)

                if start_enabled and campaign.campaign_id not in sov_started and minutes_until <= 0:
                    msg = f":alarm_clock: **Sov timer ending now:** {self._format_sov_line(campaign)}"
                    try:
                        await channel.send(msg)
                        sov_started.add(campaign.campaign_id)
                        if SentNotification:
                            SentNotification.objects.get_or_create(
                                timer_type=SentNotification.SOV,
                                timer_id=campaign.campaign_id,
                                notification_type=SentNotification.START,
                                commands_channel_id=commands_channel_id,
                            )
                    except discord.errors.Forbidden:
                        logger.error("No permission to send to commands channel id=%s", commands_channel_id)

        # Clean up DB records for timers that no longer exist.
        if SentNotification:
            try:
                cutoff = now - dt.timedelta(minutes=app_settings.DISCORDTIMERBOARD_PAST_GRACE_MINUTES)
                SentNotification.objects.filter(sent_at__lt=cutoff).delete()
            except Exception as e:
                logger.warning("Failed to clean up SentNotification records: %s", e)

    def _query_sov_campaigns(self, alliance_ids: list[int]):
        if not self._sovtimer_available() or not alliance_ids:
            return []
        try:
            Campaign = apps.get_model("sovtimer", "Campaign")
        except LookupError:
            return []
        cutoff = timezone.now() - dt.timedelta(
            minutes=app_settings.DISCORDTIMERBOARD_PAST_GRACE_MINUTES
        )
        # vulnerable_end_time is NULL during active campaigns in aa-sov-timer;
        # fall back to filtering on start_time so active contests are included.
        return list(
            Campaign.objects.select_related(
                "structure__alliance",
                "structure__solar_system",
            ).filter(
                structure__alliance__alliance_id__in=alliance_ids,
                start_time__gte=cutoff,
            ).order_by("start_time")
        )

    @classmethod
    def _get_alliance_ticker(cls, alliance_id: int) -> str:
        if alliance_id in cls._alliance_ticker_cache:
            return cls._alliance_ticker_cache[alliance_id]
        ticker = ""
        # Try AA's EveAllianceInfo first (fast, no ESI call).
        try:
            from allianceauth.eveonline.models import EveAllianceInfo
            info = EveAllianceInfo.objects.filter(alliance_id=alliance_id).first()
            if info:
                ticker = info.alliance_ticker
        except Exception:
            pass
        # Fall back to ESI for any alliance not in local auth.
        if not ticker:
            try:
                import requests
                resp = requests.get(
                    f"https://esi.evetech.net/latest/alliances/{alliance_id}/",
                    timeout=5,
                )
                if resp.ok:
                    ticker = resp.json().get("ticker", "")
            except Exception as e:
                logger.warning("ESI ticker fetch failed for alliance_id=%s: %s", alliance_id, e)
        cls._alliance_ticker_cache[alliance_id] = ticker
        return ticker

    _SOV_EVENT_TYPE_MAP = {
        "ihub_defense": ("Infrastructure Hub", "IHUB"),
        "tcu_defense": ("Territorial Claim Unit", "TCU"),
        "sovhub": ("Infrastructure Hub", "IHUB"),
        "outpost_defense": ("Outpost", "OUTPOST"),
    }

    @staticmethod
    def _format_sov_line(campaign) -> str:
        structure = campaign.structure

        try:
            system = structure.solar_system.name
        except AttributeError:
            system = "Unknown"

        region = ""
        try:
            from eveuniverse.models import EveSolarSystem as EveUniSystem
            eve_sys = EveUniSystem.objects.filter(name__iexact=system).select_related(
                "eve_constellation__eve_region"
            ).first()
            if eve_sys:
                region = eve_sys.eve_constellation.eve_region.name
        except Exception:
            pass

        ticker = ""
        try:
            alliance_id = structure.alliance.alliance_id if structure and structure.alliance_id else None
            if alliance_id:
                ticker = DiscordTimerBoard._get_alliance_ticker(alliance_id)
        except Exception:
            pass

        event_type = campaign.event_type or ""
        struct_name, type_tag = DiscordTimerBoard._SOV_EVENT_TYPE_MAP.get(
            event_type.lower(), (event_type, event_type.upper()[:8])
        )

        date_str = timezone.localtime(campaign.start_time).strftime("%Y-%m-%d %H:%M:%S") if campaign.start_time else "?"
        region_part = f" ({region})" if region else ""
        ticker_tag = f"[{ticker}]" if ticker else ""

        system_link = f"[{system}](<{DiscordTimerBoard._dotlan_system_url(system)}>)"
        return f"{date_str} {system_link}{region_part} {struct_name} {ticker_tag}[{type_tag}] 🛡️"

    def _query_timer_state(self):
        Timer = apps.get_model("structuretimers", "Timer")
        cutoff = timezone.now() - dt.timedelta(
            minutes=app_settings.DISCORDTIMERBOARD_PAST_GRACE_MINUTES
        )
        agg = Timer.objects.filter(date__isnull=False, date__gte=cutoff).aggregate(
            count=Count("pk"),
            latest_update=Max("last_updated_at"),
        )
        # Include current EVE minute so the header refreshes every minute even
        # when timer rows are unchanged.
        eve_minute = timezone.now().astimezone(dt.timezone.utc).replace(
            second=0, microsecond=0
        )
        return (
            agg.get("count", 0),
            agg.get("latest_update"),
            eve_minute,
        )

    async def update_all_timerboards(self, force: bool = False, recreate: bool = False):
        current_state = self._query_timer_state()
        if not force and current_state == self._last_timer_state:
            return
        for cfg in self._iter_server_configs():
            channel_id = cfg.get("timerboard")
            if not channel_id:
                continue
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                logger.warning("Timerboard channel not found for id=%s", channel_id)
                continue
            await self._update_timerboard_channel(channel, cfg=cfg, recreate=recreate)
        self._last_timer_state = current_state

    def _query_timers(self, past_minutes: int = None):
        Timer = apps.get_model("structuretimers", "Timer")
        if past_minutes is None:
            past_minutes = app_settings.DISCORDTIMERBOARD_PAST_GRACE_MINUTES
        cutoff = timezone.now() - dt.timedelta(minutes=past_minutes)
        return (
            Timer.objects.select_related(
                "eve_solar_system__eve_constellation__eve_region",
                "structure_type",
            )
            .filter(date__isnull=False, date__gte=cutoff)
            .exclude(timer_type="MM")
            .order_by("date", "pk")
        )

    def _format_tags(self, timer) -> str:
        tags = []
        owner = (timer.owner_name or "").strip()
        if owner:
            owner = owner.strip("[]")
            tags.append(f"[{owner}]")

        structure_name = timer.structure_type.name if timer.structure_type_id else ""
        struct_tag = STRUCTURE_DISPLAY_TAG.get(structure_name, structure_name.upper()[:12])
        if struct_tag:
            tags.append(f"[{struct_tag}]")

        timer_tag = MODEL_TIMER_TO_TAG.get(timer.timer_type, timer.get_timer_type_display().upper())
        if timer_tag and timer_tag != "NONE":
            tags.append(f"[{timer_tag}]")
        return "".join(tags)

    @staticmethod
    def _dotlan_system_url(system_name: str) -> str:
        return "https://evemaps.dotlan.net/system/" + system_name.replace(" ", "_")

    def _format_line(self, timer) -> str:
        date_str = timezone.localtime(timer.date).strftime("%Y-%m-%d %H:%M:%S")
        system = timer.eve_solar_system.name if timer.eve_solar_system_id else "Unknown"
        region = ""
        try:
            region = timer.eve_solar_system.eve_constellation.eve_region.name
        except AttributeError as e:
            logger.warning("Region lookup failed for timer pk=%s system_id=%s: %s", timer.pk, timer.eve_solar_system_id, e)
        structure = (timer.structure_name or "").strip() or timer.structure_type.name
        tags = self._format_tags(timer)
        region_part = f" ({region})" if region else ""
        tags_part = f" {tags}" if tags else ""
        system_link = f"[{system}](<{self._dotlan_system_url(system)}>)"
        return f"{date_str} {system_link}{region_part} {structure}{tags_part} ({timer.pk})"

    # Discord's hard limit is 2000; leave headroom for safety.
    _DISCORD_MSG_MAX_LEN = 1900
    # Safety cap on how many bot messages we track in a channel.
    _HISTORY_BOT_MSG_LIMIT = 200

    async def _update_timerboard_channel(self, channel, cfg: dict = None, recreate: bool = False):
        strikethrough_minutes = cfg.get("strikethrough_minutes", 5) if cfg else 5
        now = timezone.now()
        timers = self._query_timers(past_minutes=strikethrough_minutes)
        # Collect (sort_date, line) so structure and sov entries merge in time order.
        entries: list[tuple] = []
        for t in timers:
            line = self._format_line(t)
            if t.date and t.date <= now:
                line = f"~~{line}~~"
            entries.append((t.date, line))

        if cfg and cfg.get("sov_notifications_enabled"):
            sov_alliance_ids = cfg.get("sov_alliance_ids") or []
            sov_campaigns = self._query_sov_campaigns(sov_alliance_ids)
            for c in sov_campaigns:
                line = self._format_sov_line(c)
                sort_date = (c.structure.vulnerable_end_time if c.structure else None) or c.start_time
                if sort_date and sort_date <= now:
                    line = f"~~{line}~~"
                entries.append((sort_date, line))

        entries.sort(key=lambda x: x[0] or timezone.now())
        lines = [line for _, line in entries]

        eve_now = timezone.now().astimezone(dt.timezone.utc)
        header = f"Current Eve Time (UTC): {eve_now.strftime('%Y-%m-%d %H:%M')}"
        content_lines = [header, "", ""] + (lines if lines else ["No active timers."])

        payloads = []
        current = ""
        for line in content_lines:
            candidate = f"{current}\n{line}".strip("\n") if current else line
            if len(candidate) > self._DISCORD_MSG_MAX_LEN:
                payloads.append(current)
                current = line
            else:
                current = candidate
        if current:
            payloads.append(current)

        existing = []
        try:
            async for msg in channel.history(limit=None):
                if msg.author == self.bot.user:
                    existing.append(msg)
                    if len(existing) >= self._HISTORY_BOT_MSG_LIMIT:
                        logger.warning(
                            "Channel id=%s has >= %d bot messages; capping history scan",
                            channel.id,
                            self._HISTORY_BOT_MSG_LIMIT,
                        )
                        break
        except discord.errors.Forbidden:
            logger.error("No permission to read history in channel id=%s", channel.id)
            return
        existing.reverse()

        if recreate:
            for msg in existing:
                try:
                    await msg.delete()
                except discord.errors.NotFound:
                    pass
                except discord.errors.Forbidden:
                    logger.error("No permission to delete message id=%s in channel id=%s", msg.id, channel.id)
                    return
            for payload in payloads:
                try:
                    await channel.send(payload)
                except discord.errors.Forbidden:
                    logger.error("No permission to send messages in channel id=%s", channel.id)
                    return
        else:
            for idx, payload in enumerate(payloads):
                if idx < len(existing):
                    try:
                        await existing[idx].edit(content=payload)
                    except discord.errors.NotFound:
                        logger.warning("Message id=%s not found while editing; sending new", existing[idx].id)
                        await channel.send(payload)
                    except discord.errors.Forbidden:
                        logger.error("No permission to edit message id=%s in channel id=%s", existing[idx].id, channel.id)
                else:
                    try:
                        await channel.send(payload)
                    except discord.errors.Forbidden:
                        logger.error("No permission to send messages in channel id=%s", channel.id)
                        return
            for extra in existing[len(payloads):]:
                try:
                    await extra.delete()
                except discord.errors.NotFound:
                    pass
                except discord.errors.Forbidden:
                    logger.error("No permission to delete message id=%s in channel id=%s", extra.id, channel.id)

    async def _send_response(self, ctx_or_interaction, message: str, ephemeral: bool = False):
        if hasattr(ctx_or_interaction, "response"):
            if not ctx_or_interaction.response.is_done():
                await ctx_or_interaction.response.send_message(message, ephemeral=ephemeral)
            else:
                await ctx_or_interaction.followup.send(message, ephemeral=ephemeral)
            return
        if hasattr(ctx_or_interaction, "respond"):
            await ctx_or_interaction.respond(message, ephemeral=ephemeral)
            return
        await ctx_or_interaction.send(message)

    async def _guard_command_access(self, ctx_or_interaction):
        channel = getattr(ctx_or_interaction, "channel", None)
        channel_id = getattr(channel, "id", None)
        cfg = self._get_command_config_for_channel(channel_id)
        if not cfg:
            return None
        return cfg

    def _check_refresh_cooldown(self, channel_id: int) -> Optional[int]:
        """Return remaining cooldown seconds, or None if the cooldown has passed."""
        last = self._last_manual_refresh.get(channel_id)
        if last is None:
            return None
        elapsed = (timezone.now() - last).total_seconds()
        remaining = _REFRESH_COOLDOWN_SECONDS - elapsed
        return int(remaining) + 1 if remaining > 0 else None

    def _mark_refresh(self, channel_id: int):
        self._last_manual_refresh[channel_id] = timezone.now()

    @commands.command(name="refresh")
    async def refresh_cmd(self, ctx):
        cfg = await self._guard_command_access(ctx)
        if not cfg:
            return
        remaining = self._check_refresh_cooldown(ctx.channel.id)
        if remaining is not None:
            await self._send_response(ctx, f"Refresh is on cooldown. Try again in {remaining}s.")
            return
        self._mark_refresh(ctx.channel.id)
        await self.update_all_timerboards(force=True, recreate=True)
        await self._send_response(ctx, "Timerboard refreshed.")

    @commands.slash_command(
        name="refreshtimerboard",
        description="Refresh timerboard output now",
    )
    async def slash_refresh_cmd(self, ctx):
        cfg = await self._guard_command_access(ctx)
        if not cfg:
            return
        remaining = self._check_refresh_cooldown(ctx.channel.id)
        if remaining is not None:
            await self._send_response(ctx, f"Refresh is on cooldown. Try again in {remaining}s.", ephemeral=True)
            return
        self._mark_refresh(ctx.channel.id)
        await self.update_all_timerboards(force=True, recreate=True)
        await self._send_response(ctx, "Timerboard refreshed.", ephemeral=True)


    @commands.command(name="rm")
    async def remove_timer_cmd(self, ctx, timer_id: int):
        cfg = await self._guard_command_access(ctx)
        if not cfg:
            return
        if not await self._check_add_perm(ctx):
            await self._send_response(ctx, "You do not have permission to remove timers.")
            return
        await self._remove_timer_impl(ctx, timer_id, ephemeral=False)

    @commands.slash_command(name="removetimer", description="Remove timer by id")
    @option("timer_id", description="Timer ID shown at end of timer line")
    async def slash_remove_timer_cmd(self, ctx, timer_id: int):
        cfg = await self._guard_command_access(ctx)
        if not cfg:
            return
        if not await self._check_add_perm(ctx):
            await self._send_response(ctx, "You do not have permission to remove timers.", ephemeral=True)
            return
        await self._remove_timer_impl(ctx, timer_id, ephemeral=True)


    @commands.command(name="add")
    async def add_timer_cmd(self, ctx, *, input_text: str):
        cfg = await self._guard_command_access(ctx)
        if not cfg:
            return
        if not await self._check_add_perm(ctx):
            await self._send_response(ctx, "You do not have permission to add timers.")
            return
        await self._add_timer_impl(ctx, input_text, ephemeral=False)

    @commands.slash_command(name="addtimer", description="Add a structure timer")
    @option(
        "input_text",
        description=(
            "Paste timer text. Supports timerbot formats: direct, reinforced/multiline, Merc Den."
        ),
    )
    async def slash_add_timer_cmd(self, ctx, input_text: str):
        cfg = await self._guard_command_access(ctx)
        if not cfg:
            return
        if not await self._check_add_perm(ctx):
            await self._send_response(ctx, "You do not have permission to add timers.", ephemeral=True)
            return
        await self._add_timer_impl(ctx, input_text, ephemeral=True)

    @commands.command(name="bulkadd")
    async def bulk_add_timer_cmd(self, ctx, *, input_text: str):
        cfg = await self._guard_command_access(ctx)
        if not cfg:
            return
        if not await self._check_add_perm(ctx):
            await self._send_response(ctx, "You do not have permission to add timers.")
            return
        await self._bulk_add_impl(ctx, input_text, ephemeral=False)

    @commands.slash_command(
        name="bulkaddtimers",
        description="Add multiple timers from a bulk timer list (paste multiple lines)",
    )
    @option("input_text", description="Paste the full bulk timer list (multiple lines supported)")
    async def slash_bulk_add_timer_cmd(self, ctx, input_text: str):
        cfg = await self._guard_command_access(ctx)
        if not cfg:
            return
        if not await self._check_add_perm(ctx):
            await self._send_response(ctx, "You do not have permission to add timers.", ephemeral=True)
            return
        await self._bulk_add_impl(ctx, input_text, ephemeral=True)


    async def _bulk_add_impl(self, ctx_or_interaction, input_text: str, ephemeral: bool):
        if not self._structuretimers_available():
            await self._send_response(ctx_or_interaction, "`aa-structuretimers` is required but not installed.", ephemeral=ephemeral)
            return

        parsed_lines = parse_bulk_input(input_text)
        if not parsed_lines:
            await self._send_response(ctx_or_interaction, "No timer lines found in input.", ephemeral=ephemeral)
            return

        added = skipped = failed = 0
        parse_errors = []

        for line_num, raw_line, parsed in parsed_lines:
            if parsed is None:
                parse_errors.append(f"Line {line_num}: could not parse")
                failed += 1
                continue
            timer, created, error = self._create_timer_from_parsed(ctx_or_interaction, parsed)
            if error:
                parse_errors.append(f"Line {line_num}: {error}")
                failed += 1
            elif created:
                added += 1
            else:
                skipped += 1

        await self.update_all_timerboards()

        lines = [f"**Bulk add complete:** {added} added, {skipped} already exist, {failed} failed."]
        if parse_errors:
            lines.append("**Errors:**")
            lines += parse_errors[:10]
            if len(parse_errors) > 10:
                lines.append(f"…and {len(parse_errors) - 10} more errors.")
        await self._send_response(ctx_or_interaction, "\n".join(lines), ephemeral=ephemeral)

    async def _add_timer_impl(self, ctx_or_interaction, input_text: str, ephemeral: bool):
        if not self._structuretimers_available():
            await self._send_response(
                ctx_or_interaction,
                "`aa-structuretimers` is required but not installed.",
                ephemeral=ephemeral,
            )
            return

        parsed = parse_add_input(input_text)
        if not parsed:
            await self._send_response(
                ctx_or_interaction,
                "Invalid format. Use direct, reinforced/multiline, or Merc Den formats.",
                ephemeral=ephemeral,
            )
            return

        timer, created, error = self._create_timer_from_parsed(ctx_or_interaction, parsed)
        if error:
            await self._send_response(ctx_or_interaction, error, ephemeral=ephemeral)
            return

        await self.update_all_timerboards()
        if created:
            await self._send_response(
                ctx_or_interaction,
                f"Added timer {timer.pk}: {self._format_line(timer)}",
                ephemeral=ephemeral,
            )
        else:
            await self._send_response(
                ctx_or_interaction,
                f"Matching timer already exists ({timer.pk}): {self._format_line(timer)}",
                ephemeral=ephemeral,
            )

    def _archive_timer(self, timer, ctx_or_interaction):
        ArchivedTimer = apps.get_model("discordtimerboard", "ArchivedTimer")
        author = getattr(ctx_or_interaction, "author", None) or getattr(
            ctx_or_interaction, "user", None
        )
        archived_by = str(author) if author else ""
        try:
            ArchivedTimer.objects.create(
                original_id=timer.pk,
                timer_date=timer.date,
                system_name=timer.eve_solar_system.name if timer.eve_solar_system_id else "",
                structure_type_name=timer.structure_type.name if timer.structure_type_id else "",
                structure_name=(timer.structure_name or "").strip(),
                owner_name=(timer.owner_name or "").strip(),
                timer_type=timer.timer_type or "",
                archived_by=archived_by,
            )
        except Exception as e:
            logger.warning("Failed to archive timer pk=%s: %s", timer.pk, e)

    async def _remove_timer_impl(self, ctx_or_interaction, timer_id: int, ephemeral: bool):
        Timer = apps.get_model("structuretimers", "Timer")
        timer = Timer.objects.select_related("eve_solar_system", "structure_type").filter(pk=timer_id).first()
        if not timer:
            await self._send_response(
                ctx_or_interaction,
                f"No timer found with ID {timer_id}.",
                ephemeral=ephemeral,
            )
            return
        self._archive_timer(timer, ctx_or_interaction)
        try:
            timer.delete()
        except Exception as e:
            logger.error("Failed to delete timer pk=%s: %s", timer_id, e)
            await self._send_response(
                ctx_or_interaction,
                f"Error removing timer {timer_id}. Check logs for details.",
                ephemeral=ephemeral,
            )
            return
        await self.update_all_timerboards()
        await self._send_response(
            ctx_or_interaction,
            f"Removed timer {timer_id}.",
            ephemeral=ephemeral,
        )

    def _resolve_structure_type(self, parsed: ParsedTimerInput):
        # Usually 2nd tag is structure type in [OWNER][STRUCT][TYPE].
        struct_tag = parsed.tags[1].upper() if len(parsed.tags) >= 2 else ""
        type_name = STRUCTURE_ALIAS_TO_EVE_TYPE_NAME.get(struct_tag)
        if type_name:
            t = EveType.objects.filter(name__iexact=type_name).first()
            if t:
                logger.debug("Resolved structure type %r via tag %r", type_name, struct_tag)
                return t
            logger.debug("Tag %r mapped to %r but EveType not found in DB", struct_tag, type_name)

        # Fallback: infer from structure name.
        upper_name = parsed.structure_name.upper()
        for alias, eve_name in STRUCTURE_ALIAS_TO_EVE_TYPE_NAME.items():
            if alias in upper_name:
                t = EveType.objects.filter(name__iexact=eve_name).first()
                if t:
                    logger.debug("Resolved structure type %r via structure name alias %r", eve_name, alias)
                    return t

        # Last fallback: substring search by structure words.
        for token in upper_name.replace("-", " ").split():
            if len(token) < 4:
                continue
            for alias, eve_name in STRUCTURE_ALIAS_TO_EVE_TYPE_NAME.items():
                if token in alias:
                    t = EveType.objects.filter(name__iexact=eve_name).first()
                    if t:
                        logger.debug("Resolved structure type %r via token %r matching alias %r", eve_name, token, alias)
                        return t

        logger.warning(
            "Could not resolve structure type: tags=%r structure_name=%r",
            parsed.tags,
            parsed.structure_name,
        )
        return None

    def _resolve_timer_type(self, parsed: ParsedTimerInput) -> str:
        # Usually third tag, but some variants only include one/two tags.
        for tag in reversed(parsed.tags):
            match = TIMER_TYPE_TAG_TO_MODEL.get(tag.upper())
            if match:
                return match
        return "NO"

    def _create_timer_from_parsed(self, ctx_or_interaction, parsed: ParsedTimerInput):
        Timer = apps.get_model("structuretimers", "Timer")

        solar_system = EveSolarSystem.objects.filter(name__iexact=parsed.system).first()
        if not solar_system:
            logger.warning("Unknown solar system from command input: %s", parsed.system)
            return None, False, f"Unknown solar system: `{parsed.system}`."

        structure_type = self._resolve_structure_type(parsed)
        if not structure_type:
            logger.warning("Could not resolve structure type from tags=%s", parsed.tags)
            return (
                None,
                False,
                "Could not resolve structure type from tags/structure name. "
                "Include `[OWNER][STRUCT][TYPE]` (example: `[NC][FORT][ARMOR]`).",
            )

        owner_name = parsed.tags[0].strip() if len(parsed.tags) >= 1 else None
        timer_type = self._resolve_timer_type(parsed)

        existing = Timer.objects.filter(
            eve_solar_system=solar_system,
            structure_name__iexact=parsed.structure_name,
            date__gte=parsed.timer_time - dt.timedelta(minutes=1),
            date__lte=parsed.timer_time + dt.timedelta(minutes=1),
        ).first()
        if existing:
            return existing, False, None

        timer = Timer(
            date=parsed.timer_time,
            eve_solar_system=solar_system,
            structure_type=structure_type,
            structure_name=parsed.structure_name,
            owner_name=owner_name,
            objective=Timer.Objective.UNDEFINED,
            timer_type=timer_type,
            visibility=Timer.Visibility.UNRESTRICTED,
        )

        author = getattr(ctx_or_interaction, "author", None) or getattr(
            ctx_or_interaction, "user", None
        )
        guild = getattr(ctx_or_interaction, "guild", None)
        try:
            auth_user = get_auth_user(author, guild=guild)
        except Exception as e:
            logger.warning("Could not resolve auth user for author=%s guild=%s: %s", author, guild, e)
            auth_user = None
        if auth_user:
            timer.user = auth_user
            try:
                main = auth_user.profile.main_character
                timer.eve_character = main
                timer.eve_corporation = main.corporation
                timer.eve_alliance = getattr(main, "alliance", None)
            except Exception as e:
                logger.warning("Could not set character/corp/alliance for user=%s on timer: %s", auth_user, e)

        timer.save()
        return timer, True, None


def setup(bot):
    bot.add_cog(DiscordTimerBoard(bot))
