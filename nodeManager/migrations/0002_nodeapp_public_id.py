import uuid

from django.db import migrations, models


def populate_public_ids(apps, schema_editor):
    NodeApp = apps.get_model("nodeManager", "NodeApp")
    for app in NodeApp.objects.filter(public_id__isnull=True):
        app.public_id = uuid.uuid4()
        app.save(update_fields=["public_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("nodeManager", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="nodeapp",
            name="public_id",
            field=models.UUIDField(db_index=True, editable=False, null=True),
        ),
        migrations.RunPython(populate_public_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="nodeapp",
            name="public_id",
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
