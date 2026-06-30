from django.db import migrations, models


SAFE_START_COMMANDS = (
    "node --max-old-space-size=512 server.js",
    "node .next/standalone/server.js",
)


def add_safe_start_commands(apps, schema_editor):
    NodeManagerSettings = apps.get_model("nodeManager", "NodeManagerSettings")
    for settings in NodeManagerSettings.objects.all():
        commands = [line.strip() for line in (settings.allowed_start_commands or "").splitlines() if line.strip()]
        changed = False
        for command in SAFE_START_COMMANDS:
            if command not in commands:
                commands.append(command)
                changed = True
        if changed:
            settings.allowed_start_commands = "\n".join(commands)
            settings.save(update_fields=["allowed_start_commands"])


class Migration(migrations.Migration):

    dependencies = [
        ("nodeManager", "0003_nodeapp_memory_limit"),
    ]

    operations = [
        migrations.AlterField(
            model_name="nodemanagersettings",
            name="allowed_start_commands",
            field=models.TextField(
                default=(
                    "npm start\nnpm run start\nyarn start\npnpm start\n"
                    "node server.js\nnode --max-old-space-size=512 server.js\n"
                    "node dist/main.js\nnode build/bin/server.js\nnode .next/standalone/server.js"
                )
            ),
        ),
        migrations.RunPython(add_safe_start_commands, migrations.RunPython.noop),
    ]
