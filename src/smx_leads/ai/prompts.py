from __future__ import annotations

from smx_leads.repository import LeadSubmission


def build_lead_analysis_prompt(lead: LeadSubmission) -> str:
    return f"""You are the Lead Intelligence Agent for a SyntaxMatrix-based project.

Analyze the lead submission and return a JSON object with these fields:

- summary
- category
- priority
- suggested_status
- recommended_action
- draft_reply
- spam_risk

Allowed priority values:
- low
- medium
- high

Allowed suggested_status values:
- new
- reviewed
- contacted
- closed
- spam

Allowed spam_risk values:
- low
- medium
- high

Lead submission:

Reference:
{lead.public_id}

Source:
{lead.source}

Current status:
{lead.status}

Full name:
{lead.full_name}

Email:
{lead.email}

Phone:
{lead.phone}

Company:
{lead.company}

Subject:
{lead.subject}

Message:
{lead.message}

Return only structured JSON-compatible data. Do not invent facts that are not present in the lead.
"""
