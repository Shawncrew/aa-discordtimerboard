from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DiscordTimerboardConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64, unique=True)),
                (
                    "discord_server_id",
                    models.BigIntegerField(
                        blank=True,
                        help_text="Optional Discord server ID this config belongs to.",
                        null=True,
                    ),
                ),
                (
                    "timerboard_channel_id",
                    models.BigIntegerField(help_text="Channel where timerboard lines are rendered."),
                ),
                (
                    "commands_channel_id",
                    models.BigIntegerField(help_text="Channel where !add/!rm/!refresh commands are accepted."),
                ),
                ("enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Discord Timerboard Config",
                "verbose_name_plural": "Discord Timerboard Configs",
                "ordering": ("name",),
            },
        ),
    ]
