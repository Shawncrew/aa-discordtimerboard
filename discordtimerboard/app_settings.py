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

DISCORDTIMERBOARD_SERVERS = getattr(
    settings,
    "DISCORDTIMERBOARD_SERVERS",
    {},
)

DISCORDTIMERBOARD_SERVER = getattr(
    settings,
    "DISCORDTIMERBOARD_SERVER",
    {},
)

DISCORDTIMERBOARD_UPDATE_INTERVAL = int(
    getattr(settings, "DISCORDTIMERBOARD_UPDATE_INTERVAL", 60)
)

DISCORDTIMERBOARD_PAST_GRACE_MINUTES = int(
    getattr(settings, "DISCORDTIMERBOARD_PAST_GRACE_MINUTES", 240)
)


def get_server_configs():
    """
    Return list of channel configs.

    Preference order:
    1) DB configs from DiscordTimerboardConfig (enabled rows)
    2) Static fallback from DISCORDTIMERBOARD_SERVER setting
       (or legacy DISCORDTIMERBOARD_SERVERS)
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

    # Preferred static config: single server block.
    if isinstance(DISCORDTIMERBOARD_SERVER, dict):
        timerboard = DISCORDTIMERBOARD_SERVER.get("timerboard")
        commands = DISCORDTIMERBOARD_SERVER.get("commands")
        if timerboard and commands:
            return [
                {
                    "name": "default",
                    "guild_id": DISCORDTIMERBOARD_SERVER.get("guild_id"),
                    "timerboard": timerboard,
                    "commands": commands,
                }
            ]

    # Legacy static config: multi-server map.
    configs = []
    for name, cfg in DISCORDTIMERBOARD_SERVERS.items():
        if not isinstance(cfg, dict):
            continue
        configs.append(
            {
                "name": str(name),
                "guild_id": cfg.get("guild_id"),
                "timerboard": cfg.get("timerboard"),
                "commands": cfg.get("commands"),
            }
        )
    return configs
