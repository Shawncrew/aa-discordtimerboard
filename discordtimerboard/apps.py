from django.apps import AppConfig

from . import __version__


class DiscordTimerBoardConfig(AppConfig):
    name = "discordtimerboard"
    label = "discordtimerboard"
    verbose_name = f"Discord Timerboard v{__version__}"
