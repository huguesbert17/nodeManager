import uuid

from django.db import models
from django.utils import timezone


class NodeApp(models.Model):
    STATUS_CREATED = "created"
    STATUS_INSTALLING = "installing"
    STATUS_BUILDING = "building"
    STATUS_RUNNING = "running"
    STATUS_STOPPED = "stopped"
    STATUS_ERROR = "error"
    STATUS_DELETED = "deleted"

    STATUS_CHOICES = (
        (STATUS_CREATED, "Created"),
        (STATUS_INSTALLING, "Installing"),
        (STATUS_BUILDING, "Building"),
        (STATUS_RUNNING, "Running"),
        (STATUS_STOPPED, "Stopped"),
        (STATUS_ERROR, "Error"),
        (STATUS_DELETED, "Deleted"),
    )

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)
    owner_user_id = models.IntegerField(db_index=True)
    owner_username = models.CharField(max_length=50, db_index=True)
    domain = models.CharField(max_length=255, db_index=True)
    website_id = models.IntegerField(null=True, blank=True, db_index=True)
    app_name = models.CharField(max_length=64)
    app_root = models.CharField(max_length=500)
    git_url = models.CharField(max_length=500, blank=True, default="")
    branch = models.CharField(max_length=100, blank=True, default="main")
    port = models.IntegerField(unique=True)
    node_version = models.CharField(max_length=40, blank=True, default="")
    package_manager = models.CharField(max_length=20, default="npm")
    install_command = models.CharField(max_length=120, default="npm install")
    build_command = models.CharField(max_length=120, blank=True, default="")
    start_command = models.CharField(max_length=160, default="npm start")
    pm2_name = models.CharField(max_length=180, unique=True)
    env_file_path = models.CharField(max_length=500, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CREATED, db_index=True)
    last_error = models.TextField(blank=True, default="")
    deploy_log = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_deploy_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "node_manager_apps"
        unique_together = (("owner_user_id", "domain", "app_name"),)
        ordering = ("-created_at",)

    def __str__(self):
        return "%s/%s" % (self.domain, self.app_name)


class NodeManagerSettings(models.Model):
    port_range_start = models.IntegerField(default=30000)
    port_range_end = models.IntegerField(default=39999)
    max_apps_per_user = models.IntegerField(default=5)
    allowed_package_managers = models.TextField(default="npm\nyarn\npnpm")
    allowed_install_commands = models.TextField(default="npm install\nnpm ci\nyarn install\npnpm install")
    allowed_build_commands = models.TextField(default="npm run build\nyarn build\npnpm build")
    allowed_start_commands = models.TextField(
        default="npm start\nnpm run start\nyarn start\npnpm start\nnode server.js\nnode dist/main.js\nnode build/bin/server.js"
    )
    allow_git_deploy = models.BooleanField(default=True)
    allow_env_editor = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "node_manager_settings"
        verbose_name = "Node Manager Settings"
        verbose_name_plural = "Node Manager Settings"

    @classmethod
    def current(cls):
        obj = cls.objects.order_by("id").first()
        if obj:
            return obj
        return cls.objects.create()

    def list_value(self, field_name):
        value = getattr(self, field_name, "") or ""
        return [line.strip() for line in value.splitlines() if line.strip()]
