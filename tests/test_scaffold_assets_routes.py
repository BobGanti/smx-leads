from pathlib import Path
import shutil

from flask import Flask

from smx_leads import setup_leads


def test_setup_serves_scaffold_logo_and_favicon_assets(tmp_path):
    app = Flask(__name__)

    setup_leads(app, project_root=tmp_path, init_schema=True)

    client = app.test_client()

    logo = client.get("/leads/assets/logo.png")
    favicon = client.get("/leads/assets/favicon.png")

    assert logo.status_code == 200
    assert favicon.status_code == 200
    assert logo.data.startswith(b"\x89PNG")
    assert favicon.data.startswith(b"\x89PNG")


def test_public_template_uses_configured_logo_and_favicon(tmp_path):
    app = Flask(__name__)

    setup_leads(app, project_root=tmp_path, init_schema=True)

    client = app.test_client()
    response = client.get("/leads", headers={"Accept": "text/html"})

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'href="/leads/assets/favicon.png"' in html
    assert 'src="/leads/assets/logo.png"' in html
    assert 'alt="SyntaxMatrix logo"' in html
