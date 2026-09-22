# SYNC AUDIT

**Frozen plan SHA-256:** `fba2b20623392dd809d5ed28c7850387acc721e9a91ff1611e7fba0d89fc889d`  **Commit:** COMMIT PENDING

Scope: whether a released stream may be treated as independent samples in time, and what its real update rate is.

---

## 1. MyoKi - ONE declared grid, SIX different real rates

The `.mat` carries a single scalar `frequency` field. This audit measured the number of rows that differ from their immediate predecessor for every stream of the official synchronisation recording.  `[EMPIRICAL]`

| stream | rows on the grid | rows that actually change | distinguishable update rate | representation inflation | duplicate-row share |
|---|---|---|---|---|---|
| `glove` | 83267 | 1480 | 35.548 Hz | **56.26x** | 98.22% |
| `glove_calibrated` | 83267 | 1480 | 35.548 Hz | **56.26x** | 98.22% |
| `emg` | 83267 | 83266 | 1999.978 Hz | **1.00x** | 0.00% |
| `acc` | 83267 | 6163 | 148.030 Hz | **13.51x** | 92.60% |
| `gyro` | 83267 | 6163 | 148.030 Hz | **13.51x** | 92.60% |
| `fmg` | 83267 | 3589 | 86.205 Hz | **23.20x** | 95.69% |
| `task` | 83267 | 1 | 0.024 Hz | **83267.00x** | 100.00% |
| `timestamp` | 83267 | 83266 | 1999.978 Hz | **1.00x** | 0.00% |

* declared `frequency` = **2000 Hz**; measured grid rate = 2000.002 Hz
* The file is on ONE declared 2000 Hz grid. Only the EMG stream actually changes at that rate. The kinematic stream changes ~56x less often, so ~98% of its rows are exact copies of the preceding row. Any statistic that treats kinematic rows as independent inflates its sample size by roughly two orders of magnitude and makes every interval spuriously narrow.
* lower-bound caveat: the distinguishable-state count is a LOWER bound on the true update rate: two consecutive acquisitions may carry identical values and be merged. The paper reports a glove acquisition rate of 80.85 +/- 0.16 Hz across participants, which is consistent with an effective independent-sample count between the distinguishable-state rate and that figure - and NOT with 2000 Hz either way.

### 1.1 What a user must do

1. Never compute a kinematic rate, a window or an interval on the raw 2000 Hz rows. De-duplicate to distinguishable states first, or resample explicitly.
2. The paper's own alignment is zero-order hold: *'Power spectral density (PSD) comparison between raw data (blue line) and upsampled data using zero-order hold (ZOH)'*, and the paper itself warns that *'zero-order hold (ZOH) upsampling may have introduced minor timing inaccuracies due to frequency mismatch between the source and target sampling rates'*. `[DOC]`
3. The paper reports a glove acquisition rate of 80.85 +/- 0.16 Hz across participants, which is consistent with an effective independent-sample count between the 35.5 Hz measurable lower bound and 80.85 Hz - and **not** with 2000 Hz under any reading.

### 1.2 Reported cross-modality delays `[DOC]`

The paper's own synchronisation validation reports EMG->FMG = 2.22 ms, FMG->Motion = 12.66 ms, EMG->Motion = 14.89 ms, and explicitly cautions that the absolute delays differ from the literature and that ZOH upsampling may have introduced timing inaccuracies. This audit did **not** re-measure them: it holds one recording.

---
## 2. KIN-MUS

* released grid: no released column is the derived DIP of any other column, so the 18-column block is the 22-angle pipeline with the four DIPs REMOVED (and the two wrists kept), not the first 18 angles
* implied rate (median over 1716 containers) = 100.0000 Hz; documented rate = 100 Hz; non-monotonic timestamp trials: 0
* every container is released ONCE per (subject, ADL, phase); there is no upsampled grid and therefore no representation inflation in this release. `[EMPIRICAL]`

---
## 3. KINE-ADL

* rate: degrees; 'Joint angles (deg)' in the guide data-structure header [DOC] - 100 Hz per the paper and the guide `[DOC]`
* the corpus was not downloaded, so no independent rate measurement is possible here. `[UNRESOLVED]`

