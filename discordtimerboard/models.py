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
    sov_notifications_enabled = models.BooleanField(
        default=False,
        help_text="Include sovereignty hub timers from aa-sov-timer on this timerboard.",
    )
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
    strikethrough_minutes = models.PositiveIntegerField(
        default=5,
        help_text="How many minutes to show a fired timer as struck-through before removing it.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Discord Timerboard Config"
        verbose_name_plural = "Discord Timerboard Configs"
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} ({self.timerboard_channel_id}/{self.commands_channel_id})"


class SovAllianceFilter(models.Model):
    """Maps a config to an alliance ID with no FK constraints (MySQL-safe)."""

    config_id = models.IntegerField(db_index=True)
    alliance_id = models.PositiveBigIntegerField()

    class Meta:
        unique_together = ("config_id", "alliance_id")

    def __str__(self):
        return str(self.alliance_id)


class SentNotification(models.Model):
    """Tracks which notifications have been posted so reboots don't re-alert."""

    WARNING = "warning"
    START = "start"
    STRUCTURE = "structure"
    SOV = "sov"

    timer_type = models.CharField(max_length=16)
    timer_id = models.IntegerField(db_index=True)
    notification_type = models.CharField(max_length=16)
    commands_channel_id = models.BigIntegerField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("timer_type", "timer_id", "notification_type", "commands_channel_id")

    def __str__(self):
        return f"{self.timer_type}:{self.timer_id} {self.notification_type}"


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
