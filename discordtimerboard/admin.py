from django.contrib import admin

from .models import DiscordTimerboardConfig


@admin.register(DiscordTimerboardConfig)
class DiscordTimerboardConfigAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "discord_server_id",
        "timerboard_channel_id",
        "commands_channel_id",
        "enabled",
        "updated_at",
    )
    list_filter = ("enabled",)
    search_fields = (
        "name",
        "discord_server_id",
        "timerboard_channel_id",
        "commands_channel_id",
    )
