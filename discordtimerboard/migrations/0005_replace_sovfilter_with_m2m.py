from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("discordtimerboard", "0004_sov_support"),
        ("sovtimer", "0001_initial"),
    ]

    operations = [
        migrations.DeleteModel(
            name="SovAllianceFilter",
        ),
        migrations.AddField(
            model_name="discordtimerboardconfig",
            name="sov_alliances",
            field=models.ManyToManyField(
                blank=True,
                help_text="Alliances whose sovereignty timers appear on this timerboard.",
                related_name="+",
                to="sovtimer.alliance",
            ),
        ),
    ]
