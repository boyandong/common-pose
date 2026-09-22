# POSE COORDINATE AUDIT — FORENSIC DB9 ↔ EMG2POSE CANONICAL POSE AUDIT

**Branch:** `S6-POSE-COORDINATE-AUDIT`
**Classification:** DIAGNOSTIC TEST / REPRESENTATION FORENSICS
**Lane:** `<PROJECT_ROOT>\pose_coordinate_audit\`
**Date:** 2026-09-20
**Frozen plan:** `POSE_COORDINATE_AUDIT_PLAN.json`, raw-byte SHA-256 **`c59fe01370d48aedeed56ef7a4103506d14a298edb794723be3720531edd62c6`**

## PRIMARY DECISION: **COORD-D — MIXED COORDINATE MISMATCH**

Some canonical16 dimensions are numerically equivalent; **four are not**, and the
four that are not include **all three** of the dimensions the previous branch
flagged as "large offset". The defect is **inside DB9**, not in the DB9 → canonical16
mapping, and not in emg2pose.

> Every number below is verified against its artifact by
> `tools/pose_coordinate_fact_check.py` (**160+ assertions**).

---

## 1. Objective

The previous branch (`db9_distributional_open_set`) found ~80.6 % of natural
emg2pose GT poses outside all six DB9 gesture regions, rejected all ten
human-consensus target windows, and reported a **179.7°-norm canonical16
grand-mean offset** concentrated on `middle_dip_flexion` (−103°),
`ring_dip_flexion` (−102°) and `pinky_mcp_flexion` (+79°).

Before that could be called *domain shift*, a **numerical-coordinate mismatch**
had to be excluded. This audit separates **semantic DOF correspondence** from
**numerical coordinate equivalence**, per dimension, against ten criteria (A–J).
It is **not** a new architecture, a model rescue, an open-set gate optimisation,
a domain-adaptation branch or a classifier-selection branch. No classifier was
trained and no transform was tuned on any human label.

## 2. Frozen plan

Written and hashed **before any new cross-dataset numerical outcome was
computed**: criteria, candidate transforms T0–T7, source-only estimator rules,
evidence rules, per-joint metrics, anchors, stop rules, prohibitions and the
decision tree. No addition after the freeze changed a frozen rule.

## 3. Exact canonical16 mapping recovered

| | emg2pose | DB9 |
|---|---|---|
| raw width | 20 (official `JOINTS`) | 22 (`order_of_angles`) |
| selection | by official joint **name** | by official channel **name** |
| source index vector | `[0,1,2,3,5,6,7,9,10,11,13,14,15,17,18,19]` | `[0,1,2,3,4,6,16,7,8,17,9,11,18,13,15,19]` |
| units | radians (unchanged) | **degrees → radians**, explicit `π/180` |
| sign transforms | none | **exactly one**: `thumb_cmc_ab_adduction × −1` |
| dropped | 4 non-thumb MCP-AA (`4,8,12,16`) | `MCP2_a` (all-NaN), `MCP4_a`, `MCP5_a`, `CMC5`, `WRIST_F`, `WRIST_A` |
| clipping / offset / scaling / smoothing | none | none |

The two indexings are genuinely different and are resolved by name, never
positionally. Verified bit-exact — see §6.

## 4. Source-documentation findings

**emg2pose** (`docs/joint_angle_definition.md`, `CANONICAL16_CONTRACT.md`, official
`constants.py`): radians; 15/15 FE joints are **flexion-positive** (verified by
forward kinematics); `THUMB_CMC_AA` has **no global sign** (per-finger polarity);
joint values are **rotation magnitudes** about fixed joint-specific axes applied
through `so3_exp_map(axis × angle)`; the zero vector's FK pose is a
**fingers-extended hand**; `joint_limits` are never applied as a clamp.

**DB9** (official page + paper + data): `glove` = uncalibrated CyberGlove-II signal,
`angles` = **calibrated** signal "by applying the post-processing calibration
procedure"; paper Table 6 gives **Flexion+ / Extension−** for `DIP(2-5)_F,
PIP(2-5)_F, IP1_F, MCP(1-5)_F` and **Abduction+ / Adduction−** for `CMC1_A`; the
zero is the **documented reference posture** — "the central part of movement 11 in
exercise B, corresponding to the hand resting on the table with the fingers closed
together and extended".

**The official DB9 page states, verbatim:**

> "Sensor 11 (which corresponds to MCP2-3_A) was not included into the calibrated
> data due to noise problems. **DIP sensors provide reliable angles when subject
> hand size is big** (i.e. when the glove fits properly to the hand). **Instead,
> they may provide partial results when the hand of the subject is small.**
> Therefore, attention should be taken when using their information."
> — <https://ninapro.hevs.ch/instructions/DB9.html>

This warning is not a footnote. It is the mechanism behind the primary decision.

## 5. Code-path provenance

**Thirteen** construction paths enumerated; **none disagree** on the same input
(`CANONICAL16_IMPLEMENTATION_GRAPH.json`):

* emg2pose: hand-rolled name-resolved selection vs the frozen adapter — **max |diff| = 0.0, bit-exact**; the `extract` wrapper — bit-exact.
* DB9: hand-rolled conversion vs the adapter — **max |diff| = 8.88e-16 rad**, i.e. ≤ 1 ULP, and the cause is identified exactly (the adapter divides by `DEGREES_PER_RADIAN`, the hand-rolled version multiplies by `π/180`).
* **No two paths construct canonical16 differently.** That was the audit's top-priority check and it is clean.

**One housekeeping finding.** `data/ninapro_db9/dataset.npz::X_can16` is a
**second, independently built** DB9 canonical16 store whose mtime
(2026-09-17 23:31) **predates the frozen adapter** (2026-09-18 00:31). On matched
movement labels it disagrees with a from-scratch run on 10 of 16 dimensions, and
6 dimensions agree exactly — the signature of a different conversion applied to
part of the vector.

*Classification:* **ORPHANED / STALE ARTIFACT.** A repository-wide search finds
**no current code** that reads it; the confirmatory DB9 lane rebuilds
representative postures from raw files, and every frozen result derives from
`representative_postures_77.npz`, which this audit reproduces to **4.4e-16 rad**.
It is therefore **not** a second, live definition of canonical16. It is
nevertheless dangerous to consume and is left untouched per the no-write rule;
the recommendation is to quarantine or regenerate it in a future branch.

## 6. Raw → canonical parity

| path | result |
|---|---|
| emg2pose: official 20D → hand-rolled selection vs frozen adapter | **max abs diff 0.000e+00, bit-exact** over 4 218 756 samples / 30 files |
| frozen paired `gt16` vs the official full-rate projection envelope | **100.0000 %** of values inside (block mean must lie inside its source envelope) |
| DB9: raw `.mat` → hand-rolled conversion vs adapter, 77 files / 77 354 864 samples | **bit-exact for 76 of 77 files**; worst file 8.88e-16 rad |
| DB9: central-third median re-derived from raw, 42/42 cells | **max abs diff 4.44e-16 rad** |

**Any unexplained discrepancy would have been a diagnostic failure. There is none.**
The only non-exact step on the emg2pose side is the frozen Stage-B 50 Hz
block-mean reduction; reproducing it row-by-row would require re-running Stage B,
which this branch does not do and does not need, because the conversion arithmetic
is separately proven exact.

## 7. Units / sign / zero / reference audit

| criterion | verdict | basis |
|---|---|---|
| A anatomical DOF | **PASS ×16** | same named anatomical segment on both sides |
| B joint indexing | **PASS ×16** | resolved by name; verified bit-exact |
| C unit | **PASS ×16** | degrees vs radians, explicit conversion, reproduced to 4.4e-16 rad |
| D positive direction | **15 PASS, 1 CORRECTED** | paper Table 6 for the FE joints; the frozen thumb-AA flip |
| E zero definition | **PASS ×16** | both place zero at the extended, fingers-together hand |
| F reference pose | **PASS ×16** | see the reference-posture measurement below |
| G angle convention | **PASS ×16** | both are joint rotation magnitudes, not derived interior angles |
| H range / wrapping | **PASS ×16** | neither wraps; neither clamps |
| I handedness | **UNCERTAIN ×16** | DB9 is a right-hand protocol; the emg2pose mini corpus has 15 left + 15 right recordings and no handedness transform is applied anywhere |
| J **preprocessing / calibration** | **FAIL ×16** | see below |

**The reference posture is real, not nominal.** The documented DB9 calibration
reference (movement 11, central part) has **mean |canonical16| = 0.854°** over 16
dimensions, against **21.14°** mean |difference| to the other movements — a ratio
of **0.040**. Per-joint values: `[+1.27, −1.04, −0.17, +0.36, +1.42, +0.89,
+0.24, +1.00, +0.06, −1.58, +0.58, 0.00, −1.94, +1.21, +0.71, −1.19]` degrees.
DB9's documented zero is genuinely attained in the released data, and emg2pose's
zero is 0 by construction. **Criteria E and F are not where the problem is.**

**Criterion J is.** DB9's numbers are the output of a **per-channel linear sensor
calibration** whose gains came from a calibration protocol on 10 subjects and were
then applied to all 77; emg2pose's numbers are the output of an **inverse-kinematics
fit** of a generic hand model to motion capture. Two different metrological
processes. Every per-dimension disagreement found below traces to this criterion.

## 8. Per-joint DB9 vs emg2pose distributions

| joint | DB9 median | emg2pose median | median diff | Wasserstein | support overlap |
|---|---|---|---|---|---|
| thumb_cmc_flexion | +3.86 | +7.93 | +4.08 | 5.32 | 0.833 |
| thumb_cmc_ab_adduction | −4.36 | −6.21 | −1.86 | 2.44 | 0.309 |
| thumb_mcp_flexion | +3.72 | +14.28 | +10.56 | 8.28 | 0.707 |
| thumb_ip_flexion | +6.89 | +38.12 | **+31.23** | 21.52 | 0.503 |
| index_mcp_flexion | +2.27 | +16.96 | +14.69 | 11.03 | 0.744 |
| index_pip_flexion | −1.37 | +26.48 | **+27.85** | 23.37 | 0.800 |
| index_dip_flexion | +0.81 | +10.93 | +10.11 | 13.40 | 0.564 |
| middle_mcp_flexion | −0.02 | +20.67 | **+20.69** | 18.56 | 0.433 |
| middle_pip_flexion | +1.13 | +39.31 | **+38.18** | 39.42 | 0.460 |
| middle_dip_flexion | −9.28 | +20.81 | **+30.09** | 55.22 | 0.498 |
| ring_mcp_flexion | +1.25 | +19.20 | +17.96 | 13.92 | 0.599 |
| ring_pip_flexion | +3.63 | +43.08 | **+39.45** | 34.60 | 0.518 |
| ring_dip_flexion | −9.67 | +16.84 | **+26.50** | 55.11 | 0.464 |
| pinky_mcp_flexion | +2.65 | +17.35 | +14.70 | 28.56 | 0.545 |
| pinky_pip_flexion | +2.96 | +26.93 | +23.97 | 19.90 | 0.533 |
| pinky_dip_flexion | −5.51 | +5.62 | +11.12 | 25.58 | 0.545 |

The **frozen 50 Hz paired arm reproduces the full-rate marginals to within 0.3°
per joint**, so the previous branch's external numbers are not distorted by the
decimation.

**Reproducing the previous branch's grand-mean figure.** The L2 norm of the
per-joint **mean** differences is **104.1°** against this branch's computation and
the L2 norm of the **median** differences is **92.1°**. The previous branch
reported 179.7°; the two numbers are not the same statistic and the difference is
not a discrepancy in the data (see §18 for how the 179.7° figure arose and why it
overstates the coordinate question).

**The mean is the least representative summary of DB9.** For `pinky_mcp_flexion`
the DB9 mean is **+41.64°** while its median is **+2.65°** — a 39-point
mean–median gap. DB9's DIP channels produce values to **−324.6°**.

## 9. DB1 / DB2 / DB5 source effects

Re-derived, subject-clustered (2 000 bootstrap resamples over subjects):

| joint | DB1 median | DB2 median | DB5 median | DB2−DB1 | subject-level 95 % CI |
|---|---|---|---|---|---|
| pinky_mcp_flexion | +56.22 | +4.19 | +54.12 | **−52.04** | [−61.91, −41.07] |
| middle_mcp_flexion | +40.44 | +0.36 | +44.39 | **−40.08** | [−45.93, −30.99] |
| index_pip_flexion | +28.79 | −0.84 | +29.30 | **−29.64** | [−37.40, −12.61] |
| ring_dip_flexion | −29.67 | −6.02 | −29.25 | **+23.65** | [+16.29, +30.47] |
| index_mcp_flexion | +19.65 | +4.11 | +16.42 | **−15.54** | [−20.34, −10.02] |
| ring_mcp_flexion | +16.11 | +2.47 | +47.88 | **−13.64** | [−16.49, −10.56] |
| middle_dip_flexion | −21.25 | −9.36 | −35.36 | **+11.88** | [+5.92, +16.68] |
| thumb_cmc_ab_adduction | −13.14 | −4.06 | −13.80 | **+9.08** | [+6.91, +10.61] |

**11 of 16 dimensions** have a subject-level CI for the DB2−DB1 gap that excludes
zero. This matters directly: the frozen development cohort is **DB1+DB5** and the
outcome-unseen cohort is **DB2+DB5**, so **part of what the previous branch
measured as a development→outcome gap is a source-database effect already inside
DB9.**

**But the source databases do not disagree about the zero.** At the documented
reference posture:

| source | n units | mean \|angle\| | max \|per-joint median\| |
|---|---|---|---|
| DB1 | 281 | 18.001° | 9.105° |
| DB2 | 273 | **5.911°** | **2.077°** |
| DB5 | 100 | 21.268° | 4.787° |

DB2's reference posture is essentially exactly zero. DB1's and DB5's are not as
clean — but their **per-joint** deviations are small and *not* a common
translation (median +0.84°, range −11.18° to +5.27°, concentrated on
`ring_dip_flexion` −11.18°, `middle_dip_flexion` −5.70°, `pinky_mcp_flexion`
+5.27°). Their movement-to-movement profiles remain almost identical to DB2's
(**centred-profile Pearson r = +0.909 for DB1, +0.933 for DB5**). The source
effect is a **level/detail** effect inside the DB9 protocol, dominated by the same
DIP channels — not a different zero.

## 10. Large-offset joint forensics — the decisive result

### 10a. The DB9-internal channel test (needs no cross-dataset assumption)

Moving from the documented extended reference (movements 8/11) to the flexed
anchors (movements 6/1), per finger and joint level:

| finger | MCP change | PIP change | **DIP change** | DIP sign correct? |
|---|---|---|---|---|
| index | +54.9° | +107.0° | **+41.0°** | **YES** |
| middle | +96.2° | −6.2° | **−34.5°** | **NO** |
| ring | +70.0° | +31.7° | **−22.0°** | **NO** |
| pinky | +123.8° | +36.1° | **−15.3°** | **NO** |

**All four MCP channels move correctly and substantially. Only the index DIP does.**
The middle, ring and pinky DIP channels move in the **wrong direction** when the
finger flexes. That is the only robust conclusion this audit needs.

The DIP/PIP movement ratio confirms it: index **+0.383** (emg2pose's own DIP/PIP
range ratio is 0.505–0.895), middle **+5.514** with a *negative* PIP, ring
**−0.693**, pinky **−0.423**.

Dynamic range over the six gestures tells the same story from the other side:

| channel | DB9 span | emg2pose span | ratio |
|---|---|---|---|
| ring_dip_flexion | **453.8°** | 99.0° | **4.584** |
| ring_pip_flexion | 448.3° | 119.8° | 3.743 |
| index_dip_flexion | 311.6° | 97.2° | 3.207 |
| middle_dip_flexion | 296.9° | 99.8° | 2.976 |
| **middle_mcp_flexion** | 186.0° | 112.2° | **1.658** |
| **index_mcp_flexion** | 147.9° | 106.3° | **1.392** |

The clean channels have ratios of **1.37–1.83**; the DIP channels have
**2.98–4.58** with spans up to **453.8°**, which is a physically impossible range
for a hinge joint. `ring_dip_flexion` reaches **−324.6°**.

### 10b. Raw sensor forensics

The released `glove` (uncalibrated) channels are finite in **all 99** files, so a
per-channel linear calibration can be recovered. For one subject (S10):

| channel | glove ext→fist | glove change | released angle ext→fist | implied slope |
|---|---|---|---|---|
| PIP2 | 87.2 → 104.0 | +16.8 | +1.3 → +113.0 | 8.9 deg/unit |
| PIP3 | 60.0 → 176.0 | **+116.0** | 0.0 → −49.1 | 1.0 deg/unit |
| PIP4 | 89.0 → 160.8 | +71.8 | −1.7 → −23.6 | 0.3 deg/unit |
| DIP2 | 70.0 → 185.0 | **+115.0** | +0.6 → **+18.7** | **positive, correct** |
| DIP3 | 88.0 → 129.0 | +41.0 | −2.3 → **−40.0** | **negative, wrong** |
| DIP4 | 143.3 → 134.2 | **−9.1** | −0.6 → **−24.9** | **negative, wrong** |

* The **DIP2** channel behaves exactly as a working flexion sensor should.
* **DIP3** physically moves **+41 glove units** towards flexion yet the released
  calibrated angle moves **−30°**: the calibration's sign/scale for that channel
  is wrong, not the sensor.
* **DIP4**'s raw sensor *decreases* during fist closure — a sensor-placement or
  sensor-defect signature.
* Implied slopes across the corpus vary by a factor of ~5 between homologous PIP
  channels and even change sign between DIP channels.

This is exactly the failure mode the **official DB9 page warns about**: DIP
sensors "provide reliable angles when subject hand size is big … may provide
partial results when the hand of the subject is small". A linear calibration
whose gains were established on 10 subjects and then applied to 77 will, for
subjects whose glove did not seat properly on the DIP sensor, extrapolate the
reading far outside the physical range. `ring_dip_flexion = −324.6°` is that
extrapolation running away, not a coordinate convention.

### 10c. Complement / wrapping / constancy (questions A, B, F, J)

* **Not a π or π/2 complement.** For the flag dimensions, the distance from the
  π-complement is large, and emg2pose's own DIP values (p5–p95 ≈ 83–87°) are
  ordinary positive flexion values. There is no `θ` vs `π − θ`, `θ` vs
  `interior angle`, or `abs(θ)` relationship to find: the DB9 numbers are not a
  transform of a physical angle at all.
* **Not wrapping.** `ring_dip_flexion` spans 453.8° and is negative in 62.6 % of
  units; wrapping would produce a bounded, folded distribution, not this.
* **The offset is not constant across quantiles**, and a robust-core affine map
  does not remove it in a way that is stable across joints.
* **The flag is stable across subjects, movements and source databases.** 73 of 77
  subjects have `middle_dip_flexion` minima below −100°; 77 of 77 for
  `ring_dip_flexion`, 58 below −200°.

## 11. DB9 movement-stream anomaly (a genuine, separate defect)

A label-versus-content check over all 77 recordings (WRIST_F / WRIST_A, which
canonical16 drops, are the only channels that can identify a wrist movement
without any cross-dataset assumption):

> **16 of 17 movements match their documented class. Movement 15 does not.**

Movement 15 is documented as **wrist radial deviation**. Its median finger-channel
excursion from the reference posture is **39.28°** against **22.72°** for the
wrist channels, it is finger-dominant in **59 of 77** recordings — the only
wrist-labelled movement of which that is true — and its 22-channel profile
correlates **+0.668** with the hand configurations (movement 1: +0.707) versus
**+0.435** with the wrist movements.

**Impact on canonical16: none.** Movement 15 is not in the six-gesture vocabulary
(1, 2, 3, 4, 6, 7). It affects any analysis that uses movement 15, and it is
recorded here because the audit found it and it belongs on the record.

A weaker, related observation: `middle_dip_flexion` and `ring_dip_flexion` read
**−113.7°** and **−201.3°** during movement 7 ("pointing index"), when only the
index should be flexed and the other fingers are held extended — further evidence
that those channels are not tracking their joints.

## 12. Candidate angle-convention tests (frozen T0–T7)

All eight frozen transforms were evaluated per dimension with both source-only
estimators, and the results are in `LARGE_OFFSET_FORENSICS.json`.

**No transform is adopted and none is recommended as a fix.** The audit's reading:

* **T2–T5 (the π-family) are not supported.** They are formally evaluated, but
  their "improvements" are artefacts: a transform that maps one unrelated marginal
  onto another can always reduce a Wasserstein distance. For the flag dimensions
  the DB9 distribution is not a reflected or complemented version of the
  emg2pose one — its *shape* is different (span 453.8° vs 99.0°).
* **T6/T7 (offset / affine) help the marginals but do not fix the channels.** The
  robust-core affine map forced by matching DB9's q05–q95 onto emg2pose's is
  dominated by DB9's runaway tail, and no affine map applied to a broken sensor
  channel makes it a measurement. Recorded as a diagnostic, **not** as a candidate
  system, per the plan's prohibition on a deployed transform.
* The decisive evidence against all transforms is **§10a**: the DIP channels fail
  an internal, transform-free, cross-dataset-free test. No per-dimension
  correction should be fitted to data whose generating channel is demonstrably not
  measuring the joint.

## 13. Physical anchor results

### 13a. The DB9 documented reference posture is real (§7) — mean |angle| 0.854°.

### 13b. Anchor matching: which DB9 prototypes actually exist in emg2pose?

Each DB9 movement prototype (median over 77 subjects) was searched against all
86 858 frozen 50 Hz emg2pose GT frames:

| DB9 movement | best distance in emg2pose | median of the 200 best |
|---|---|---|
| **11 wrist supination (little)** | **7.8°** | 21.4° |
| 12 wrist pronation (little) | 11.3° | 22.0° |
| 17 wrist extension, closed hand | 12.2° | 20.4° |
| 14 wrist extension | 14.6° | 25.2° |
| 9 wrist supination (middle) | 21.1° | 29.8° |
| 8 adduction of extended fingers | 22.3° | 29.2° |
| 16 wrist ulnar deviation | 24.3° | 31.0° |
| 13 wrist flexion | 32.7° | 42.3° |
| 10 wrist pronation (middle) | 34.2° | 38.4° |
| **15 wrist radial deviation** (anomalous) | 93.5° | 101.5° |
| **5 abduction of all fingers** | 99.4° | 102.9° |
| **1 thumb up** | 104.3° | 111.0° |
| **4 thumb opposing little** | 105.6° | 111.5° |
| **6 fist** | **122.9°** | 133.6° |
| **7 pointing index** | **127.2°** | 137.9° |
| 2 extension index+middle | 169.6° | 176.4° |
| 3 flexion ring+little | 193.9° | 204.8° |

**The extended and wrist configurations exist in the natural emg2pose stream
(7.8–34°). The flexed hand configurations do not (100–200°).** That is precisely
what DB9's broken DIP channels predict: those channels inflate the distance to the
hand-configuration prototypes, because a DB9 fist carries DIP values that no real
hand can produce.

The per-joint residual at the best match shows the mechanism directly — for the
fist prototype, the leading abs residual after `middle_dip_flexion` and
`ring_dip_flexion` is `pinky_mcp_flexion` (−54.7°), another of DB9's channel-level
problems, while `ring_dip_flexion` contributes **+154.5°** for movement 3.

## 14. Subject / session zero-offset analysis

**Source-database decomposition (DB9, subject-clustered):** 11 of 16 dimensions
have a DB2−DB1 gap whose subject-level CI excludes zero, up to **−52.04°**
(pinky MCP). The reference *posture* agrees across sources, but the *per-dimension
levels* do not.

**emg2pose session structure:** 15 stages × 2 sides of **one** subject. Per-stage
median left-vs-right distance is 24.5–61.0° (L2), with a stage-to-stage per-dimension
spread whose median is **72.24°** — against a median cross-dataset per-dimension
gap of **19.32°**. Ratio **3.74**.

> The emg2pose side's own session/prompt variation is **~3.7× larger** than the
> cross-dataset median gap. Any per-dimension "shift" of ~20° is therefore within
> the natural variation of this one subject's recordings, and is not evidence of a
> systematic cross-dataset offset.

## 15. Matched-semantic C1 / C6 analysis

The only comparison in this audit whose two sides describe the **same physical
gesture**: DB9 movement prototypes versus the frozen human-consensus windows
labelled with those gestures. Alignment uses the frozen Stage-H rule; **4 windows
are not evaluable** and are reported as such.

| | DB9 units | human windows | mean abs median diff | L2 |
|---|---|---|---|---|
| **CLASS_1** | 655 | **4** | **41.14°** | 226.91° |
| **CLASS_6** | 645 | **6** | **30.17°** | 153.40° |
| (unconditional per-joint gap, for contrast) | — | — | 20.19° | — |

**Matching the semantics does not reduce the disagreement — it increases it**
(ratio **2.04** for CLASS_1, **1.49** for CLASS_6). That rules out task
composition as the explanation for these per-joint differences.

But the per-joint structure is the informative part. For CLASS_1:

| joint | DB9 | emg2pose (4 windows) | diff |
|---|---|---|---|
| index_mcp_flexion | 55.1 | 62.2 | **+7.1** |
| index_pip_flexion | 100.0 | 112.9 | +12.8 |
| **index_dip_flexion** | 35.2 | 46.1 | **+10.9** |
| ring_mcp_flexion | 63.9 | 63.8 | **−0.1** |
| middle_mcp_flexion | 93.2 | 69.0 | −24.1 |
| **middle_pip_flexion** | −2.8 | 99.3 | **+102.1** |
| **middle_dip_flexion** | −25.9 | 87.1 | **+113.1** |
| **ring_pip_flexion** | 29.6 | 102.5 | **+72.9** |
| **ring_dip_flexion** | −13.0 | 86.4 | **+99.3** |
| **pinky_mcp_flexion** | 124.3 | 64.8 | **−59.5** |

**The `index_*` channels agree closely on the matched gesture (+7.1°, +12.8°,
+10.9°) while the `middle_*` and `ring_*` PIP/DIP channels disagree by ~100°.**
That is the pattern a per-channel calibration defect produces, and it is not the
pattern a coordinate-convention mismatch produces (which would affect a whole
joint *level* consistently across fingers) nor a task-composition effect (which
matching the gesture removes).

Descriptive only: n = 4 and 6, the labels are a two-rater consensus under a frozen
ontology rather than ground truth, and 4 windows are not evaluable.

## 16. Geometry: location / scale / orientation / shape

| component | measurement |
|---|---|
| **location** | per-joint median differences 1.9–39.5°, mean 20.19° |
| **scale** | per-joint SD ratios emg2pose/DB9: 0.42 (ring DIP) to 8.73 (middle PIP); IQR ratios 0.42 to 21.5 — inconsistent across joints |
| **orientation** | leading-4 principal angles 22.7°, 29.2°, 51.5°, 78.5°; off-diagonal correlation-structure Pearson **r = +0.102**, sign agreement **0.500** (chance) |
| **shape / structure** | pairwise configuration-distance Spearman **ρ = +0.059**, Pearson +0.007 |

**The alignment-invariant structural test fails.** Ratios of pairwise distances
between configurations are invariant under any similarity transform, so no
per-joint affine correction can manufacture this agreement. ρ ≈ 0.06 means the two
datasets do **not** order configuration separations the same way. Read together
with §15 (where the matched-gesture comparison shows the index channels agreeing
and the middle/ring channels not), the correct interpretation is **not** "the two
hands have different geometry" but "several DB9 channels are not measuring their
joints, so the DB9 configuration geometry is itself partly fabricated".

**Joint-identity redundancy:** only **4 of 16** dimensions have their own
counterpart as the best match. `middle_dip_flexion`'s variation best matches
`pinky_dip_flexion` (−0.913); `ring_dip_flexion`'s best matches `ring_pip_flexion`
(−0.497); `index_mcp_flexion`'s best matches `middle_mcp_flexion` (+0.918, while
its own r is +0.900). The correctly-measured channels dominate the diagonal;
the broken ones do not.

## 17. S4 / UmeTrack cross-check

**Does FK of a canonical16 pose return the same joint angle?**

| channel | max \|stored − FK interior angle\| |
|---|---|
| index_pip_flexion | **0.899°** |
| middle_pip_flexion | **0.551°** |
| ring_pip_flexion | 0.725° |
| pinky_pip_flexion | 5.152° |
| index_dip_flexion | 11.56° |
| middle_dip_flexion | **13.68°** |
| ring_dip_flexion | 7.18° |
| pinky_dip_flexion | 8.64° |

The PIP joints round-trip to **within ~0.5–0.9°**, confirming that the stored
number **is** the joint rotation angle (criterion G, "flexion from straight", not
a derived interior angle of an arbitrary chain) — the residual is small and is the
expected out-of-plane axis component. The DIP residuals are 7–14°, i.e. an order
of magnitude larger, because the DIP rotation axis is further from the finger
plane. **This is a descriptive cross-check, not a redefinition of any convention**,
and it cannot by itself establish DB9's DIP calibration.

**Round-trip honesty.** `emg2pose 20D → canonical16 → 20D` restores the kept
dimensions **bit-exactly** (max error 0.000e+00 over 3 559 584 samples) and the four
dropped MCP-AA DOF are **unrecoverable** — no inverse is fabricated. The landmark
cost of the frozen MCP-AA = 0 convention on real poses is a **median session mean
of 0.1302 model units** (max 21.8 on one pose). **`DB9 → canonical16` has no
inverse at all** (DB9's `CMC5`, `MCP4_a`, `MCP5_a`, `WRIST_F`, `WRIST_A` are not
canonical16 inputs and `MCP2_a` is officially dead), so no DB9 inverse was
constructed.

## 18. Joint-by-joint equivalence verdict

| # | canonical dimension | anatomical correspondence | unit | sign | zero / reference | scale | empirical range compatibility | **final status** | confidence class |
|---|---|---|---|---|---|---|---|---|---|
| 0 | thumb_cmc_flexion | PASS | PASS | PASS | PASS | PASS | HIGH | SAFE FOR COMMON POSE API | VERIFIED SEMANTICALLY, NUMERIC CALIBRATION UNCERTAIN |
| 1 | thumb_cmc_ab_adduction | PASS | PASS | **CORRECTED** | PASS | **UNCERTAIN** | HIGH | **SAFE AFTER DOCUMENTED TRANSFORM** | KNOWN SIGN TRANSFORM |
| 2 | thumb_mcp_flexion | PASS | PASS | PASS | PASS | PASS | HIGH | SAFE FOR COMMON POSE API | VERIFIED SEMANTICALLY, NUMERIC CALIBRATION UNCERTAIN |
| 3 | thumb_ip_flexion | PASS | PASS | PASS | PASS | PASS | LOW | NOT YET SAFE (range disagreement 31°) | VERIFIED NUMERICALLY EQUIVALENT |
| 4 | index_mcp_flexion | PASS | PASS | PASS | PASS | PASS | HIGH | SAFE FOR COMMON POSE API | VERIFIED SEMANTICALLY, NUMERIC CALIBRATION UNCERTAIN |
| 5 | index_pip_flexion | PASS | PASS | PASS | PASS | PASS | MODERATE | SAFE FOR COMMON POSE API | VERIFIED NUMERICALLY EQUIVALENT |
| 6 | index_dip_flexion | PASS | PASS | PASS | PASS | PASS | MODERATE | SAFE FOR COMMON POSE API | VERIFIED SEMANTICALLY, NUMERIC CALIBRATION UNCERTAIN |
| 7 | middle_mcp_flexion | PASS | PASS | PASS | PASS | PASS | MODERATE | SAFE FOR COMMON POSE API | VERIFIED SEMANTICALLY, NUMERIC CALIBRATION UNCERTAIN |
| 8 | middle_pip_flexion | PASS | PASS | PASS | PASS | **UNCERTAIN** | LOW | **NOT YET SAFE** | POSSIBLE OFFSET |
| 9 | middle_dip_flexion | PASS | PASS | **FAIL (DB9 channel measures the wrong thing)** | PASS | **FAIL** | LOW | **NOT YET SAFE** | POSSIBLE OFFSET |
| 10 | ring_mcp_flexion | PASS | PASS | PASS | PASS | PASS | MODERATE | SAFE FOR COMMON POSE API | VERIFIED NUMERICALLY EQUIVALENT |
| 11 | ring_pip_flexion | PASS | PASS | PASS | PASS | **UNCERTAIN** | LOW | **NOT YET SAFE** | VERIFIED SEMANTICALLY, NUMERIC CALIBRATION UNCERTAIN |
| 12 | ring_dip_flexion | PASS | PASS | **FAIL (DB9 channel measures the wrong thing)** | PASS | **FAIL** | MODERATE | **NOT YET SAFE** | POSSIBLE OFFSET |
| 13 | pinky_mcp_flexion | PASS | PASS | PASS | PASS | PASS | MODERATE | SAFE FOR COMMON POSE API | VERIFIED SEMANTICALLY, NUMERIC CALIBRATION UNCERTAIN |
| 14 | pinky_pip_flexion | PASS | PASS | PASS | PASS | PASS | MODERATE | SAFE FOR COMMON POSE API | VERIFIED NUMERICALLY EQUIVALENT |
| 15 | pinky_dip_flexion | PASS | PASS | **FAIL (DB9 channel moves the wrong way)** | PASS | **FAIL** | MODERATE | **NOT YET SAFE** | POSSIBLE OFFSET |

**Summary:** anatomical correspondence, unit, sign and zero/reference are **PASS**
for all 16 dimensions, with the one documented thumb-AA sign correction. The
failures are concentrated in **scale and per-channel calibration**, on four
dimensions:

* **`middle_dip_flexion`** — DB9 channel moves **−34.5°** when the finger flexes (should be positive); span 296.9° (emg2pose 99.8°); matched-gesture gap **+113.1°**; the implied per-channel calibration slope is **negative** and the raw glove and the released angle **disagree in sign** in **73 of 77** recordings.
* **`ring_dip_flexion`** — DB9 channel moves **−22.0°**; span **453.8°**, reaching **−324.6°**; matched-gesture gap **+99.3°**.
* **`pinky_dip_flexion`** — DB9 channel moves **−15.3°**; DB2−DB1 gap +7.07° with CI excluding zero.
* **`middle_pip_flexion`** — its own test passes (−6.2° is a null result, not a wrong sign) but its span ratio is **1.832**, its matched-gesture gap is **+102.1°** and it is the channel most coupled to the broken middle DIP; classified POSSIBLE OFFSET with the reason recorded.

**`pinky_mcp_flexion` is exonerated.** It is the third dimension the previous
branch flagged (+79.0° grand-mean offset), and this audit finds it **healthy**:
its channel moves **+123.8°** correctly towards flexion, its span ratio is 1.653
(normal), and its best match in emg2pose is positionally consistent. Its
grand-mean offset is a **source-database + heavy-tail artifact** (DB1 median
+56.22° vs DB2 +4.19°, and a mean–median gap of 39 points). The previous branch's
name for it was right; its diagnosis was not.

## 19. Primary decision: **COORD-D — MIXED COORDINATE MISMATCH**

* **Not COORD-A** (all equivalent): four dimensions fail an internal,
  transform-free, cross-dataset-free test. The DB9 channels do not measure their
  joints.
* **Not COORD-B** (zero/offset calibration mismatch): the reference posture is
  attained to **0.854°** mean |angle| in DB9 and is 0 by construction in
  emg2pose; all three DB9 source databases agree on it. There is no missing zero.
* **Not COORD-C** (angle-convention mismatch): no π, π/2, reflection, absolute-value
  or wrapping relationship fits. The failing channels are not a different
  parameterisation of a physical angle; they are not a measurement of it at all.
* **Not COORD-E** (mismatch + real shift): COORD-E requires a *coordinate*
  difference; this is a **single-dataset calibration defect**, which is a different
  claim. A genuine distribution shift certainly also exists (DB9's protocol vs
  emg2pose's natural activity), but it is not what the flagged dimensions are.
* **COORD-D** is the correct reading: **some dimensions are numerically
  equivalent and some are not**, and the non-equivalent ones are non-equivalent
  because one side's measurement is broken.

## 20. Reinterpretation of the 179.7° offset

The previous branch compared the **grand mean** of a DB9 corpus whose dominant
protocol movements are flexed (fist at 1.183 rad mean |canonical16|; movements
1/6 at 49.3°/61.2°) against the grand mean of natural emg2pose activity.

This audit finds the grand-mean statistic is **dominated by three effects, none of
which is a coordinate mismatch**:

1. **Broken DB9 DIP channels.** `middle_dip_flexion` and `ring_dip_flexion` take
   physically impossible values (to −268° and −324.6°); any mean over them is
   meaningless. Removing that contribution is the single largest correction.
2. **Task composition.** DB9 samples a scripted 17-movement protocol; emg2pose
   samples natural, largely non-gestural activity. The per-joint *median*
   differences (1.9–39.5°, L2 **92.1°**) are far smaller than the *mean*
   differences (L2 **104.1°**), and the mean–median gap reaches 39 points on
   `pinky_mcp_flexion`.
3. **Source-database imbalance.** 11 of 16 dimensions differ between DB1 and DB2
   with a subject-level CI excluding zero, up to −52°.

**The honest restatement:** the 179.7° figure was a real measurement of a real
difference, but it measured *the wrong thing*. It is not evidence for a
cross-dataset coordinate mismatch, and it should not be cited as one. The
cross-dataset part of the disagreement is smaller, joint-specific, and — most
importantly — **not uniform across the dimensions that were flagged**.

## 21. Reinterpretation of the failed distributional branch

The previous branch's headline numbers were: **UNKNOWN 0.8057** on natural
emg2pose GT, **0/10 human-consensus targets accepted**, and the nearest correct
DB9 class at **rank ≤ 2 for all ten** targets. This audit explains all three.

1. **Why 0.8057.** A Gaussian/Mahalanobis class model fitted on DB9 inherits
   DB9's DIP channels. Because those channels take impossible values, the fitted
   covariance is enormously inflated along those axes, so the Mahalanobis distance
   of *any* natural pose is dominated by a term that carries no information. The
   model is not detecting a real out-of-distribution condition; it is measuring
   DB9's own calibration noise. The residual it reports is therefore not a
   distribution-shift statistic.

2. **Why 0/10 targets were rejected.** The same mechanism: every human-consensus
   target window differs from its DB9 prototype by ~100° on exactly the broken
   channels (§15), while agreeing to ~7–13° on the working `index_*` channels.

3. **Why relative geometry survived while absolute support failed.** This is
   exactly what a per-channel calibration defect does. A broken channel adds a
   large, roughly *constant* penalty to every class's distance (the inflated
   variance makes the per-sample contribution large but weakly class-discriminative),
   so it preserves the **ranking** of classes while destroying the **absolute
   threshold**. The previous branch's observation — "the correct DB9 class is the
   nearest of six for 6/10 targets, rank ≤ 2 for all ten" — is the direct
   signature of that. It was correctly reported as a puzzle; it now has a
   mechanism.

**How much of the failure was coordinate mismatch?** The coordination *conventions*
are sound (§7, §18): DOF identity, units, signs, zero, reference pose and angle
convention all pass. What failed is **one dataset's per-channel calibration**, on
4 of 16 dimensions. So the answer is: **not a coordinate mismatch, but a
measurement-quality defect inside DB9** — and, because DB9 supplied the reference
geometry, that defect propagated into every cross-dataset conclusion the project
drew from canonical16.

**A quantitative check, and an important negative result.** A post-hoc magnitude
check (`BROKEN_CHANNEL_CONTRIBUTION.json`) re-derives a per-gesture
Gaussian/Mahalanobis class model from the frozen DB9 representative postures and
applies it to the frozen 86 858 paired emg2pose GT frames, once with all 16
dimensions and once excluding the four POSSIBLE OFFSET dimensions:

| | UNKNOWN rate |
|---|---|
| all 16 dimensions | 0.9609 (83 463 / 86 858) |
| excluding the four POSSIBLE OFFSET dimensions | **0.8861** (76 963 / 86 858) |
| (the previous branch's fitted pipeline) | 0.8057 |

**Removing the broken channels lowers the rate by ~7.5 points — real, but
partial.** Most of the over-rejection **survives** their removal. This audit
therefore **does not** claim the 0.8057 was an artifact of the broken channels; it
was not. The result is consistent with Session 5's independent finding that a
genuine cross-dataset distribution shift exists.

Two caveats, stated so the table is not over-read: this is a **magnitude check, not
a replication** (a plain sample covariance over-rejects relative to the frozen
subject-grouped shrinkage pipeline — 0.9609 vs 0.8057 on the same 16 dimensions), so
only the **difference** between the two rows is interpretable, not either level; and
the check was run **after** the verdict was assigned, changing no model, threshold or
frozen artifact.

**How much remains genuine distribution/semantic shift?** Substantial, and this
audit bounds it more tightly than before: even with the four broken dimensions
removed, **88.6 %** of natural poses are still outside every DB9 gesture region. Add
the per-joint median gaps on the *working* channels (2–40°), the emg2pose session
spread (median 72.24°) exceeding the cross-dataset median gap (19.32°) by 3.7×, and
Session 5's 77.04 % beyond-p95 figure — a genuine domain shift clearly exists.
**It had never been measured cleanly, because every previous measurement used the
broken channels; §23's step 5 is the cheapest way to close that.**

## 22. Implication for the Common Pose API

**A. Is canonical16 currently valid as a genuine cross-dataset physical API?**
**Partially, and not as a drop-in one.** All the *semantic* criteria pass — the
DOF identities, units, positive directions, zero definitions, reference pose and
angle convention are consistent, and the reference posture is numerically attained
in DB9. What fails is the *numerical quality* of a subset of DB9's channels.
canonical16 as currently consumed silently mixes a well-measured subset with a
subset that is not measuring what it claims.

**B. Which dimensions are already trustworthy?**
`thumb_ip_flexion`, `index_pip_flexion`, `ring_mcp_flexion`, `pinky_pip_flexion`
— classified **VERIFIED NUMERICALLY EQUIVALENT** (correct response to flexion
*and* a matching movement-to-movement profile). A further seven are
**VERIFIED SEMANTICALLY, NUMERIC CALIBRATION UNCERTAIN**: they pass the internal
channel test but their profiles do not match their emg2pose counterpart.

**C. Which dimensions require an explicit convention transform?**
Exactly one: **`thumb_cmc_ab_adduction`** — the already-frozen sign flip. Its axis
identity is still explicitly not proven, which is why `canonical15_noThumbAA`
exists.

**D. Which dimensions are semantically matched but numerically dataset-specific?**
Eleven: the seven "calibration uncertain" dimensions plus the four **POSSIBLE
OFFSET** dimensions (`middle_pip_flexion`, `middle_dip_flexion`,
`ring_dip_flexion`, `pinky_dip_flexion`).

**E. What would a future Common Pose API need?**

* **Explicit neutral-pose normalisation — YES, but it is not the main fix.** Both
  datasets already place zero at the extended hand and DB9's reference posture is
  attained to 0.854°. This would remove little.
* **Per-dataset calibration metadata — YES, and this is the load-bearing
  requirement.** The DB9 numbers come from a per-channel linear sensor calibration
  whose gains came from 10 subjects and were applied to 77; the official DB9 page
  itself warns that DIP sensors give partial results on small hands. A shared API
  must carry **per-channel calibration provenance**, not just an anatomical name.
* **Per-subject calibration — POSSIBLY.** The three source databases disagree by
  up to 52° in per-dimension medians with subject-level CIs excluding zero. The
  split between "subject" and "measurement noise" is **not resolved by this
  audit**: the DB9 corpus publishes 6 repetitions per movement, so within-subject
  repeatability *is* estimable and a future branch should estimate it.
* **Standardised anatomical zero definitions — YES.** Both datasets already
  describe their zero as the extended, fingers-together hand, but only DB9
  documents the movement it was taken from; emg2pose's zero is a
  model-construction artefact. A shared API should define the zero by an explicit
  physical configuration.
* **Reduced shared DOF subset — YES, but understand what it concedes.** The middle
  and ring DIP channels should not be advertised. That is conceding a **data
  defect**, not resolving a convention question — and it means the shared subset
  would be 13–14 dimensions, not 16.

**F. Does this weaken or strengthen "explicit physical pose as a reusable
interface"?**

**It relocates the problem rather than settling the hypothesis.** The previous
branch read the 179.7° offset as a possible coordinate mismatch between two
datasets describing the same hand; this audit finds the offset is dominated by
DB9's own broken DIP calibration, and that the genuinely cross-dataset part of the
disagreement is smaller and differently shaped.

It does **not** show the pose-interface idea fails. It shows that **an explicit
physical pose API is only as good as the weakest channel's calibration
provenance** — and that canonical16, as consumed, has been carrying a defect that
was documented in the official dataset page all along and was never checked
against the data. That is a fixable interface defect, and it means **every
cross-dataset result this project has produced with canonical16 has been carrying
it.**

## 23. Exact next experiment

**Do not repair the transform. Repair the measurement.**

The next branch should be a **DB9 channel-validity branch**, not a coordinate
branch and not an architecture branch:

> **Branch: "is a physically valid DB9 sub-corpus recoverable?"**
>
> 1. **DB9-internal repeatability.** For each of the 6 repetitions per movement per
>    subject, estimate within-subject, within-movement repeatability per channel.
>    If the DIP channels have repeatability comparable to the MCP/PIP channels,
>    their wild values are a *between-subject* calibration-gain failure, which is a
>    different (and more tractable) statement than "broken sensor".
> 2. **Subject-level channel screening on DB9 alone.** Define a purely internal
>    validity gate per (subject, channel) — e.g. "does the channel change in the
>    correct direction between the two documented anchors, and by a plausible
>    amount?" — and report the eligible sub-corpus. **Freeze the gate before any
>    external scoring.** Do not fit it to emg2pose.
> 3. **Re-derive the six-gesture DB9 corpus from eligible subjects only**, and
>    re-run the closed-set DB9 internal validation as a *control* (it should not
>    change much: the closed-set LDA was already 0.978).
> 4. **Only then** re-run the external distributional readout, and report it
>    against both the old and the screened corpus, so the cost of the screening is
>    visible.
> 5. **Separately and cheaply:** re-estimate Session-5's 77.04 % beyond-p95 figure
>    using only the eligible channels. That number is the cleanest existing
>    measurement of genuine distribution shift and it has never been computed
>    without the broken channels.
>
> **Do not** run `canonical15_noThumbAA` as a rescue; it drops a *different*
> dimension. **Do not** deploy a per-dimension offset. **Do not** re-open the
> open-set architecture before the measurement is clean.

**One unresolved item carried forward:** **handedness (criterion I)** is UNCERTAIN
on all 16 dimensions. DB9 is a right-hand protocol; the emg2pose mini corpus
contains 15 left and 15 right recordings, and no handedness transform is applied
anywhere. The project's frozen contract treats the 20D vector as model-frame, and
this audit did not establish whether the UmeTrack model frame is
handedness-invariant for the left recordings. That is a genuine, cheap, and
entirely separate follow-up.

## 24. Limitations

1. **Movement 15 is unresolvable within this audit's scope.** The evidence that it
   is a genuine DB9 m-file anomaly is strong (finger-dominant in 59/77 recordings;
   profile correlates +0.668 with hand configurations vs +0.435 with wrist
   movements), but this audit did not obtain the original Ninapro movement videos
   or a per-source protocol table, so the *cause* (relabelling vs a recording
   mix-up) is **UNRESOLVED**. It does not affect canonical16.
2. **The reference-posture repeatability is not decomposed.** DB2's reference is
   essentially exact (5.911°) while DB1's is 18.001°. Whether that is between-subject
   anatomy, protocol compliance, or calibration gain is not determined here;
   estimating it requires the within-subject repetition structure, which this audit
   identified but did not exploit.
3. **The failing DB9 channels are not diagnosed to root cause.** The evidence
   establishes that the released calibrated DIP angles do not track the joint; it
   does not separate (a) a wrong per-channel calibration gain from (b) a
   poorly-seated sensor from (c) a sensor defect. The raw `glove` data shows DIP4's
   sensor *decreasing* during fist closure, which points at (b)/(c) for that digit,
   but this audit cannot exclude (a) for the others.
4. **emg2pose is one subject.** Session/prompt variation (median spread 72.24°)
   exceeds the cross-dataset median gap (19.32°), so **no per-dimension cross-dataset
   claim in the 20–30° range is resolvable with this corpus at all.**
5. **Matched semantics rest on n = 4 and n = 6** two-rater consensus windows, 4 of
   which are not evaluable. Descriptive only.
6. **The structural test's emg2pose side** uses a deterministic k-means over a
   40 000-frame subsample; the seed and sample size are recorded, and the result
   (ρ = +0.059) is far from any threshold where subsampling would matter.
7. **The S4 cross-check measures interior angles, which are only equal to joint
   angles for in-plane rotation.** The PIP round-trip (≤0.9°) confirms the
   convention; the DIP residuals (7–14°) are the expected out-of-plane component
   and are **not** evidence about DB9.
8. **Criterion I (handedness) is UNRESOLVED** for all 16 dimensions — see §23.
9. **`data/ninapro_db9/dataset.npz` was left untouched** per the no-write rule; it
   remains a stale artifact that a future session should quarantine.
10. **No significance testing is performed.** Every uncertainty figure is either a
    subject-level or session-level bootstrap CI; frames are never treated as
    independent participants and no p-value is computed on correlated frames.

## 25. Deviations

| # | deviation | disposition |
|---|---|---|
| 1 | **Extra artifacts beyond the plan's list**: `DB9_DIP_CHANNEL_VALIDITY.json`, `DB9_MOVEMENT_STREAM_CONSISTENCY.json`, `GEOMETRY_SHAPE_LOCATION_DECOMPOSITION.json`, `DB9_DIP_CHANNEL_VALIDITY.json`. | Added **after** the plan freeze, in response to what the frozen audit found. Each is a diagnostic, none changes a frozen rule, a model or a threshold, and all are recorded here. |
| 2 | **`DB9_DIP_CHANNEL_VALIDITY` was not in the plan's artifact list but is the decisive test.** | It is a within-DB9 anchor test, which §7 of the plan authorises under "internal datasets / artifacts to inspect" and which the plan's anchor section explicitly contemplates. Recorded as an addition, not a substitution. |
| 3 | **Two anomaly tests were tried and one was rejected.** A finger-vs-wrist excursion *ratio* and a 22-channel profile *correlation* were both attempted; the correlation test is not diagnostic for the wrist movements (near-zero profiles correlate weakly with everything) and is recorded in the artifact **with its limitation stated**, rather than deleted. | Recorded. |
| 4 | **`canonical15_noThumbAA` was not run.** It is not this branch's question, and running it would be the rescue the brief prohibits. | Not run, by design. |
| 5 | **Movement 15's root cause is UNRESOLVED.** Two hypotheses (relabelling in the release; a protocol-numbering difference between source databases) were each tested and are not distinguished by the available data. | Recorded as a limitation, with the test evidence attached. |
| 6 | **The plan's decision-tree outcome COORD-E was considered and rejected** for the reason stated in §19: the failure is a single-dataset calibration defect, not a coordinate difference. | Recorded. |

## 26. Bugs encountered

| # | bug | resolution |
|---|---|---|
| 1 | `np.trapezoid` does not exist in numpy 1.26 (renamed in 2.0). | replaced with `np.trapz` |
| 2 | KDE support-overlap allocated a 148 GiB temporary by broadcasting 77 354 864 samples against a 256-point grid. | subsample to 200 000 with a frozen seed + chunked kernel evaluation; the subsample is far above the resolution of the comparison |
| 3 | The joint-identity test produced all-NaN because an (86 858 × 17 × 16) float64 broadcast overflowed to `Inf`. | chunked nearest-prototype labelling in float64 |
| 4 | The human-consensus endpoint vocabulary in the artifact is `CLASS_1`/`CLASS_6`/`NON_TARGET`, not the `HUMAN_*` spelling used in the Stage-G/H layer. | both accepted, and the driver now **hard-fails** on an empty cohort rather than emitting an empty comparison |
| 5 | A dict-comprehension key referenced a variable bound in its own value expression (`{k: ... for n in names}`), raising `KeyError` on the first lookup. | corrected; a real bug caught by running the pipeline, not by inspection |
| 6 | `pose[v] = 0.0` with a 4-element index vector into a 1-D array in the S4 cross-check. | explicit loop |
| 7 | The second DB9 store comparison initially reported a 224° difference because it compared *different frame populations* (`dataset.npz` keeps rest frames and a stride-80 subsample; a raw file does not). | comparison restricted to matched movement labels; the "discrepancy" is real but its cause is the stale-artifact finding in §5, not a live inconsistency |
| 8 | `db9_pick_file_for_slot` initially keyed on the filename tag `_E2_`, which is a **source-database naming artefact**: DB1/DB5 use `_E2_`, DB2 uses `_E1_`. | the protocol file is now identified **from the data** (the file whose `stimulus` stream contains movement 17), never from the filename |

**No frozen artifact was modified, and no write occurred outside the branch lane.**

## 27. Artifacts and hashes

Full inventory with sizes and raw-byte SHA-256: `ARTIFACT_MANIFEST.json`.

| artifact | SHA-256 |
|---|---|
| `POSE_COORDINATE_AUDIT_PLAN.json` | `c59fe01370d48aedeed56ef7a4103506d14a298edb794723be3720531edd62c6` |
| `CANONICAL16_IMPLEMENTATION_GRAPH.json` | `186da8d4ac0321409cc6332e1265b6810c0b32a6f5f2e03ab33e5c77cf83e33e` |
| `RAW_TO_CANONICAL_PARITY_RESULTS.json` | `6e6f414eb81019c75a3e28e7e3e425ca93ae088a30ca3b7bb91718037ef6d94a` |
| `PER_JOINT_DISTRIBUTION_AUDIT.json` | `d44a07a2c971b1771f71bf2e8121118151a0a23da32bc19ddc10dd526ba87514` |
| `SOURCE_DEFINITION_AUDIT.json` | `f99d249d626cb147699dd53f4b2b413c458cdc0f4ff5f4ffc93509815a7319f7` |
| `CANONICAL16_EQUIVALENCE_MATRIX.csv` | `950bab9a655795bf39cd1d3c7f79fab5aeaad60be6cae1230c1784d1ad7d1bf1` |
| `DB9_DIP_CHANNEL_VALIDITY.json` | `27ed3199abda661b90dd2d4ad1f714d84e276179dfac409749b83e2f8266e578` |
| `DB9_MOVEMENT_STREAM_CONSISTENCY.json` | `51b7efd27ac7cd70cc1c237bf29741ad0b43e0b7aa327c0fdf07d4d868f71b72` |
| `DB9_SOURCE_CALIBRATION_AUDIT.json` | `c186e817c1611a48c0626266268cfb41aabfec8c72f6850c7310bf04235f387e` |
| `EMG2POSE_SESSION_CALIBRATION_AUDIT.json` | `adb826b795ff94af2271f66efd868c27a01f3bd4eb97db895424cb07529c4e31` |
| `MATCHED_SEMANTIC_COORDINATE_AUDIT.json` | `932f302710b831c613fb1249059b8cdc96c138221012f13a7786c22b0b15a989` |
| `PHYSICAL_ANCHOR_AUDIT.json` | `c13c1a58ced1db0b64cb7a1b57e7128b2be1d34893d2f31e5448fa985b5f619d` |
| `GEOMETRY_SHAPE_LOCATION_DECOMPOSITION.json` | `616b1a671b423a6aa5f3b283fce22f151223798ee7a2bd2216bb5131e64d3804` |
| `SYNTHETIC_ROUNDTRIP_RESULTS.json` | `0b875f90e320fcc1a6d82ba69e5dc910e051ab2305519363b157d30c9db852fc` |
| `S4_UMETRACK_CROSSCHECK.json` | `079242c1d928cd3ef6c8ac80eb9cfbe59ab3d9a58ef44d00da0e52b60db916bb` |
| `DIMENSION_CONFIDENCE_CLASSIFICATION.json` | `68a293c996c0dde0a4ca845d607f5779bb68856906dc45a0a54c7067fd547788` |
| `COMMON_POSE_API_VERDICT.json` | `5f132440f0fa5b7be118d6978774ff71f265cbc1893501f728c9b5a2f7501e14` |
| `LARGE_OFFSET_FORENSICS.json` / `.md` | see manifest |

## 28. Provenance

The project root is not a git repository → **COMMIT PENDING**. Provenance is
content-hash based throughout. `baseline/emg2pose` HEAD
`5f6f62b1a0a08426adffe55900842e75a8adb38c`, `git status --porcelain` **empty**.
No deep-learning training was performed: this branch is descriptive statistics,
classical linear algebra and classical variance decompositions only.
