from django import forms
from django.contrib import admin
from django.apps import apps

from .models import ArchivedTimer, DiscordTimerboardConfig


class DiscordTimerboardConfigForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            Alliance = apps.get_model("sovtimer", "Alliance")
            qs = Alliance.objects.order_by("name")
            self.fields["sov_alliances"].queryset = qs
            self.fields["sov_alliances"].label_from_instance = lambda obj: obj.name
        except LookupError:
            pass

    class Meta:
        model = DiscordTimerboardConfig
        fields = "__all__"


@admin.register(DiscordTimerboardConfig)
class DiscordTimerboardConfigAdmin(admin.ModelAdmin):
    form = DiscordTimerboardConfigForm
    list_display = (
        "name",
        "discord_server_id",
        "timerboard_channel_id",
        "commands_channel_id",
        "enabled",
        "sov_notifications_enabled",
        "warning_notifications_enabled",
        "start_notifications_enabled",
        "warning_minutes",
        "updated_at",
    )
    list_filter = ("enabled", "sov_notifications_enabled", "warning_notifications_enabled", "start_notifications_enabled")
    search_fields = (
        "name",
        "discord_server_id",
        "timerboard_channel_id",
        "commands_channel_id",
    )
    filter_horizontal = ("sov_alliances",)


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
