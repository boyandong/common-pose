# S6 — BLINDING SPEC

**Lane:** `human_semantic_validation/` (Session 6 — human semantic validation).
**Status:** frozen before any window was generated and before any human label exists.

This document states *exactly* what may and may not influence (a) which windows the
annotator sees and (b) what the annotator is shown. Both are enforced in code and
tested (`tests/test_s6_annotation_benchmark.py`).

---

## 1. What the annotation benchmark is blind to

During candidate selection, payload construction, rendering and annotation, the
following quantities are **never computed, never loaded, never stored**:

| forbidden quantity | why it is forbidden |
|---|---|
| DB9 decoder predictions | the future endpoint; seeing it now would let sampling chase a class the decoder already gets right |
| DB9 decoder probabilities / margins | same, plus they carry the decision confidence the endpoint measures |
| DB9 support / OOD distance (`p95` support statistic) | would bias selection toward or away from "inside-support" poses |
| VEMG2Pose predicted pose | the other future endpoint |
| GT-vs-predicted agreement | a direct summary of the endpoint |
| stage labels / stage names | the emg2pose stages are semantically named (`ThumbsUpDownThumbRotationsCWCCWP`, …); a shortlist of stages is a shortlist of postures |
| gesture / class predictions from any model | any semantic prediction is the answer key |
| angular velocity / "settledness" used for *selection* | would turn the Naturalistic set into a stable-posture set and destroy its prevalence meaning |
| hand side used for *selection* | side is a hidden variable that must not skew the sample |

Implementation notes:

