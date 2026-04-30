from django.db import migrations, models


class Migration(migrations.Migration):
    """Matches the server-generated migration that altered id fields to BigAutoField."""

    dependencies = [
        ("discordtimerboard", "0006_auto_server_generated"),
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
        migrations.AlterField(
            model_name="sovalliancefilter",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
    ]
