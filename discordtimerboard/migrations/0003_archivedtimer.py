from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("discordtimerboard", "0002_notification_settings"),
    ]

    operations = [
        migrations.CreateModel(
            name="ArchivedTimer",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ("original_id", models.IntegerField(db_index=True, help_text="PK of the deleted Timer.")),
                ("timer_date", models.DateTimeField(blank=True, null=True)),
                ("system_name", models.CharField(blank=True, max_length=64)),
                ("structure_type_name", models.CharField(blank=True, max_length=64)),
                ("structure_name", models.CharField(blank=True, max_length=128)),
                ("owner_name", models.CharField(blank=True, max_length=64)),
                ("timer_type", models.CharField(blank=True, max_length=8)),
                ("archived_at", models.DateTimeField(auto_now_add=True)),
                ("archived_by", models.CharField(blank=True, max_length=128, help_text="Discord user tag who ran !rm")),
            ],
            options={
                "verbose_name": "Archived Timer",
                "verbose_name_plural": "Archived Timers",
                "ordering": ("-archived_at",),
            },
        ),
    ]
