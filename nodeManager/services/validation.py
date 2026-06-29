import re

from django import forms

APP_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{1,63}$")
DOMAIN_RE = re.compile(r"^(?=.{1,255}$)([a-zA-Z0-9][a-zA-Z0-9-]{0,62}\.)+[a-zA-Z]{2,}$")
ENV_KEY_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9._/@-]{1,100}$")

DANGEROUS_TOKENS = (
    ";",
    "&&",
    "||",
    "|",
    ">",
    "<",
    "`",
    "$(",
    "sudo",
    "su",
    "rm -rf",
    "chmod 777",
    "chown root",
    "curl",
    "wget",
    "bash",
    "sh",
    "python",
    "perl",
    "nc",
    "netcat",
)


def validate_app_name(value):
    if not APP_NAME_RE.match(value or ""):
        raise forms.ValidationError("Use 2-64 letters, numbers, dashes, or underscores. Start with a letter or number.")


def validate_domain(value):
    if not DOMAIN_RE.match(value or ""):
        raise forms.ValidationError("Invalid domain name.")


def validate_git_url(value):
    if not (value.startswith("https://") or value.startswith("git@")):
        raise forms.ValidationError("Git URL must start with https:// or git@.")
    if any(token in value for token in (";", "&&", "||", "|", "`", "$(", ">", "<")):
        raise forms.ValidationError("Git URL contains unsafe shell characters.")


def validate_branch(value):
    if value and not BRANCH_RE.match(value):
        raise forms.ValidationError("Branch name contains unsupported characters.")


def validate_command(value, allowed_commands):
    normalized = " ".join((value or "").strip().split())
    lowered = normalized.lower()
    for token in DANGEROUS_TOKENS:
        if token in lowered:
            raise forms.ValidationError("Command contains a blocked token: %s" % token)
    if normalized not in allowed_commands:
        raise forms.ValidationError("Command is not allowed by Node Manager settings.")


def parse_env_text(value):
    env = {}
    for line_number, raw_line in enumerate((value or "").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise forms.ValidationError("Environment line %s must use KEY=value format." % line_number)
        key, env_value = line.split("=", 1)
        key = key.strip()
        if not ENV_KEY_RE.match(key):
            raise forms.ValidationError("Invalid environment key on line %s." % line_number)
        env[key] = env_value.strip()
    return env


def validate_env_text(value):
    parse_env_text(value)
