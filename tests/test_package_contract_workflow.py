from pathlib import Path

from flask import Flask

from smx_leads import ensure_leads_scaffold, setup_leads


def test_setup_leads_import_contract_exists():
    assert callable(setup_leads)


def test_scaffold_creates_client_owned_leads_folder(tmp_path):
    scaffold = ensure_leads_scaffold(project_root=tmp_path)

    assert scaffold.scaffold_dir == tmp_path / "plugins" / "leads"
    assert scaffold.data_dir == tmp_path / "plugins" / "leads" / "data"
    assert scaffold.assets_dir == tmp_path / "plugins" / "leads" / "assets"
    assert scaffold.db_file == tmp_path / "plugins" / "leads" / "data" / "smx_leads_dev.db"
    assert scaffold.deploy_env_example_file == tmp_path / "plugins" / "leads" / ".smx_leads.deploy_example.env"
    assert scaffold.logo_file == tmp_path / "plugins" / "leads" / "assets" / "logo.png"
    assert scaffold.favicon_file == tmp_path / "plugins" / "leads" / "assets" / "favicon.png"

    assert (tmp_path / "plugins" / "leads" / "__init__.py").is_file()
    assert (tmp_path / "plugins" / "leads" / "smx_leads_setup.py").is_file()
    assert (tmp_path / "plugins" / "leads" / ".smx_leads.env").is_file()
    assert (tmp_path / "plugins" / "leads" / ".smx_leads_example.env").is_file()
    assert (tmp_path / "plugins" / "leads" / ".smx_leads.deploy_example.env").is_file()
    assert (tmp_path / "plugins" / "leads" / "assets").is_dir()
    assert (tmp_path / "plugins" / "leads" / "assets" / "logo.png").is_file()
    assert (tmp_path / "plugins" / "leads" / "assets" / "favicon.png").is_file()

    setup_text = (tmp_path / "plugins" / "leads" / "smx_leads_setup.py").read_text(
        encoding="utf-8"
    )
    env_text = (tmp_path / "plugins" / "leads" / ".smx_leads.env").read_text(
        encoding="utf-8"
    )
    deploy_text = (tmp_path / "plugins" / "leads" / ".smx_leads.deploy_example.env").read_text(
        encoding="utf-8"
    )

    assert "from smx_leads import setup_leads as _setup_leads" in setup_text
    assert "def setup_leads" in setup_text
    assert "def register_leads_plugin" in setup_text
    assert "def register_leads_plugin(smx_app, *, init_schema: bool = True, ai_profile=None):" in setup_text
    assert "PROJECT_ROOT = Path(__file__).resolve().parents[2]" in setup_text
    assert "ai_profile=ai_profile" in setup_text

    assert "SMX_LEADS_DATABASE_URL=sqlite+pysqlite:///" in env_text
    assert "SMX_LEADS_ADMIN_TOKEN=local-leads-admin-token" in env_text
    assert "SMX_LEADS_ASSETS_DIR=" in env_text
    assert "/leads/assets" in env_text.replace("\\", "/")
    assert "SMX_LEADS_LOGO_URL=/leads/assets/logo.png" in env_text
    assert "SMX_LEADS_FAVICON_URL=/leads/assets/favicon.png" in env_text

    assert "SMX_LEADS_PUBLIC_BASE_URL=https://your-domain.com" in deploy_text
    assert "SMX_LEADS_ADMIN_TOKEN=leads-admin-token-vault:latest" in deploy_text


def test_setup_leads_creates_scaffold_and_returns_app(tmp_path):
    app = Flask(__name__)

    result = setup_leads(app, project_root=tmp_path)

    assert result is app
    assert (tmp_path / "plugins" / "leads" / "smx_leads_setup.py").is_file()


def test_package_includes_html_templates_for_wheel_distribution():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "[tool.setuptools.package-data]" in pyproject
    assert "templates/admin/*.html" in pyproject
    assert "templates/public/*.html" in pyproject


def test_package_has_default_branding_assets():
    logo = Path("src/smx_leads/default_assets/logo.png")
    favicon = Path("src/smx_leads/default_assets/favicon.png")

    assert logo.is_file()
    assert favicon.is_file()
    assert logo.read_bytes().startswith(b"\x89PNG")
    assert favicon.read_bytes().startswith(b"\x89PNG")
