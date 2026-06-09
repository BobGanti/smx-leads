from flask import Flask

from smx_leads import init_leads


def test_all_plugin_routes_are_namespaced_under_leads():
    app = Flask(__name__)

    init_leads(
        app,
        config={
            "database_url": "sqlite+pysqlite:///:memory:",
            "admin_token": "secret-admin-token",
            "flask_secret_key": "test-secret-key",
        },
        init_schema=True,
    )

    allowed_non_plugin_routes = {
        "/static/<path:filename>",
    }

    routes = {
        str(rule)
        for rule in app.url_map.iter_rules()
    }

    plugin_routes = {
        route
        for route in routes
        if route not in allowed_non_plugin_routes
    }

    assert plugin_routes

    for route in plugin_routes:
        assert route.startswith("/leads"), route

    assert "/admin" not in routes
    assert "/submit" not in routes
    assert "/thank-you" not in routes
    assert "/submissions" not in routes
    assert "/branding" not in routes
