# Work Plan

Roadmap generated from GitHub label state by the Guide triage role. Only the
region between the markers is machine-generated and overwritten each time.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

_None._

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#30**: T1 item 2 (layout): generated detector layout with area recorded

## Important

`loom:important`; taken before unlabelled work.

- **#29**: T1 item 9 (testbenches shipped): the eight planned row benches, inventory and --attest 9
- **#35**: T1 item 6 (Monte Carlo): tb_threshold_mc klt yield campaign on threshold accuracy (row 5)
- **#76**: Row 5 error budget: split the threshold trip-point error by contributor from the committed records
- **#77**: Comparator path misses the row 6 latency target at a 2.97 V detector supply
- **#83**: Threshold reference drifts into the LDO ±2% window at a 3.63 V detector supply, so the detector flags continuously at a nominal rail
- **#87**: sim/toolchain.json pins ngspice 46 but the host runs 47p1, and four benches' numbers move

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#80**: Wire tests/test_item10_coverage.py into CI: the attest-inventory completeness guard never runs
- **#86**: Finish the record-header consolidation: tb_rail_model_check hand-rolls pdk_record_header and records one wrapper hash instead of 14 model-file hashes

## In Progress

Issues currently being built (`loom:building`).

- **#77**: Comparator path misses the row 6 latency target at a 2.97 V detector supply
- **#78**: README and design/README.md still describe the block as before the comparator, filter and flags landed
- **#85**: Dedupe the ngspice thread-count knob: one host-concurrency policy in sim/lib, not 13 scattered settings

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#82**: docs: refresh README status prose to the five netlisted blocks and 11 row benches
- **#84**: fix: resize comparator and flag_logic output path to meet row 6 at 2.97 V
- **#88**: sim: move the ngspice thread count into sim/lib/ngspice_run.sh and force it per run

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

_None._

## Proposed

Issues carrying `loom:curated`.

- **#29**: T1 item 9 (testbenches shipped): the eight planned row benches, inventory and --attest 9 *(curated)*
- **#30**: T1 item 2 (layout): generated detector layout with area recorded *(curated)*
- **#35**: T1 item 6 (Monte Carlo): tb_threshold_mc klt yield campaign on threshold accuracy (row 5) *(curated)*
- **#76**: Row 5 error budget: split the threshold trip-point error by contributor from the committed records *(curated)*
- **#77**: Comparator path misses the row 6 latency target at a 2.97 V detector supply *(curated)*
- **#78**: README and design/README.md still describe the block as before the comparator, filter and flags landed *(curated)*
- **#79**: Dedupe the ratified four-level threshold table copied into 12 sites across the sim benches *(curated)*

## Proposed (Architect / Hermit)

- **#79**: Dedupe the ratified four-level threshold table copied into 12 sites across the sim benches *(hermit)*
- **#81**: Wire up or drop tests/test_item10_coverage.py: an inventory-completeness guard no runner executes *(hermit)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 1 |
| Important | 6 |
| Ready (`loom:issue`) | 2 |
| In Progress (`loom:building`) | 3 |
| PRs awaiting review | 3 |
| Approved PRs awaiting merge | 0 |
| Curated | 7 |
| Architect / Hermit proposals | 2 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
