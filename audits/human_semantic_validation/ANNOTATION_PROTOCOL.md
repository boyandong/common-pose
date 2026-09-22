# S6 — ANNOTATION PROTOCOL

Human annotator instructions and study-operator procedure for the blinded semantic benchmark.
Companion documents: `LABEL_DEFINITIONS.md` (what each label means), `BLINDING_SPEC.md` (what
is hidden and why), `FUTURE_ANALYSIS_PLAN.md` (what will be computed once labels are frozen).

---

## 1. What you are doing

You will be shown a sequence of **396 short hand animations**. For each one you choose a
**posture label** for the **pinned centre frame** of the animation.

That is the whole task. There is no right answer to guess at and no model being tested against
you: you are producing the **human ground truth** that a future analysis will be measured
against.

Your session is expected to take roughly 30–60 minutes. You may stop at any time and resume
later in the same browser: your choices are saved automatically as you go.

---

## 2. THE CENTRAL RULE

> ### Label the posture at the PINNED CENTRAL FRAME.

Every item is a 0.60-second animation (31 poses at 50 Hz) with one frame marked as the pinned
centre. The animation exists **only** to help you decide three things about the centre frame:

* is the centre frame a **stable, meaningful posture**; or
* is it **part of a transition**; or
* is it **between two postures** (ambiguous)?

**Do not label** the pose that occurs just before, just after, or anywhere else in the
animation. **Do not infer intention** ("this looks like they were about to make a fist").
**Do not label the movement** — only the pose at the pinned centre frame.

The slider under the animation lets you step through the 31 frames yourself. Stepping is
allowed and encouraged when you are unsure what is moving; the label still applies to the
pinned centre frame only.

---

## 3. The interface

| part of the screen | what it is |
|---|---|
| **View A — palm view (fixed)** | the palm side of the hand, camera fixed |
| **View B — little-finger side (fixed)** | the little-finger border of the hand, camera fixed |
| **slider / Pause** | 31 frames of the item, looping; drag to step frame by frame. Playback **holds each pass briefly at the centre frame** (an affordance only — the GT trajectory, the 31 frames and the 0.60 s window are unchanged) and the indicator turns green reading `CENTRE FRAME — label this one` |
| **Current item** | the item's random code (e.g. `S6-9DBA5J4S`) and its position |
| **Target postures** | the five primary classes and the one diagnostic class — keys `1`–`6` |
| **Not a target posture** | UNKNOWN / AMBIGUOUS / UNJUDGEABLE — keys `7`–`9` |
| **Confidence (optional)** | 1 low · 2 medium · 3 high |
| **Session** | Previous / Next / auto-advance toggle / **Export my labels** / **Recover from file…** / live save status |
| **Questions box** | free text for anything unclear about the current item |

**Both views are fixed on purpose.** The camera cannot be rotated or zoomed. Every item is
seen from exactly the same two angles, so differences between items are differences in the
*pose*, never differences in how the hand is being held in space. A fixed view set is a
control, not a limitation: free camera exploration would make the *view* a confound.

**Keys**: `1`–`9` choose a label · `Space` play/pause · `←`/`→` step one frame ·
`Shift`+`←`/`→` previous/next item · `Ctrl`+`S` export your labels.

**Auto-advance** moves you to the next item shortly after you choose a label. You can turn it
off to stay on an item as long as you like.

---

## 4. How to decide — order of operations

1. **Can the pose be judged at all** from these two views? If required information is not
   visible → **UNJUDGEABLE** (key `9`). This should be rare.
2. **Is the pinned centre frame one defensible posture**, or is it mid-transition / between
   two postures? If the latter → **AMBIGUOUS** (key `8`).
3. **Does it match one of the six defined postures?** If none → **UNKNOWN** (key `7`).
4. Otherwise choose the matching class, using the discriminators in
   `LABEL_DEFINITIONS.md` §4.

Use the animation for steps 1 and 2 only.

---

## 5. Six things that are easy to get wrong

