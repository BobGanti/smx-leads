from __future__ import annotations

from functools import wraps

from flask import Blueprint, jsonify, redirect, render_template, request, session

from smx_leads.models import LeadSubmissionStatus
from smx_leads.repository import LeadRepository
from smx_leads.runtime import LeadsRuntime


ADMIN_SESSION_KEY = "smx_leads_admin_authenticated"


def create_admin_leads_blueprint(runtime: LeadsRuntime) -> Blueprint:
    bp = Blueprint(
        "smx_leads_admin",
        __name__,
        template_folder="templates",
    )

    def require_admin(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if not runtime.config.admin_token:
                if _wants_json():
                    return jsonify({"error": "Leads admin token is not configured."}), 503

                return render_template(
                    "admin/login.html",
                    leads_config=runtime.config,
                    error="Leads admin token is not configured.",
                ), 503

            if session.get(ADMIN_SESSION_KEY) is True:
                return view_func(*args, **kwargs)

            if _wants_json():
                return jsonify({"error": "Authentication required."}), 401

            return redirect("/leads/admin/login", code=303)

        return wrapper

    @bp.get("/leads/admin/login")
    def login_page():
        if session.get(ADMIN_SESSION_KEY) is True:
            return redirect("/leads/admin", code=303)

        if _wants_json():
            return jsonify({"status": "ok", "login": "required"})

        return render_template(
            "admin/login.html",
            leads_config=runtime.config,
            error=None,
        )

    @bp.post("/leads/admin/login")
    def submit_login():
        payload = _payload()
        submitted_token = (
            payload.get("admin_token")
            or payload.get("admin_api_key")
            or ""
        ).strip()

        if not runtime.config.admin_token:
            return _login_error(runtime, "Leads admin token is not configured.", status_code=503)

        if submitted_token != runtime.config.admin_token:
            return _login_error(runtime, "Invalid admin token.", status_code=401)

        session[ADMIN_SESSION_KEY] = True

        if _wants_json():
            return jsonify({"status": "ok", "authenticated": True})

        return redirect("/leads/admin", code=303)

    @bp.post("/leads/admin/logout")
    def logout():
        session.pop(ADMIN_SESSION_KEY, None)

        if _wants_json():
            return jsonify({"status": "ok", "authenticated": False})

        return redirect("/leads/admin/login", code=303)

    @bp.get("/leads/admin")
    @require_admin
    def admin_home():
        if _wants_json():
            return jsonify(
                {
                    "status": "ok",
                    "admin": True,
                    "submissions_url": "/leads/admin/submissions",
                }
            )

        return render_template(
            "admin/home.html",
            leads_config=runtime.config,
        )

    @bp.get("/leads/admin/submissions")
    @require_admin
    def submissions_list():
        status = (request.args.get("status") or "").strip().lower() or None
        source = (request.args.get("source") or "").strip().lower() or None

        with runtime.session_scope() as db_session:
            repo = LeadRepository(db_session)
            submissions = repo.list_submissions(
                status=status,
                source=source,
                limit=200,
            )

        if _wants_json():
            return jsonify(
                {
                    "status": "ok",
                    "submissions": [
                        {
                            "public_id": item.public_id,
                            "source": item.source,
                            "status": item.status,
                            "full_name": item.full_name,
                            "email": item.email,
                            "subject": item.subject,
                        }
                        for item in submissions
                    ],
                }
            )

        return render_template(
            "admin/submissions_list.html",
            leads_config=runtime.config,
            submissions=submissions,
            selected_status=status or "",
            selected_source=source or "",
            statuses=[item.value for item in LeadSubmissionStatus],
        )

    @bp.get("/leads/admin/submissions/<public_id>")
    @require_admin
    def submission_detail(public_id: str):
        with runtime.session_scope() as db_session:
            repo = LeadRepository(db_session)
            submission = repo.get_submission(public_id)

        if submission is None:
            if _wants_json():
                return jsonify({"error": "Lead submission not found."}), 404

            return render_template(
                "admin/submission_detail.html",
                leads_config=runtime.config,
                submission=None,
                statuses=[item.value for item in LeadSubmissionStatus],
                error="Lead submission not found.",
            ), 404

        if _wants_json():
            return jsonify(
                {
                    "status": "ok",
                    "submission": {
                        "public_id": submission.public_id,
                        "source": submission.source,
                        "status": submission.status,
                        "full_name": submission.full_name,
                        "email": submission.email,
                        "phone": submission.phone,
                        "company": submission.company,
                        "subject": submission.subject,
                        "message": submission.message,
                        "internal_notes": submission.internal_notes,
                    },
                }
            )

        return render_template(
            "admin/submission_detail.html",
            leads_config=runtime.config,
            submission=submission,
            statuses=[item.value for item in LeadSubmissionStatus],
            error=None,
        )

    @bp.post("/leads/admin/submissions/<public_id>/status")
    @require_admin
    def update_submission_status(public_id: str):
        payload = _payload()

        try:
            with runtime.session_scope() as db_session:
                repo = LeadRepository(db_session)
                submission = repo.update_status(
                    public_id=public_id,
                    status=payload.get("status", ""),
                    internal_notes=payload.get("internal_notes"),
                )

        except ValueError as exc:
            if _wants_json():
                return jsonify({"error": str(exc)}), 400

            with runtime.session_scope() as db_session:
                repo = LeadRepository(db_session)
                current = repo.get_submission(public_id)

            return render_template(
                "admin/submission_detail.html",
                leads_config=runtime.config,
                submission=current,
                statuses=[item.value for item in LeadSubmissionStatus],
                error=str(exc),
            ), 400

        if _wants_json():
            return jsonify(
                {
                    "status": "ok",
                    "submission": {
                        "public_id": submission.public_id,
                        "status": submission.status,
                        "internal_notes": submission.internal_notes,
                    },
                }
            )

        return redirect(f"/leads/admin/submissions/{public_id}", code=303)

    return bp


def _payload() -> dict:
    if request.is_json:
        return request.get_json(silent=True) or {}

    return dict(request.form.items())


def _wants_json() -> bool:
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept


def _login_error(runtime: LeadsRuntime, message: str, *, status_code: int):
    if _wants_json():
        return jsonify({"error": message}), status_code

    return render_template(
        "admin/login.html",
        leads_config=runtime.config,
        error=message,
    ), status_code
