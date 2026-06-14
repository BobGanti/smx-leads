from flask import Flask

from smx_leads import init_leads


class FakeLeadAIClient:
    def __init__(self):
        self.prompts = []

    def generate_lead_insight(self, *, prompt: str):
        self.prompts.append(prompt)
        return {
            "summary": "Bob wants a demo for the AI platform.",
            "category": "demo_request",
            "priority": "high",
            "suggested_status": "reviewed",
            "recommended_action": "Offer demo slots within 24 hours.",
            "draft_reply": "Hi Bob, thanks for your interest. We can arrange a demo.",
            "spam_risk": "low",
            "model_name": "host-model",
            "usage": {
                "provider": "xai",
                "model": "grok-test",
                "input_tokens": 11,
                "output_tokens": 7,
                "thinking_tokens": 5,
                "other_tokens": 0,
                "total_tokens": 23,
                "raw": {},
            },
        }


def create_app(ai_client=None, ai_profile=None):
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
        ai_profile=ai_profile,
        ai_client=ai_client,
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
    return response.headers["Location"].split("lead_id=", 1)[1]


def test_admin_ai_analyze_requires_configured_ai_client():
    client = create_app(ai_client=None).test_client()
    lead_id = seed_lead(client)
    login(client)

    response = client.post(
        f"/leads/admin/submissions/{lead_id}/ai/analyze",
        headers={"Accept": "text/html"},
    )

    assert response.status_code == 503
    html = response.get_data(as_text=True)

    assert "Lead AI client is not configured" in html
    assert "Bob Nti" in html


def test_admin_ai_analyze_persists_insight_and_redirects():
    fake_ai = FakeLeadAIClient()
    client = create_app(ai_client=fake_ai).test_client()
    lead_id = seed_lead(client)
    login(client)

    response = client.post(
        f"/leads/admin/submissions/{lead_id}/ai/analyze",
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["Location"] == f"/leads/admin/submissions/{lead_id}"
    assert len(fake_ai.prompts) == 1

    detail = client.get(
        f"/leads/admin/submissions/{lead_id}",
        headers={"Accept": "text/html"},
    )

    html = detail.get_data(as_text=True)

    assert detail.status_code == 200
    assert "AI insight" in html
    assert "Bob wants a demo for the AI platform." in html
    assert "demo_request" in html
    assert "high" in html
    assert "Offer demo slots within 24 hours." in html
    assert "Hi Bob, thanks for your interest" in html
    assert "AI usage" in html
    assert "Input tokens:" in html
    assert "11" in html
    assert "Output tokens:" in html
    assert "7" in html
    assert "Thinking/other tokens:" in html
    assert "5" in html
    assert "Total billable/model tokens:" in html
    assert "23" in html


def test_admin_ai_analyze_json_response():
    fake_ai = FakeLeadAIClient()
    client = create_app(ai_client=fake_ai).test_client()
    lead_id = seed_lead(client)
    login(client)

    response = client.post(
        f"/leads/admin/submissions/{lead_id}/ai/analyze",
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 201
    payload = response.get_json()

    assert payload["status"] == "ok"
    assert payload["ai_insight"]["summary"] == "Bob wants a demo for the AI platform."
    assert payload["ai_insight"]["category"] == "demo_request"
    assert payload["ai_insight"]["priority"] == "high"
    assert payload["ai_insight"]["usage"]["input_tokens"] == 11
    assert payload["ai_insight"]["usage"]["output_tokens"] == 7
    assert payload["ai_insight"]["usage"]["thinking_tokens"] == 5
    assert payload["ai_insight"]["usage"]["other_tokens"] == 0
    assert payload["ai_insight"]["usage"]["total_tokens"] == 23


def test_admin_ai_analyze_accepts_host_built_ai_profile():
    fake_ai = FakeLeadAIClient()
    client = create_app(
        ai_profile={
            "provider": "xai",
            "model": "grok-test",
            "client": fake_ai,
        }
    ).test_client()
    lead_id = seed_lead(client)
    login(client)

    response = client.post(
        f"/leads/admin/submissions/{lead_id}/ai/analyze",
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["ai_insight"]["summary"] == "Bob wants a demo for the AI platform."
    assert len(fake_ai.prompts) == 1
