# DIP HAND-SIZE HYPOTHESIS

**Frozen plan SHA-256:** `4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793`

## Official warning `[OFFICIAL]`

> 'DIP sensors provide reliable angles when subject hand size is big (i.e. when the glove fits properly to the hand). Instead, they may provide partial results when the hand of the subject is small. Therefore, attention should be taken when using their information.'  - Ninapro DB9 instructions

## Metadata availability

Released subject metadata columns: `['file', 'subject', 'handedness', 'sex', 'age', 'height_cm', 'weight_kg']` (0 subjects parsed from the official Ninapro subject table).
Hand length or width published: **False**.

**HAND_SIZE_HYPOTHESIS_NOT_TESTABLE_FROM_RELEASED_METADATA - the released subject table carries sex, handedness, age, height and weight only; no hand length or width is published.  Height is used as the only available substitute and sex as an explicitly labelled exploratory secondary proxy.**

## Substitution analysis (height as the only available size proxy)

| channel | n with metadata | median Î”raw | subjects positive | subjects negative | Pearson r (height vs Î”angle) | slope (deg/cm) |
|---|---|---|---|---|---|---|
| `DIP2` | 0 | +65.65 | 28 | 9 | n/a | n/a |
| `DIP3` | 0 | -32.58 | 2 | 35 | n/a | n/a |
| `DIP4` | 0 | -8.88 | 8 | 28 | n/a | n/a |
| `DIP5` | 0 | -9.12 | 5 | 32 | n/a | n/a |

A correlation found here classifies the failure; it is never used to repair, rescale or re-sign any channel.

## What the analysis can and cannot settle

* It can classify the DIP failure as universal vs subset-only vs size-dependent.
* It cannot repair a channel, and it is not used to do so.
* Sex is available but is **not** used as a hand-size ground truth; height is the only continuous size proxy the release supports, and it is a weak one.
