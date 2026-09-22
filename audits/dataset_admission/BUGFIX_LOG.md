# BUGFIX LOG

**Lane:** `<DATA_ROOT>set_admission_audit_v1\`
**Frozen plan SHA-256:** `fba2b20623392dd809d5ed28c7850387acc721e9a91ff1611e7fba0d89fc889d`

Required by frozen plan section 2. Every entry records: symptom, root cause, files changed,
whether any measured result of this audit had already been inspected when the bug was fixed,
and whether the rerun invalidates any previous artifact of this audit.

---

## BUG-001 - `IndexError` in the empty-container classification

* **Symptom.** `scripts/02_schema_audit.py` raised
  `IndexError: list index out of range` at the line
  `empty = [m for m in meta if m["shape"][0] == 0 or len(m["shape"]) < 2]`.
* **Root cause.** An empty MATLAB container deserialises through
  `scipy.io.loadmat(..., squeeze_me=True)` to a 0-d array, so `list(shape) == []`. The
  `or` operands were evaluated left to right and `m["shape"][0]` was reached first.
* **Files changed.** `scripts/02_schema_audit.py` - operand order reversed to
  `len(m["shape"]) < 2 or m["shape"][0] == 0`.
* **Measured results already inspected?** No. The driver had produced no output at all; it
  crashed before writing any artifact.
* **Rerun invalidates previous artifacts?** No. `DATASET_MANIFEST.csv`,
  `SOURCE_PROVENANCE.md` (driver 01) are unaffected; driver 02 had written nothing.

## BUG-002 - `KeyError` in discrimination test D4

* **Symptom.** `scripts/03_shared10_provenance.py` raised `KeyError: 5` inside `order_tests`.
* **Root cause.** D4 was written against a `{finger: column}` map in which the abduction
  channels were keyed by a single finger, but the three relative-abduction channels span
  metacarpal *pairs* (2-3, 3-4, 4-5), so the fourth finger has no abduction entry.
* **Files changed.** `scripts/03_shared10_provenance.py` - D4 rewritten to work from
  name -> column maps and to evaluate each abduction channel against the MCP-flexion
  channels of the two metacarpals it spans. This is a code correction only; the pre-declared
  expectation in `AUDIT_PLAN.md` section 7 is unchanged.
* **Measured results already inspected?** Partially. D1 and D2 had printed before the crash.
  Neither was altered, and neither the D4 expectation nor the resolution rule in the frozen
  plan was changed: the rerun reports D1-D4 in full for **both** hypotheses.
* **Rerun invalidates previous artifacts?** No. `SHARED10_PROVENANCE.json` had not been
  written at the time of the crash.

## BUG-003 - missing `rationale` key in the markdown renderer

* **Symptom.** `KeyError: 'rationale'` while rendering `SHARED10_PROVENANCE_AUDIT.md`.
* **Root cause.** Test D2's result dictionary was built without a `rationale` field while the
  renderer iterated all four tests uniformly.
* **Files changed.** `scripts/03_shared10_provenance.py` - `rationale` added to D2.
  Documentation-only; no test, threshold or expectation changed.
* **Measured results already inspected?** Yes - the D1-D4 verdicts and the per-index table had
  printed. The JSON artifact had already been written.
* **Rerun invalidates previous artifacts?** The JSON artifact is rewritten byte-identically in
  all fields except the added `rationale` string; the numeric content is unchanged. The
  markdown artifact is produced for the first time.

## BUG-005 - four false alarms in the fact-checker's own document parsing

* **Symptom.** `scripts/99_fact_check_audit.py` reported four failures:
  `KINMUS_T2_18` mismatch, `KINE-ADL guide yields 18 right-hand names: got 16`,
  `GUIDE18` mismatch, and `KINE-ADL guide: WR_A ulnar + / radial -: got False`.
* **Root cause.** All four were defects in the CHECKER's parsers, not in the audit:
  1. the KIN-MUS paper names the wrist channels `WRIST_F` / `WRIST_A` while the guide
     names them `WR_F` / `WR_A`; the comparison did not normalise the prefix (the
     substance - same DOF, same position - was never in question);
  2. the KINE-ADL name regex used `[A-Z0-9_\-]+`, which cannot match `R_PalmArch`
     because of its lower-case letters, and the capture window was too short;
  3. the `WR_A` sign-criterion regex required `deviation+/` with no intervening space
     while the guide prints `deviation +/`.
* **Files changed.** `scripts/99_fact_check_audit.py` - the two regexes, the window
  length, and a `WRIST_ -> WR_` normalisation with an added assertion that records the
  prefix difference explicitly.
* **Measured results already inspected?** Yes; all four failures were in the checker.
  **No driver output, threshold or artifact was changed**, and the fix tightened the
  check: the checker now asserts the WRIST_/WR_ naming difference rather than ignoring
  it.
* **Rerun invalidates previous artifacts?** No. Nothing outside the checker changed.

## BUG-006 - the checker treated the defined writer helpers as out-of-lane writes

* **Symptom.** `no numbered driver writes to a path outside this lane: got
  [('aud_common.py', 'open(path'), ...]` and then
  `[('99_fact_check_audit.py', 'open(path')]`.
* **Root cause.** The scan matched `open(path, "w")` inside `aud_common.py` itself - i.e.
  the generic writer helpers `write_json` / `write_text` / `write_csv` - and inside the
  checker, which re-hashes artifacts through `aud_common.sha256_file`. Neither is a call
  site.
* **Files changed.** `scripts/99_fact_check_audit.py` - `aud_common.py` and the checker
  excluded from that one scan, with the reason recorded in-line. The scan still covers
  every other numbered driver.
* **Measured results already inspected?** Yes; guard-only.
* **Rerun invalidates previous artifacts?** No.

## BUG-007 - the manifest required itself

* **Symptom.** `no required deliverable is missing: got ['README.md',
  'ARTIFACT_MANIFEST.json']`.
* **Root cause.** `13_manifest.py` listed `ARTIFACT_MANIFEST.json` among the required
  deliverables and then checked that every required deliverable exists - before writing
  it. (`README.md` was genuinely missing at that point and was written.)
* **Files changed.** `scripts/13_manifest.py` - the self-reference excluded from the
  precondition, with a comment, and `README.md` created.
* **Measured results already inspected?** Yes; guard-only.
* **Rerun invalidates previous artifacts?** No.

## Final state

`scripts/99_fact_check_audit.py`: **142 assertions, 0 failed.**

* **Symptom.** The summary paragraph said the two orders "differ at 4 of 18 positions" while
  the table below reports `8 of 18 positions differ`.
* **Root cause.** Four adjacent pairs are swapped, so four *pairs* and eight *positions*
  differ. The prose used the pair count with the position unit.
* **Files changed.** `scripts/03_shared10_provenance.py` - prose corrected to
  "four swapped adjacent pairs (8 of 18 positions)".
* **Measured results already inspected?** Yes. No measured quantity is affected; the
  underlying `side_by_side_18` table and `n_positions_differing == 8` were already correct.
* **Rerun invalidates previous artifacts?** No numeric artifact changes; only the prose.


---

## Final state

`scripts/99_fact_check_audit.py`: **142 assertions, 0 failed.**

