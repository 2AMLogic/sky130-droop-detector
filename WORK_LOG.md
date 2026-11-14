# Work Log

Chronological record of merged PRs and closed issues, maintained by the Guide
triage role. Newest first.

### 2026-11-14

- **PR #75**: docs: roadmap as of 2026-11-13

### 2026-11-13

- **PR #73**: Bump Repo Skills 0.25.10 -> 0.26.1

### 2026-11-07

- **PR #72**: feat: run threshold-MC negative control in every mismatch section
- **PR #71**: Bump Repo Skills 0.25.1 -> 0.25.10

### 2026-11-06

- **PR #70**: refactor: share ngspice run and result-check helpers across sim bench drivers
- **PR #69**: fix: fail closed on unreadable netlist/checker paths in pdk_record_header
- **PR #67**: refactor: share the record-provenance header across 12 sim drivers
- **PR #64**: refactor: use shared PDK-pin helper in rail-model and threshold-MC drivers
- **PR #62**: refactor: share PDK-pin gate across sim bench drivers
- **PR #60**: feat: check all bench runners and scripts in item-10 inventory and README table
- **PR #58**: feat: add threshold Monte Carlo bench with first batch record (row 5 not met)
- **Issue #68** (closed): pdk_record_header comment claims unreadable netlist paths exit 2, but they do not
- **Issue #66** (closed): Share the ngspice run / result-key check / get() helpers across 11 sim run.sh drivers
- **Issue #65** (closed): Share the record-provenance header block across 12 sim run.sh drivers
- **Issue #63** (closed): Dedupe PDK pin-check preamble copied into 14 sim run.sh scripts
- **Issue #61** (closed): Move tb_rail_model_check and tb_threshold_mc onto sim/lib/pdk_pin.sh
- **Issue #59** (closed): Extend the item-10 hygiene inventory and README reproduce table to all 14 benches
- **Issue #21** (closed): Consolidate duplicated PDK-pin/ngspice boilerplate across sim bench run.sh drivers

### 2026-11-05

- **PR #57**: refactor: share rail-envelope waveform code between the envelope generators
- **PR #56**: chore: untrack stray ngspice bsim4v5.out and ignore it
- **PR #53**: feat: add latency, min-width and supply-headroom benches for detector top
- **PR #52**: feat: add threshold-accuracy, false-flag and Iq benches for detector_top
- **PR #51**: feat: add glitch-filter and flag-logic benches with sequence checker
- **PR #50**: feat: add glitch filter, flag logic and detector top design sources
- **PR #42**: feat: add continuous-time comparator schematic, netlist and nominal-corner bench
- **Issue #55** (closed): Dedupe rail-envelope waveform code shared by gen_envelope.py and gen_envelope_ff.py
- **Issue #54** (closed): Remove stray ngspice output sim/tb_false_flag/bsim4v5.out
- **Issue #40** (closed): T1 item 9 (testbenches c): tb_filter and tb_flag_logic (rows 9, 10)
- **Issue #39** (closed): T1 item 9 (testbenches b): tb_threshold_accuracy, tb_false_flag, tb_iq (rows 5, 8, 11)
- **Issue #38** (closed): T1 item 9 (testbenches a): tb_supply_headroom, tb_latency, tb_min_width (rows 2, 6, 7)
- **Issue #27** (closed): T1 item 1 (design sources): glitch filter, sticky/live flags and detector top netlist + attest 1
- **Issue #26** (closed): T1 item 1 (design sources): comparator schematic and netlist on the 3.3 V detector supply

### 2026-11-04

- **PR #46**: docs: mark target spec and DR-001 ratified by PR #8
- **Issue #45** (closed): T1 status: correct spec/target-spec.md and DR-001 headers — ratified 2026-10-20 by the merge of PR #8, still read "proposed"

### 2026-11-01

- **PR #49**: Bump Repo Skills 0.24.7 -> 0.25.1

### 2026-10-27

- **PR #41**: feat: attest T1 item 10 (repo hygiene) and document bench reproduction
- **Issue #28** (closed): T1 item 10 (repo hygiene): README reproduction for every bench, PDK-free checks in CI, --attest 10

### 2026-10-24

- **PR #24**: refactor(sim): generate rail-model point inputs from one template
- **Issue #23** (closed): Simplify: generate the four netlist-form request/wrapper files in run.sh instead of committing copies

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
