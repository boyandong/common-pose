# Dataset access decision — emg2pose full dataset (Session 1)

**Date:** 2026-09-17
**Status:** ⏸️ **LOCAL DOWNLOAD PAUSED BY PI — AWAITING SERVER PATH**
**Lane:** Session 1 (full dataset acquisition + data-directory organization)

---

## PI DECISION (2026-09-17)

> 暂停在本机继续下载完整 431 GiB 数据集，**不将 Session 1 降级为子集任务**。
> 保留"完整 emg2pose 数据集获取与管理"职责。当前先完成并验证：官方数据源、
> 下载脚本、断点续传、完整性校验、目录结构、split/metadata 解析、预计最终磁盘
> 需求，并生成**可直接迁移到远程服务器执行的一键下载方案**。
> 不要重复 Session 3 的 priority subset 下载，也不要因为本机空间不足改变完整
> 数据集最终目标。等 PI 之后提供具有足够磁盘空间的服务器路径后，再直接在远程
> 服务器继续完整下载。当前阶段完成后停止等待，**不要继续占用本机空间或尝试绕过
> 官方限制**。

**Consequences I am operating under:**

* Scope stays **full dataset** — this is not descoped to a subset.
* **No** further consumption of local disk for dataset acquisition.
* **No** attempts to circumvent official distribution limits.
* **No** duplication of Session 3's priority-subset lane.
* This stage is complete; I am holding until a server path is provided.

Everything the PI asked for in this stage was completed and verified — see
`docs/SERVER_ACQUISITION_RUNBOOK.md` for the one-command server plan, and
"Current verified state" below for what was run.

---

## What I did

1. Located and verified the official source, official download method, exact
   object sizes, and the official per-file schema.
2. Measured local disk capacity and real network throughput to the official host.
3. Built and tested a resumable downloader, a space-safe resumable tar extractor,
   an HDF5 inspector, and an integrity verifier (`data/tools/`).
4. Recovered the **official metadata CSV, verified bit-identical to the official
   S3 ETag MD5**, and derived all dataset statistics from it.
5. Verified the real data end-to-end: 30 official HDF5 files opened and validated.

## What I found

### 1. The dataset cannot fit on this machine — hard stop

| | |
|---|---|
| Official full dataset (`emg2pose_dataset.tar`) | **462,824,048,640 B = 431.04 GiB** (VERIFIED via HTTP HEAD) |
| Extracted tree | ~431 GiB (uncompressed tar ⇒ payload ≈ tar size) |
| Official workflow peak requirement (tar + extracted together) | **~862 GiB** |
| Total free space, all local volumes | **280.07 GiB** (C: 14.45 + D: 77.43 + E: 188.19) |
| Largest single volume free | 188.19 GiB (E:) |
| **Shortfall** | **~582 GiB** |

This is not a close call, and it is what the session brief anticipated
("如果空间不足，停止完整下载并报告"). **No bytes of the full dataset were
downloaded**, and nothing was written in a way that risks filling a disk.

### 2. Even with infinite disk, this network path cannot deliver it

Measured with `curl` against the exact official URL (logged in
`logs/download_full/speedtest_*.txt`):

| Probe | Result |
|---|---|
| Target host `fb-ctrl-oss.s3.amazonaws.com`, 200 MB range requested | **190,963 B in 180 s ≈ 1.06 KB/s** |
| Target host, 1 MiB range | **469,473 B in 60 s ≈ 7.8 KB/s** |
| Cloudflare control, 10 MB | **10,485,760 B in 46.7 s ≈ 224 KB/s** |

The local link is not the problem — the control transfer ran ~29× faster. The
China→`fb-ctrl-oss` S3 path specifically is degraded. Projected transfer time for
431 GiB:

| Scenario | Time |
|---|---|
| Measured typical (7.8 KB/s) | **~685 days** |
| Best single-stream observed (~20 KB/s) | ~268 days |
| Optimistic 32 parallel streams × 20 KB/s = 640 KB/s | ~8.2 days |
| (Reference: a 100 Mbit/s link) | 10.3 hours |

The official host serves one monolithic 431 GiB tar and the bucket **denies
listing (HTTP 403)**, so there is no official way to fetch a subset. Session 3's
tar-offset-index lane is the only practical way to pull individual sessions over
this path.

