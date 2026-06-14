# smx-leads

`smx-leads` is a lead capture and admin inbox plugin for SyntaxMatrix-based projects.

It adds a namespaced public lead form, admin lead inbox, branding assets, non-blocking lead notification email support, and a client-owned scaffold folder using the same plugin pattern as `smx-commerce`.

---

## 1. Business Use Case

Many SyntaxMatrix-based projects need a lightweight way to collect and manage inbound interest before they need a full commerce system.

`smx-leads` is useful for:

- Contact enquiries
- Demo requests
- Pilot requests
- Waitlist signups
- Partnership enquiries
- Support/contact messages
- Bootcamp or programme interest forms
- Sales lead capture for AI/SaaS landing pages

The plugin gives the host project a ready-made lead workflow:

```text
Visitor submits enquiry
  -> Lead stored in database
  -> Optional email notification sent
  -> Admin reviews lead
  -> Admin updates status and internal notes
```

---

## 2. When to Use smx-leads

Use `smx-leads` when a SyntaxMatrix-based project needs enquiry capture but does not need full checkout, order, or payment logic.

Use `smx-commerce` when the project needs products, carts, checkout, orders, or payment workflow.

A common project progression is:

```text
smx-leads
  -> capture early interest, pilots, demos, contacts, waitlists

smx-commerce
  -> sell products, courses, subscriptions, paid services
```

---

## 3. Installation

Install from PyPI:

```powershell
pip install smx-leads
```

For local development inside this repository:

```powershell
pip install -r requirements-dev.txt
```

Runtime package dependencies are declared in `pyproject.toml`, not `requirements.txt`.

---

## 4. Client Import Pattern

In the SyntaxMatrix-based client project:

```python
from pathlib import Path

from smx_leads import setup_leads


PROJECT_ROOT = Path(__file__).resolve().parent


setup_leads(
    app,
    project_root=PROJECT_ROOT,
    init_schema=True,
)
```

The public import pattern is:

```python
from smx_leads import setup_leads
```

This follows the same mental pattern as `smx-commerce`.

---

## 5. Client-Owned Scaffold

When `setup_leads(...)` runs, it injects a client-owned scaffold folder:

```text
leads/
  __init__.py
  smx_leads_setup.py
  .smx_leads.env
  .smx_leads_example.env
  .smx_leads.deploy_example.env
  assets/
    logo.png
    favicon.png
  data/
    smx_leads_dev.db
```

Existing client files are not overwritten.

The injected `leads/` folder belongs to the client project. The package owns the reusable plugin logic; the client owns local configuration and branding assets.

---

## 6. Public Routes

All public routes are namespaced under `/leads`.

```text
/leads
/leads/submit
/leads/thank-you
/leads/static/smx-leads.css
/leads/assets/logo.png
/leads/assets/favicon.png
```

There are no loose public routes such as `/submit` or `/thank-you`.

---

## 7. Admin Routes

All admin routes are namespaced under `/leads/admin`.

```text
/leads/admin
/leads/admin/login
/leads/admin/logout
/leads/admin/submissions
/leads/admin/submissions/<public_id>
/leads/admin/submissions/<public_id>/status
/leads/admin/branding
/leads/admin/branding/assets
```

There are no loose admin routes such as `/admin`, `/submissions`, or `/branding`.

---

## 8. Local Development Configuration

The local scaffold writes:

```text
plugins/leads/.smx_leads.env
```

Important local defaults:

```text
SMX_LEADS_DATABASE_URL=sqlite+pysqlite:///.../plugins/leads/data/smx_leads_dev.db
SMX_LEADS_ADMIN_TOKEN=local-leads-admin-token
SMX_LEADS_FLASK_SECRET_KEY=replace-with-a-strong-session-secret
SMX_LEADS_HOST_SITE_TITLE=SyntaxMatrix
SMX_LEADS_HOST_HOME_URL=/
SMX_LEADS_MODULE_TITLE=Leads
SMX_LEADS_PUBLIC_BASE_URL=http://localhost:5055
SMX_LEADS_ASSETS_DIR=<resolved-client-project-path>/plugins/leads/assets
SMX_LEADS_LOGO_URL=/leads/assets/logo.png
SMX_LEADS_FAVICON_URL=/leads/assets/favicon.png
```

Use the local admin token to log in at:

```text
/leads/admin
```

---

## 9. Production Configuration

Local development uses SQLite.

Production should use Postgres.

The production deployment example is generated at:

```text
leads/.smx_leads.deploy_example.env
```

Production database example:

```text
SMX_LEADS_DATABASE_URL=postgresql+psycopg://user:password@host:5432/database
```

The package includes the Postgres driver dependency:

```text
psycopg[binary]>=3.1
```

For Cloud Run or similar deployment, use Secret Manager mappings for sensitive values:

```text
SMX_LEADS_ADMIN_TOKEN=leads-admin-token-vault:latest
SMX_LEADS_FLASK_SECRET_KEY=leads-flask-secret-key-vault:latest
SMX_LEADS_SMTP_PASSWORD=leads-smtp-password-vault:latest
```

---

## 10. Branding Assets

The package contains default branding assets:

```text
src/smx_leads/default_assets/
  logo.png
  favicon.png
```

During scaffold creation, these are copied into the client project:

```text
plugins/leads/assets/
  logo.png
  favicon.png
```

