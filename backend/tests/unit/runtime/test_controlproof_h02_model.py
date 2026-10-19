import json
from uuid import uuid4

import pytest
from interview_evidence.runtime.controlproof_h02_binding import capture
from interview_evidence.runtime.controlproof_model_substitute import ControlProofH02Model
from interview_evidence.shared.tenant import ActorType, TenantContext


@pytest.mark.parametrize("score", [35, 90])
def test_h02_score_is_model_output_with_real_evidence_and_own_receipt(tmp_path, score):
    context = TenantContext(
        company_id=uuid4(),
        actor_id=uuid4(),
        actor_type=ActorType.SYSTEM,
        request_id=uuid4(),
        trace_id="h02-fixed",
    )
    evidence = str(uuid4())
    payload = {
        "task": "assess_interview_criterion",
        "criterion": {
            "criterion_id": str(uuid4()),
            "text": "[controlproof-spec004 mode=VALID] synthetic",
        },
        "provided_answers": [
            {
                "evidence_id": evidence,
                "answer_text": f"[controlproof-h02 score={score}] Synthetic answer",
            }
        ],
        "axes": [{"key": "correctness"}],
    }
    request = {"messages": [{"content": [{"type": "text", "text": json.dumps(payload)}]}]}
    result = ControlProofH02Model(tmp_path).generate(context, request)
    assert result["axis_scores"][0]["score"] == score
    assert result["axis_scores"][0]["quoted_evidence_ids"] == [evidence]
    receipt = json.loads(next((tmp_path / "h02-model").glob("*.json")).read_text())
    assert receipt["emitted_score"] == score and receipt["request_id"] == str(context.request_id)


def test_inspector_is_disabled_before_runtime_dependency_construction():
    with pytest.raises(RuntimeError, match="disabled"):
        capture({"APP_ENVIRONMENT": "production"})


def test_inspector_traverses_actual_included_router_routes():
    from fastapi import APIRouter, FastAPI
    from interview_evidence.runtime.controlproof_h02_binding import _application_routes

    router = APIRouter(prefix="/v1/assistant")

    @router.post("/answers")
    def answer():
        return {}

    app = FastAPI()
    app.include_router(router)
    assert [
        (r.path, r.endpoint)
        for r in _application_routes(app.routes)
        if "/assistant/" in getattr(r, "path", "")
    ] == [("/v1/assistant/answers", answer)]
