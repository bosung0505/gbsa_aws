# ControlProof maintenance checkpoint — 2026-10-19

Later sharing decision (2026-10-19, ControlProof D-029): the user requested sharing reviewed actual
evidence and lineage with the code so teammates can view the same result snapshot. The exclusion
of all new bundles below describes the preceding publication checkpoint, not a continuing ban.
Raw probes/.env/credentials remain excluded; preserve original bytes and source SHAs. Policy and
preparation are documented in the sibling ControlProof repository's
`docs/research/Run_Record_Sharing_Preparation.md`. Subsequent Spec008 implements the shared snapshot
(25 actual Runs/600 files), read-only default viewer and isolated Git clone validation. See the sibling
ControlProof `review-data/README.md` and Spec008 validation. Sharing a past Run is not independent re-execution. No WhyYou code change is needed
for the policy update or for reading an existing sealed result.
ControlProof shared-view implementation/data publication checkpoint: `b76af4c8daeeadbb5aa7c7e40a4d9365e33ad08b`
on `bosung0505/AI_Compliance_SaaS_controlproof` / `fixes-and-remaining-work`.

User authorized committing/pushing the completed work on the existing fixes-and-remaining-work
branch in both repositories. WhyYou publishes to the personal fork bosung0505/gbsa_aws; upstream
main remains unchanged. No new publication branch is used. Runtime probes/new bundles/.env/credentials
are excluded. Preserve the exact historical Spec003 bundle exception.

Included WhyYou changes: H01 COMPANY_USER check before final batch-stage decisions; H02 read-only
assistant pipeline reader; disabled local/test-only actual-composition inspectors and separate
H01/H02 synthetic model bindings/receipts; regression tests and handoff documentation.
ControlProof contains canonical H01/H02 profiles, sealed evidence validation and result display.
Only H02 currently displays discovery→separate WhyYou development remedy→ControlProof retest;
other completed scenarios have a documented historical audit, not the same new display yet.

Actual validation source SHAs are frozen local checkpoints, not this publication commit:
H01 WhyYou08c397e / CP2edd0b0; H02 WhyYouaf36f25 / CPf3ede39. Final H01 39a0d317… all6PASS,
H02 c12c2ce8… all6PASS, restore succeeded and independent44-table owned residues0. First factual
FAIL and all incomplete runs remain unchanged. Fixed synthetic models/local environment only;
external model quality and AWS not tested. Details in ControlProof Spec006/007 actual-closure,
Spec005 remediation-history and docs/research/WhyYou_Remediation_History_Audit.md.

Completed validation before publication: WhyYou288 scoped regression PASS; CP display/readmodel
44 PASS and permitted-loopback HTTP8 PASS; actual UI16pages/20panels at1280/1024, allHTTP200 and
no overflow/console errors; source-byte preservation and all291viewerfile hashes unchanged.
Full Spec005 external usability and N01/N03 work remain separate.
