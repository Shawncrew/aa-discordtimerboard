from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("discordtimerboard", "0003_archivedtimer"),
    ]

    operations = [
        migrations.AddField(
            model_name="discordtimerboardconfig",
            name="sov_notifications_enabled",
            field=models.BooleanField(
                default=False,
                help_text="Include sovereignty hub timers from aa-sov-timer on this timerboard.",
            ),
        ),
        migrations.CreateModel(
            name="SovAllianceFilter",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                (
                    "config",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sov_alliance_filters",
                        to="discordtimerboard.discordtimerboardconfig",
                    ),
                ),
                ("alliance_id", models.PositiveBigIntegerField(help_text="EVE alliance ID to include.")),
                (
                    "alliance_name",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        help_text="Label only — not used for filtering.",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sov Alliance Filter",
                "verbose_name_plural": "Sov Alliance Filters",
                "unique_together": {("config", "alliance_id")},
            },
        ),
    ]