1. **"Thumb up" is palm-relative.** It means *thumb distinctly extended relative to this
   palm, with the hand otherwise closed*. It never means *the thumb points up*. The render
   has **no world orientation**: the wrist is the identity transform by construction, so
   gravity, camera direction and body posture do not exist in the image. Do not use the
   thumb's apparent direction on screen as evidence.
2. **Class 4 is diagnostic only.** "Thumb positioned / opposed toward the little-finger base"
   records **position**, not contact. Never judge whether anything is touching, and remember
   this class is analysed separately from the five primary classes.
3. **Never judge contact for any label.** The hand is a generic mesh with no soft tissue, and
   its 788 vertices cannot separate "touching" from "nearly touching" for adjacent fingers.
   In particular the **index and middle fingertips are usually together or nearly together** —
   read the *proximal* joints and the fingers' overall extension/flexion, not the tip gap.
4. **Watch for the thumb crossing the palm.** A closed hand with the thumb carried across the
   palm is not automatically the thumb-up configuration. Ask specifically: *is the thumb
   distinctly extended/abducted away from the palm plane?*
5. **UNKNOWN, AMBIGUOUS and UNJUDGEABLE are three different answers.** "The pose is clear but
   it is none of the six" is UNKNOWN. "I cannot tell which of two it is" is AMBIGUOUS. "I
   cannot see what I would need to see" is UNJUDGEABLE. They are counted separately and mean
   different things.
6. **The hand is a generic model, not the participant's hand.** Finger lengths and thumb
   attachment are the official generic UmeTrack hand's. Do not reason about the participant's
   anatomy; judge the *configuration* shown.

---

## 6. Study-operator procedure

### 6.1 One-time build and check

```powershell
# 1. corpus + benchmark integrity (also checks that recording-14 is no longer corrupt)
<EMG2POSE_VENV>\Scripts\python.exe human_semantic_validation/tools/build_corpus_integrity_manifest.py
<EMG2POSE_VENV>\Scripts\python.exe human_semantic_validation/tools/make_left_hand_geometry.py
<EMG2POSE_VENV>\Scripts\python.exe human_semantic_validation/tools/make_naturalistic_sampling_spec.py
<EMG2POSE_VENV>\Scripts\python.exe human_semantic_validation/tools/make_annotation_benchmark.py

# 2. stage the per-annotator serving vaults (this is what the servers serve)
<EMG2POSE_VENV>\Scripts\python.exe human_semantic_validation/tools/stage_annotation_site.py
<EMG2POSE_VENV>\Scripts\python.exe human_semantic_validation/tools/stage_annotation_site.py --check

# 3. gates
<EMG2POSE_VENV>\Scripts\python.exe -m pytest human_semantic_validation/tests -q
node human_semantic_validation/tests/s6_mirror_equivariance.mjs
<EMG2POSE_VENV>\Scripts\python.exe human_semantic_validation/verifier/verify_mirror_geometry.py
<EMG2POSE_VENV>\Scripts\python.exe human_semantic_validation/tests/test_annotation_server_adversarial.py
<EMG2POSE_VENV>\Scripts\python.exe human_semantic_validation/tests/test_server_startup_clean_shell.py
```

Nothing above requires an environment variable: the servers force UTF-8 output and print an
ASCII-safe URL, so the documented commands work in a clean Windows shell.

### 6.2 Start one server per annotator (two terminals)

```powershell
# Annotator A  (port 8791)
<EMG2POSE_VENV>\Scripts\python.exe human_semantic_validation/tools/serve_annotation.py --annotator A

# Annotator B  (port 8792)
<EMG2POSE_VENV>\Scripts\python.exe human_semantic_validation/tools/serve_annotation.py --annotator B
```

Each server prints its URL and serves a **staged per-annotator vault**, whose document root
contains only that annotator's 16 required files (page, payload, shared UI assets, hand geometry,
frozen S4 renderer modules and configs). The evaluator manifests, the other annotator's package
and every repository directory have no URL because they are not in the served tree.

