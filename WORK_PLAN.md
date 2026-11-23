# Work Plan

Roadmap generated from GitHub label state by the Guide triage role. Only the
region between the markers is machine-generated and overwritten each time.

<!-- guide:plan-body:start -->
_Generated: 2026-11-23T01:30:00Z (snapshot; compare against live labels)_
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#98**: spec: re-anchor ngspice pin to 47 via DR-004, append records for three stale benches

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#30**: T1 item 2 (layout): generated detector layout with area recorded *(held)*

## Important

`loom:important`; taken before unlabelled work.

- **#29**: T1 item 9 (testbenches shipped): the eight planned row benches, inventory and --attest 9 *(held)*
- **#35**: T1 item 6 (Monte Carlo): tb_threshold_mc klt yield campaign on threshold accuracy (row 5) *(held)*
- **#83**: Threshold reference drifts into the LDO ±2% window at a 3.63 V detector supply, so the detector flags continuously at a nominal rail
- **#87**: sim/toolchain.json pins ngspice 46 but the host runs 47p1, and four benches' numbers move

## Ready

Human-approved issues (`loom:issue`) ready for implementation — excluding held (`loom:blocked`/`loom:operator`/`loom:frozen`), `loom:building`, and issues closed by an open `loom:pr` PR (listed under Approved).

_None._

## In Progress

Issues currently being built (`loom:building`).

_None._

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#93**: measure the threshold reference's supply sensitivity across row 2's box and decide its topology — closes #83

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#98**: spec: re-anchor ngspice pin to 47 via DR-004, append records for three stale benches — closes #87

## Proposed

Issues carrying `loom:curated`.

- **#29**: T1 item 9 (testbenches shipped): the eight planned row benches, inventory and --attest 9 *(curated)* *(held)*
- **#30**: T1 item 2 (layout): generated detector layout with area recorded *(curated)* *(held)*
- **#35**: T1 item 6 (Monte Carlo): tb_threshold_mc klt yield campaign on threshold accuracy (row 5) *(curated)* *(held)*
- **#83**: Threshold reference drifts into the LDO ±2% window at a 3.63 V detector supply, so the detector flags continuously at a nominal rail *(curated)*
- **#87**: sim/toolchain.json pins ngspice 46 but the host runs 47p1, and four benches' numbers move *(curated)*

## Proposed (Architect / Hermit)

- **#81**: Wire up or drop tests/test_item10_coverage.py: an inventory-completeness guard no runner executes *(hermit)* *(held)*
- **#91**: Remove the redundant 'Validate committed JSON parses' step from signoff.yml: the next step already fails on every case it guards *(hermit)* *(held)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 1 |
| Very important | 1 |
| Important | 4 |
| Ready (`loom:issue`, net of holds/building/merge-pending) | 0 |
| In Progress (`loom:building`) | 0 |
| PRs awaiting review | 1 |
| Approved PRs awaiting merge | 1 |
| Curated | 5 |
| Architect / Hermit proposals | 2 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
