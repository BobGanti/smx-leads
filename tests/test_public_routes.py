from flask import Flask

from smx_leads import init_leads


def create_app():
    app = Flask(__name__)
    init_leads(
        app,
        config={
            "database_url": "sqlite+pysqlite:///:memory:",
            "host_site_title": "SyntaxMatrix",
            "host_home_url": "/",
            "module_title": "Leads",
        },
        init_schema=True,
    )
    return app


def test_public_lead_form_renders_html():
    client = create_app().test_client()

    response = client.get("/leads", headers={"Accept": "text/html"})

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "SyntaxMatrix · Leads" in html
    assert 'method="post" action="/leads/submit"' in html
    assert 'name="full_name"' in html
    assert 'name="email"' in html
    assert 'name="message"' in html
    assert 'name="website"' in html


def test_public_lead_submit_validates_required_fields():
    client = create_app().test_client()

    response = client.post(
        "/leads/submit",
        data={
            "full_name": "",
            "email": "bob@example.com",
            "message": "Hello",
        },
        headers={"Accept": "text/html"},
    )

    assert response.status_code == 400
    assert "Full name is required" in response.get_data(as_text=True)


def test_public_lead_submit_creates_submission_and_redirects():
    client = create_app().test_client()

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
    assert response.headers["Location"].startswith("/leads/thank-you?lead_id=lead_")


def test_public_lead_submit_json_returns_created_lead():
    client = create_app().test_client()

    response = client.post(
        "/leads/submit",
        json={
            "full_name": "Bob Nti",
            "email": "bob@example.com",
            "message": "I want a demo.",
            "source": "demo",
        },
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 201
    payload = response.get_json()

    assert payload["status"] == "ok"
    assert payload["lead"]["public_id"].startswith("lead_")
    assert payload["lead"]["status"] == "new"
    assert payload["lead"]["source"] == "demo"


def test_public_thank_you_page_renders():
    client = create_app().test_client()

    response = client.get(
        "/leads/thank-you?lead_id=lead_test123",
        headers={"Accept": "text/html"},
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Thank you" in html
    assert "lead_test123" in html
