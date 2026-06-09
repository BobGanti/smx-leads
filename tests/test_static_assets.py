from flask import Flask

from smx_leads import init_leads


def create_app():
    app = Flask(__name__)
    init_leads(
        app,
        config={
            "database_url": "sqlite+pysqlite:///:memory:",
            "admin_token": "secret-admin-token",
            "flask_secret_key": "test-secret-key",
            "host_site_title": "SyntaxMatrix",
            "host_home_url": "/",
            "module_title": "Leads",
        },
        init_schema=True,
    )
    return app


def test_public_page_links_package_stylesheet():
    client = create_app().test_client()

    response = client.get("/leads", headers={"Accept": "text/html"})

    assert response.status_code == 200
    assert 'href="/leads/static/smx-leads.css"' in response.get_data(as_text=True)


def test_admin_page_links_package_stylesheet():
    client = create_app().test_client()

    client.post(
        "/leads/admin/login",
        data={"admin_token": "secret-admin-token"},
        headers={"Accept": "text/html"},
    )

    response = client.get("/leads/admin", headers={"Accept": "text/html"})

    assert response.status_code == 200
    assert 'href="/leads/static/smx-leads.css"' in response.get_data(as_text=True)


def test_package_static_css_is_served_under_leads_namespace():
    client = create_app().test_client()

    response = client.get("/leads/static/smx-leads.css")

    assert response.status_code == 200
    assert "text/css" in response.content_type
    assert ".smx-panel" in response.get_data(as_text=True)
