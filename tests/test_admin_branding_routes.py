from io import BytesIO
from pathlib import Path

from flask import Flask

from smx_leads import setup_leads


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\r\n-\xb4"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def create_app(tmp_path):
    app = Flask(__name__)
    setup_leads(app, project_root=tmp_path, init_schema=True)
    return app


def login(client):
    response = client.post(
        "/leads/admin/login",
        data={"admin_token": "local-leads-admin-token"},
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_admin_branding_page_renders_upload_form(tmp_path):
    client = create_app(tmp_path).test_client()
    login(client)

    response = client.get("/leads/admin/branding", headers={"Accept": "text/html"})

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "SyntaxMatrix · Leads Branding Admin" in html
    assert "Branding/settings" in html
    assert 'action="/leads/admin/branding/assets"' in html
    assert 'name="logo"' in html
    assert 'name="favicon"' in html
    assert 'src="/leads/assets/logo.png"' in html
    assert 'src="/leads/assets/favicon.png"' in html


def test_admin_branding_upload_replaces_logo_and_favicon(tmp_path):
    client = create_app(tmp_path).test_client()
    login(client)

    response = client.post(
        "/leads/admin/branding/assets",
        data={
            "logo": (BytesIO(PNG_BYTES), "logo.png"),
            "favicon": (BytesIO(PNG_BYTES), "favicon.png"),
        },
        content_type="multipart/form-data",
        headers={"Accept": "text/html"},
    )

    assert response.status_code == 200
    assert "Branding assets updated" in response.get_data(as_text=True)

    assert (tmp_path / "plugins" / "leads" / "assets" / "logo.png").read_bytes() == PNG_BYTES
    assert (tmp_path / "plugins" / "leads" / "assets" / "favicon.png").read_bytes() == PNG_BYTES


def test_admin_branding_upload_rejects_non_png(tmp_path):
    client = create_app(tmp_path).test_client()
    login(client)

    response = client.post(
        "/leads/admin/branding/assets",
        data={
            "logo": (BytesIO(b"not-png"), "logo.txt"),
        },
        content_type="multipart/form-data",
        headers={"Accept": "text/html"},
    )

    assert response.status_code == 400
    assert "Only PNG files are supported" in response.get_data(as_text=True)
