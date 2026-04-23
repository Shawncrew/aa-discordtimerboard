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
from ..parsing import ParsedTimerInput, parse_add_input

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
    def __init__(self, bot):
        self.bot = bot
        self._last_timer_state = None
        self._last_manual_refresh: dict[int, dt.datetime] = {}
        if not self.refresh_boards.is_running():
            self.refresh_boards.start()

    def cog_unload(self):
        if self.refresh_boards.is_running():
            self.refresh_boards.cancel()

    @staticmethod
    def _structuretimers_available() -> bool:
        return apps.is_installed("structuretimers")

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

    @refresh_boards.before_loop
    async def _before_refresh_boards(self):
        await self.bot.wait_until_ready()

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

    async def update_all_timerboards(self, force: bool = False):
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
            await self._update_timerboard_channel(channel)
        self._last_timer_state = current_state

    def _query_timers(self):
        Timer = apps.get_model("structuretimers", "Timer")
        cutoff = timezone.now() - dt.timedelta(
            minutes=app_settings.DISCORDTIMERBOARD_PAST_GRACE_MINUTES
        )
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
        system_link = f"[{system}]({self._dotlan_system_url(system)})"
        return f"{date_str} {system_link}{region_part} {structure}{tags_part} ({timer.pk})"

    # Discord's hard limit is 2000; leave headroom for safety.
    _DISCORD_MSG_MAX_LEN = 1900
    # Safety cap on how many bot messages we track in a channel.
    _HISTORY_BOT_MSG_LIMIT = 200

    async def _update_timerboard_channel(self, channel):
        timers = self._query_timers()
        lines = [self._format_line(t) for t in timers]

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
                pass  # Already gone, nothing to do.
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
        await self.update_all_timerboards(force=True)
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
        await self.update_all_timerboards(force=True)
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

    async def _remove_timer_impl(self, ctx_or_interaction, timer_id: int, ephemeral: bool):
        Timer = apps.get_model("structuretimers", "Timer")
        timer = Timer.objects.filter(pk=timer_id).first()
        if not timer:
            await self._send_response(
                ctx_or_interaction,
                f"No timer found with ID {timer_id}.",
                ephemeral=ephemeral,
            )
            return
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
