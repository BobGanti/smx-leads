import pytest

from smx_leads.models import LeadSubmissionStatus
from smx_leads.repository import LeadRepository
from smx_leads.runtime import LeadsRuntime


def make_runtime():
    runtime = LeadsRuntime.from_mapping(
        {"database_url": "sqlite+pysqlite:///:memory:"}
    )
    runtime.init_schema()
    return runtime


def test_repository_can_create_and_read_submission():
    runtime = make_runtime()

    with runtime.session_scope() as session:
        repo = LeadRepository(session)
        created = repo.create_submission(
            full_name="Bob Nti",
            email="BOB@example.com",
            phone="123",
            company="SyntaxMatrix",
            subject="Demo request",
            message="I want a product demo.",
            source="demo",
            extra={"page": "/pricing"},
        )

        loaded = repo.get_submission(created.public_id)

    assert created.public_id.startswith("lead_")
    assert created.status == LeadSubmissionStatus.NEW.value
    assert created.email == "bob@example.com"
    assert created.source == "demo"

    assert loaded is not None
    assert loaded.public_id == created.public_id
    assert loaded.extra["page"] == "/pricing"


def test_repository_validates_required_fields():
    runtime = make_runtime()

    with runtime.session_scope() as session:
        repo = LeadRepository(session)

        with pytest.raises(ValueError, match="Full name is required"):
            repo.create_submission(full_name="", email="bob@example.com", message="Hello")

        with pytest.raises(ValueError, match="valid email"):
            repo.create_submission(full_name="Bob", email="bad-email", message="Hello")

        with pytest.raises(ValueError, match="Message is required"):
            repo.create_submission(full_name="Bob", email="bob@example.com", message="")


def test_repository_can_list_and_filter_submissions():
    runtime = make_runtime()

    with runtime.session_scope() as session:
        repo = LeadRepository(session)

        contact = repo.create_submission(
            full_name="Contact Buyer",
            email="contact@example.com",
            message="Contact me.",
            source="contact",
        )
        demo = repo.create_submission(
            full_name="Demo Buyer",
            email="demo@example.com",
            message="Book demo.",
            source="demo",
        )

        repo.update_status(
            public_id=demo.public_id,
            status=LeadSubmissionStatus.CONTACTED.value,
            internal_notes="Called once.",
        )

        all_items = repo.list_submissions()
        demo_items = repo.list_submissions(source="demo")
        contacted_items = repo.list_submissions(status=LeadSubmissionStatus.CONTACTED.value)

    assert {item.public_id for item in all_items} == {contact.public_id, demo.public_id}
    assert [item.public_id for item in demo_items] == [demo.public_id]
    assert [item.public_id for item in contacted_items] == [demo.public_id]
    assert contacted_items[0].internal_notes == "Called once."


def test_repository_rejects_invalid_status():
    runtime = make_runtime()

    with runtime.session_scope() as session:
        repo = LeadRepository(session)
        created = repo.create_submission(
            full_name="Bob",
            email="bob@example.com",
            message="Hello",
        )

        with pytest.raises(ValueError, match="Invalid lead status"):
            repo.update_status(public_id=created.public_id, status="paid")