Add `--check` to validate the vault and exit without binding a port; add `--print-url` if you also
want the full filesystem path printed.

Verify the guards at any time:

```powershell
# full attack suite (launches and cleans up its own servers)
<EMG2POSE_VENV>\Scripts\python.exe human_semantic_validation/tests/test_annotation_server_adversarial.py

# live state of the two running servers, from outside the server code
<EMG2POSE_VENV>\Scripts\python.exe human_semantic_validation/tests/report_server_state.py
```

### 6.3 Independent page verification (optional but recommended, once per session)

```powershell
node human_semantic_validation/verifier/verify_annotation_page.mjs `
     --url "http://127.0.0.1:8791/annotator_A/index.html" `
     --expect-annotator A --out human_semantic_validation/logs/verifier_annotator_A.json
```

This drives a real headless Chrome against the served page and reports what the browser
actually rendered/did: 63 checks covering boot, item count, blind-id format, the label set, the
two fixed views, a live render loop, the camera's non-rotatability, the left/right mirror
identities, the payload contract, autosave + progress + recovery behaviour, the centre-frame
dwell, the absence of every forbidden token in the DOM, and a screenshot. `OVERALL: PASS` is
required before handing the URL to a human.

### 6.4 Handing over

Give each annotator **their own URL only**, in their own browser window. Do not let them see
the other annotator's page, and do not discuss individual items with either annotator while
annotation is in progress.

### 6.5 Collecting the labels

Each annotator presses **Export my labels** when finished and saves
`s6_labels_annotator_A.json` / `s6_labels_annotator_B.json` to
`human_semantic_validation/annotations/`.

### 6.5b Storage, periodic export and recovery (operator + annotator procedure)

There is **no server write endpoint**. Everything below happens in the annotator's browser; the
server only ever serves static files.

| mechanism | behaviour |
|---|---|
| **autosave** | every choice is written to `localStorage` immediately, keyed `s6_annotation_v1_<A\|B>` |
| **visible status** | the Session card shows `saved locally HH:MM · n / 396 labelled (export regularly …)`, or a red `NOT SAVED — …` line if the write failed |
| **progress counter** | the same line, and the header's `n / 396 labelled` |
| **export** | the **Export my labels** button (or `Ctrl+S`) downloads `s6_labels_annotator_<X>.json` |
| **recovery** | **Recover from file…** reads a previously exported JSON, merges it into the current state and reports `added / identical / overwritten / skipped` |

**Annotator instructions:** keep the download; it is the only copy that survives clearing
browser data or a machine change. If the browser is reset, reopen the same URL and use
**Recover from file** — nothing is lost as long as an export exists.

**Operator instructions:**

1. At the **start**, tell the annotator to export after the first few items and confirm the file
   appears in their Downloads folder.
2. **Periodically** (suggested: every 15–20 minutes, and whenever the annotator pauses), ask for
   a fresh export and copy it to `annotations/` with a timestamp suffix
   (`s6_labels_annotator_A_20260918T1930.json`). Later exports supersede earlier ones.
3. At the **end**, take a final export and confirm `labelled_item_count` is 396.
4. If a browser must be reset mid-session, export first if at all possible; if not, recover from
   the most recent export and the annotator re-labels only the items after it. The page reports
   how many items it recovered, so the gap is visible and quantifiable.
5. **Never** edit a label file by hand, and **never** import an annotator's file into the other
   annotator's page. The page warns and asks for confirmation if the file's `annotator` field
   disagrees with the page, but the responsibility is the operator's.

An export contains exactly: `annotator`, `app_version`, `exported_utc`, `payload_item_count`,
`labelled_item_count`, `notes`, and `items` where each entry is
`{label, confidence, updated_utc}` keyed by `blind_id` — the four fields
`blind_id / label / confidence / updated_utc`, with no model output of any kind.

### 6.6 After annotation

Follow `FUTURE_ANALYSIS_PLAN.md` in the order it specifies. The analysis plan is
pre-registered; deviations must be recorded as deviations, not silently applied.