The admin can replace them from:

```text
/leads/admin/branding
```

The application serves them from:

```text
/leads/assets/logo.png
/leads/assets/favicon.png
```

---

## 11. Email Notifications

`smx-leads` supports optional non-blocking email notifications when a new lead is submitted.

Lead capture is always the priority. If email sending fails, the lead is still stored.

Relevant env vars:

```text
SMX_LEADS_EMAIL_PROVIDER=smtp
SMX_LEADS_SMTP_HOST=smtp.gmail.com
SMX_LEADS_SMTP_PORT=587
SMX_LEADS_SMTP_USERNAME=your-smtp-username
SMX_LEADS_SMTP_PASSWORD=your-smtp-password
SMX_LEADS_DEFAULT_FROM_EMAIL=your-from-email
SMX_LEADS_NOTIFY_TO_EMAIL=admin@example.com
SMX_LEADS_SMTP_USE_TLS=1
```

Set this to disable notifications:

```text
SMX_LEADS_EMAIL_PROVIDER=none
```

---

## 12. Lead Status Workflow

Supported lead statuses:

```text
new
reviewed
contacted
closed
spam
```

Admins can update status and internal notes from:

```text
/leads/admin/submissions/<public_id>
```

---

## 13. UI Shell

The plugin includes a package-owned stylesheet:

```text
src/smx_leads/static/smx-leads.css
```

It is served from:

```text
/leads/static/smx-leads.css
```

The UI follows the SyntaxMatrix plugin shell pattern:

- Top navbar/header
- Desktop navigation on wide screens
- Hamburger/details-style menu on mobile
- Content below the navbar
- No loose navigation links injected randomly into page content

---

## 14. Package Data

The PyPI package includes:

```text
templates/admin/*.html
templates/public/*.html
static/*.css
default_assets/*.png
```

These are declared in `pyproject.toml` under:

```toml
[tool.setuptools.package-data]
```

---

## 15. Development

Install development dependencies:

```powershell
pip install -r requirements-dev.txt
```

Run tests:

```powershell
python -m pytest -q
```

Build package:

```powershell
python -m build
```

---

## 16. Wheel Install Smoke Test

After building:

```powershell
python -m build
```

Install the wheel into a clean virtual environment and verify:

```text
/leads
/leads/admin/login
/leads/static/smx-leads.css
/leads/assets/logo.png
/leads/assets/favicon.png
```

The wheel must include templates, CSS, and default branding assets.

---

## 17. Route Namespace Contract

The test suite protects the namespace contract. All plugin routes must begin with:

```text
/leads
```

This prevents accidental creation of un-namespaced routes such as:

```text
/admin
/submit
/submissions
/branding
```

---

## 18. Public API

The main public import is:

```python
from smx_leads import setup_leads
```

Exported functions:

```python
ensure_leads_scaffold
init_leads
init_leads_from_env
setup_leads
create_leads_assets_blueprint
create_leads_static_blueprint
```

---

## 19. Release Checklist

Before publishing:

```powershell
python -m pytest -q
Remove-Item -Recurse -Force dist build -ErrorAction SilentlyContinue
python -m build
```


---

## 20. Lead AI Agent

`smx-leads` includes an optional Lead AI Agent workflow.

The Lead AI Agent helps admins understand and respond to incoming lead submissions. It can:

- Summarize a lead submission
- Classify the lead type
- Estimate lead priority
- Suggest the next lead status
- Recommend a follow-up action
- Draft a reply
- Estimate spam risk

The AI workflow is admin-triggered. The plugin does not automatically call AI for every new lead.

### Host-Provided AI Client Rule

`smx-leads` does not instantiate or own LLMs.

The host SyntaxMatrix project must provide the AI/model infrastructure.

This keeps the architecture consistent with the SyntaxMatrix plugin pattern:

```text
SyntaxMatrix host project
  -> owns model providers, AI clients, routing, guardrails

smx-leads plugin
  -> owns lead workflow, prompts, contracts, persistence, and admin UI
```

The AI client is passed into the plugin:

```python
from smx_leads import setup_leads

setup_leads(
    app,
    project_root=PROJECT_ROOT,
    init_schema=True,
    ai_profile=AI_PROFILES["google"],
)
```

The host-provided AI client must implement this contract:

```python
class LeadAIClient:
    def generate_lead_insight(self, *, prompt: str) -> dict:
        ...
```

### Admin AI Route

The admin-triggered AI route is:

```text
/leads/admin/submissions/<public_id>/ai/analyze
```

This route is protected by admin authentication and remains under the `/leads/admin` namespace.

If no AI client is configured, the route returns a clear error instead of trying to create a model internally.

### AI Insight Persistence

AI analysis results are stored separately from the original lead submission.

The AI insight table stores:

```text
summary
category
priority
suggested_status
recommended_action
draft_reply
spam_risk
model_name
raw
created_at
```

This preserves the original lead while allowing multiple AI analyses to be stored over time.

### AI Insight Categories

Supported AI insight categories:

```text
general_enquiry
demo_request
pilot_request
support_request
partnership
waitlist
sales
spam
```

Supported priority values:

```text
low
medium
high
```

Supported spam risk values:

```text
low
medium
high
```

Supported suggested statuses:

```text
new
reviewed
contacted
closed
spam
```
