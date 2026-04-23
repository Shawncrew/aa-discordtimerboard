from django.db import models


class DiscordTimerboardConfig(models.Model):
    name = models.CharField(max_length=64, unique=True)
    guild_id = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Optional Discord guild/server id this config belongs to.",
    )
    timerboard_channel_id = models.BigIntegerField(
        help_text="Channel where timerboard lines are rendered."
    )
    commands_channel_id = models.BigIntegerField(
        help_text="Channel where !add/!rm/!refresh commands are accepted."
    )
    required_role_ids = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text=(
            "Optional comma-separated Discord role IDs allowed to run commands in this "
            "commands channel. Leave empty for no Discord-role restriction."
        ),
    )
    require_structuretimers_add_perm = models.BooleanField(
        default=True,
        help_text="Require Alliance Auth permission `structuretimers.add_timer` for add/remove commands.",
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
