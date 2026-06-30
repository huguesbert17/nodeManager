from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("nodeManager", "0002_nodeapp_public_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="nodeapp",
            name="memory_limit",
            field=models.CharField(blank=True, default="700M", max_length=20),
        ),
    ]
