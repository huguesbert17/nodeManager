from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="NodeApp",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("owner_user_id", models.IntegerField(db_index=True)),
                ("owner_username", models.CharField(db_index=True, max_length=50)),
                ("domain", models.CharField(db_index=True, max_length=255)),
                ("website_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("app_name", models.CharField(max_length=64)),
                ("app_root", models.CharField(max_length=500)),
                ("git_url", models.CharField(blank=True, default="", max_length=500)),
                ("branch", models.CharField(blank=True, default="main", max_length=100)),
                ("port", models.IntegerField(unique=True)),
                ("node_version", models.CharField(blank=True, default="", max_length=40)),
                ("package_manager", models.CharField(default="npm", max_length=20)),
                ("install_command", models.CharField(default="npm install", max_length=120)),
                ("build_command", models.CharField(blank=True, default="", max_length=120)),
                ("start_command", models.CharField(default="npm start", max_length=160)),
                ("pm2_name", models.CharField(max_length=180, unique=True)),
                ("env_file_path", models.CharField(blank=True, default="", max_length=500)),
                ("status", models.CharField(choices=[("created", "Created"), ("installing", "Installing"), ("building", "Building"), ("running", "Running"), ("stopped", "Stopped"), ("error", "Error"), ("deleted", "Deleted")], db_index=True, default="created", max_length=20)),
                ("last_error", models.TextField(blank=True, default="")),
                ("deploy_log", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("last_deploy_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "node_manager_apps", "ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="NodeManagerSettings",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("port_range_start", models.IntegerField(default=30000)),
                ("port_range_end", models.IntegerField(default=39999)),
                ("max_apps_per_user", models.IntegerField(default=5)),
                ("allowed_package_managers", models.TextField(default="npm\nyarn\npnpm")),
                ("allowed_install_commands", models.TextField(default="npm install\nnpm ci\nyarn install\npnpm install")),
                ("allowed_build_commands", models.TextField(default="npm run build\nyarn build\npnpm build")),
                ("allowed_start_commands", models.TextField(default="npm start\nnpm run start\nyarn start\npnpm start\nnode server.js\nnode dist/main.js\nnode build/bin/server.js")),
                ("allow_git_deploy", models.BooleanField(default=True)),
                ("allow_env_editor", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "node_manager_settings", "verbose_name": "Node Manager Settings", "verbose_name_plural": "Node Manager Settings"},
        ),
        migrations.AlterUniqueTogether(name="nodeapp", unique_together={("owner_user_id", "domain", "app_name")}),
    ]
