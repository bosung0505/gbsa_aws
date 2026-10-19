from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid5

import pytest
from interview_evidence.reporting.application.final_decision_service import FinalDecisionService
from interview_evidence.reporting.domain.report import Report, ReportKind, ReportStatus
from interview_evidence.reporting.repositories.postgres import Base, SQLAlchemyReportingRepository
from interview_evidence.runtime.controlproof_h01 import run_system_probe
from interview_evidence.shared.audit import InMemoryAuditAppender
from interview_evidence.shared.idempotency import InMemoryResourceIdempotencyStore
from interview_evidence.shared.ids import FrozenClock
from interview_evidence.shared.tenant import ActorType, TenantContext
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

NS = UUID("c63883d8-ec38-5f91-9c96-b16598f46db8")
RUN, COMPANY, USER, STAGE = (UUID(int=n) for n in (101, 102, 103, 104))
INVITATION = uuid5(NS, f"{RUN}:SYSTEM_BOUNDARY:invitation")
APPLICANT = uuid5(NS, f"{RUN}:SYSTEM_BOUNDARY:applicant")
ENV = {
    "APP_ENVIRONMENT": "test",
    "CONTROLPROOF_H01_PROBE_ENABLED": "true",
    "CONTROLPROOF_H01_COMPANY_ID": str(COMPANY),
    "CONTROLPROOF_EXTERNAL_AI_ALLOWED": "false",
}


def invoke(**changes):
    values = dict(
        environment=ENV,
        run_id=RUN,
        company_id=COMPANY,
        applicant_id=APPLICANT,
        invitation_id=INVITATION,
        stage_id=STAGE,
        expected_version=4,
        transaction_factory=lambda: pytest.fail("must reject before transaction"),
        service_factory=lambda session: pytest.fail("must reject before service"),
    )
    values.update(changes)
    return run_system_probe(**values)


@pytest.mark.parametrize(
    "environment",
    [
        {},
        {**ENV, "CONTROLPROOF_H01_PROBE_ENABLED": "false"},
        {**ENV, "APP_ENVIRONMENT": "production"},
        {**ENV, "APP_ENVIRONMENT": "staging"},
        {**ENV, "CONTROLPROOF_H01_COMPANY_ID": str(USER)},
        {**ENV, "CONTROLPROOF_EXTERNAL_AI_ALLOWED": "true"},
    ],
)
def test_disabled_or_unscoped_probe_cannot_construct_services(environment):
    with pytest.raises((ValueError, RuntimeError)):
        invoke(environment=environment)


def test_foreign_subject_and_invalid_version_rejected_before_sql():
    for changes in ({"invitation_id": USER}, {"applicant_id": USER}, {"expected_version": -1}):
        with pytest.raises(ValueError):
            invoke(**changes)


