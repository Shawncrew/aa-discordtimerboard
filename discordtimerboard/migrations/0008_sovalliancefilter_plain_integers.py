from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Replace the FK-based SovAllianceFilter through model with plain integer
    fields so MySQL never has to enforce foreign key constraints.
    """

    dependencies = [
        ("discordtimerboard", "0005_replace_sovfilter_with_m2m"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                # Drop old table(s) safely regardless of current DB state.
                migrations.RunSQL(
                    "DROP TABLE IF EXISTS `discordtimerboard_sovalliancefilter`",
                    reverse_sql=migrations.RunSQL.noop,
                ),
                # Create the new constraint-free table.
                migrations.RunSQL(
                    sql="""
                        CREATE TABLE `discordtimerboard_sovalliancefilter` (
                            `id` bigint NOT NULL AUTO_INCREMENT PRIMARY KEY,
                            `config_id` integer NOT NULL,
                            `alliance_id` bigint unsigned NOT NULL,
                            UNIQUE KEY `dtb_sov_config_alliance_uniq` (`config_id`, `alliance_id`),
                            KEY `dtb_sov_config_id_idx` (`config_id`)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """,
                    reverse_sql="DROP TABLE IF EXISTS `discordtimerboard_sovalliancefilter`",
                ),
            ],
            state_operations=[
                # Remove the M2M field from the config model.
                migrations.RemoveField(
                    model_name="discordtimerboardconfig",
                    name="sov_alliances",
                ),
                # Replace the old through model with the new plain-integer one.
                migrations.DeleteModel(name="SovAllianceFilter"),
                migrations.CreateModel(
                    name="SovAllianceFilter",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("config_id", models.IntegerField(db_index=True)),
                        ("alliance_id", models.PositiveBigIntegerField()),
                    ],
                    options={"unique_together": {("config_id", "alliance_id")}},
                ),
            ],
        ),
    ]
