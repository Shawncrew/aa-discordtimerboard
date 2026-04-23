from django.contrib import admin

from .models import DiscordTimerboardConfig


@admin.register(DiscordTimerboardConfig)
class DiscordTimerboardConfigAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "guild_id",
        "timerboard_channel_id",
        "commands_channel_id",
        "required_role_ids",
        "require_structuretimers_add_perm",
        "enabled",
        "updated_at",
    )
    list_filter = ("enabled",)
    search_fields = (
        "name",
        "guild_id",
        "timerboard_channel_id",
        "commands_channel_id",
        "required_role_ids",
    )
