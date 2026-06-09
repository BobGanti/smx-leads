from __future__ import annotations

from flask import Blueprint, jsonify, redirect, render_template, request

from smx_leads.notifications import LeadNotificationEmailService
from smx_leads.repository import LeadRepository
from smx_leads.runtime import LeadsRuntime


def create_public_leads_blueprint(runtime: LeadsRuntime) -> Blueprint:
    bp = Blueprint(
        "smx_leads_public",
        __name__,
        template_folder="templates",
    )

    @bp.get("/leads")
    def lead_form():
        if _wants_json():
            return jsonify(
                {
                    "status": "ok",
                    "form": "lead",
                    "submit_url": "/leads/submit",
                }
            )

        return render_template(
            "public/lead_form.html",
            leads_config=runtime.config,
            error=None,
            form={},
        )

    @bp.post("/leads/submit")
    def submit_lead():
        payload = _payload()

        # Honeypot: bots may fill this; real users do not see/use it.
        if (payload.get("website") or "").strip():
            if _wants_json():
                return jsonify({"status": "ok"}), 200

            return redirect("/leads/thank-you", code=303)

        try:
            with runtime.session_scope() as session:
                repo = LeadRepository(session)
                lead = repo.create_submission(
                    full_name=payload.get("full_name", ""),
                    email=payload.get("email", ""),
                    phone=payload.get("phone", ""),
                    company=payload.get("company", ""),
                    subject=payload.get("subject", ""),
                    message=payload.get("message", ""),
                    source=payload.get("source", "contact"),
                    extra={
                        "user_agent": request.headers.get("User-Agent", ""),
                        "remote_addr": request.headers.get("X-Forwarded-For")
                        or request.remote_addr
                        or "",
                    },
                )

            # Email notifications must never block lead capture.
            try:
                LeadNotificationEmailService(
                    config=runtime.config,
                ).send_new_lead_notification(lead)
            except Exception:
                pass

        except ValueError as exc:
            if _wants_json():
                return jsonify({"error": str(exc)}), 400

            return render_template(
                "public/lead_form.html",
                leads_config=runtime.config,
                error=str(exc),
                form=payload,
            ), 400

        if _wants_json():
            return jsonify(
                {
                    "status": "ok",
                    "lead": {
                        "public_id": lead.public_id,
                        "status": lead.status,
                        "source": lead.source,
                    },
                }
            ), 201

        return redirect(
            f"/leads/thank-you?lead_id={lead.public_id}",
            code=303,
        )

    @bp.get("/leads/thank-you")
    def thank_you():
        if _wants_json():
            return jsonify({"status": "ok", "message": "Lead received."})

        return render_template(
            "public/thank_you.html",
            leads_config=runtime.config,
            lead_id=request.args.get("lead_id"),
        )

    return bp


def _payload() -> dict:
    if request.is_json:
        return request.get_json(silent=True) or {}

    return dict(request.form.items())


def _wants_json() -> bool:
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept
