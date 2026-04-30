from django.db import migrations, models


class Migration(migrations.Migration):
    """Matches server-generated migration 0006_alter_archivedtimer_id_and_more."""

    dependencies = [
        ("discordtimerboard", "0005_replace_sovfilter_with_m2m"),
    ]

    operations = [
        migrations.AlterField(
            model_name="archivedtimer",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
        migrations.AlterField(
            model_name="discordtimerboardconfig",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
    ]
