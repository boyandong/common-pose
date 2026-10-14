# Supplemental segmented source transport — 2026-10-10

Authorized successor: COMMON-POSE-CONFIRMATION-20261010-TRANSPORT-DIAGNOSIS.
The human authorized same-member execution/transport repair in the successor.
Original acquisition, frozen scientific protocol and both failed attempts remain
intact. This amendment changes transport only, before any N80 prediction/effect.

Verified diagnosis: 664 complete local files / 11,792,195,984 bytes rehashed PASS;
remote frozen dependencies, numerical versions, eight threads and upstream tree
PASS; no qualification or inference stage dispatched. Nine retained partials
were probed read-only: all eight nonempty tails match official exact Range/ETag;
the ninth is empty. Small 256KiB ranges completed in approximately 2–11 seconds.
On the second failed member, a read-only 512KiB prefix from its remaining 5,947,456
byte request took 6.593s; from a 4MiB request it took 2.282s. These observations
do not establish the historical network root cause. Tiny-progress socket waits
and a cumulative 900s member deadline remain a working diagnosis.

Supplemental implementation uses at most 4MiB per exact Range; 10s socket timeout,
120s elapsed deadline per request, eight finite attempts per fixed segment, eight
workers. `read1` exposes received byte progress. Successful segments advance the
same retained partial; retries validate its exact 4096-byte tail. No cumulative
900s member deadline rejects an otherwise progressing member. A segment with
exhausted retries fails the lane with a terminal receipt, preserving all bytes.

Every request preserves the official URL, If-Match/ETag, 206 status, exact
Content-Range and additionally checks Content-Length and identity encoding.
Whole-file length and SHA256, immutable source receipts, remote full hashes and
qualification still gate inference. Complete old receipts retain their producer
hash; new receipts identify the supplemental runner. No deletion, replacement,
interpolation, scientific method or statistic change. The sole existing uploader
continues; the original sealed supervisor uses freshly observed launch handles.

See SUCCESSOR_PREFLIGHT_TRANSPORT_DIAGNOSIS_20261010.json and
SUCCESSOR_RANGE_SIZE_COMPARISON_20261010.json. These are transport evidence,
not scientific qualification, new-user results or full-goal completion.
