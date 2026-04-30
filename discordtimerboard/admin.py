from django import forms
from django.contrib import admin
from django.apps import apps

from .models import ArchivedTimer, DiscordTimerboardConfig, SovAllianceFilter


def _alliance_queryset():
    try:
        Alliance = apps.get_model("sovtimer", "Alliance")
        return Alliance.objects.order_by("name")
    except LookupError:
        return None


class SovAllianceFilterForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = _alliance_queryset()
        if qs is not None:
            self.fields["alliance"].queryset = qs
            self.fields["alliance"].label_from_instance = lambda obj: obj.name

    class Meta:
        model = SovAllianceFilter
        fields = ("alliance",)


class SovAllianceFilterInline(admin.TabularInline):
    model = SovAllianceFilter
    form = SovAllianceFilterForm
    extra = 1
    verbose_name = "Sov Alliance"
    verbose_name_plural = "Sov Alliances"


@admin.register(DiscordTimerboardConfig)
class DiscordTimerboardConfigAdmin(admin.ModelAdmin):
    inlines = [SovAllianceFilterInline]
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
