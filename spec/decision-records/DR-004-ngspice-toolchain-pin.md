# DR-004: ngspice toolchain pin re-anchored to 47

- **Status**: **proposed** — becomes ratified when the operator merges the PR carrying it
  (the ratify-by-merge path of DR-001).
- **Date**: 2026-11-15
- **Author**: Builder agent, implementing issue #87.
- **Amends**: [DR-001](DR-001-target-spec-ratification.md) provenance parenthetical
  (`sim/toolchain.json` toolchain statement) only. **No bound, threshold or pass
  criterion changes.**

## Context

`sim/toolchain.json` pinned `"ngspice": "46"`, but the worker now provisions
ngspice-47p1 (`/home/ubuntu/.local/opt/ngspice-47p1`, exec'd by the `ngspice` on
`PATH`), whose banner reads `ngspice-47`. The tree therefore *stated* one
toolchain while *evidencing* another: nine of twelve benches already carry
committed `ngspice-47` records — landed by `1dadde4` ("fix: resize comparator
and flag_logic output path to meet row 6 at 2.97 V") for `tb_comparator`,
`tb_false_flag`, `tb_filter`, `tb_flag_logic`, `tb_iq`, `tb_latency`,
`tb_min_width`, `tb_supply_headroom` and `tb_threshold_accuracy` — against a pin
that still said 46. Three benches (`smoke`, `tb_ref_droop`,
`tb_threshold_select`) still had ngspice-46 as their newest committed record,
and the prose pin sites (`spec/target-spec.md:168`,
DR-001`:95`) still asserted 46.

What moved on the 46 → 47 bump (SIMULATED, tt / 27 °C, each bench's own
testbench, fresh run vs newest committed record):

- `tb_false_flag` — W1 settled level [netlist-derived, **graded**]:
  `1.7955..1.7995 V` → `1.8004..1.8006 V`; load-step excursion [reported]:
  `1.6061..1.9262 V` → `1.6074..1.9273 V`.
- `tb_latency` — r6 l2 start hi: `4.811 ns` → `4.810 ns`; worst envelope
  latency `4.9594 ns` → `4.9593 ns`.
- `tb_supply_headroom` — supply 2.97 V, l1: live max `1.6158 V` → `1.6159 V`.
- `tb_filter` — level 0 post-droop max `7.1589E-10` → `7.15889E-10`
  (formatting of the same value, not a real move).

The graded `tb_false_flag` move is already committed evidence, not a pending
result: the committed 2026-11-14 record reads `W1 settled level
[netlist-derived, graded]: rail 1.8004..1.8006 V` (line 41) with
`verdict (this corner, graded cases only): zero flags` (line 52) intact.

## Decision

1. **Pin ngspice 47.** `sim/toolchain.json` records `"ngspice": "47"` as the
   pinned simulator, matching what the worker provisions and what the record
   provenance lines stamp.
2. **Why the string `47`, not `47p1`.** `sim/lib/pdk_pin.sh:43` captures the
   provenance as `ngspice --version | grep -m1 -o 'ngspice-[0-9.]*'`, and the
   47p1 build's banner reads `** ngspice-47 : Circuit level simulation
   program`. The pattern cannot match a `p`, so every record produced on this
   host stamps `ngspice: ngspice-47` — pinning `47p1` would create a permanent,
   by-construction mismatch between the pin and every record it anchors. `47`
   is the only value that can ever byte-match.
3. **Append fresh records for the three stale benches only.** `smoke`,
   `tb_ref_droop` and `tb_threshold_select` each gain one appended record under
   their own `records/`, stamped `ngspice: ngspice-47`. The nine benches that
   already carry ngspice-47 records are not re-run.
4. **Prose re-anchoring.** `spec/target-spec.md` and DR-001's provenance
   parenthetical cite this record for the current pin instead of asserting 46
   (DR-001's ratified rows, bounds and decisions are untouched).

## Not relaxed

This is a re-anchoring of **provenance**, not of any spec bound. No graded
bound moves and no verdict changes: all twelve benches exit 0 and reach the
same pass/fail verdicts on 47 as on 46; the only graded figure that differs
(`tb_false_flag`'s W1 settled level) moved *toward* nominal rail (1.800 V) and
its committed record already carries the post-bump value with the `zero flags`
verdict intact. A ratification phrase here ratifies which simulator the
evidence is anchored to; it does not relax any threshold, window or pass
criterion ratified by DR-001 or DR-002.

## Rejected alternatives

- *Pin `"47p1"` to match the installed directory name* — rejected: the
  binary's banner says `ngspice-47` and `pdk_pin.sh:43` cannot capture a `p`,
  so the pin would never match any record it anchors.
- *Widen the capture in `sim/lib/pdk_pin.sh` to record `47p1`* — rejected: it
  changes the provenance-line format of every future record for a cosmetic
  gain, and collides with PR #88's in-flight `sim/lib` work.
- *Keep the pin at 46 and have `run.sh` select the still-installed
  `/home/ubuntu/.local/opt/ngspice-46`* — rejected: it anchors the evidence to
  a build the worker spec no longer puts on `PATH`, and per the host rules a
  change to what the worker provisions belongs in `2AMLogic/2am
  infra/aws/loom-worker/`, not here.
- *Re-run all twelve benches for a uniform sweep* — rejected: nine already
  carry ngspice-47 records, and re-running them adds no evidence while
  inflating the diff.
