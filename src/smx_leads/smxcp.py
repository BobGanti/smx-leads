from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SCAFFOLD_DIR_NAME = "leads"
SETUP_FILE_NAME = "smx_leads_setup.py"
ENV_EXAMPLE_FILE_NAME = ".smx_leads_example.env"
ENV_FILE_NAME = ".smx_leads.env"
DEPLOY_ENV_EXAMPLE_FILE_NAME = ".smx_leads.deploy_example.env"
DATA_DIR_NAME = "data"
ASSETS_DIR_NAME = "assets"
DEV_DB_FILE_NAME = "smx_leads_dev.db"


FALLBACK_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\r\n-\xb4"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


@dataclass(frozen=True)
class SmxLeadsScaffold:
    project_root: Path
    scaffold_dir: Path
    data_dir: Path
    assets_dir: Path
    setup_file: Path
    env_example_file: Path
    env_file: Path
    deploy_env_example_file: Path
    db_file: Path
    logo_file: Path
    favicon_file: Path


def ensure_leads_scaffold(
    *,
    project_root: str | Path | None = None,
) -> SmxLeadsScaffold:
    """
    Ensure a client project has the smx-leads integration scaffold.

    This creates missing files only. Existing customer files are never overwritten.
    """
    root = Path(project_root or Path.cwd()).resolve()

    scaffold_dir = root / SCAFFOLD_DIR_NAME
    data_dir = scaffold_dir / DATA_DIR_NAME
    assets_dir = scaffold_dir / ASSETS_DIR_NAME
    db_file = data_dir / DEV_DB_FILE_NAME
    logo_file = assets_dir / "logo.png"
    favicon_file = assets_dir / "favicon.png"

    init_file = scaffold_dir / "__init__.py"
    setup_file = scaffold_dir / SETUP_FILE_NAME
    env_example_file = scaffold_dir / ENV_EXAMPLE_FILE_NAME
    env_file = scaffold_dir / ENV_FILE_NAME
    deploy_env_example_file = scaffold_dir / DEPLOY_ENV_EXAMPLE_FILE_NAME

    scaffold_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    _write_if_missing(init_file, "")
    _write_if_missing(setup_file, _render_setup_file())
    _write_if_missing(env_example_file, _render_env_example_file())
    _write_if_missing(env_file, _render_runtime_env_file(db_file=db_file))
    _write_if_missing(deploy_env_example_file, _render_deploy_env_example_file())
    _write_bytes_if_missing(logo_file, FALLBACK_PNG_BYTES)
    _write_bytes_if_missing(favicon_file, FALLBACK_PNG_BYTES)

    return SmxLeadsScaffold(
        project_root=root,
        scaffold_dir=scaffold_dir,
        data_dir=data_dir,
        assets_dir=assets_dir,
        setup_file=setup_file,
        env_example_file=env_example_file,
        env_file=env_file,
        deploy_env_example_file=deploy_env_example_file,
        db_file=db_file,
        logo_file=logo_file,
        favicon_file=favicon_file,
    )


def _write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        return

    path.write_text(content, encoding="utf-8")


def _write_bytes_if_missing(path: Path, content: bytes) -> None:
    if path.exists():
        return

    path.write_bytes(content)


def _sqlite_url_for(path: Path) -> str:
    return "sqlite+pysqlite:///" + path.resolve().as_posix()


def _render_setup_file() -> str:
    return '''from __future__ import annotations

from pathlib import Path

from smx_leads import setup_leads as _setup_leads


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def setup_leads(app, *, init_schema: bool = True):
    """
    Initialize smx-leads for this client project.

    This file is customer-owned after creation.
    smx-leads will not overwrite it.
    """
    return _setup_leads(
        app=app,
        project_root=PROJECT_ROOT,
        init_schema=init_schema,
    )


def register_leads_plugin(app, *, init_schema: bool = True):
    """
    Compatibility alias for plugin-style host applications.
    """
    return setup_leads(
        app,
        init_schema=init_schema,
    )
'''


