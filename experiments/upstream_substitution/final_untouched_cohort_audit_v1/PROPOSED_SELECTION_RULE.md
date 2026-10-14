# Proposed future cohort rule — not executed

**Status:** proposal only. The final N and user/file manifest are not frozen here. No candidate HDF5 or outcome was opened. `FINAL_TEST_LOCKED` remains its separate existing identity reservation; `CALIBRATION_LOCKED` is not silently reassigned.

Before any selection, resolve the frozen upstream checkpoint's actual training-user membership with checkpoint-specific official/frozen evidence. Obtain authoritative metadata that establishes paired EMG and GT Pose availability, or separately authorize a preplanned structural qualification with a stop-on-failure rule. If either prerequisite remains unresolved, stop; do not call a user Group A or run final inference.

For the strongest unseen-user system claim, use only users (1) absent from `TOUCHED_USER_REGISTRY.json`, (2) proven absent from the frozen upstream training membership, and (3) confirmed paired by the authorized metadata/structural rule. Do not substitute Group B/C automatically. Preserve the ten pre-reserved `FINAL_TEST_LOCKED` identities only if all meet those conditions and the future final protocol explicitly incorporates them. If not, stop for a new PI decision; do not silently replace a locked identity.

After the PI fixes N and the above conditions, construct a complete eligible-user table using the same official user IDs and session/recording identities. Sort additional eligible users ascending by the pair

`(SHA256(UTF8("COMMON_POSE_FINAL_UNTOUCHED_V1|2026-09-24|" + user_id)), user_id)`.

Take the first `N - eligible_pre_reserved_FINAL_TEST_count` additional users, excluding all already reserved identities. For each chosen user, select the preflight-eligible session minimizing `(SHA256(UTF8("COMMON_POSE_GATE4B_SESSION_V1|" + user_id + "|" + session_id)), session_id)`, retaining the already frozen Gate4B session for pre-reserved users. Freeze the ordered user/session/filename list, official source object identity, tar-index hash and member sizes before downloading or unlocking. Per-file SHA256 values are unavailable in the retained official index; after an authorized download, compute and seal actual file hashes and structural receipts **before** model inference. A missing, corrupt or structurally invalid file is a stop; there is no outcome-guided replacement.

The seed, ordering and conditional rule above are specified for the next separately authorized freeze step. This audit did not compute the ordering or identify the first N. No signal quality, GT class composition, pose outcome, Flip, Fisher, or gate score may enter this selection.