---

## 7. Rendering contract (what the annotator's image is, exactly)

* **Renderer:** the frozen, independently audited S4 implementation
  (`hand_visualizer/src/hand_model.js`, `viewer.js`). Nothing in S4 was modified. The
  annotation page imports those modules unchanged through an import map the local server
  injects.
* **Pose source:** emg2pose **ground-truth** `joint_angles` only. No EMG, no model, no
  prediction, in any part of the pipeline.
* **Windows:** 31 GT poses at 50 Hz spanning 0.60 s (centre ± 0.30 s), the centre frame
  pinned. Every frame of every window is GT-valid by construction (the official all-zero
  IK-failure signature is excluded from candidate centres).
* **Views:** exactly two, fixed: `palm_flat` and `ulnar` — the minimal set established as
  sufficient by the S4 audit (§8, §15 Q7). `back` is excluded; it hides the thumb.
* **Camera:** fixed once at boot and never re-framed per pose, so **zoom is constant across
  all items** and a closed fist cannot be scaled up to look like a large open hand. The
  camera cannot be rotated by the annotator.
* **Both hands are rendered faithfully.** The mini corpus is 15 left / 15 right recordings,
  and the frozen S4 geometry is a single **right** hand. Rendering a left-hand recording on it
  would be a mirror image with the thumb on the wrong side of the palm and inverted occlusion
  layering (S4 audit §6) — which matters most for the diagnostic class 4. S6 therefore
  renders left-hand items from an **analytic mirror** of the official geometry
  (`annotator_common/left_hand_geometry.json`, derived by
  `tools/make_left_hand_geometry.py`), and the two fixed views are mapped into the mirrored
  frame. The geometry is exact and the rule is derivable:

  ```
  M = diag(1, -1, 1)                      reflection about the palm plane
  points    p' = M p                      (joint rest positions, landmarks, mesh vertices)
  axes      w' = -M w                     (because det M = -1 flips hat(Mw) = M hat(w) M^T)
  winding   reversed                      (det M < 0)
  views     d' = M d = (d.x, -d.y, d.z)   (a view direction is a plain vector, not an axis)
  ```

  `verifier/verify_mirror_geometry.py` proves the axis rule on 20 000 random rotations
  (max error 0.0), proves the served geometry obeys it exactly, and proves the two palm-side
  identities `camera_dir(palm_flat, hand) · palmar(hand) = +1.000` for **both** hands with the
  `ulnar` views at 0.0136 (a profile view). `tests/s6_mirror_equivariance.mjs` additionally shows
  every inter-landmark distance and every bone length is bit-identical between the two geometries
  over 60 poses — i.e. same pose, other viewpoint. On the pose data this is a pure change of
  viewpoint. The **annotator is not told which hand an item is** (the payload carries no side),
  but the hand's identity is physically visible — see `BLINDING_SPEC.md` §5 for why that is
  declared and not a leak.

  > **Correction (S6 Stage-A remediation).** An earlier version of this section implied the view
  > transform had been found by exhaustive search with no valid geometric argument behind it.
  > The search result was right, but the claim about the absence of an argument was wrong: the
  > derivation above is the argument, and the search is what confirmed the sign convention.
* **Known renderer limits that the protocol compensates for** (from the S4 audit):
  no global wrist orientation (§7); no contact information, with a ≈3.7-unit adjacent-finger
  resolution floor (§13); generic, non-participant anatomy (§12); sub-0.573° joint angles
  rendered as exactly 0.573° by the official `so3_exp_map` (§15 Q11.11), so sub-degree
  distinctions in the image are not meaningful.

---

## 8. What is deliberately NOT in the interface

No joint-angle values, no model output of any kind, no stage name, no source filename, no
timestamp, no hand side, no preset names, no validity or limit-violation banners, and no
indication of which items are hidden repeats. See `BLINDING_SPEC.md` §2 for the full table and
§6 for how each claim is verified.
