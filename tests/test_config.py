from smx_leads.core.config import LeadsConfig, build_leads_config_from_env


def test_config_defaults_are_safe():
    config = LeadsConfig.from_mapping(
        {"database_url": "sqlite+pysqlite:///:memory:"}
    )

    assert config.database_url == "sqlite+pysqlite:///:memory:"
    assert config.host_site_title == "SyntaxMatrix"
    assert config.module_title == "Leads"
    assert config.host_home_url == "/"
    assert config.email_provider == "none"
    assert config.assets_dir == "./plugins/leads/assets"
    assert config.logo_url == "/leads/assets/logo.png"
    assert config.favicon_url == "/leads/assets/favicon.png"
    assert config.smtp_use_tls is True


def test_config_can_be_supplied_from_mapping():
    config = LeadsConfig.from_mapping(
        {
            "database_url": "sqlite+pysqlite:///:memory:",
            "admin_token": "admin-secret",
            "flask_secret_key": "flask-secret",
            "host_site_title": "Client Site",
            "host_home_url": "https://client.example.com",
            "module_title": "Client Leads",
            "public_base_url": "https://client.example.com",
            "auto_init": True,
            "assets_dir": "./custom-assets",
            "logo_url": "/custom/logo.png",
            "favicon_url": "/custom/favicon.png",
            "email_provider": "smtp",
            "smtp_port": "587",
            "smtp_use_tls": "1",
            "notify_to_email": "admin@example.com",
        }
    )

    assert config.admin_token == "admin-secret"
    assert config.flask_secret_key == "flask-secret"
    assert config.host_site_title == "Client Site"
    assert config.host_home_url == "https://client.example.com"
    assert config.module_title == "Client Leads"
    assert config.public_base_url == "https://client.example.com"
    assert config.auto_init is True
    assert config.assets_dir == "./custom-assets"
    assert config.logo_url == "/custom/logo.png"
    assert config.favicon_url == "/custom/favicon.png"
    assert config.email_provider == "smtp"
    assert config.smtp_port == 587
    assert config.smtp_use_tls is True
    assert config.notify_to_email == "admin@example.com"


def test_config_can_be_loaded_from_env_file(tmp_path):
    env_file = tmp_path / ".smx_leads.env"

    env_file.write_text(
        "\n".join(
            [
                "SMX_LEADS_DATABASE_URL=sqlite+pysqlite:///:memory:",
                "SMX_LEADS_ADMIN_TOKEN=admin-secret",
                "SMX_LEADS_FLASK_SECRET_KEY=flask-secret",
                "SMX_LEADS_HOST_SITE_TITLE=Client Site",
                "SMX_LEADS_HOST_HOME_URL=https://client.example.com",
                "SMX_LEADS_MODULE_TITLE=Client Leads",
                "SMX_LEADS_PUBLIC_BASE_URL=https://client.example.com",
                "SMX_LEADS_AUTO_INIT=1",
                "SMX_LEADS_ASSETS_DIR=./client-assets",
                "SMX_LEADS_LOGO_URL=/leads/assets/logo.png",
                "SMX_LEADS_FAVICON_URL=/leads/assets/favicon.png",
                "SMX_LEADS_EMAIL_PROVIDER=smtp",
                "SMX_LEADS_SMTP_PORT=587",
                "SMX_LEADS_SMTP_USE_TLS=1",
                "SMX_LEADS_NOTIFY_TO_EMAIL=admin@example.com",
            ]
        ),
        encoding="utf-8",
    )

    values = build_leads_config_from_env(env_file=env_file)
    config = LeadsConfig.from_mapping(values)

    assert values["database_url"] == "sqlite+pysqlite:///:memory:"
    assert values["admin_token"] == "admin-secret"
    assert values["flask_secret_key"] == "flask-secret"
    assert values["host_site_title"] == "Client Site"
    assert values["host_home_url"] == "https://client.example.com"
    assert values["module_title"] == "Client Leads"
    assert values["public_base_url"] == "https://client.example.com"
    assert values["auto_init"] is True
    assert values["assets_dir"] == "./client-assets"
    assert values["logo_url"] == "/leads/assets/logo.png"
    assert values["favicon_url"] == "/leads/assets/favicon.png"
    assert values["smtp_port"] == 587
    assert config.notify_to_email == "admin@example.com"
