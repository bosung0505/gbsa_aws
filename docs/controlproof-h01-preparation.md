# ControlProof H-01 — local stage2 complete (2026-10-19)

Final actual39a0d317-b36d-4cf1-8b09-aebb404d5891:15 cases across final-decision/final-accept/final-reject,
A1~A6 PASS, VERIFIED17, restore SUCCEEDED. Independent read-only44-table audit: owned residues0,
baseline company/user1 each retained. Frozen local sources CP2edd0b097fef7089bdc580020c7f4ddca46ad986 /
Why08c397e68fca5d4179e1fcd83afd27bfc1ed78a2; these are validation SHAs, not remote publication SHAs.

First actual7d6024ce FAIL exposed SYSTEM batch final-accept/reject writes. Preserve that bundle and
its disclosed collector-journal recovery. HiringService now requires COMPANY_USER for final stages
before writes; ordinary nonfinal SYSTEM moves remain allowed. Both intermediate INCONCLUSIVE Runs
remain visible. The CLI-only local/test SYSTEM binding invokes real SQL services and transactions.

Actual assistant API uses company authentication, not an invented AI actor. H-01-only opt-in fixed
model/embedder binding emits an adversarial decision claim; actual generation receipts, owned report
sources, assistant audits and unchanged decision state were verified for all three paths. Default,
legacy and production composition remain unchanged. Synthetic completed-interview inputs prepare the
real state transitions/consent/report worker; this does not claim external AI quality or a real interview.

Final WhyYou regression237 PASS. Shared ControlProof QA20 pages/32 proof panels passed, documentation
and12/6/3/3 catalog converged. Runtime artifacts stay outside Git. Both original workspaces remain
fixes-and-remaining-work; no H-01 commit/push. See ControlProof specs/006-h01-human-decision/validation.md,
actual-closure.md and quickstart.md for exact lineage/hashes/portable commands. H-02/AWS remain NOT_RUN.

## Historical stage1 preparation — 2026-10-18

Branch `fixes-and-remaining-work`; baseline `33aa9967e6b69de4b3789d2009cae1d3eb798d74`.
User authorized stage1 only. Actual H-01 NOT_RUN; no live DB/service/worker execution in this work.

Existing final-decision API, company authentication, domain guard and transaction boundaries are
unchanged. New module `runtime/controlproof_h01.py` supplies only an opt-in local/test SYSTEM
probe around a caller-supplied product service and transaction. It is not registered as an HTTP
route or composed into the application. Production/staging/default-disabled, non-allowlisted
companies and noncanonical Run-owned subjects are rejected before service/transaction construction.

SYSTEM denial is caught outside the transaction to preserve rollback. Only the exact existing
product guard denial is classified DENIED; unrelated PermissionError/transaction errors remain
ERROR. Acceptance is retained as ACCEPTED, never forged into a successful refusal. No AI role is
added. Real assistant requests currently use company-user caller authentication; that fact does
not mean an assistant has final-decision authority.

Automatic evidence: new helper/router suite14 PASS, covering actual FinalDecisionService/domain
guard with a transactional SQLite hiring-writer fixture and real FastAPI final-decision routes.
The SQLite writer is a test double; these tests do not prove live product Postgres rollback.
Full final regressions/source mapping are in ControlProof Spec006 validation/traceability.

Stage2 must bind real report lifecycle/owned cleanup, product transaction/service factories,
actual assistant operation, refusal records and final-stage batch-route coverage before full
official actual validation. No product guard is fixed before a preserved real FAIL. Existing
runtime probes/.env/new bundles stay local. No main merge or remote publication in this stage.

## Final regression

WhyYou runtime/reporting + human-only/recruiting-stage/final-decision idempotency selection:
224 PASS in6.02s. The first collection exposed removed InMemoryReportingRepository in the
legacy H-01 test; restored it to current SQL persistence/SQLite and SYSTEM/APPLICANT cases
without modifying product guards. CP preparation/compatibility selection122 PASS in4.25s.
Both changed-source Ruff/diff checks pass. Dependency deprecations remain documented in CP
validation. Sources are local/uncommitted; actual H-01 NOT_RUN and stage2 binding gates remain.
