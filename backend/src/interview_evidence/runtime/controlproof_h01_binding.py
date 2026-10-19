"""Isolated H-01 process boundary using production SQL service classes, no HTTP bypass route."""

import json
import os
import sys
from contextlib import contextmanager
from uuid import UUID, uuid5

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from interview_evidence.company_management.adapters.applicant_session import ApplicantSessionAdapter
from interview_evidence.company_management.api import create_sql_repository as company_repository
from interview_evidence.company_management.application.company_service import (
    CompanyManagementPublic,
)
from interview_evidence.company_management.application.hiring_service import (
    ApplicantPipelineMove,
    HiringService,
)
from interview_evidence.integration.reporting_company import (
    ReportingCompanyBoundary,
    ReportingHiringBoundary,
)
from interview_evidence.reporting.api import create_sql_repository as reporting_repository
from interview_evidence.reporting.application.deletion_service import DeletionService
from interview_evidence.reporting.application.final_decision_service import FinalDecisionService
from interview_evidence.reporting.application.public import ReportingPublic
from interview_evidence.runtime.controlproof_h01 import NAMESPACE, run_system_probe
from interview_evidence.shared.ids import CommandMeta, SystemClock
from interview_evidence.shared.persistence import (
    SQLApplicantSessionStore,
    SQLAuditAppender,
    SQLCommandIdempotencyStore,
)
from interview_evidence.shared.tenant import ActorType, TenantContext


def main():
    body = json.load(sys.stdin)  # synthetic IDs only; never a credential
    env = os.environ
    if (
        env.get("APP_ENVIRONMENT") not in {"local", "test"}
        or env.get("CONTROLPROOF_H01_PROBE_ENABLED") != "true"
        or env.get("CONTROLPROOF_EXTERNAL_AI_ALLOWED") != "false"
    ):
        raise RuntimeError("H01 binding disabled")
    run_id, company_id, applicant_id, invitation_id, stage_id = (
        UUID(body[k]) for k in ("run_id", "company_id", "applicant_id", "invitation_id", "stage_id")
    )
    preparation = body.get("operation") == "prepare_completed_interview_fixture"
    case = body.get("case") if preparation else "SYSTEM_BOUNDARY"
    if (
        env.get("CONTROLPROOF_H01_COMPANY_ID") != str(company_id)
        or case
        not in {
            "COMPANY_CONTROL",
            "APPLICANT_HTTP",
            "ANONYMOUS_HTTP",
            "SYSTEM_BOUNDARY",
            "AI_ASSISTANT",
        }
        or applicant_id != uuid5(NAMESPACE, f"{run_id}:{case}:applicant")
        or invitation_id != uuid5(NAMESPACE, f"{run_id}:{case}:invitation")
        or body["path"] not in {"FINAL_DECISION", "BATCH_ACCEPT", "BATCH_REJECT"}
    ):
        raise ValueError("H01 subject not owned")
    from urllib.parse import urlsplit

    if urlsplit(env["DATABASE_URL"].replace("postgresql+psycopg", "postgresql")).hostname not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
        raise ValueError("H01 database must be loopback")
    engine = create_engine(env["DATABASE_URL"])

    @contextmanager
    def transaction():
        with Session(engine) as session, session.begin():
            yield session

    if preparation:
        clock = SystemClock()
        context = TenantContext(
            company_id=company_id,
            actor_type=ActorType.SYSTEM,
            actor_id=uuid5(NAMESPACE, f"{run_id}:fixture-system"),
            request_id=uuid5(NAMESPACE, f"{run_id}:fixture-prepare"),
            trace_id=f"controlproof:h01:{run_id}:fixture",
        )
        transitions = []
        with transaction() as session:
            company = CompanyManagementPublic(company_repository(session), clock)
            states = (
                "consented",
                "materials_submitted",
                "analyzing",
                "ready",
                "interviewing",
                "completed",
            )
            for previous, following in zip(states[:-1], states[1:], strict=True):
                current = company.authorize_invitation(
                    context, invitation_id, required_state=previous
                )
                updated = company.advance_invitation_state(
                    context,
                    invitation_id,
                    from_state=previous,
                    to_state=following,
                    meta=CommandMeta.create(
                        f"h01-fixture-{run_id}-{following}",
                        expected_version=current.row_version,
                        clock=clock,
                    ),
                )
                transitions.append(
                    {"from": previous, "to": updated.state, "row_version": updated.row_version}
                )
        print(
            json.dumps(
                {
                    "operation": "prepare_completed_interview_fixture",
                    "run_id": str(run_id),
                    "invitation_id": str(invitation_id),
                    "transitions": transitions,
                    "synthetic_completed_interview": True,
                }
            )
        )
        return

    def services(session):
        clock = SystemClock()
        company = company_repository(session)
        reports = reporting_repository(session)
        sessions = ApplicantSessionAdapter(clock=clock, store=SQLApplicantSessionStore(session))
        hiring = HiringService(company, sessions, clock, SQLCommandIdempotencyStore(session))
        boundary = ReportingHiringBoundary(CompanyManagementPublic(company, clock), hiring)
        final = FinalDecisionService(
            repository=reports,
            invitations=boundary,
            audit=SQLAuditAppender(session),
            clock=clock,
            idempotency=SQLCommandIdempotencyStore(session),
        )
        return (
            final,
            hiring,
            ReportingCompanyBoundary(
                ReportingPublic(repository=reports, deletion_service=DeletionService(reports))
            ),
        )

    if body["path"] == "FINAL_DECISION":
        result = run_system_probe(
            env,
            run_id=run_id,
            company_id=company_id,
            applicant_id=applicant_id,
            invitation_id=invitation_id,
            stage_id=stage_id,
            expected_version=body["expected_version"],
            transaction_factory=transaction,
            service_factory=lambda s: services(s)[0],
        )
    else:
        request_id = uuid5(NAMESPACE, f"{run_id}:SYSTEM_BOUNDARY:request")
        context = TenantContext(
            company_id=company_id,
            actor_type=ActorType.SYSTEM,
            actor_id=uuid5(NAMESPACE, f"{run_id}:SYSTEM_BOUNDARY:system"),
            request_id=request_id,
            trace_id=f"controlproof:h01:{run_id}:SYSTEM_BOUNDARY",
        )
        response, entered = "ERROR", False
        try:
            with transaction() as session:
                _, hiring, reviews = services(session)
                entered = True
                hiring.move_applicants(
                    context,
                    position_id=UUID(body["position_id"]),
                    target_stage_id=stage_id,
                    moves=(ApplicantPipelineMove(invitation_id, body["expected_version"]),),
                    invitation_reviews=reviews,
                    require_final_report=True,
                )
                response = "ACCEPTED"
        except PermissionError as error:
            if entered and str(error) == "final stage requires a human company user":
                response = "DENIED"
        except Exception:
            response = "ERROR"
        result = dict(
            boundary="SYSTEM_INTERNAL_BATCH_STAGE",
            case="SYSTEM_BOUNDARY",
            run_id=str(run_id),
            request_id=str(request_id),
            response=response,
            request_observed=entered,
        )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
