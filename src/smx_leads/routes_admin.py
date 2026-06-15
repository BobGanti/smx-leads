from __future__ import annotations

from functools import wraps
from pathlib import Path

from flask import Blueprint, jsonify, redirect, render_template, request, session
from werkzeug.utils import secure_filename

from smx_leads.ai import LeadAIService
from smx_leads.ai.repository import LeadAIInsightRepository
from smx_leads.models import LeadSubmissionStatus
from smx_leads.repository import LeadRepository
from smx_leads.runtime import LeadsRuntime


ADMIN_SESSION_KEY = "smx_leads_admin_authenticated"


def create_admin_leads_blueprint(runtime: LeadsRuntime, *, ai_client=None) -> Blueprint:
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

    @bp.get("/leads/admin/branding")
    @require_admin
    def branding_page():
        if _wants_json():
            return jsonify(
                {
                    "status": "ok",
                    "logo_url": runtime.config.logo_url,
                    "favicon_url": runtime.config.favicon_url,
                }
            )

        return render_template(
            "admin/branding.html",
            leads_config=runtime.config,
            error=None,
            message=None,
        )

    @bp.post("/leads/admin/branding/assets")
    @require_admin
    def update_branding_assets():
        try:
            updated = _save_branding_assets(runtime)
        except ValueError as exc:
            if _wants_json():
                return jsonify({"error": str(exc)}), 400

            return render_template(
                "admin/branding.html",
                leads_config=runtime.config,
                error=str(exc),
                message=None,
            ), 400

        if _wants_json():
            return jsonify(
                {
                    "status": "ok",
                    "updated": updated,
                    "logo_url": runtime.config.logo_url,
                    "favicon_url": runtime.config.favicon_url,
                }
            )

        return render_template(
            "admin/branding.html",
            leads_config=runtime.config,
            error=None,
            message="Branding assets updated.",
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
            ai_repo = LeadAIInsightRepository(db_session)
            ai_insight = ai_repo.get_latest_for_lead(lead_public_id=public_id)

        if submission is None:
            if _wants_json():
                return jsonify({"error": "Lead submission not found."}), 404

            return render_template(
                "admin/submission_detail.html",
                leads_config=runtime.config,
                submission=None,
                statuses=[item.value for item in LeadSubmissionStatus],
                ai_insight=None,
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
            ai_insight=ai_insight,
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
                ai_insight=None,
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


    @bp.post("/leads/admin/submissions/<public_id>/delete")
    @require_admin
    def delete_submission(public_id: str):
        with runtime.session_scope() as db_session:
            ai_repo = LeadAIInsightRepository(db_session)
            ai_repo.delete_for_lead(lead_public_id=public_id)

            repo = LeadRepository(db_session)
            deleted = repo.delete_submission(public_id=public_id)

        if not deleted:
            if _wants_json():
                return jsonify({"error": "Lead submission not found."}), 404

            return render_template(
                "admin/submission_detail.html",
                leads_config=runtime.config,
                submission=None,
                statuses=[item.value for item in LeadSubmissionStatus],
                ai_insight=None,
                error="Lead submission not found.",
            ), 404

        if _wants_json():
            return jsonify({"status": "ok", "deleted": True, "public_id": public_id})

        return redirect("/leads/admin/submissions", code=303)


    @bp.post("/leads/admin/submissions/<public_id>/ai/analyze")
    @require_admin
    def analyze_submission_with_ai(public_id: str):
        if ai_client is None:
            if _wants_json():
                return jsonify({"error": "Lead AI client is not configured."}), 503

            with runtime.session_scope() as db_session:
                repo = LeadRepository(db_session)
                current = repo.get_submission(public_id)
                ai_repo = LeadAIInsightRepository(db_session)
                ai_insight = ai_repo.get_latest_for_lead(lead_public_id=public_id)

            return render_template(
                "admin/submission_detail.html",
                leads_config=runtime.config,
                submission=current,
                statuses=[item.value for item in LeadSubmissionStatus],
                ai_insight=ai_insight,
                error="Lead AI client is not configured.",
            ), 503

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
                    ai_insight=None,
                    error="Lead submission not found.",
                ), 404

            insight = LeadAIService(ai_client=ai_client).analyze_lead(submission)

            ai_repo = LeadAIInsightRepository(db_session)
            stored = ai_repo.create_insight(
                lead_public_id=public_id,
                insight=insight,
            )

        if _wants_json():
            return jsonify(
                {
                    "status": "ok",
                    "ai_insight": {
                        "id": stored.id,
                        "summary": stored.summary,
                        "category": stored.category,
                        "priority": stored.priority,
                        "suggested_status": stored.suggested_status,
                        "spam_risk": stored.spam_risk,
                        "usage": dict(stored.raw.get("usage", {}) or {}),
                    },
                }
            ), 201

        return redirect(f"/leads/admin/submissions/{public_id}", code=303)


    return bp



def _save_branding_assets(runtime: LeadsRuntime) -> list[str]:
    assets_dir = Path(runtime.config.assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)

    updated: list[str] = []

    logo = request.files.get("logo")
    if logo and logo.filename:
        _save_png_upload(logo, assets_dir / "logo.png")
        updated.append("logo")

    favicon = request.files.get("favicon")
    if favicon and favicon.filename:
        _save_png_upload(favicon, assets_dir / "favicon.png")
        updated.append("favicon")

    if not updated:
        raise ValueError("Upload a logo or favicon file.")

    return updated


def _save_png_upload(upload, destination: Path) -> None:
    filename = secure_filename(upload.filename or "")
    if not filename.lower().endswith(".png"):
        raise ValueError("Only PNG files are supported for branding assets.")

    data = upload.read()
    if not data.startswith(b"\x89PNG"):
        raise ValueError("Uploaded branding asset must be a PNG file.")

    destination.write_bytes(data)


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
