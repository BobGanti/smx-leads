from flask import Flask

from smx_leads import init_leads


class FakeNotificationService:
    calls = []

    def __init__(self, *, config):
        self.config = config

    def send_new_lead_notification(self, lead):
        self.calls.append(
            {
                "public_id": lead.public_id,
                "email": lead.email,
                "full_name": lead.full_name,
                "source": lead.source,
            }
        )


def create_app():
    app = Flask(__name__)
    init_leads(
        app,
        config={
            "database_url": "sqlite+pysqlite:///:memory:",
            "host_site_title": "SyntaxMatrix",
            "host_home_url": "/",
            "module_title": "Leads",
            "email_provider": "smtp",
            "notify_to_email": "admin@example.com",
        },
        init_schema=True,
    )
    return app


def test_public_submit_calls_notification_service(monkeypatch):
    FakeNotificationService.calls = []

    monkeypatch.setattr(
        "smx_leads.routes_public.LeadNotificationEmailService",
        FakeNotificationService,
    )

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
    assert len(FakeNotificationService.calls) == 1

    call = FakeNotificationService.calls[0]

    assert call["public_id"].startswith("lead_")
    assert call["email"] == "bob@example.com"
    assert call["full_name"] == "Bob Nti"
    assert call["source"] == "demo"
