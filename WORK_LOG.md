# Work Log

Chronological record of merged PRs and closed issues, maintained by the Guide
triage role. Newest first.

### 2026-10-23

- **PR #20**: feat(sim): add rail-model check bench (envelope bounds + LDO netlist form)
- **PR #19**: feat: add threshold reference schematic with select and ref-droop benches
- **Issue #17** (closed): Rail model bench: netlist-derived LDO rail and behavioural envelope, checked against the interface rows (sim/tb_rail_model_check)
- **Issue #18** (closed): Threshold reference and 4-level tap network: first schematic with tb_ref_droop and tb_threshold_select at tt

### 2026-10-21

- **PR #15**: Bump Repo Skills 0.24.3 -> 0.24.7

### 2026-10-20

- **PR #8**: docs: propose droop-detector target spec, DR-001 and reuse ledger
- **PR #11**: feat(ci): run ngspice smoke from check:ci, check:all and test
- **PR #6**: ci: grade T1 tier state with klt signoff against a committed verdict of record
- **PR #13**: fix(sim): check each smoke result key separately
- **Issue #2** (closed): Draft and ratify the target spec
- **Issue #9** (closed): Demonstrate signoff CI gate going red on a stale verdict record
- **Issue #10** (closed): Wire check:ci to sim/smoke/run.sh instead of placeholder exit 0
- **Issue #5** (closed): T1 item 10: add CI and a klt signoff block manifest as the verdict of record
- **Issue #12** (closed): Fix vacuous tphl/tplh check in sim/smoke/run.sh (fail-open despite fail-closed claim)

### 2026-10-17

- **PR #7**: feat(sim): pin PDK revision and add fail-closed ngspice smoke bench
- **PR #1**: chore(loom): Install Loom 0.19.1181
- **Issue #4** (closed): Pin the sky130 PDK and ngspice toolchain and commit a smoke simulation (T1 item 9 groundwork)