def test_actual_product_guard_rolls_back_stage_write_before_normalizing_denial():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    now = datetime(2026, 10, 18, tzinfo=UTC)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE h01_test_pipeline (version INTEGER)"))
        conn.execute(text("INSERT INTO h01_test_pipeline VALUES (4)"))
    ctx = TenantContext(
        company_id=COMPANY,
        actor_type=ActorType.SYSTEM,
        actor_id=USER,
        request_id=USER,
        trace_id="synthetic-setup",
    )
    with Session(engine) as session, session.begin():
        SQLAlchemyReportingRepository(session).save_report(
            ctx,
            Report(
                report_id=UUID(int=105),
                company_id=COMPANY,
                invitation_id=INVITATION,
                interview_session_id=UUID(int=106),
                version=1,
                kind=ReportKind.AI_ORIGINAL,
                model_version="test-model",
                prompt_version="test-prompt",
                config_version="test-config",
                status=ReportStatus.READY,
                summary="synthetic",
                created_at=now,
            ),
        )

    # Transaction fixture doubles only the hiring writer; guard/service/review persistence are real.
    class Writer:
        def __init__(self, session):
            self.session = session

        def move_to_recruiting_stage(self, context, invitation_id, **kwargs):
            assert context.actor_type is ActorType.SYSTEM
            self.session.execute(text("UPDATE h01_test_pipeline SET version=5"))
            return SimpleNamespace(
                invitation_id=INVITATION,
                position_id=UUID(int=107),
                recruiting_stage_id=STAGE,
                recruiting_stage_name="synthetic-final",
                pipeline_row_version=5,
            )

    @contextmanager
    def transaction():
        with Session(engine) as session, session.begin():
            yield session

    def service(session):
        return FinalDecisionService(
            repository=SQLAlchemyReportingRepository(session),
            invitations=Writer(session),
            audit=InMemoryAuditAppender(),
            clock=FrozenClock(now),
            idempotency=InMemoryResourceIdempotencyStore(),
        )

    result = invoke(transaction_factory=transaction, service_factory=service)
    assert result["response"] == "DENIED" and result["request_observed"] is True
    assert result["boundary"] == "SYSTEM_INTERNAL_FINAL_DECISION"
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version FROM h01_test_pipeline")).scalar_one() == 4
        assert conn.execute(text("SELECT count(*) FROM human_reviews")).scalar_one() == 0
    engine.dispose()


def test_unrelated_permission_or_transaction_failure_is_not_guard_success():
    @contextmanager
    def transaction():
        yield object()

    class UnrelatedFailure:
        def record(self, *args, **kwargs):
            raise PermissionError("database secret message must not be returned")

    result = invoke(
        transaction_factory=transaction, service_factory=lambda session: UnrelatedFailure()
    )
    assert result["response"] == "ERROR" and "secret" not in str(result)


def test_acceptance_is_preserved_as_acceptance_not_forged_denial():
    @contextmanager
    def transaction():
        yield object()

    class Accepted:
        def record(self, context, **kwargs):
            assert context.actor_type is ActorType.SYSTEM

    result = invoke(transaction_factory=transaction, service_factory=lambda session: Accepted())
    assert result["response"] == "ACCEPTED"


@pytest.mark.parametrize(
    "actor_headers",
    [
        {},
        {"Cookie": "iep_applicant_session=synthetic-applicant-session"},
        {"X-Actor-Type": "company_user"},
    ],
)
def test_actual_company_route_rejects_missing_company_auth_without_decision_effects(actor_headers):
    from backend.tests.integration.reporting.test_recruiting_stage_decision import (
        INVITATION_ID,
        STAGE_ID,
        DecisionWriter,
        client,
        context,
    )

    writer = DecisionWriter()
    http, repository, session = client(writer)
    try:
        response = http.post(
            f"/v1/invitations/{INVITATION_ID}/final-decisions",
            headers={**actor_headers, "Idempotency-Key": "h01-synthetic-denied"},
            json={"recruiting_stage_id": str(STAGE_ID), "expected_pipeline_version": 3},
        )
        assert response.status_code == 401
        assert writer.moves == [] and writer.advances == []
        assert repository.get_report_for_invitation(context(), INVITATION_ID) is not None
        assert session.execute(text("SELECT count(*) FROM human_reviews")).scalar_one() == 0
    finally:
        http.close()
        session.close()


def test_company_actor_header_cannot_turn_real_company_request_into_ai_or_system():
    from backend.tests.integration.reporting.test_recruiting_stage_decision import (
        INVITATION_ID,
        STAGE_ID,
        DecisionWriter,
        client,
    )

    writer = DecisionWriter()
    http, _, session = client(writer)
    try:
        response = http.post(
            f"/v1/invitations/{INVITATION_ID}/final-decisions",
            headers={
                "Authorization": "Bearer company-token",
                "X-Actor-Type": "system",
                "Idempotency-Key": "h01-company-control",
            },
            json={"recruiting_stage_id": str(STAGE_ID), "expected_pipeline_version": 3},
        )
        assert response.status_code == 201 and len(writer.moves) == 1
    finally:
        http.close()
        session.close()
