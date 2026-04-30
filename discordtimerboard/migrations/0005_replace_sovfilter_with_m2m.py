from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("discordtimerboard", "0004_sov_support"),
        ("sovtimer", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SovAllianceFilter",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                (
                    "config",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sov_alliance_filters",
                        to="discordtimerboard.discordtimerboardconfig",
                    ),
                ),
                (
                    "alliance",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="sovtimer.alliance",
                    ),
                ),
            ],
            options={
                "unique_together": {("config", "alliance")},
            },
        ),
        migrations.AddField(
            model_name="discordtimerboardconfig",
            name="sov_alliances",
            field=models.ManyToManyField(
                blank=True,
                help_text="Alliances whose sovereignty timers appear on this timerboard.",
                related_name="+",
                through="discordtimerboard.SovAllianceFilter",
                to="sovtimer.alliance",
            ),
        ),
    ]
