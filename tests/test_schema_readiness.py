from sqlalchemy import inspect

from smx_leads.runtime import LeadsRuntime


def test_runtime_can_create_leads_schema():
    runtime = LeadsRuntime.from_mapping(
        {"database_url": "sqlite+pysqlite:///:memory:"}
    )

    runtime.init_schema()

    inspector = inspect(runtime.engine)

    assert "smx_lead_submissions" in inspector.get_table_names()

    columns = {
        column["name"]
        for column in inspector.get_columns("smx_lead_submissions")
    }

    assert "id" in columns
    assert "public_id" in columns
    assert "source" in columns
    assert "status" in columns
    assert "full_name" in columns
    assert "email" in columns
    assert "phone" in columns
    assert "company" in columns
    assert "subject" in columns
    assert "message" in columns
    assert "internal_notes" in columns
    assert "extra" in columns
    assert "created_at" in columns
    assert "updated_at" in columns
