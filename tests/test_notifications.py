from smx_leads.core.config import LeadsConfig
from smx_leads.models import LeadSubmissionStatus
from smx_leads.notifications.emailer import LeadNotificationEmailService
from smx_leads.repository import LeadSubmission


class FakeEmailSender:
    def __init__(self):
        self.messages = []

    def send_message(self, *, to_email, subject, body_text, from_email=None):
        self.messages.append(
            {
                "to_email": to_email,
                "from_email": from_email,
                "subject": subject,
                "body_text": body_text,
            }
        )


def make_lead():
    return LeadSubmission(
        public_id="lead_test123",
        source="demo",
        status=LeadSubmissionStatus.NEW.value,
        full_name="Bob Nti",
        email="bob@example.com",
        phone="123",
        company="SyntaxMatrix",
        subject="Demo request",
        message="I want a demo.",
        internal_notes="",
        extra={},
    )


def test_notification_is_skipped_when_email_provider_is_none():
    config = LeadsConfig.from_mapping(
        {
            "database_url": "sqlite+pysqlite:///:memory:",
            "email_provider": "none",
            "notify_to_email": "admin@example.com",
        }
    )
    sender = FakeEmailSender()
    service = LeadNotificationEmailService(config=config, sender=sender)

    result = service.send_new_lead_notification(make_lead())

    assert result.sent is False
    assert result.skipped is True
    assert sender.messages == []


def test_notification_is_skipped_without_notify_email():
    config = LeadsConfig.from_mapping(
        {
            "database_url": "sqlite+pysqlite:///:memory:",
            "email_provider": "smtp",
            "default_from_email": "leads@example.com",
        }
    )
    sender = FakeEmailSender()
    service = LeadNotificationEmailService(config=config, sender=sender)

    result = service.send_new_lead_notification(make_lead())

    assert result.sent is False
    assert result.skipped is True
    assert "NOTIFY_TO_EMAIL" in result.error_message
    assert sender.messages == []


def test_notification_sends_new_lead_email_with_configured_sender():
    config = LeadsConfig.from_mapping(
        {
            "database_url": "sqlite+pysqlite:///:memory:",
            "email_provider": "smtp",
            "notify_to_email": "admin@example.com",
            "default_from_email": "leads@example.com",
        }
    )
    sender = FakeEmailSender()
    service = LeadNotificationEmailService(config=config, sender=sender)

    result = service.send_new_lead_notification(make_lead())

    assert result.sent is True
    assert result.skipped is False

    assert len(sender.messages) == 1
    message = sender.messages[0]

    assert message["to_email"] == "admin@example.com"
    assert message["from_email"] == "leads@example.com"
    assert message["subject"] == "New lead enquiry: Bob Nti"
    assert "Reference: lead_test123" in message["body_text"]
    assert "Email: bob@example.com" in message["body_text"]
    assert "Message:" in message["body_text"]
    assert "I want a demo." in message["body_text"]


def test_notification_reports_sender_failure():
    class BrokenSender:
        def send_message(self, *, to_email, subject, body_text, from_email=None):
            raise RuntimeError("SMTP failed")

    config = LeadsConfig.from_mapping(
        {
            "database_url": "sqlite+pysqlite:///:memory:",
            "email_provider": "smtp",
            "notify_to_email": "admin@example.com",
        }
    )

    service = LeadNotificationEmailService(config=config, sender=BrokenSender())

    result = service.send_new_lead_notification(make_lead())

    assert result.sent is False
    assert result.skipped is False
    assert "SMTP failed" in result.error_message
