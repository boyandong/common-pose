# Common Pose

Current research code, frozen evaluation results, and the **CommonPose EMBC 2027 V5.2 submission candidate** (2026-10-14).

Common Pose tests decision preservation when an EMG-estimated pose replaces a measured pose at the input of an unchanged downstream classifier. A **Flip** is a difference between the two model outputs; it is not independently labelled action error.

## Latest manuscript

- [English five-page PDF](docs/papers/20261014_v5_2_submission_candidate/output/pdf/CommonPose_EMBC2027_V5_2_EN.pdf)
- [Chinese review PDF](docs/papers/20261014_v5_2_submission_candidate/output/pdf/CommonPose_EMBC2027_V5_2_ZH.pdf)
- [Complete English LaTeX](docs/papers/20261014_v5_2_submission_candidate/CommonPose_EMBC2027_V5_2_EN.tex): all prose, equations, Table I and ten references inline; vector figures and IEEE class included alongside it.
- [Revision notes and build instructions](docs/papers/20261014_v5_2_submission_candidate/README.md)

The candidate has four technical pages and a references-only fifth page. It has not been submitted or approved by the supervisor. The current author information is Boyan Dong, Southeast University.

## Latest evidence

- [Participant intervals, matched controls and six source-consumer reproductions](experiments/paper_evidence/local_closeout_20261014/LOCAL_REPORT.md)
- [Server feature/field ablations, lag/window sensitivity and measured computational costs](experiments/paper_evidence/server_closeout_20261014/COMPUTATIONAL_CLOSEOUT_REPORT.md)
- [Complete signed field-ablation results](experiments/paper_evidence/server_closeout_20261014/verified_remote/field_delivery/results/score_field_ablation/REPORT.md)
- [No-retraining provenance, public-recipe subgroup and interface audits](experiments/paper_evidence/no_retrain_closeout_20261014/REPORT_ZH.md)
- [Original 27-goal review ledger](docs/reviews/20261014_embc_no_supplement_audit/ALL_27_REVISION_GOALS_AND_FINDINGS.md)

At N80 and 30% offline retention, Full/U reduced overall disagreement relative to Boundary across six frozen consumers. The same 79 evaluable SHOW participants showed an overall reduction of 2.608 percentage points and a class-balanced reduction of -20.880 points (a deterioration). DB9-posture class support fell from 22/80 participants without rejection to 3/80 under Full/U selection. Reported intervals are descriptive participant-level paired intervals; correlated comparisons are not independent confirmations.

## Evidence boundaries

Actual upstream checkpoint training membership, common physical pose zeros, independent residual synchronization, target-action correctness, and deployable causal online rejection remain unverified. Public training-recipe overlap is not proof of actual checkpoint leakage or unseen-user generalization. Exploratory variants were evaluated on previously examined cohorts. Source validation does not validate target semantics.

## Reproduction and contents

The repository includes analysis code, frozen configurations, aggregate and participant-level result tables, verification records, and manuscript plotting inputs. Download restricted datasets and the upstream estimator separately from official sources; raw signals, source pose arrays, model weights, credentials, runtime libraries and system fonts are not mirrored here.

The older DB9 research record remains available under the preserved frozen lanes and [historical README](docs/archive/README_BEFORE_V5_2.md). Dated reports describe their state at creation; later closeout reports and V5.2 are the current writing/evidence entry points.

Core requirements: `python -m pip install -r requirements.txt`. The current API-contract checks passed 51 tests. Plotting additionally needs matplotlib; manuscript compilation needs a LaTeX engine. See the manuscript build instructions above.

## Availability and licensing

This is the current CommonPose repository replacing `boyandong/commonpose-v1` at the owner's request. Repository-wide licensing remains pending provenance review; no new blanket licence is asserted. See [licensing notes](docs/licensing.md). IEEE template files retain their embedded licence notices. Scientific source hashes and published-copy hashes are recorded in [publication provenance](provenance/PUBLICATION_20261014.json); only machine-local path strings are replaced in public copies, with original local artifacts preserved.
