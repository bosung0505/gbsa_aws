# N-02 analysis preparation — stage 1 (2026-10-18)

User authorized preparation/automatic verification first, actual N-02 validation second.
Branch: `feature/n02-analysis-preparation`, base `374b122`; source changes are local/uncommitted.
The historical WhyYou N-02 actual verdict remains INCONCLUSIVE. No new actual Run in this stage.

## Contract and implementation

- Opt-in fixture `n02-analysis-v1`, SHA-256 identity digest
  `092de5950a39ba3a7255c8696ffb073cddc65cda4615237044e3d910e32f9828`.
- `ControlProofAnalysisModel` produces deterministic `build_interview_strategy` responses using
  only provided source/criterion UUIDs. Missing/malformed axes and unsupported tasks fail;
  report assessment delegates to the unchanged H-03 model. No external fallback.
- `resolve_controlproof_analysis` replaces model and embedding in the analysis worker pipeline
  only for this fixture, under existing local/test and external-AI isolation controls.
  Legacy H-03/Spec004 and disabled/production defaults preserve their original analysis dependencies.
- The API/worker isolation fingerprint includes the new identity; restart both with matching
  settings. ControlProof checks managed-worker freshness and matching isolation proof.
- Native text PDF extraction, product response validation and persistence remain real pipeline
  operations. The fixture does not directly insert successful analysis/strategy rows.
- ControlProof explicitly drives both required materials (resume and cover_letter). Selecting
  this fixture alone does not start an actual Run or update the web/official verdict.

## Cycle and verification

Specify/clarify/plan/tasks/analyze recorded first in ControlProof
`specs/003-n02-consent-order/analysis-preparation.md` (FR-042~045, T094~T100).
Initial new model tests: 11 expected failures. After implementation, model/legacy suite 64 PASS;
composition/pipeline suite 22 PASS. Final scoped regression 385 PASS in 11.76 seconds:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -x -p no:cacheprovider --basetemp ../AI_Compliance_SaaS_controlproof/.controlproof/test-tmp/n02-wy-regression-unsandboxed --tb=short backend/tests/unit/runtime backend/tests/unit/submission_analysis backend/tests/unit/reporting backend/tests/unit/interview_engine backend/tests/unit/shared/test_pdf_document_extraction.py backend/tests/integration/submission_analysis/test_analysis_pipeline.py backend/tests/integration/test_worker_delivery.py
```

Use an existing writable TEMP/TMP and a fresh bounded pytest temp leaf. Windows sandbox restricted
default temp writes and stalled an existing in-process HTTP TestClient; the same selection passed
outside the sandbox. No service workaround was introduced. Changed-file Ruff and diff check PASS.
Deprecation warnings remain in dependencies; no failing test in the final selected suite.

Integration checks cover actual PDF parsing, persisted chunks/analysis, validated strategy,
idempotent processing/finalization and invalid structured output preventing strategy creation.
These in-memory/stubbed infrastructure tests do not prove a running API/worker or external-model quality.

Stage 2: reviewed/versioned sources, matching local API/managed workers, current cleanup/parent
checks, fresh ControlProof preflight with `scenarios/_N-02-analysis.yaml`, new linked actual Run,
verify/restore and truthful official/UI closure. No main merge, credentials, production data or
raw evidence publication is part of this checkpoint.

## Stage-2 actual outcome — 2026-10-18

Preparation was followed by an isolated real API/managed-worker N-02 Run, using clean local
WhyYou source `e64ff9deb1e46dd8c6da452434f3ff8d3a1aa613` and CP `3ea1509603173702dbae25de268fd2276c07346d`. Final child
`16dbd987-23a5-4030-bb62-77787488969b`: A1~A7 PASS, COMPLETED, VERIFIED21, restore SUCCEEDED.
Normal and recovered document analysis traverse real product parsing/structured-response
validation/persistence; deterministic model output is not an external AI quality evaluation.
CP fixed projected start receipts and bounded dependent cleanup after preserving two interim
attempts. Independent audit of all three Runs: owned DB residual rows0, no active faults/blocks;
isolated synthetic object uploads retained. Original WhyYou workspace and `.env` were not used
as actual source/environment. Main/remote publication/AWS/latest-fixture other-PC validation separate.
Full source, manifest, attempts and journal references: ControlProof Spec003 actual-closure/validation.

## Continuing integration branch — 2026-10-18

After local closure, the user authorized committing and pushing this state and continuing future
fixes/remaining tasks on `fixes-and-remaining-work`. Publish this WhyYou branch to the `fork`
remote (`bosung0505/gbsa_aws`); ControlProof uses the same branch name on its `origin`.
The actual Run's frozen source SHA remains unchanged; publication commits are later checkpoints.
Runtime probes, `.env`, credentials and new raw bundles stay local. No upstream main merge.
