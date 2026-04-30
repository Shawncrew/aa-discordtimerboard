from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("discordtimerboard", "0008_sovalliancefilter_plain_integers"),
    ]

    operations = [
        migrations.AddField(
            model_name="discordtimerboardconfig",
            name="strikethrough_minutes",
            field=models.PositiveIntegerField(
                default=5,
                help_text="How many minutes to show a fired timer as struck-through before removing it.",
            ),
        ),
        migrations.CreateModel(
            name="SentNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("timer_type", models.CharField(max_length=16)),
                ("timer_id", models.IntegerField(db_index=True)),
                ("notification_type", models.CharField(max_length=16)),
                ("commands_channel_id", models.BigIntegerField()),
                ("sent_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "unique_together": {("timer_type", "timer_id", "notification_type", "commands_channel_id")},
            },
        ),
    ]
