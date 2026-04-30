from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("discordtimerboard", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="discordtimerboardconfig",
            name="warning_notifications_enabled",
            field=models.BooleanField(
                default=True,
                help_text="Post a warning message to the commands channel before a timer fires.",
            ),
        ),
        migrations.AddField(
            model_name="discordtimerboardconfig",
            name="start_notifications_enabled",
            field=models.BooleanField(
                default=True,
                help_text="Post a message to the commands channel when a timer starts.",
            ),
        ),
        migrations.AddField(
            model_name="discordtimerboardconfig",
            name="warning_minutes",
            field=models.PositiveIntegerField(
                default=60,
                help_text="How many minutes before a timer to post the warning notification.",
            ),
        ),
    ]
