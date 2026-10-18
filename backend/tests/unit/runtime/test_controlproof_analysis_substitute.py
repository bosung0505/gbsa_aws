from __future__ import annotations

import json
from uuid import uuid4

import pytest
from interview_evidence.runtime import controlproof_model_substitute as substitutes
from interview_evidence.shared.tenant import ActorType, TenantContext

FIXTURE = "n02-analysis-v1"
DIGEST = "092de5950a39ba3a7255c8696ffb073cddc65cda4615237044e3d910e32f9828"


def environment(fixture: str = FIXTURE) -> dict[str, str]:
    return {
        "APP_ENVIRONMENT": "test",
        "CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED": "true",
        "CONTROLPROOF_MODEL_FIXTURE_ID": fixture,
        "CONTROLPROOF_EXTERNAL_AI_ALLOWED": "false",
        "AI_PROVIDER": "aws",
        "EMBEDDING_PROVIDER": "aws",
        "STT_PROVIDER": "disabled",
        "TTS_PROVIDER": "text_only",
        "BEDROCK_RUNTIME_ENDPOINT_URL": "http://127.0.0.1:4566",
        "TRANSCRIBE_ENDPOINT_URL": "http://127.0.0.1:4566",
        "POLLY_ENDPOINT_URL": "http://127.0.0.1:4566",
        "GCP_DOCUMENT_AI_API_ENDPOINT": "127.0.0.1:4566",
    }


def context() -> TenantContext:
    return TenantContext(
        company_id=uuid4(),
        actor_type=ActorType.SYSTEM,
        actor_id=uuid4(),
        request_id=uuid4(),
        trace_id="n02-analysis-test",
    )


def model_input(payload):
    return {"messages": [{"content": [{"type": "text", "text": json.dumps(payload)}]}]}


def test_strategy_uses_only_current_input_and_preserves_legacy_identity():
    model = substitutes.resolve_controlproof_model(environment(), object())
    criteria = [str(uuid4()), str(uuid4())]
    sources = [str(uuid4()), str(uuid4())]
    payload = {
        "task": "build_interview_strategy",
        "provided_criterion_ids": criteria,
        "provided_source_candidates": [{"source_id": sid} for sid in sources],
    }
    result = model.generate(context(), model_input(payload))
    assert result == model.generate(context(), model_input(payload))
    assert {p["criterion_id"] for p in result["verification_points"]} == set(criteria)
    assert all(set(p["source_ids"]) <= set(sources) for p in result["verification_points"])
    next_source = str(uuid4())
    payload["provided_source_candidates"] = [{"source_id": next_source}]
    following = model.generate(context(), model_input(payload))
    assert {s for p in following["verification_points"] for s in p["source_ids"]} == {next_source}
    health = substitutes.controlproof_health(environment())
    assert (health["fixture_id"], health["fixture_digest"]) == (FIXTURE, DIGEST)
    legacy = substitutes.controlproof_health(environment("h03-report-v1"))
    assert health["ai_isolation_digest"] != legacy["ai_isolation_digest"]
    assert legacy["fixture_digest"] == substitutes.FIXTURE_DIGEST


@pytest.mark.parametrize("bad", [[], ["invalid-uuid"]])
@pytest.mark.parametrize("field", ["provided_criterion_ids", "provided_source_candidates"])
def test_strategy_rejects_missing_or_invalid_axes(field, bad):
    model = substitutes.resolve_controlproof_model(environment(), object())
    payload = {
        "task": "build_interview_strategy",
        "provided_criterion_ids": [str(uuid4())],
        "provided_source_candidates": [{"source_id": str(uuid4())}],
    }
    payload[field] = bad
    with pytest.raises(ValueError):
        model.generate(context(), model_input(payload))


def test_new_fixture_delegates_report_tasks_without_changing_outputs():
    payload = {
        "task": "assess_interview_criterion",
        "criterion": {"criterion_id": str(uuid4())},
        "axes": [{"key": "depth"}],
        "provided_answers": [{"evidence_id": str(uuid4())}],
    }
    request = model_input(payload)
    model = substitutes.resolve_controlproof_model(environment(), object())
    assert model.generate(context(), request) == substitutes.ControlProofFixedModel().generate(
        context(), request
    )
    with pytest.raises(ValueError, match="does not support"):
        model.generate(context(), model_input({"task": "unknown"}))


@pytest.mark.parametrize("fixture", ["h03-report-v1", "spec004-report-v1"])
def test_analysis_replacement_is_opt_in(fixture):
    model, embedder = object(), object()
    resolved = substitutes.resolve_controlproof_analysis(environment(fixture), model, embedder)
    assert resolved == (model, embedder)
    resolved = substitutes.resolve_controlproof_analysis(environment(), model, embedder)
    assert isinstance(resolved[1], substitutes.ControlProofFixedEmbedder)
    assert resolved[0].fixture_id == FIXTURE
    assert substitutes.resolve_controlproof_analysis(
        {"APP_ENVIRONMENT": "production"}, model, embedder
    ) == (model, embedder)


@pytest.mark.parametrize(
    "override",
    [
        {"APP_ENVIRONMENT": "production"},
        {"CONTROLPROOF_EXTERNAL_AI_ALLOWED": "true"},
        {"BEDROCK_RUNTIME_ENDPOINT_URL": "https://bedrock.amazonaws.com"},
    ],
)
def test_analysis_replacement_rejects_nonisolated_configuration(override):
    with pytest.raises(RuntimeError):
        substitutes.resolve_controlproof_analysis(environment() | override, object(), object())
