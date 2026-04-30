from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("activity", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentintent",
            name="scenario_run_id",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="paymentintent",
            name="scenario_source",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="paymentintent",
            name="scenario_tags",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddIndex(
            model_name="paymentintent",
            index=models.Index(fields=["tier", "status"], name="activity_pay_tier_0c9652_idx"),
        ),
        migrations.AddIndex(
            model_name="paymentintent",
            index=models.Index(fields=["scenario_run_id"], name="activity_pay_scenar_2cd1e1_idx"),
        ),
    ]
