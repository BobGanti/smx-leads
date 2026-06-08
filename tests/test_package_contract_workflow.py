from pathlib import Path

from flask import Flask

from smx_leads import ensure_leads_scaffold, setup_leads


def test_setup_leads_import_contract_exists():
    assert callable(setup_leads)


def test_scaffold_creates_client_owned_leads_folder(tmp_path):
    scaffold = ensure_leads_scaffold(project_root=tmp_path)

    assert scaffold.scaffold_dir == tmp_path / "leads"
    assert scaffold.data_dir == tmp_path / "leads" / "data"
    assert scaffold.db_file == tmp_path / "leads" / "data" / "smx_leads_dev.db"
    assert scaffold.deploy_env_example_file == tmp_path / "leads" / ".smx_leads.deploy_example.env"

    assert (tmp_path / "leads" / "__init__.py").is_file()
    assert (tmp_path / "leads" / "smx_leads_setup.py").is_file()
    assert (tmp_path / "leads" / ".smx_leads.env").is_file()
    assert (tmp_path / "leads" / ".smx_leads_example.env").is_file()
    assert (tmp_path / "leads" / ".smx_leads.deploy_example.env").is_file()

    setup_text = (tmp_path / "leads" / "smx_leads_setup.py").read_text(
        encoding="utf-8"
    )
    env_text = (tmp_path / "leads" / ".smx_leads.env").read_text(
        encoding="utf-8"
    )
    deploy_text = (tmp_path / "leads" / ".smx_leads.deploy_example.env").read_text(
        encoding="utf-8"
    )

    assert "from smx_leads import setup_leads as _setup_leads" in setup_text
    assert "def setup_leads" in setup_text
    assert "def register_leads_plugin" in setup_text

    assert "SMX_LEADS_DATABASE_URL=sqlite+pysqlite:///" in env_text
    assert "SMX_LEADS_ADMIN_TOKEN=local-leads-admin-token" in env_text

    assert "SMX_LEADS_PUBLIC_BASE_URL=https://your-domain.com" in deploy_text
    assert "SMX_LEADS_ADMIN_TOKEN=leads-admin-token-vault:latest" in deploy_text


def test_setup_leads_creates_scaffold_and_returns_app(tmp_path):
    app = Flask(__name__)

    result = setup_leads(app, project_root=tmp_path)

    assert result is app
    assert (tmp_path / "leads" / "smx_leads_setup.py").is_file()


def test_package_includes_html_templates_for_wheel_distribution():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "[tool.setuptools.package-data]" in pyproject
    assert "templates/admin/*.html" in pyproject
    assert "templates/public/*.html" in pyproject
