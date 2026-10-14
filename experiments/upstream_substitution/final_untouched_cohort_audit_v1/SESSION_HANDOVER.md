# CommonPose final-cohort audit handover — 2026-09-24

## Objective and frozen decisions

This completed lane is a metadata-only availability/sample-size audit. It did not choose N, freeze final identities, download candidate files, or inspect candidate outcomes. Gate4E Requirement-U and Gate4F Requirement-B are separate closed contracts. The proposed future rule is in `PROPOSED_SELECTION_RULE.md`; it has not been executed.

## Verified state and scientific evidence

Official metadata SHA256 `0e7ad04a79a0f162385d22ec8d6f43af9b8360978ca11ef9d601bbf9594b09e6` contains 193 users; 29 are development-touched and 164 are identity-untouched candidates. Ten `FINAL_TEST_LOCKED` and ten `CALIBRATION_LOCKED` users remain unexposed according to available manifests, with no overlap against the 29. Gate4E/F DEV each improved its own 30%-coverage risk in 19/19 users; prospective planning recommends minimum 15, preferred 20, maximum practical 30 users, conditional on eligibility. All counts, caveats and output hashes are in `AUDIT_SUMMARY.md` and sidecars.

## Unknown / contaminated state

The frozen upstream checkpoint's actual training-user membership is unresolved: no Group-A user is proven. Candidate paired EMG/GT streams are indicated by official archive metadata but not structurally certified. The 29 touched users are ineligible for new prospective confirmation, including the Gate4C source-defective user. `VALIDATION` is not untouched merely because of its split name. No protected outcome was read in this audit.

## External runtime and worktree

This audit used only already-local official metadata and repository manifests/results; no remote runtime was queried. A successor must reverify any remote store, checkpoint provenance, source objects, free space and hashes before a future freeze or download. The local audit lane is new and untracked in Git; Gate4E/F are pre-existing untracked frozen lanes and were not edited here.

## Next action and prohibitions

First obtain checkpoint-specific upstream training membership evidence and a metadata/authorized structural basis for paired EMG/GT availability. Then seek separate PI authorization for final N and cohort-manifest freeze. Do not silently mix upstream exposure groups, repurpose `CALIBRATION_LOCKED`, execute the proposed hash ordering now, inspect candidate signal/outcome arrays, retune either gate, or treat blocks as independent users.

Recommended next session: `COMMON-POSE-FINAL-COHORT-FREEZE-20260924-ELIGIBILITY-RESOLUTION`.
