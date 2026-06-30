from django.db import migrations, models


NEXT_START_COMMAND = "node node_modules/next/dist/bin/next start"


def add_direct_next_start_command(apps, schema_editor):
    NodeManagerSettings = apps.get_model("nodeManager", "NodeManagerSettings")
    for settings in NodeManagerSettings.objects.all():
        commands = [line.strip() for line in (settings.allowed_start_commands or "").splitlines() if line.strip()]
        if NEXT_START_COMMAND not in commands:
            insert_at = 0
            for index, command in enumerate(commands):
                if command.startswith("npm") or command.startswith("yarn") or command.startswith("pnpm"):
                    insert_at = index + 1
            commands.insert(insert_at, NEXT_START_COMMAND)
            settings.allowed_start_commands = "\n".join(commands)
            settings.save(update_fields=["allowed_start_commands"])


class Migration(migrations.Migration):
    dependencies = [
        ("nodeManager", "0004_update_default_start_commands"),
    ]

    operations = [
        migrations.AlterField(
            model_name="nodemanagersettings",
            name="allowed_start_commands",
            field=models.TextField(
                default=(
                    "npm start\nnpm run start\nyarn start\npnpm start\n"
                    "node node_modules/next/dist/bin/next start\n"
                    "node server.js\nnode --max-old-space-size=512 server.js\n"
                    "node dist/main.js\nnode build/bin/server.js\nnode .next/standalone/server.js"
                )
            ),
        ),
        migrations.RunPython(add_direct_next_start_command, migrations.RunPython.noop),
    ]
