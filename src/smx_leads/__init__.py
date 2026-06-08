from __future__ import annotations

from smx_leads.smxcp import ensure_leads_scaffold


def init_leads(app, *, config=None, init_schema: bool = False):
    """
    Initialize smx-leads.

    Route/database registration will be added in the next patch.
    """
    return app


def init_leads_from_env(
    app,
    *,
    env_file: str = "leads/.smx_leads.env",
    init_schema: bool = False,
):
    """
    Initialize smx-leads from the client-owned env file.

    Full env parsing will be added in the next patch.
    """
    return init_leads(
        app,
        config={},
        init_schema=init_schema,
    )


def setup_leads(
    app,
    *,
    project_root=None,
    init_schema: bool = True,
):
    """
    Create the client scaffold and initialize smx-leads.
    """
    scaffold = ensure_leads_scaffold(project_root=project_root)

    return init_leads_from_env(
        app,
        env_file=scaffold.env_file,
        init_schema=init_schema,
    )


__all__ = [
    "ensure_leads_scaffold",
    "init_leads",
    "init_leads_from_env",
    "setup_leads",
]
