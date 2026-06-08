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


def login(client):
    response = client.post(
        "/leads/admin/login",
        data={"admin_token": "secret-admin-token"},
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def seed_lead(client):
    response = client.post(
        "/leads/submit",
        data={
            "full_name": "Bob Nti",
            "email": "bob@example.com",
            "phone": "123",
            "company": "SyntaxMatrix",
            "subject": "Demo",
            "message": "I want a demo.",
            "source": "demo",
        },
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )

    assert response.status_code == 303

    location = response.headers["Location"]
    return location.split("lead_id=", 1)[1]


def test_admin_submissions_requires_login():
    client = create_app().test_client()

    response = client.get(
        "/leads/admin/submissions",
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["Location"] == "/leads/admin/login"


def test_admin_submissions_list_renders_seeded_lead():
    client = create_app().test_client()
    lead_id = seed_lead(client)
    login(client)

    response = client.get(
        "/leads/admin/submissions",
        headers={"Accept": "text/html"},
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "SyntaxMatrix · Leads Submissions Admin" in html
    assert "Lead submissions" in html
    assert "Bob Nti" in html
    assert "bob@example.com" in html
    assert "demo" in html
    assert f'href="/leads/admin/submissions/{lead_id}"' in html


def test_admin_submission_detail_renders_and_updates_status():
    client = create_app().test_client()
    lead_id = seed_lead(client)
    login(client)

    detail = client.get(
        f"/leads/admin/submissions/{lead_id}",
        headers={"Accept": "text/html"},
    )

    assert detail.status_code == 200
    html = detail.get_data(as_text=True)

    assert "Lead submission" in html
    assert "Bob Nti" in html
    assert "I want a demo." in html
    assert f'action="/leads/admin/submissions/{lead_id}/status"' in html

    update = client.post(
        f"/leads/admin/submissions/{lead_id}/status",
        data={
            "status": "contacted",
            "internal_notes": "Called once.",
        },
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )

    assert update.status_code == 303
    assert update.headers["Location"] == f"/leads/admin/submissions/{lead_id}"

    updated = client.get(
        f"/leads/admin/submissions/{lead_id}",
        headers={"Accept": "text/html"},
    )

    updated_html = updated.get_data(as_text=True)

    assert "contacted" in updated_html
    assert "Called once." in updated_html


def test_admin_submission_status_rejects_invalid_status():
    client = create_app().test_client()
    lead_id = seed_lead(client)
    login(client)

    response = client.post(
        f"/leads/admin/submissions/{lead_id}/status",
        data={
            "status": "paid",
            "internal_notes": "Bad state.",
        },
        headers={"Accept": "text/html"},
    )

    assert response.status_code == 400
    assert "Invalid lead status" in response.get_data(as_text=True)
