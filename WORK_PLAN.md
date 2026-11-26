# Work Plan

Roadmap generated from GitHub label state by the Guide triage role. Only the
region between the markers is machine-generated and overwritten each time.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#98**: spec: re-anchor the local ngspice pin to 47 and document its simulation evidence

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#30**: T1 item 2 (layout): generated detector layout with area recorded

## Important

`loom:important`; taken before unlabelled work.

- **#35**: T1 item 6 (Monte Carlo): tb_threshold_mc klt yield campaign on threshold accuracy (row 5)
- **#83**: Threshold reference drifts into the LDO ±2% window at a 3.63 V detector supply, so the detector flags continuously at a nominal rail
- **#87**: sim/toolchain.json pins ngspice 46 but the host runs 47p1, and four benches' numbers move
- **#167**: Reduce trip-point mismatch through ladder and comparator input-pair sizing
- **#177**: Collect the code-00 baseline and input-pair trial on a batch submit host

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#83**: Threshold reference drifts into the LDO ±2% window at a 3.63 V detector supply, so the detector flags continuously at a nominal rail

## In Progress

Issues currently being built (`loom:building`).

_None._

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#98**: spec: re-anchor the local ngspice pin to 47 and document its simulation evidence

## Proposed

Issues carrying `loom:curated`.

- **#30**: T1 item 2 (layout): generated detector layout with area recorded *(curated)*
- **#35**: T1 item 6 (Monte Carlo): tb_threshold_mc klt yield campaign on threshold accuracy (row 5) *(curated)*
- **#83**: Threshold reference drifts into the LDO ±2% window at a 3.63 V detector supply, so the detector flags continuously at a nominal rail *(curated)*
- **#87**: sim/toolchain.json pins ngspice 46 but the host runs 47p1, and four benches' numbers move *(curated)*
- **#167**: Reduce trip-point mismatch through ladder and comparator input-pair sizing *(curated)*
- **#168**: Measure and reduce the systematic sf/fs trip-point spread *(curated)*

## Proposed (Architect / Hermit)

- **#163**: Remove ROADMAP.md status sections: a stale hand-kept copy of the signoff manifest and work plan *(hermit)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 1 |
| Very important | 1 |
| Important | 5 |
| Ready (`loom:issue`) | 1 |
| In Progress (`loom:building`) | 0 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 1 |
| Curated | 6 |
| Architect / Hermit proposals | 1 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
