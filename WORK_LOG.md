# Work Log

Chronological record of merged PRs and closed issues, maintained by the Guide
triage role. Newest first.

### 2026-11-26

- **Issue #175** (closed): WORK_PLAN.md no longer shows that a held issue is held, now that the region is a verbatim renderer capture
- **Issue #173** (closed): Regenerate the WORK_PLAN.md marker region from the Guide renderer
- **PR #174**: docs: replace WORK_PLAN marker region with verbatim Guide render
- **PR #171**: refactor: derive sim/run_all.sh bench list from sim/inventory.json
- **Issue #170** (closed): Dedupe sim/run_all.sh bench list: read sim/inventory.json instead of hardcoding all 14 benches

### 2026-11-24

- **PR #161**: fix: NUL-split sim/ enumeration and fail loudly on unreadable paths in thread-policy guard
- **Issue #160** (closed): Thread-policy guard silently skips sim/ files with spaces or non-ASCII names (same ls-files defect as #158)
- **PR #159**: fix: read item-10 tracked-file list NUL-delimited from git ls-files -z
- **Issue #158** (closed): Item-10 inventory coverage misses an unlisted Unicode guard filename
- **PR #156**: chore: discover tests/ guards via git ls-files in CI and npm scripts
- **Issue #155** (closed): Dedupe hardcoded tests/*.py guard lists across signoff.yml, package.json and READMEs

### 2026-11-23

- **Issue #81** (closed): Wire up or drop tests/test_item10_coverage.py: an inventory-completeness guard no runner executes
- **Issue #29** (closed): T1 item 9 (testbenches shipped): the eight planned row benches, inventory and --attest 9
- **PR #153**: feat(sim): attest T1 item 9 - testbench inventory, cold-start envelope, CI gate
- **Issue #91** (closed): Remove the redundant 'Validate committed JSON parses' step from signoff.yml: the next step already fails on every case it guards
- **PR #152**: ci: fold committed-JSON parse check into the klt signoff step
- **PR #150**: ci: wire thread-policy and record-header guard tests into signoff workflow and npm scripts
- **Issue #149** (closed): Wire up tests/test_thread_policy.py and tests/test_record_header_threads.py: guards no runner executes

### 2026-11-18

- **PR #143**: ci: add merge_group trigger to the signoff workflow
- **Issue #142** (closed): Merge queue: add the merge_group trigger to the required-check workflow(s)

### 2026-11-17

- **PR #138**: chore(loom): resync installed Loom to v0.19.1306
- **PR #135**: ci: print the item-10 drift remedy in the signoff re-attest step
- **PR #132**: docs: name tests/ in the item-10 coverage-guard comment in signoff.yml
- **Issue #133** (closed): signoff.yml: the item-10 re-attest step reports drift without naming the regeneration command
- **Issue #127** (closed): signoff.yml step comment still says the item-10 coverage guard covers only sim/ and verification/

### 2026-11-16

- **PR #125**: chore(loom): resync installed Loom to v0.19.1302
- **PR #129**: fix: keep results: key in flag_logic wrapper record; narrow README sibling-key gloss
- **PR #126**: guard: sweep tests/ for unlisted scripts in the item-10 coverage check
- **PR #120**: tests: guard the record header's ngspice_threads coupling to ngspice_run
- **PR #111**: fix: state record supersession as one-way; emit hashes for smoke and flag_logic wrapper
- **Issue #123** (closed): Nothing keeps a tests/*.py file in attest/item10.json, so a tests/ guard can go dead in CI without turning red
- **Issue #116** (closed): Wrapper record: inherited provenance block runs into the [AB] sequence-check lines; narrow design/README's sibling-key gloss
- **Issue #114** (closed): No guard keeps pdk_record_header's ngspice_threads: field (or its cross-file coupling) from silently regressing
- **Issue #106** (closed): Narrow design/README.md's supersession rule: it is a one-way hash test, and two benches emit no hash at all
- **PR #118**: fix: enumerate depth-0 scripts in item-10 coverage guard
- **Issue #110** (closed): Item-10 coverage guard: `sim/**/*.sh` misses a script placed directly in sim/ or verification/

### 2026-11-15

- **PR #121**: test: fail closed on an added row, column or ragged row in the row-5 budget guard
- **Issue #119** (closed): check_row5_budget.py does not notice an ADDED level row or corner column in row5-error-budget.md
- **PR #115**: ci: re-derive the row-5 error-budget note from its committed records in CI
- **PR #113**: sim: record the ngspice thread policy in the record header
- **PR #108**: attest: cover sim/lib/*.sh helpers in item 10 and widen the inventory guard
- **PR #105**: docs: repoint Reproduce table to the 2026-11-14 resize records
- **PR #82**: docs: refresh README status prose to the five netlisted blocks and 11 row benches
- **Issue #112** (closed): README Reproduce table cites tb_rail_model_check's 2026-10-23 record, not the newer 2026-11-15 one
- **Issue #104** (closed): No CI guard re-derives design/row5-error-budget.md's tables from the committed records
- **Issue #107** (closed): sim records do not state the ngspice thread count they were produced with
- **Issue #99** (closed): README Reproduce table cites nine records superseded by the 2026-11-14 resizing
- **Issue #97** (closed): Attest item 10: sim/lib/*.sh escape both the inventory and the new coverage guard
- **Issue #78** (closed): README and design/README.md still describe the block as before the comparator, filter and flags landed
- **PR #103**: fix: swap tb_rail_model_check's hand-rolled record header for pdk_record_header
- **PR #102**: docs: quote row5 budget contributor (a) as the pure 3.3 to 2.97 V supply delta, not the record's vs-nominal field
- **PR #101**: refactor: one committed table for the ratified row 4 threshold levels
- **PR #96**: ci: run the item-10 inventory-coverage guard in the signoff workflow
- **PR #88**: sim: move the ngspice thread count into sim/lib/ngspice_run.sh and force it per run
- **Issue #94** (closed): row5-error-budget.md: contributor (a) is quoted against nominal, not against the 3.3 V trip point, double-counting the ladder's tt offset by up to 0.52 mV
- **Issue #86** (closed): Finish the record-header consolidation: tb_rail_model_check hand-rolls pdk_record_header and records one wrapper hash instead of 14 model-file hashes
- **Issue #85** (closed): Dedupe the ngspice thread-count knob: one host-concurrency policy in sim/lib, not 13 scattered settings
- **Issue #80** (closed): Wire tests/test_item10_coverage.py into CI: the attest-inventory completeness guard never runs
- **Issue #79** (closed): Dedupe the ratified four-level threshold table copied into 12 sites across the sim benches

### 2026-11-14

- **PR #92**: docs: apportion the row 5 trip-point error by contributor from committed records
- **Issue #76** (closed): Row 5 error budget: split the threshold trip-point error by contributor from the committed records
- **PR #84**: fix: resize comparator and flag_logic output path to meet row 6 at 2.97 V
- **Issue #77** (closed): Comparator path misses the row 6 latency target at a 2.97 V detector supply
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
