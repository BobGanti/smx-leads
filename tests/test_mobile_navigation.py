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


def test_public_page_has_mobile_hamburger_menu():
    client = create_app().test_client()

    response = client.get("/leads", headers={"Accept": "text/html"})

    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'class="smx-nav smx-desktop-nav"' in html
    assert 'class="smx-mobile-menu"' in html
    assert 'smx-mobile-menu-icon' in html
    assert 'aria-label="Open menu"' in html


def test_admin_page_has_mobile_hamburger_menu():
    client = create_app().test_client()

    client.post(
        "/leads/admin/login",
        data={"admin_token": "secret-admin-token"},
        headers={"Accept": "text/html"},
    )

    response = client.get("/leads/admin", headers={"Accept": "text/html"})
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'class="smx-nav smx-desktop-nav"' in html
    assert 'class="smx-mobile-menu"' in html
    assert 'smx-mobile-menu-icon' in html
    assert 'Branding/settings' in html
    assert 'action="/leads/admin/logout"' in html


def test_css_defines_mobile_menu_rules():
    client = create_app().test_client()

    response = client.get("/leads/static/smx-leads.css")

    css = response.get_data(as_text=True)

    assert response.status_code == 200
    assert ".smx-mobile-menu" in css
    assert ".smx-mobile-menu-panel" in css
    assert ".smx-desktop-nav" in css
    assert "@media (max-width: 860px)" in css
