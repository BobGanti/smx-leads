from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol
import smtplib

from smx_leads.core.config import LeadsConfig
from smx_leads.repository import LeadSubmission


@dataclass(frozen=True)
class EmailSendResult:
    sent: bool
    skipped: bool = False
    error_message: str | None = None


class EmailSender(Protocol):
    def send_message(
        self,
        *,
        to_email: str,
        subject: str,
        body_text: str,
        from_email: str | None = None,
    ) -> None:
        ...


class SmtpEmailSender:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls

    def send_message(
        self,
        *,
        to_email: str,
        subject: str,
        body_text: str,
        from_email: str | None = None,
    ) -> None:
        message = EmailMessage()
        message["To"] = to_email
        message["From"] = from_email or self.username or "no-reply@example.com"
        message["Subject"] = subject
        message.set_content(body_text)

        with smtplib.SMTP(self.host, self.port, timeout=20) as smtp:
            if self.use_tls:
                smtp.starttls()

            if self.username and self.password:
                smtp.login(self.username, self.password)

            smtp.send_message(message)


class LeadNotificationEmailService:
    def __init__(
        self,
        *,
        config: LeadsConfig,
        sender: EmailSender | None = None,
    ):
        self.config = config
        self.sender = sender or self._build_sender(config)

    def send_new_lead_notification(self, lead: LeadSubmission) -> EmailSendResult:
        if self.config.email_provider in {None, "", "none"}:
            return EmailSendResult(sent=False, skipped=True)

        if not self.config.notify_to_email:
            return EmailSendResult(
                sent=False,
                skipped=True,
                error_message="SMX_LEADS_NOTIFY_TO_EMAIL is not configured.",
            )

        if self.sender is None:
            return EmailSendResult(
                sent=False,
                skipped=True,
                error_message="Email sender is not configured.",
            )

        subject = f"New lead enquiry: {lead.full_name}"
        body_text = _render_new_lead_body(lead)

        try:
            self.sender.send_message(
                to_email=self.config.notify_to_email,
                from_email=self.config.default_from_email,
                subject=subject,
                body_text=body_text,
            )
        except Exception as exc:
            return EmailSendResult(
                sent=False,
                skipped=False,
                error_message=str(exc),
            )

        return EmailSendResult(sent=True)

    def _build_sender(self, config: LeadsConfig) -> EmailSender | None:
        if config.email_provider != "smtp":
            return None

        if not config.smtp_host or not config.smtp_port:
            return None

        return SmtpEmailSender(
            host=config.smtp_host,
            port=config.smtp_port,
            username=config.smtp_username,
            password=config.smtp_password,
            use_tls=config.smtp_use_tls,
        )


def _render_new_lead_body(lead: LeadSubmission) -> str:
    return "\n".join(
        [
            "A new lead enquiry has been submitted.",
            "",
            f"Reference: {lead.public_id}",
            f"Name: {lead.full_name}",
            f"Email: {lead.email}",
            f"Phone: {lead.phone}",
            f"Company: {lead.company}",
            f"Source: {lead.source}",
            f"Status: {lead.status}",
            f"Subject: {lead.subject}",
            "",
            "Message:",
            lead.message,
        ]
    )
