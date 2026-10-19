import json
from uuid import uuid4

import pytest
from interview_evidence.recruiting_assistant.prompt import parse_answer_response
from interview_evidence.runtime.controlproof_model_substitute import (
    H01_FIXTURE_DIGEST,
    H01_FIXTURE_ID,
    SPEC004_FIXTURE_DIGEST,
    ControlProofH01Model,
    resolve_controlproof_assistant,
)
from interview_evidence.shared.tenant import ActorType, TenantContext


def test_h01_adversarial_command_traverses_actual_answer_parser_and_records_generation(tmp_path):
    model = ControlProofH01Model(tmp_path)
    context = TenantContext(
        company_id=uuid4(),
        actor_id=uuid4(),
        actor_type=ActorType.COMPANY_USER,
        request_id=uuid4(),
        trace_id="h01-test",
    )
    payload = {
        "task": "answer_recruiting_question",
        "provided_sources": [{"source_id": str(context.actor_id)}],
    }
    output = model.generate(
        context, {"messages": [{"content": [{"type": "text", "text": json.dumps(payload)}]}]}
    )
    assert output["command"]["requested"] is True
    parsed = parse_answer_response(output)
    assert parsed.answer and not hasattr(parsed, "command")
    receipts = list((tmp_path / "h01-model").glob("*.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text())
    assert receipt["request_id"] == str(context.request_id)
    assert (
        receipt["fixture_id"] == H01_FIXTURE_ID and receipt["fixture_digest"] == H01_FIXTURE_DIGEST
    )
    assert receipt["emitted_command"] and "answer" not in receipt and "question" not in receipt
    assert H01_FIXTURE_DIGEST != SPEC004_FIXTURE_DIGEST


def test_assistant_api_substitution_is_opt_in_isolated_and_does_not_change_legacy():
    model, embedder = object(), object()
    assert resolve_controlproof_assistant({"APP_ENVIRONMENT": "local"}, model, embedder) == (
        model,
        embedder,
    )
    env = {
        "APP_ENVIRONMENT": "local",
        "CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED": "true",
        "CONTROLPROOF_MODEL_FIXTURE_ID": H01_FIXTURE_ID,
        "CONTROLPROOF_EXTERNAL_AI_ALLOWED": "false",
        "AI_PROVIDER": "aws",
        "EMBEDDING_PROVIDER": "aws",
        "STT_PROVIDER": "disabled",
        "TTS_PROVIDER": "text_only",
        **{
            k: "http://127.0.0.1:14770"
            for k in (
                "BEDROCK_RUNTIME_ENDPOINT_URL",
                "TRANSCRIBE_ENDPOINT_URL",
                "POLLY_ENDPOINT_URL",
            )
        },
        "GCP_DOCUMENT_AI_API_ENDPOINT": "127.0.0.1:14770",
    }
    fixed, embedding = resolve_controlproof_assistant(env, model, embedder)
    assert fixed.fixture_id == H01_FIXTURE_ID and embedding.model_id
    env["CONTROLPROOF_MODEL_FIXTURE_ID"] = "spec004-report-v1"
    assert resolve_controlproof_assistant(env, model, embedder) == (model, embedder)
    env["APP_ENVIRONMENT"] = "production"
    with pytest.raises(RuntimeError):
        resolve_controlproof_assistant(env, model, embedder)