def _render_env_example_file() -> str:
    return '''# smx-leads client project environment example
#
# Copy this file to:
#
#   leads/.smx_leads.env
#
# Then replace placeholder values.
#
# Generate strong secrets with:
#
#   python -c "import secrets; print(secrets.token_urlsafe(32))"

SMX_LEADS_DATABASE_URL=sqlite+pysqlite:///./leads/data/smx_leads_dev.db
SMX_LEADS_ADMIN_TOKEN=replace-with-a-strong-admin-token
SMX_LEADS_FLASK_SECRET_KEY=replace-with-a-strong-session-secret

SMX_LEADS_HOST_SITE_TITLE=SyntaxMatrix
SMX_LEADS_HOST_HOME_URL=/
SMX_LEADS_MODULE_TITLE=Leads
SMX_LEADS_PUBLIC_BASE_URL=http://localhost:5055
SMX_LEADS_ASSETS_DIR=./leads/assets
SMX_LEADS_LOGO_URL=/leads/assets/logo.png
SMX_LEADS_FAVICON_URL=/leads/assets/favicon.png
'''


def _render_runtime_env_file(*, db_file: Path) -> str:
    return f'''# smx-leads local runtime environment
#
# This file is customer-owned after creation.
# smx-leads will not overwrite it.
#
# Generate strong secrets with:
#
#   python -c "import secrets; print(secrets.token_urlsafe(32))"

SMX_LEADS_DATABASE_URL={_sqlite_url_for(db_file)}
SMX_LEADS_ADMIN_TOKEN=local-leads-admin-token
SMX_LEADS_FLASK_SECRET_KEY=replace-with-a-strong-session-secret

SMX_LEADS_HOST_SITE_TITLE=SyntaxMatrix
SMX_LEADS_HOST_HOME_URL=/
SMX_LEADS_MODULE_TITLE=Leads
SMX_LEADS_PUBLIC_BASE_URL=http://localhost:5055
SMX_LEADS_ASSETS_DIR=./leads/assets
SMX_LEADS_LOGO_URL=/leads/assets/logo.png
SMX_LEADS_FAVICON_URL=/leads/assets/favicon.png
'''


def _render_deploy_env_example_file() -> str:
    return '''# smx-leads production deployment example
#
# Purpose:
# - Copy these variable names into your Cloud Run / hosting deployment script.
# - Replace placeholder values with your client/project values.
# - Do not put raw secret values in this file.
#
# Local development runtime config:
#   leads/.smx_leads.env
#
# Production deployment example:
#   leads/.smx_leads.deploy_example.env
#
# smxCP rule:
#   one Secret Manager vault -> one SMX_LEADS_* Cloud Run env var


# ---------------------------------------------------------------------
# Required production non-secret env vars
# Use these with: gcloud run deploy/update --set-env-vars
# ---------------------------------------------------------------------

SMX_LEADS_PUBLIC_BASE_URL=https://your-domain.com
SMX_LEADS_HOST_SITE_TITLE=Your Client Site
SMX_LEADS_HOST_HOME_URL=https://your-domain.com
SMX_LEADS_MODULE_TITLE=Leads

SMX_LEADS_DATABASE_URL=postgresql+psycopg://user:password@host:5432/database
SMX_LEADS_ASSETS_DIR=/app/leads/assets
SMX_LEADS_LOGO_URL=/leads/assets/logo.png
SMX_LEADS_FAVICON_URL=/leads/assets/favicon.png
SMX_LEADS_AUTO_INIT=1


# ---------------------------------------------------------------------
# Optional production email env vars
# Use these if lead notifications should be emailed.
# ---------------------------------------------------------------------

SMX_LEADS_EMAIL_PROVIDER=smtp
SMX_LEADS_SMTP_HOST=smtp.gmail.com
SMX_LEADS_SMTP_PORT=587
SMX_LEADS_SMTP_USERNAME=your-smtp-username
SMX_LEADS_DEFAULT_FROM_EMAIL=your-from-email
SMX_LEADS_NOTIFY_TO_EMAIL=admin@example.com
SMX_LEADS_SMTP_USE_TLS=1


# ---------------------------------------------------------------------
# Required production secret mappings
# Use these with: gcloud run deploy/update --set-secrets
#
# Format:
#   CLOUD_RUN_ENV_VAR=secret-manager-vault-name:latest
# ---------------------------------------------------------------------

SMX_LEADS_ADMIN_TOKEN=leads-admin-token-vault:latest
SMX_LEADS_FLASK_SECRET_KEY=leads-flask-secret-key-vault:latest


# ---------------------------------------------------------------------
# Optional production secret mappings
# ---------------------------------------------------------------------

SMX_LEADS_SMTP_PASSWORD=leads-smtp-password-vault:latest
'''
