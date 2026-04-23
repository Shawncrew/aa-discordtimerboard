from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("discordtimerboard", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="discordtimerboardconfig",
            name="required_role_ids",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Optional comma-separated Discord role IDs allowed to run commands in this "
                    "commands channel. Leave empty for no Discord-role restriction."
                ),
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name="discordtimerboardconfig",
            name="require_structuretimers_add_perm",
            field=models.BooleanField(
                default=True,
                help_text="Require Alliance Auth permission `structuretimers.add_timer` for add/remove commands.",
            ),
        ),
    ]
