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


def seed_lead(client, *, name="Bob Nti"):
    response = client.post(
        "/leads/submit",
        data={
            "full_name": name,
            "email": "bob@example.com",
            "phone": "123",
            "company": "SyntaxMatrix",
            "subject": "Password reset",
            "message": "I cannot find the password reset link.",
            "source": "support",
        },
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    return response.headers["Location"].split("lead_id=", 1)[1]


def test_admin_submissions_list_has_remove_action():
    client = create_app().test_client()
    seed_lead(client)
    login(client)

    response = client.get(
        "/leads/admin/submissions",
        headers={"Accept": "text/html"},
    )

    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Bob Nti" in html
    assert "View" in html
    assert "Remove" in html
    assert "/delete" in html


def test_admin_can_delete_submission_and_redirect_to_list():
    client = create_app().test_client()
    lead_id = seed_lead(client)
    login(client)

    response = client.post(
        f"/leads/admin/submissions/{lead_id}/delete",
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["Location"] == "/leads/admin/submissions"

    list_response = client.get(
        "/leads/admin/submissions",
        headers={"Accept": "text/html"},
    )
    assert "Bob Nti" not in list_response.get_data(as_text=True)

    detail_response = client.get(
        f"/leads/admin/submissions/{lead_id}",
        headers={"Accept": "text/html"},
    )
    assert detail_response.status_code == 404


def test_admin_delete_submission_json_response():
    client = create_app().test_client()
    lead_id = seed_lead(client)
    login(client)

    response = client.post(
        f"/leads/admin/submissions/{lead_id}/delete",
        headers={"Accept": "application/json"},
    )

    payload = response.get_json()

    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert payload["deleted"] is True
    assert payload["public_id"] == lead_id
