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
        rows = list(
            DiscordTimerboardConfig.objects.filter(enabled=True).values(
                "name",
                "discord_server_id",
                "timerboard_channel_id",
                "commands_channel_id",
            )
        )
        if rows:
            return [
                {
                    "name": row["name"],
                    "guild_id": row["discord_server_id"],
                    "timerboard": row["timerboard_channel_id"],
                    "commands": row["commands_channel_id"],
                }
                for row in rows
            ]
    except (LookupError, OperationalError, ProgrammingError):
        # Table may not exist yet before initial migration.
        pass
    return []
