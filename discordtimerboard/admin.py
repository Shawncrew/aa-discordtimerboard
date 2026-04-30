from django.contrib import admin

from .models import ArchivedTimer, DiscordTimerboardConfig


@admin.register(DiscordTimerboardConfig)
class DiscordTimerboardConfigAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "discord_server_id",
        "timerboard_channel_id",
        "commands_channel_id",
        "enabled",
        "warning_notifications_enabled",
        "start_notifications_enabled",
        "warning_minutes",
        "updated_at",
    )
    list_filter = ("enabled", "warning_notifications_enabled", "start_notifications_enabled")
    search_fields = (
        "name",
        "discord_server_id",
        "timerboard_channel_id",
        "commands_channel_id",
    )


@admin.register(ArchivedTimer)
class ArchivedTimerAdmin(admin.ModelAdmin):
    list_display = (
        "original_id",
        "timer_date",
        "system_name",
        "structure_type_name",
        "structure_name",
        "owner_name",
        "timer_type",
        "archived_by",
        "archived_at",
    )
    search_fields = ("system_name", "structure_name", "owner_name", "archived_by")
    list_filter = ("timer_type",)
    readonly_fields = (
        "original_id", "timer_date", "system_name", "structure_type_name",
        "structure_name", "owner_name", "timer_type", "archived_by", "archived_at",
    )