### 3. Two environment constraints that affect everyone

* **h5py cannot open files under a non-ASCII path on this machine.**
  `sys.getfilesystemencoding()` is `utf-8`, but h5py encodes filenames with
  `mbcs` → `UnicodeEncodeError: 'mbcs' codec can't encode characters`.
  Since the project path contains `董伯言`, **every** h5py open fails.
  **Verified fix:** an ASCII junction —
  `cmd /c mklink /J <PROJECT_ROOT> "<WORKSPACE_ROOT>"`
  then access data as `<PROJECT_ROOT>\...`. Relative paths do **not** help, and
  `Path.resolve()` silently undoes the workaround by following the junction —
  a bug I hit and fixed in my own tooling. **This is a project-wide trap: any
  session that opens HDF5 files must go through `<PROJECT_ROOT>\`.**
* The full dataset belongs on a **remote/GPU server** anyway, because training is
  under a permanent remote-only constraint. On a well-connected server the same
  download takes hours, not years.

### 4. Dataset facts now VERIFIED (not documentation-derived)

From the official `metadata.csv`, MD5-confirmed against the S3 ETag
`c3f48fd51576fa7752d455f2751c8b99`:

| Property | Value |
|---|---|
| HDF5 session files | **25,253** |
| Users | **193** |
| Sessions | **751** |
| Stages | **29** |
| Rows by split | train 17,136 / test 6,167 / val 1,950 |

**Split semantics — this matters scientifically.** The `split` column alone is
misleading; the `generalization` column carries the real structure:

| generalization | test | train | val |
|---|---|---|---|
| `none` | 0 | 17,136 | 0 |
| `stage` (= held-out stage) | 3,539 | 0 | 0 |
| `user` (= held-out user) | 2,172 | 0 | 1,618 |
| `user_stage` (= both held out) | 456 | 0 | 332 |

Consequences for our EMG → finger-state → gesture-distribution work:

* **All 158 train users also appear in test.** A naive "test" evaluation therefore
  includes same-subject samples. Cross-subject claims must be computed on the
  `generalization ∈ {user, user_stage}` subsets only (2,628 test files), or they
  are not cross-subject claims.
* `val` shares **zero** users with `train`, so `val` is the cleaner
  cross-subject signal.
* The held-out *stage* axis (3,539 test files) is the cross-task axis — the one
  that speaks to whether a representation is gesture-general rather than
  memorizing the 29 known stages.
* Any single "emg2pose test accuracy" number reported without naming the
  generalization axis is not interpretable.

### 5. Content verified on real official files (30 files, all pass)

| Quantity | Measured |
|---|---|
| `sample_rate` attr | 2000.0 on 30/30 |
| Implied rate from timestamps | 2000.14 Hz |
| EMG channels | 16 on 30/30 |
| `joint_angles` dim | **20** on 30/30 (not 5!) |
| NaN in emg / joint_angles | 0 |
| File duration | 45.7 / 58.6 / 236.9 s (min / median / max) |
| **IK-failure rows** | **0.0% / 7.0% / 35.0% (min / median / max)** |

> The last row is the one to watch. Invalid poses are encoded as **all-zero
> joint-angle rows**, not NaN, and the median file has **7%** such frames (max
> 35%). A loader that treats zeros as poses will silently train on garbage. The
> official pipeline masks these via `emg2pose.utils.get_ik_failures_mask`.

---

## Current verified state

| Artifact | Location | Status |
|---|---|---|
| Official mini dataset (30 files, 611.78 MiB) + `metadata.csv` | `data/official/emg2pose_dataset_mini/` | **VERIFIED** — all 30 files pass integrity checks; metadata MD5 matches official ETag |
| Full dataset | — | **NOT DOWNLOADED — paused by PI pending server** |
| **One-click server orchestrator** | `data/tools/acquire_emg2pose_full.py` | **EXECUTED & VERIFIED** — full pipeline reconstructed the official mini archive 30/30 byte-identical |
| Resumable downloader | `data/tools/download_emg2pose_full.py` | **EXECUTED** — resume proven bit-identical to official ETag; idempotent on re-run |
| Space-safe tar extractor | `data/tools/extract_emg2pose_tar.py` | **EXECUTED** on the real mini tar |
| HDF5 inspector (h5py only) | `data/tools/inspect_emg2pose_hdf5.py` | **EXECUTED** on official file |
| Integrity verifier | `data/tools/verify_emg2pose_dataset.py` | **EXECUTED** — 30/30 pass, JSON report emitted |
| Dataset reference doc | `docs/EMG2POSE_DATASET_REFERENCE.md` | complete, all numbers measured |
| **Server runbook** | `docs/SERVER_ACQUISITION_RUNBOOK.md` | complete — one command, resumable, self-verifying |

### Pipeline verification, executed

The acquisition pipeline was not merely written — it was **run end-to-end against
the official archive** and checked for byte-identity:

| Test | Result |
|---|---|
| Resume engine, 2 partial runs then completion | MD5 `c3f48fd51576fa7752d455f2751c8b99` = official ETag → **bit-identical** |
| Re-run after completion | **0 segments** downloaded (idempotent) |
| Full orchestrator, 3 × 300 MiB windows | 30/30 files extracted, verifier exit 0 |
| Full orchestrator, 7 × 120 MiB windows @ 8 MiB requests | exit 0, 30/30 valid |
| **Byte-identity of every reconstructed file** | **30/30 SHA256-identical, 0 mismatches** |
| Bounded-disk behaviour | 617 MiB tar reduced to 1,024 B (zero padding) |

Three genuine bugs were found and fixed **because** the test was run rather than
assumed: remote-vs-local offset confusion after pruning, non-block-aligned prune
points (tar is a 512-byte-block format), and a bounded-reader offset desync. Each
would have silently corrupted a 431 GiB run. Details in the runbook §5.

Nothing was deleted except my own incomplete duplicate `metadata.csv` partial
(superseded by the MD5-verified official copy), plus scratch directories under
`logs/download_full/` created and removed by these tests.

---

## Why this is a decision for you, not for me

I can build the pipeline and document the data, and I did. What I cannot decide
is **where 431 GiB of research data should live** — that depends on hardware you
own that I cannot see, and it changes *what the downstream sessions can do*,
which is a research-scope question, not an engineering one. I am deliberately not
picking a lane that would silently re-scope Session 1 or collide with Sessions
2–4.

## Options (superseded by the PI decision above)

> The PI has selected the **server path**, which is option A below. The others are
> retained for the record only.

**A. Provision a remote server (recommended, SELECTED).** Provide the server path
(or SSH). I then, in one closed loop: download all 431 GiB, extract, and run the
verifier over all 25,253 files. One command is already written, tested, and
documented: `docs/SERVER_ACQUISITION_RUNBOOK.md`.

**B. Attach an external drive with ≥900 GiB free** (USB/HDD). Resumable
byte-budgeted runs. Caveat: at the measured ~8 KB/s this is months of wall-clock —
viable only if the network path is separately fixed.

**C. Descope Session 1 to "documented + verified subset".** *Rejected by the PI —
scope stays full dataset.*

**D. Investigate an alternative network route/mirror** (VPN, proxy, academic
mirror). Cheap to test; can be combined with A if the server link is also slow.

---

## Next action (when a server is available)

```bash
# copy data/tools/*.py to the server, then:
python acquire_emg2pose_full.py plan   --root /data/emg2pose   # confirm ≥480 GiB
python acquire_emg2pose_full.py run    --root /data/emg2pose   # resumable
python acquire_emg2pose_full.py verify --root /data/emg2pose   # all 25,253 files
```

Expected final state: `25,253` files, `files_failed: 0`, `orphans: 0`,
`missing: 0`. Then the full dataset is available for the modelling sessions.

---

## What I have NOT done (and will not without instruction)

* No model training of any kind (also prohibited locally by standing policy).
* No modification of the official baseline code.
* No further local disk consumption for dataset acquisition.
* No attempt to circumvent the official distribution limits (no unofficial
  mirrors, no scraping the tar around the vendor's endpoint).
* No duplication of Session 3's priority-subset lane.
* No gesture-semantic derivation from the 20-D joint angles — whether "5-finger
  continuous joint state" is derived via UmeTrack FK, or read directly from a
  subset of the 20 axes, is a **representation-semantics decision** that belongs
  to you, and it gates Session 3 and the modelling sessions.
* No writes into `data/priority_pose_subset/`, `baseline/`, or `checkpoints/`
  (other sessions' lanes).
