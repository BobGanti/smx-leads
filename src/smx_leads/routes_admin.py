from __future__ import annotations

from functools import wraps

from flask import Blueprint, jsonify, redirect, render_template, request, session

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
            return _login_error("Leads admin token is not configured.", status_code=503)

        if submitted_token != runtime.config.admin_token:
            return _login_error("Invalid admin token.", status_code=401)

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

    return bp


def _payload() -> dict:
    if request.is_json:
        return request.get_json(silent=True) or {}

    return dict(request.form.items())


def _wants_json() -> bool:
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept


def _login_error(message: str, *, status_code: int):
    if _wants_json():
        return jsonify({"error": message}), status_code

    return render_template(
        "admin/login.html",
        leads_config=None,
        error=message,
    ), status_code
