from django.conf import settings
from django.apps import apps
from django.db import OperationalError, ProgrammingError

DISCORDTIMERBOARD_APP_NAME = getattr(
    settings, "DISCORDTIMERBOARD_APP_NAME", "Discord Timerboard"
)

DISCORDTIMERBOARD_DISCORD_BOT_COGS = getattr(
    settings,
    "DISCORDTIMERBOARD_DISCORD_BOT_COGS",
    ["discordtimerboard.cogs.timerboard"],
)

DISCORDTIMERBOARD_UPDATE_INTERVAL = max(
    3,
    int(getattr(settings, "DISCORDTIMERBOARD_UPDATE_INTERVAL", 5)),
)

DISCORDTIMERBOARD_PAST_GRACE_MINUTES = int(
    getattr(settings, "DISCORDTIMERBOARD_PAST_GRACE_MINUTES", 240)
)

DISCORDTIMERBOARD_API_ENABLED = bool(
    getattr(settings, "DISCORDTIMERBOARD_API_ENABLED", False)
)

DISCORDTIMERBOARD_API_KEY = (
    getattr(settings, "DISCORDTIMERBOARD_API_KEY", None) or ""
).strip()


def get_server_configs():
    """
    Return list of channel configs.

    Config source:
    - DB configs from DiscordTimerboardConfig (enabled rows)
    """
    try:
        DiscordTimerboardConfig = apps.get_model("discordtimerboard", "DiscordTimerboardConfig")
        SovAllianceFilter = apps.get_model("discordtimerboard", "SovAllianceFilter")
        configs = []
        for cfg in DiscordTimerboardConfig.objects.filter(enabled=True):
            alliance_ids = list(
                SovAllianceFilter.objects.filter(config_id=cfg.pk).values_list("alliance_id", flat=True)
            )
            configs.append(
                {
                    "name": cfg.name,
                    "guild_id": cfg.discord_server_id,
                    "timerboard": cfg.timerboard_channel_id,
                    "commands": cfg.commands_channel_id,
                    "warning_notifications_enabled": cfg.warning_notifications_enabled,
                    "start_notifications_enabled": cfg.start_notifications_enabled,
                    "warning_minutes": cfg.warning_minutes,
                    "sov_notifications_enabled": cfg.sov_notifications_enabled,
                    "sov_alliance_ids": alliance_ids,
                    "strikethrough_minutes": cfg.strikethrough_minutes,
                }
            )
        if configs:
            return configs
    except (LookupError, OperationalError, ProgrammingError):
        # Table may not exist yet before initial migration.
        pass
    return []
