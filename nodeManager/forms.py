from django import forms

from .models import NodeManagerSettings
from .services.validation import validate_app_name, validate_command, validate_env_text, validate_git_url


class NodeAppCreateForm(forms.Form):
    domain = forms.ChoiceField()
    app_name = forms.CharField(max_length=64)
    git_url = forms.CharField(max_length=500, required=False)
    branch = forms.CharField(max_length=100, required=False, initial="main")
    package_manager = forms.ChoiceField(choices=())
    install_command = forms.CharField(max_length=120, initial="npm install")
    build_command = forms.CharField(max_length=120, required=False)
    start_command = forms.CharField(max_length=160, initial="npm start")
    environment = forms.CharField(required=False, widget=forms.Textarea)

    def __init__(self, *args, domains=None, settings_obj=None, **kwargs):
        super().__init__(*args, **kwargs)
        settings_obj = settings_obj or NodeManagerSettings.current()
        domains = domains or []
        self.settings_obj = settings_obj
        self.fields["domain"].choices = [(domain, domain) for domain in domains]
        managers = settings_obj.list_value("allowed_package_managers")
        self.fields["package_manager"].choices = [(item, item) for item in managers]

    def clean_app_name(self):
        value = self.cleaned_data["app_name"].strip()
        validate_app_name(value)
        return value

    def clean_git_url(self):
        value = self.cleaned_data.get("git_url", "").strip()
        if value:
            if not self.settings_obj.allow_git_deploy:
                raise forms.ValidationError("Git deploy is disabled by the administrator.")
            validate_git_url(value)
        return value

    def clean_branch(self):
        return (self.cleaned_data.get("branch") or "main").strip()

    def clean_install_command(self):
        value = self.cleaned_data["install_command"].strip()
        validate_command(value, self.settings_obj.list_value("allowed_install_commands"))
        return value

    def clean_build_command(self):
        value = (self.cleaned_data.get("build_command") or "").strip()
        if value:
            validate_command(value, self.settings_obj.list_value("allowed_build_commands"))
        return value

    def clean_start_command(self):
        value = self.cleaned_data["start_command"].strip()
        validate_command(value, self.settings_obj.list_value("allowed_start_commands"))
        return value

    def clean_environment(self):
        value = self.cleaned_data.get("environment") or ""
        if value and not self.settings_obj.allow_env_editor:
            raise forms.ValidationError("Environment editing is disabled by the administrator.")
        validate_env_text(value)
        return value


class NodeManagerSettingsForm(forms.ModelForm):
    class Meta:
        model = NodeManagerSettings
        fields = (
            "port_range_start",
            "port_range_end",
            "max_apps_per_user",
            "allowed_package_managers",
            "allowed_install_commands",
            "allowed_build_commands",
            "allowed_start_commands",
            "allow_git_deploy",
            "allow_env_editor",
        )

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("port_range_start")
        end = cleaned.get("port_range_end")
        if start and end and start >= end:
            raise forms.ValidationError("Port range start must be lower than port range end.")
        if start and start < 1024:
            raise forms.ValidationError("Use an unprivileged internal port range above 1024.")
        return cleaned
