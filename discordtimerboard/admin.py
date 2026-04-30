from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.apps import apps

from .models import ArchivedTimer, DiscordTimerboardConfig, SentNotification, SovAllianceFilter


class DiscordTimerboardConfigForm(forms.ModelForm):
    sov_alliances = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=FilteredSelectMultiple("sov alliances", False),
        label="Sov alliances",
        help_text="Alliances whose sovereignty timers appear on this timerboard.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            Alliance = apps.get_model("sovtimer", "Alliance")
            qs = Alliance.objects.order_by("name")
            self.fields["sov_alliances"].queryset = qs
            self.fields["sov_alliances"].label_from_instance = lambda obj: obj.name
            if self.instance.pk:
                current_ids = list(
                    SovAllianceFilter.objects.filter(config_id=self.instance.pk)
                    .values_list("alliance_id", flat=True)
                )
                self.fields["sov_alliances"].initial = qs.filter(alliance_id__in=current_ids)
        except LookupError:
            del self.fields["sov_alliances"]

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
        "strikethrough_minutes",
        "updated_at",
    )
    list_filter = ("enabled", "sov_notifications_enabled", "warning_notifications_enabled", "start_notifications_enabled")
    search_fields = (
        "name",
        "discord_server_id",
        "timerboard_channel_id",
        "commands_channel_id",
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if "sov_alliances" not in form.fields:
            return
        selected = form.cleaned_data.get("sov_alliances") or []
        selected_ids = {a.alliance_id for a in selected}
        SovAllianceFilter.objects.filter(config_id=obj.pk).exclude(
            alliance_id__in=selected_ids
        ).delete()
        existing_ids = set(
            SovAllianceFilter.objects.filter(config_id=obj.pk).values_list("alliance_id", flat=True)
        )
        for alliance in selected:
            if alliance.alliance_id not in existing_ids:
                SovAllianceFilter.objects.create(config_id=obj.pk, alliance_id=alliance.alliance_id)


@admin.register(SentNotification)
class SentNotificationAdmin(admin.ModelAdmin):
    list_display = ("timer_type", "timer_id", "notification_type", "commands_channel_id", "sent_at")
    list_filter = ("timer_type", "notification_type")
    readonly_fields = ("timer_type", "timer_id", "notification_type", "commands_channel_id", "sent_at")


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
