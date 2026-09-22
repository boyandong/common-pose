# S6 — LABEL DEFINITIONS

**Status:** frozen before annotation. Core reference for what each label means, in the terms
the frozen S4 renderer can actually show.

Every definition below is **palm-relative**. The 20-DOF emg2pose state contains no wrist or
forearm DOF — S4 passes `W = identity` by construction (S4 audit §7) — so a world-referenced
"up" is not representable and is never asked for.

**No definition depends on physical contact.** S4 has no force or soft-tissue model, and the
official 788-vertex mesh cannot resolve an adjacent-finger gap below ≈3.7 model units
(measured at the rest pose in the S4 audit §13). Apparent touching is therefore not evidence
of contact for any label.

---

## 1. PRIMARY semantic vocabulary — FIVE classes

These five are the pre-registered primary evaluation set, and only these five enter PRIMARY
semantic accuracy.

### CLASS 1 — thumb-up configuration (palm-relative)
**Choose when:** the thumb is **distinctly extended relative to the palm** — clearly away from
the palm plane and not folded across it — **while digits II–V are predominantly flexed/closed**.
**Do not choose** because the thumb points up in the world; there is no world reference in the
render. The decision is entirely about the thumb's configuration relative to *this* palm
together with a closed hand.
**Closest confusion:** CLASS 6 (fist). The discriminator is whether the thumb itself has a
distinct extended/abducted configuration, not whether the hand is closed.

### CLASS 2 — index + middle extended, others flexed
**Choose when:** index and middle are predominantly **extended**, ring and little predominantly
**flexed**, and the **thumb is predominantly flexed/closed**.
**Closest confusion:** CLASS 3 (which is the same finger pattern with the thumb extended/open)
and CLASS 7 (which has only the index extended).
**Read the proximal joints, not the tip gap:** index and middle tips are at or near contact in
≈44% of real frames, and the rest pose itself has an index–middle gap of only 2.75 units, so
"do the tips touch" is not usable evidence here.

### CLASS 3 — ring + little flexed, others extended
**Choose when:** ring and little are predominantly **flexed**, index and middle predominantly
**extended**, and the **thumb is predominantly extended/open**.
**Closest confusion:** CLASS 2. The discriminator is the *thumb* (flexed in 2, extended in 3)
plus which pair of fingers is closed.
**View requirement:** this class is the reason View B exists — the palmar view shows the ring
and little fingers imperfectly in some poses.

### CLASS 6 — fist
**Choose when:** digits II–V are predominantly **flexed into a closed-hand configuration**,
**and the thumb does not form the distinct extended-thumb configuration of CLASS 1**.
The thumb may lie across the closed fingers, rest against them, or be partly folded; what is
excluded is a distinctly extended/abducted thumb.
**Closest confusion:** CLASS 1.

### CLASS 7 — pointing index
**Choose when:** the **index is predominantly extended**, and **middle, ring and little are
predominantly flexed**.
**Closest confusion:** CLASS 2 (index *and* middle extended). The discriminator is the middle
finger's state.

---

## 2. DIAGNOSTIC-ONLY label

### CLASS 4 — thumb-opposition-like (DIAGNOSTIC ONLY — never in the primary metric)
Operational wording, to be used verbatim in the interface:

> **"Thumb positioned / opposed toward the little-finger base."**

**Choose when:** the thumb is carried **across the palm toward the ulnar (little-finger) side**,
so that its tip approaches the region of the little-finger base / palm's ulnar border.

Three restrictions, all of which are load-bearing:

1. **Not a contact claim.** The wording records *position*, not verified physical contact. No
   annotator is asked whether the thumb actually touches anything.
2. **Never in the primary metric.** Class 4 is reported separately, always, in every table.
   It is never pooled with classes 1/2/3/6/7 and never counted in "primary semantic accuracy".
3. **Its interpretation is handedness-sensitive and mapping-limited.** The S4 audit found the
   frozen DB9 movement 4 (thumb opposes little-finger base) does **not** render as true
   opposition when driven from the available glove kinematics, because the CyberGlove carries
   no thumb circumduction/opposition channel. Class 4 is retained here because a *human* can
   still judge the position from an emg2pose GT render — but that is exactly why it is kept
   out of the primary vocabulary rather than rescued into it.

---

## 3. Non-target labels — THREE distinct categories, never merged

These are not "other". They are three different statements and they are analysed separately.
Annotators must be able to choose each one, and the analysis plan keeps them apart.

| label | means | is the pose interpretable? | is the class knowable? |
|---|---|---|---|
| **UNKNOWN** | the posture **is** visually interpretable but does **not** match any target class | yes | yes — and the answer is "none of them" |
| **AMBIGUOUS** | the centre pose lies **between** classes, or is changing enough that one class is not defensible | yes | no |
| **UNJUDGEABLE** | the posture **cannot be confidently judged** because required information is not visible/represented by the render | no | no |

**Why they must not be merged.** UNKNOWN is a *substantive prevalence result* (this pose is
outside the vocabulary). AMBIGUOUS is a *category-boundary* statement. UNJUDGEABLE is a
*renderer/information* statement. Collapsing them would silently convert a renderer limitation
into a prevalence figure.

**UNJUDGEABLE is expected to be rare** on this corpus, because each window is gated to be
fully GT-valid, is shown as a 0.60 s animation with a pinned centre frame, and is rendered
from the two views the S4 audit established as minimally sufficient (`palm_flat` + `ulnar`).
A high UNJUDGEABLE rate is therefore a signal about the *renderer or the protocol*, not about
the data, and must be investigated as such rather than reported as a class.

---

## 4. Decision order (recommended, so the classes are applied consistently)

1. **Is the pose interpretable at all?** If required information is missing or illegible →
   **UNJUDGEABLE**. (Rare; use the animation and both views before choosing it.)
2. **Is the centre frame a single defensible posture**, rather than mid-transition or between
   two classes? If not → **AMBIGUOUS**.
3. **Does the posture match any of the six defined postures?** If not → **UNKNOWN**.
4. **Which one?** Apply the definitions above, using the closest-confusion discriminators
   (thumb state for 1 vs 6 and 2 vs 3; middle-finger state for 2 vs 7; which finger pair is
   closed for 2 vs 3).

Steps 1–3 before step 4 is deliberate: it prevents a forced choice between target classes when
the honest answer is one of the three non-target labels.

---

## 5. Interface label ids (stable machine names)

| id | group | interface key | enters primary metric |
|---|---|---|---|
| `CLASS_1` | primary | `1` | **yes** |
| `CLASS_2` | primary | `2` | **yes** |
| `CLASS_3` | primary | `3` | **yes** |
| `CLASS_7` | primary | `4` | **yes** |
| `CLASS_6` | primary | `5` | **yes** |
| `CLASS_4` | diagnostic | `6` | no — always reported separately |
| `UNKNOWN` | non-target | `7` | no |
| `AMBIGUOUS` | non-target | `8` | no |
| `UNJUDGEABLE` | non-target | `9` | no |

`CLASS_n` uses the **DB9 movement number** as the id (1, 2, 3, 4, 6, 7), which is why the ids
skip 5. The ids are stable across the two annotator packages; only the presentation *order*
differs between A and B.

Confidence is recorded separately on a 1–3 scale and is **never** used to remove a sample from
the primary analysis (see `FUTURE_ANALYSIS_PLAN.md` §6).
