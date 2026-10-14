# Mutable local progress replacement repair — 2026-10-10

Direct human authorization after the incident: `继续上传`. This authorizes
same-cohort upload resumption and the necessary pure execution repair in this
session. The prior forensic handover and failed attempts remain intact. The human
also requested reduced consumption and checks after completion: use passive exit
signals, not model progress polling. This request does not itself restart inference.

Known failure: original V2 uploader exited because local `os.replace` of its
mutable progress JSON received WinError5. Exact original lock owner is UNKNOWN.
V3 uses a separate dated, sealed implementation. It preserves original V2 SSH
reconnection and original per-file copy/full-local-and-remote-SHA256 functions,
official members, scientific protocol, qualification and immutable receipts.

Only replacement of the mutable progress snapshot gains finite retries:
Windows errors5/32/33, at most20 attempts with50ms delays (at most950ms sleep).
Other errors fail immediately; permanent denial preserves the prior snapshot
and temporary attempt, then stops with a separate immutable terminal receipt.
Original frozen runtime_common.py is unchanged; its immutable save() is unchanged.

Control tests cover transient denial, bounded permanent denial, unrelated I/O
failure, and a real Windows reader opened without delete sharing. This establishes
that the remedy handles that mechanism; it does not identify the historical lock
owner. Existing sources and prior hash receipts are retained. One uploader only,
old handle reverified missing before launch. Controller remains stopped until a
separately valid continuation reaches the original scientific gates.
