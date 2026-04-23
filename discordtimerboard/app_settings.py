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
    2) Static fallback from DISCORDTIMERBOARD_SERVERS setting
    """
    try:
        DiscordTimerboardConfig = apps.get_model("discordtimerboard", "DiscordTimerboardConfig")
        rows = list(
            DiscordTimerboardConfig.objects.filter(enabled=True).values(
                "name",
                "guild_id",
                "timerboard_channel_id",
                "commands_channel_id",
                "required_role_ids",
                "require_structuretimers_add_perm",
            )
        )
        if rows:
            return [
                {
                    "name": row["name"],
                    "guild_id": row["guild_id"],
                    "timerboard": row["timerboard_channel_id"],
                    "commands": row["commands_channel_id"],
                    "required_role_ids": row["required_role_ids"],
                    "require_structuretimers_add_perm": row["require_structuretimers_add_perm"],
                }
                for row in rows
            ]
    except (LookupError, OperationalError, ProgrammingError):
        # Table may not exist yet before initial migration.
        pass

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
                "required_role_ids": cfg.get("required_role_ids", ""),
                "require_structuretimers_add_perm": cfg.get(
                    "require_structuretimers_add_perm", True
                ),
            }
        )
    return configs
