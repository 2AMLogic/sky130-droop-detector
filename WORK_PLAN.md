# Work Plan

Roadmap generated from GitHub label state by the Guide triage role. Only the
region between the markers is machine-generated and overwritten each time.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#93**: measure the threshold reference's supply sensitivity across row 2's box and decide its topology
- **#98**: spec: re-anchor ngspice pin to 47 via DR-004, append records for three stale benches
- **#125**: chore(loom): resync installed Loom to v0.19.1302

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

- **#116**: Wrapper record: inherited provenance block runs into the [AB] sequence-check lines; narrow design/README's sibling-key gloss
- **#127**: signoff.yml step comment still says the item-10 coverage guard covers only sim/ and verification/

## In Progress

Issues currently being built (`loom:building`).

_None._

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#93**: measure the threshold reference's supply sensitivity across row 2's box and decide its topology
- **#98**: spec: re-anchor ngspice pin to 47 via DR-004, append records for three stale benches
- **#125**: chore(loom): resync installed Loom to v0.19.1302

## Proposed

Issues carrying `loom:curated`.

- **#29**: T1 item 9 (testbenches shipped): the eight planned row benches, inventory and --attest 9 *(curated)*
- **#30**: T1 item 2 (layout): generated detector layout with area recorded *(curated)*
- **#35**: T1 item 6 (Monte Carlo): tb_threshold_mc klt yield campaign on threshold accuracy (row 5) *(curated)*
- **#83**: Threshold reference drifts into the LDO ±2% window at a 3.63 V detector supply, so the detector flags continuously at a nominal rail *(curated)*
- **#87**: sim/toolchain.json pins ngspice 46 but the host runs 47p1, and four benches' numbers move *(curated)*
- **#116**: Wrapper record: inherited provenance block runs into the [AB] sequence-check lines; narrow design/README's sibling-key gloss *(curated)*
- **#127**: signoff.yml step comment still says the item-10 coverage guard covers only sim/ and verification/ *(curated)*

## Proposed (Architect / Hermit)

- **#81**: Wire up or drop tests/test_item10_coverage.py: an inventory-completeness guard no runner executes *(hermit)*
- **#91**: Remove the redundant 'Validate committed JSON parses' step from signoff.yml: the next step already fails on every case it guards *(hermit)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 3 |
| Very important | 1 |
| Important | 4 |
| Ready (`loom:issue`) | 2 |
| In Progress (`loom:building`) | 0 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 3 |
| Curated | 7 |
| Architect / Hermit proposals | 2 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
