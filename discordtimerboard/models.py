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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Discord Timerboard Config"
        verbose_name_plural = "Discord Timerboard Configs"
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} ({self.timerboard_channel_id}/{self.commands_channel_id})"
