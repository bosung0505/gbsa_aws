"""Opt-in local/test SYSTEM probe around the existing final-decision transaction.

Not an HTTP endpoint, new role, guard, or production composition change. The actual binding
must supply the product transaction/service and collect independent post-request state.
"""

from uuid import UUID, uuid5

from interview_evidence.shared.tenant import ActorType, TenantContext

NAMESPACE = UUID("c63883d8-ec38-5f91-9c96-b16598f46db8")


def run_system_probe(
    environment,
    *,
    run_id,
    company_id,
    applicant_id,
    invitation_id,
    stage_id,
    expected_version,
    transaction_factory,
    service_factory,
):
    if (
        environment.get("CONTROLPROOF_H01_PROBE_ENABLED", "").lower() != "true"
        or environment.get("APP_ENVIRONMENT") not in {"local", "test"}
        or environment.get("CONTROLPROOF_EXTERNAL_AI_ALLOWED", "").lower() != "false"
    ):
        raise RuntimeError("H-01 probe is disabled or outside isolated local/test")
    run_id, company_id, applicant_id, invitation_id, stage_id = (
        UUID(str(value)) for value in (run_id, company_id, applicant_id, invitation_id, stage_id)
    )
    if environment.get("CONTROLPROOF_H01_COMPANY_ID") != str(company_id):
        raise ValueError("H-01 company is not allowlisted")
    if (
        invitation_id != uuid5(NAMESPACE, f"{run_id}:SYSTEM_BOUNDARY:invitation")
        or applicant_id != uuid5(NAMESPACE, f"{run_id}:SYSTEM_BOUNDARY:applicant")
        or type(expected_version) is not int
        or expected_version < 0
    ):
        raise ValueError("H-01 subject is not canonical and Run owned")
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
        with transaction_factory() as session:
            service = service_factory(session)
            entered = True
            service.record(
                context,
                invitation_id=invitation_id,
                recruiting_stage_id=stage_id,
                expected_pipeline_version=expected_version,
                idempotency_key=f"controlproof:h01:{request_id}",
            )
            response = "ACCEPTED"
    except PermissionError as error:
        # Outside `with`: the actual transaction has already rolled back.
        if entered and str(error) in {
            "final decision requires a human company user",
            "final stage requires a human company user",
        }:
            response = "DENIED"
    except Exception:  # noqa: BLE001 - safe result; no provider message leaves the boundary
        response = "ERROR"
    return {
        "boundary": "SYSTEM_INTERNAL_FINAL_DECISION",
        "case": "SYSTEM_BOUNDARY",
        "run_id": str(run_id),
        "request_id": str(request_id),
        "response": response,
        "request_observed": entered,
    }
