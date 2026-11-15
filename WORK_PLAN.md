# Work Plan

Roadmap generated from GitHub label state by the Guide triage role. Only the
region between the markers is machine-generated and overwritten each time.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#93**: measure the threshold reference's supply sensitivity across row 2's box and decide its topology
- **#98**: spec: re-anchor ngspice pin to 47 via DR-004, append records for three stale benches

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#30**: T1 item 2 (layout): generated detector layout with area recorded

## Important

`loom:important`; taken before unlabelled work.

- **#29**: T1 item 9 (testbenches shipped): the eight planned row benches, inventory and --attest 9
- **#35**: T1 item 6 (Monte Carlo): tb_threshold_mc klt yield campaign on threshold accuracy (row 5)
- **#83**: Threshold reference drifts into the LDO ±2% window at a 3.63 V detector supply, so the detector flags continuously at a nominal rail
- **#87**: sim/toolchain.json pins ngspice 46 but the host runs 47p1, and four benches' numbers move

## Ready

Human-approved issues ready for implementation (`loom:issue`).

_None._

## In Progress

Issues currently being built (`loom:building`).

- **#83**: Threshold reference drifts into the LDO ±2% window at a 3.63 V detector supply, so the detector flags continuously at a nominal rail
- **#87**: sim/toolchain.json pins ngspice 46 but the host runs 47p1, and four benches' numbers move
- **#104**: No CI guard re-derives design/row5-error-budget.md's tables from the committed records
- **#106**: Narrow design/README.md's supersession rule: it is a one-way hash test, and two benches emit no hash at all

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#93**: measure the threshold reference's supply sensitivity across row 2's box and decide its topology
- **#98**: spec: re-anchor ngspice pin to 47 via DR-004, append records for three stale benches
- **#111**: fix: state record supersession as one-way; emit hashes for smoke and flag_logic wrapper

## Proposed

Issues carrying `loom:curated`.

- **#29**: T1 item 9 (testbenches shipped): the eight planned row benches, inventory and --attest 9 *(curated)*
- **#30**: T1 item 2 (layout): generated detector layout with area recorded *(curated)*
- **#35**: T1 item 6 (Monte Carlo): tb_threshold_mc klt yield campaign on threshold accuracy (row 5) *(curated)*
- **#83**: Threshold reference drifts into the LDO ±2% window at a 3.63 V detector supply, so the detector flags continuously at a nominal rail *(curated)*
- **#87**: sim/toolchain.json pins ngspice 46 but the host runs 47p1, and four benches' numbers move *(curated)*
- **#104**: No CI guard re-derives design/row5-error-budget.md's tables from the committed records *(curated)*
- **#106**: Narrow design/README.md's supersession rule: it is a one-way hash test, and two benches emit no hash at all *(curated)*
- **#110**: Item-10 coverage guard: `sim/**/*.sh` misses a script placed directly in sim/ or verification/ *(curated)*
- **#114**: No guard keeps pdk_record_header's ngspice_threads: field (or its cross-file coupling) from silently regressing *(curated)*

## Proposed (Architect / Hermit)

- **#81**: Wire up or drop tests/test_item10_coverage.py: an inventory-completeness guard no runner executes *(hermit)*
- **#91**: Remove the redundant 'Validate committed JSON parses' step from signoff.yml: the next step already fails on every case it guards *(hermit)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 2 |
| Very important | 1 |
| Important | 4 |
| Ready (`loom:issue`) | 0 |
| In Progress (`loom:building`) | 4 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 3 |
| Curated | 9 |
| Architect / Hermit proposals | 2 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
