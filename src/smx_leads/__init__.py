from __future__ import annotations

from pathlib import Path
from flask import Blueprint

from smx_leads.ai import build_lead_ai_client_from_profile
from smx_leads.core.config import build_leads_config_from_env
from smx_leads.routes_admin import create_admin_leads_blueprint
from smx_leads.routes_public import create_public_leads_blueprint
from smx_leads.runtime import LeadsRuntime
from smx_leads.smxcp import ensure_leads_scaffold


def create_leads_assets_blueprint(runtime: LeadsRuntime) -> Blueprint:
    assets_dir = Path(runtime.config.assets_dir).resolve()

    return Blueprint(
        "smx_leads_assets",
        __name__,
        static_folder=str(assets_dir),
        static_url_path="/leads/assets",
    )


def create_leads_static_blueprint() -> Blueprint:
    return Blueprint(
        "smx_leads_static",
        __name__,
        static_folder="static",
        static_url_path="/leads/static",
    )


def init_leads(
    app,
    *,
    config=None,
    init_schema: bool = False,
    ai_profile=None,
    ai_client=None,
):
    """
    Initialize smx-leads.
    """
    resolved_config = config or {}

    runtime = LeadsRuntime.from_mapping(resolved_config)

    if runtime.config.flask_secret_key and not getattr(app, "secret_key", None):
        app.config["SECRET_KEY"] = runtime.config.flask_secret_key

    if init_schema:
        runtime.init_schema()

    resolved_ai_client = ai_client or build_lead_ai_client_from_profile(ai_profile)

    app.register_blueprint(create_leads_static_blueprint())
    app.register_blueprint(create_leads_assets_blueprint(runtime))
    app.register_blueprint(create_public_leads_blueprint(runtime))
    app.register_blueprint(create_admin_leads_blueprint(runtime, ai_client=resolved_ai_client))

    return app


def init_leads_from_env(
    app,
    *,
    env_file: str = "plugins/leads/.smx_leads.env",
    init_schema: bool = False,
    ai_profile=None,
    ai_client=None,
):
    """
    Initialize smx-leads from the client-owned env file.
    """
    config = build_leads_config_from_env(env_file=env_file)

    return init_leads(
        app,
        config=config,
        init_schema=init_schema,
        ai_profile=ai_profile,
        ai_client=ai_client,
    )


def setup_leads(
    app,
    *,
    project_root=None,
    init_schema: bool = True,
    ai_profile=None,
    ai_client=None,
):
    """
    Create the client scaffold and initialize smx-leads.
    """
    scaffold = ensure_leads_scaffold(project_root=project_root)

    return init_leads_from_env(
        app,
        env_file=scaffold.env_file,
        init_schema=init_schema,
        ai_profile=ai_profile,
        ai_client=ai_client,
    )


__all__ = [
    "create_leads_assets_blueprint",
    "create_leads_static_blueprint",
    "ensure_leads_scaffold",
    "init_leads",
    "init_leads_from_env",
    "setup_leads",
]
