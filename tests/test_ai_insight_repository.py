from sqlalchemy import inspect

from smx_leads.ai import LeadAIInsight, LeadAIInsightRepository
from smx_leads.repository import LeadRepository
from smx_leads.runtime import LeadsRuntime


def make_runtime():
    runtime = LeadsRuntime.from_mapping(
        {"database_url": "sqlite+pysqlite:///:memory:"}
    )
    runtime.init_schema()
    return runtime


def make_insight(summary="Bob wants a demo."):
    return LeadAIInsight(
        summary=summary,
        category="demo_request",
        priority="high",
        suggested_status="reviewed",
        recommended_action="Offer demo slots.",
        draft_reply="Hi Bob, thanks for your interest.",
        spam_risk="low",
        model_name="host-model",
        raw={"summary": summary},
    )


def test_schema_includes_ai_insight_table():
    runtime = make_runtime()
    inspector = inspect(runtime.engine)

    assert "smx_lead_ai_insights" in inspector.get_table_names()

    columns = {
        column["name"]
        for column in inspector.get_columns("smx_lead_ai_insights")
    }

    assert "id" in columns
    assert "lead_public_id" in columns
    assert "summary" in columns
    assert "category" in columns
    assert "priority" in columns
    assert "suggested_status" in columns
    assert "recommended_action" in columns
    assert "draft_reply" in columns
    assert "spam_risk" in columns
    assert "model_name" in columns
    assert "raw" in columns
    assert "created_at" in columns


def test_ai_insight_repository_can_save_and_fetch_latest_for_lead():
    runtime = make_runtime()

    with runtime.session_scope() as session:
        lead_repo = LeadRepository(session)
        lead = lead_repo.create_submission(
            full_name="Bob Nti",
            email="bob@example.com",
            message="I want a demo.",
            source="demo",
        )

        insight_repo = LeadAIInsightRepository(session)
        first = insight_repo.create_insight(
            lead_public_id=lead.public_id,
            insight=make_insight("First summary."),
        )
        second = insight_repo.create_insight(
            lead_public_id=lead.public_id,
            insight=make_insight("Second summary."),
        )

        items = insight_repo.list_for_lead(lead_public_id=lead.public_id)
        latest = insight_repo.get_latest_for_lead(lead_public_id=lead.public_id)

    assert first.id != second.id
    assert [item.summary for item in items] == ["Second summary.", "First summary."]

    assert latest is not None
    assert latest.id == second.id
    assert latest.lead_public_id == lead.public_id
    assert latest.category == "demo_request"
    assert latest.priority == "high"
    assert latest.suggested_status == "reviewed"
    assert latest.raw["summary"] == "Second summary."
