from django.db import models


class DiscordTimerboardConfig(models.Model):
    name = models.CharField(max_length=64, unique=True)
    discord_server_id = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Optional Discord server ID this config belongs to.",
    )
    timerboard_channel_id = models.BigIntegerField(
        help_text="Channel where timerboard lines are rendered."
    )
    commands_channel_id = models.BigIntegerField(
        help_text="Channel where !add/!rm/!refresh commands are accepted."
    )
    enabled = models.BooleanField(default=True)
    warning_notifications_enabled = models.BooleanField(
        default=True,
        help_text="Post a warning message to the commands channel before a timer fires.",
    )
    start_notifications_enabled = models.BooleanField(
        default=True,
        help_text="Post a message to the commands channel when a timer starts.",
    )
    warning_minutes = models.PositiveIntegerField(
        default=60,
        help_text="How many minutes before a timer to post the warning notification.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Discord Timerboard Config"
        verbose_name_plural = "Discord Timerboard Configs"
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} ({self.timerboard_channel_id}/{self.commands_channel_id})"


class ArchivedTimer(models.Model):
    """Snapshot of a structuretimers Timer captured when it is deleted via !rm."""

    original_id = models.IntegerField(db_index=True, help_text="PK of the deleted Timer.")
    timer_date = models.DateTimeField(null=True, blank=True)
    system_name = models.CharField(max_length=64, blank=True)
    structure_type_name = models.CharField(max_length=64, blank=True)
    structure_name = models.CharField(max_length=128, blank=True)
    owner_name = models.CharField(max_length=64, blank=True)
    timer_type = models.CharField(max_length=8, blank=True)
    archived_at = models.DateTimeField(auto_now_add=True)
    archived_by = models.CharField(max_length=128, blank=True, help_text="Discord user tag who ran !rm")

    class Meta:
        verbose_name = "Archived Timer"
        verbose_name_plural = "Archived Timers"
        ordering = ("-archived_at",)

    def __str__(self):
        return f"[{self.original_id}] {self.system_name} {self.timer_date}"
