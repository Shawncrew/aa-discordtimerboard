"""Bring the migration state in line with the database and the models.

The id columns of these tables are INT (AutoField) in the database, and the models resolve
to AutoField, but the migration history still recorded BigAutoField. Update the recorded
state only; no DDL is issued.
"""

from django.db import migrations, models

MODELS = [
    "archivedtimer",
    "discordtimerboardconfig",
    "sentnotification",
    "sovalliancefilter",
]


class Migration(migrations.Migration):

    dependencies = [
        ("discordtimerboard", "0009_strikethrough_and_sentnotification"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name=model_name,
                    name="id",
                    field=models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                )
                for model_name in MODELS
            ],
        ),
    ]