* the only pose-derived signal entering selection is the **validity boolean**
  (`emg2pose.utils.get_ik_failures_mask`, i.e. "not the all-zero IK-failure
  signature"). It is a data-availability flag: it says *a pose was recorded here*,
  not *what the pose is*;
* the sampler never opens `bridge_audit/`, `posture_decoder/`, `representation/`,
  `data/db9_posture16/` or any S5 result, and never imports a model;
* a test asserts the sampler source contains no reference to those paths, and another
  asserts the served payloads contain none of the forbidden keys.

## 2. What the annotator sees

Per item, the annotator-facing payload carries **only**:

1. a random `blind_id` (`S6-XXXXXXXX`, 8 chars from a 31-symbol alphabet);
2. `frames`: **31 GT 20D pose vectors** at 50 Hz over 0.60 s (centre pinned) —
   ground-truth emg2pose `joint_angles` only;
3. the item's position in that annotator's own randomised order;
4. the label choices and an optional confidence field (UI constants, no data).

Nothing else. Explicitly **not** shown, at any time, in any control, tooltip, URL,
console log or DOM node:

| hidden | how it is hidden |
|---|---|
| joint-angle numbers | no numeric panel exists in the annotation UI; the UI is a canvas + label buttons |
| model predictions / probabilities | the payload contains no such key and the UI has no code path that could display one |
| stage names | never loaded into the payload |
| DB9 labels / classes 1–7 as DB9 movements | the UI shows the S6 semantic choice text only; the string `DB9` appears nowhere in the served tree |
| source filenames | session stem kept in the evaluator-only manifest |
| timestamps | frame times are not sent; poses are plain vectors |
| recording date / session id | not sent |
| hand side | not sent; the evaluator-only manifest records it |
| decoder / OOD information | not computed |
| S4 semantic preset names | the annotation UI does not load `config/presets.json` and has no preset list |
| validity / limit-violation banners | the UI never displays `report.validity` or `report.violations` |
| duplicate markers | duplicates are byte-identical to ordinary items and carry no flag |

## 3. Physical separation (not just visual hiding)

```
human_semantic_validation/
├── NATURALISTIC_SAMPLING_SPEC.json      evaluator-side (algorithm record)
├── corpus_integrity_manifest.json       evaluator-side (GT integrity, no semantics)
├── hidden/                              EVALUATOR ONLY
│   ├── hidden_sample_manifest.json      session, frame indices, side, spans
│   ├── hidden_duplicate_map.json        original <-> duplicate pairing
│   └── hidden_payload_contract.json     the payload schema the UI is tested against
├── annotator_A/  index.html · payload.json     source package (NOT served directly)
├── annotator_B/  index.html · payload.json     source package (NOT served directly)
└── annotator_common/                    shared UI source, styling, template, mirrored geometry
```

**What each server serves is a staged per-annotator vault, not this lane and not the project
root.** `tools/stage_annotation_site.py` builds, per annotator, a minimal directory holding
exactly 16 files:

```
<temp>/s6_vault/annotator_A/
    index.html   payload.json   annotation_ui.js   annotation_style.css
    hand_geometry.json   left_hand_geometry.json
    s4src/{hand_model,kinematics,pose,collision,math3d,viewer}.js
    s4assets/three/three.module.js   s4assets/three/controls/OrbitControls.js
    s4config/hand_model.json         s4config/hand_model.geometry.json
```

The server's **document root is that directory**, so:

* `human_semantic_validation/hidden/` is **absent from the served filesystem tree**. It has no URL
  for the same reason `/data/` or `/logs/` has none: it is not in the tree.

  > **Correction (S6 Stage-A remediation).** An earlier version of this document said `hidden/`
  > "is a sibling of the root, so it has no URL at all — the separation is filesystem-level, not
  > path-filter-level". **That was false as shipped.** The Stage-A server's document root was the
  > *project root*, and `hidden/` was excluded by an HTTP path filter; `%68idden/...` bypassed the
  > filter and returned the full 767 KB sample manifest, and the same root exposed `data/`,
  > `logs/`, `docs/`, `posture_decoder/` and S5 artifacts. Both defects are fixed by staging, and
  > the served filesystem is now the boundary, with the HTTP checks below as defence in depth.
* the **other annotator's package** is likewise absent from each vault, and is additionally
  refused by the canonicalizer, which rejects any `annotator_*` component other than the
  server's own.
* the project root, `data/`, `logs/`, `docs/`, `checkpoints/`, `posture_decoder/` and the S5
  `bridge_audit/` artifacts are absent as well.
* the geometry map is served at the neutral path `hand_geometry.json` rather than under a random
  filename, because its path is no longer what protects anything — the vault contains no
  evaluator file to find.

`tools/serve_annotation.py` takes one vault as its root:

```
<EMG2POSE_VENV>\Scripts\python.exe human_semantic_validation/tools/serve_annotation.py --annotator A
```

* every request is canonicalized **before** any access decision: percent-decoded repeatedly until
  stable, separators normalized, dot segments / drive letters / forbidden component names
  rejected, and the resolved filesystem path required to lie inside the vault. The attack corpus
  (including `%68idden/`, `%2568idden/`, `%252568idden/`, `%252e%252e/`, backslashes and NUL) is in
  `tests/test_annotation_server_adversarial.py`;
* directories are never listed, and a trailing-slash directory URL **redirects** to the injected
  page instead of returning an unprocessed template (the Stage-A behaviour);
* the two annotators are given **different ports and different URLs**, so neither annotator's
  browser has any route to the other's answers;
* the server never writes and accepts no upload: annotation output is produced by the annotator's
  own browser via **Export my labels**, and restored with **Recover from file** (which reads a
  local file in the page — no server involvement).

## 4. Why the two annotator packages are identical in content and different in order

Both annotators receive the same 396 items (360 unique windows + 36 hidden
duplicates), with the same blind ids, in two independent randomised orders. A
per-annotator id shuffle was considered and rejected: it would break the
cross-annotator agreement computation (the two label files could no longer be joined)
while adding no real blinding, because neither annotator can see the other's file
anyway. The order shuffle is what removes position/context effects.

## 5. What is *not* blind (declared, not hidden)

* **Handedness is physically visible.** The mini corpus has 15 left- and 15
  right-hand recordings; the frozen S4 geometry is a single right hand. Left-hand
  sessions are rendered from an analytic mirror of the official model (see
  `ANNOTATION_PROTOCOL.md` §Rendering), so left-hand items show a left hand. The
  annotator can therefore *see* which hand an item is — that is unavoidable and is
  not a leak, because the side is not in the payload, the session→side mapping is not
  available, and no label decision depends on knowing the side. Analytic mirroring is
  a *fidelity fix*, not a blinding fix: without it, left-hand frames would show the
  thumb on the wrong side of the palm (S4 audit §6).

  The rendering-only `hand_geometry.json` in each vault is the blind_id → hand-side
  table the page needs for this. It contains that mapping and nothing else (checked in
  `tests/test_annotation_server_adversarial.py::geometry_map_shape_only_mapping`), and it
  carries no session, stage, time, frame index or class information.
* **Generic anatomy.** The rendered hand is the official *generic* UmeTrack hand, not
  the participant's. Finger lengths and thumb attachment are the model's, so apparent
  fingertip contact is not evidence about the participant (S4 audit §12).
* **No global orientation.** The 20D state has no wrist DOF; the renderer's world
  frame is the model frame. "Thumb up" is therefore defined palm-relative and can
  never be judged against gravity (S4 audit §7).
* **Mesh resolution floor.** The 788-vertex mesh cannot resolve an adjacent-finger
  gap below ~3.7 units, so "touching" between adjacent fingers is not readable. No
  label may depend on it (S4 audit §13).

## 6. Integrity of the blinding claim

The claim "no model-derived semantic output has been computed or exposed" is backed by:

1. `tests/test_s6_annotation_benchmark.py::test_03_no_model_output_enters_sampling` — the sampler
   is AST-walked for every forbidden module/attribute and its string literals for every model
   artifact path (prose in a docstring is not an executable reference, so the check parses the
   code instead of grepping it);
2. `...::test_05_ui_payload_contains_no_decoder_output` — both served payloads are walked
   recursively and every key checked against the contract denylist; item keys must be exactly
   `{blind_id, position, frames}`;
3. `...::test_07_ui_payload_contains_no_hand_side` — the served payload key set is exactly
   `{items, blind_id, position, frames}`; the hand side lives only in the separate
   rendering-only geometry map;
4. `...::test_13_label_files_cannot_access_hidden_evaluator_metadata` — no file on the
   annotator-facing path mentions `hidden/*`, `duplicate_of`, the corpus manifest or the spec,
   and each source package contains only `index.html` + `payload.json`;
5. `tests/test_annotation_server_adversarial.py` — **253 live HTTP cases** against both real
   servers, covering the allowed routes, cross-annotator access, the evaluator files, out-of-tree
   paths (`/data/`, `/logs/`, `/docs/`, `/posture_decoder/`, S5 artifacts), traversal /
   single-, double- and triple-encoded variants, response bodies as well as status codes, and an
   explicit assertion that the suite releases both ports when it finishes;
6. `verifier/verify_annotation_page.mjs` — loads the real page in headless Chrome and dumps the
   **entire** `document.documentElement.outerHTML` plus the live render/camera state, so the
   blind claim is checked against what the browser actually rendered, not against source code;
7. `verifier/verify_mirror_geometry.py` — proves the mirror's axis rule, the served geometry's
   compliance with it, and the two palm-side view identities, so "the left hand is the same pose
   seen from the other side" is a checked statement rather than an assumption.
