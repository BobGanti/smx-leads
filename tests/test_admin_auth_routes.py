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


def test_admin_home_redirects_to_login_without_session():
    client = create_app().test_client()

    response = client.get(
        "/leads/admin",
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["Location"] == "/leads/admin/login"


def test_admin_login_page_renders():
    client = create_app().test_client()

    response = client.get(
        "/leads/admin/login",
        headers={"Accept": "text/html"},
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "SyntaxMatrix · Leads Admin Login" in html
    assert 'method="post" action="/leads/admin/login"' in html
    assert 'name="admin_token"' in html
    assert 'href="/leads"' in html


def test_admin_login_rejects_bad_token():
    client = create_app().test_client()

    response = client.post(
        "/leads/admin/login",
        data={"admin_token": "wrong"},
        headers={"Accept": "text/html"},
    )

    assert response.status_code == 401
    assert "Invalid admin token" in response.get_data(as_text=True)


def test_admin_login_allows_dashboard_access_and_logout():
    client = create_app().test_client()

    login = client.post(
        "/leads/admin/login",
        data={"admin_token": "secret-admin-token"},
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )

    assert login.status_code == 303
    assert login.headers["Location"] == "/leads/admin"

    dashboard = client.get(
        "/leads/admin",
        headers={"Accept": "text/html"},
    )

    assert dashboard.status_code == 200
    html = dashboard.get_data(as_text=True)

    assert "SyntaxMatrix · Leads Admin" in html
    assert "Leads Admin Dashboard" in html
    assert 'href="/leads/admin/submissions"' in html
    assert 'action="/leads/admin/logout"' in html

    logout = client.post(
        "/leads/admin/logout",
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )

    assert logout.status_code == 303
    assert logout.headers["Location"] == "/leads/admin/login"
