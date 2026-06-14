from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os


@dataclass(frozen=True)
class LeadsConfig:
    database_url: str
    admin_token: str | None = None
    flask_secret_key: str | None = None

    host_site_title: str = "SyntaxMatrix"
    host_home_url: str = "/"
    module_title: str = "Leads"
    public_base_url: str | None = None
    assets_dir: str = "./plugins/leads/assets"
    logo_url: str = "/leads/assets/logo.png"
    favicon_url: str = "/leads/assets/favicon.png"

    auto_init: bool = False

    email_provider: str = "none"
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    default_from_email: str | None = None
    notify_to_email: str | None = None

    @classmethod
    def from_mapping(cls, values: dict[str, Any] | None) -> "LeadsConfig":
        values = values or {}

        return cls(
            database_url=str(
                values.get("database_url")
                or os.getenv("SMX_LEADS_DATABASE_URL")
                or "sqlite+pysqlite:///./plugins/leads/data/smx_leads_dev.db"
            ),
            admin_token=values.get("admin_token") or os.getenv("SMX_LEADS_ADMIN_TOKEN") or None,
            flask_secret_key=values.get("flask_secret_key") or os.getenv("SMX_LEADS_FLASK_SECRET_KEY") or None,
            host_site_title=str(values.get("host_site_title") or os.getenv("SMX_LEADS_HOST_SITE_TITLE") or "SyntaxMatrix"),
            host_home_url=str(values.get("host_home_url") or os.getenv("SMX_LEADS_HOST_HOME_URL") or "/"),
            module_title=str(values.get("module_title") or os.getenv("SMX_LEADS_MODULE_TITLE") or "Leads"),
            public_base_url=values.get("public_base_url") or os.getenv("SMX_LEADS_PUBLIC_BASE_URL") or None,
            assets_dir=str(values.get("assets_dir") or os.getenv("SMX_LEADS_ASSETS_DIR") or "./plugins/leads/assets"),
            logo_url=str(values.get("logo_url") or os.getenv("SMX_LEADS_LOGO_URL") or "/leads/assets/logo.png"),
            favicon_url=str(values.get("favicon_url") or os.getenv("SMX_LEADS_FAVICON_URL") or "/leads/assets/favicon.png"),
            auto_init=bool(values.get("auto_init", False)),
            email_provider=str(values.get("email_provider") or os.getenv("SMX_LEADS_EMAIL_PROVIDER") or "none"),
            smtp_host=values.get("smtp_host") or os.getenv("SMX_LEADS_SMTP_HOST") or None,
            smtp_port=_optional_int(values.get("smtp_port") or os.getenv("SMX_LEADS_SMTP_PORT")),
            smtp_username=values.get("smtp_username") or os.getenv("SMX_LEADS_SMTP_USERNAME") or None,
            smtp_password=values.get("smtp_password") or os.getenv("SMX_LEADS_SMTP_PASSWORD") or None,
            smtp_use_tls=_bool_value(values.get("smtp_use_tls", os.getenv("SMX_LEADS_SMTP_USE_TLS", "1"))),
            default_from_email=values.get("default_from_email") or os.getenv("SMX_LEADS_DEFAULT_FROM_EMAIL") or None,
            notify_to_email=values.get("notify_to_email") or os.getenv("SMX_LEADS_NOTIFY_TO_EMAIL") or None,
        )


ENV_TO_CONFIG = {
    "DATABASE_URL": "database_url",
    "ADMIN_TOKEN": "admin_token",
    "FLASK_SECRET_KEY": "flask_secret_key",
    "HOST_SITE_TITLE": "host_site_title",
    "HOST_HOME_URL": "host_home_url",
    "MODULE_TITLE": "module_title",
    "PUBLIC_BASE_URL": "public_base_url",
    "ASSETS_DIR": "assets_dir",
    "LOGO_URL": "logo_url",
    "FAVICON_URL": "favicon_url",
    "AUTO_INIT": "auto_init",
    "EMAIL_PROVIDER": "email_provider",
    "SMTP_HOST": "smtp_host",
    "SMTP_PORT": "smtp_port",
    "SMTP_USERNAME": "smtp_username",
    "SMTP_PASSWORD": "smtp_password",
    "SMTP_USE_TLS": "smtp_use_tls",
    "DEFAULT_FROM_EMAIL": "default_from_email",
    "NOTIFY_TO_EMAIL": "notify_to_email",
}

BOOLEAN_CONFIG_KEYS = {"auto_init", "smtp_use_tls"}
INTEGER_CONFIG_KEYS = {"smtp_port"}


def load_env_file(env_file: str | os.PathLike[str] | None) -> dict[str, str]:
    if not env_file:
        return {}

    path = Path(env_file)

    if not path.exists():
        return {}

    values: dict[str, str] = {}

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[len("export "):].strip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)

        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key:
            values[key] = value

    return values


def build_leads_config_from_env(
    *,
    env_file: str | os.PathLike[str] | None = "plugins/leads/.smx_leads.env",
    prefix: str = "SMX_LEADS_",
) -> dict[str, Any]:
    file_values = load_env_file(env_file)
    config: dict[str, Any] = {}

    for env_suffix, config_key in ENV_TO_CONFIG.items():
        env_key = f"{prefix}{env_suffix}"

        raw_value = os.getenv(env_key)

        if raw_value is None:
            raw_value = file_values.get(env_key)

        if raw_value is None or raw_value == "":
            continue

        config[config_key] = _coerce_config_value(config_key, raw_value)

    return config


def _coerce_config_value(config_key: str, value: str) -> Any:
    if config_key in BOOLEAN_CONFIG_KEYS:
        return _bool_value(value)

    if config_key in INTEGER_CONFIG_KEYS:
        return int(value)

    return value


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None

    return int(value)
