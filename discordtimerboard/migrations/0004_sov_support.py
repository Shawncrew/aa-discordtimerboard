from django.db import migrations, models


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
    ]
