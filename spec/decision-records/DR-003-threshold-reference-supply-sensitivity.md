# DR-003: the threshold reference needs supply compensation to meet row 5

- **Status**: **proposed** — becomes ratified when the operator merges the PR carrying it
  (the ratify-by-merge path of DR-001).
- **Date**: 2026-11-14
- **Author**: Builder agent, implementing issue #83.
- **Amends**: [DR-001](DR-001-target-spec-ratification.md) §(b) and
  `spec/target-spec.md` row 5's immunity floor (wording only). It also closes the item
  [DR-002](DR-002-threshold-accuracy-statistical-form.md) left open under *"Noted, not part
  of this change"* ("the committed `threshold_ref` currently tracks the supply (≈0.31 V/V)
  … is not addressed here"). **No fallback, target or stretch number is changed.**
- **Implemented by**: #90 (the reference revision). This DR decides *what* to build; it
  builds nothing. A closed #83 does **not** mean the detector has stopped flagging at a
  nominal rail.

## Context

Row 3 permits the threshold reference to be "generated in-tree from the detector supply
rail (not ratioed to it)", and charges "its residual supply sensitivity … to the row 5
error budget". Row 2 names the supply corners 2.97 / 3.3 / 3.63 V. Nobody had measured
what that residual sensitivity actually costs across that box: every committed record
was taken at 3.3 V, or (for `tb_ref_droop`) at 3.3 → 2.97 V only. Issue #83 reported that
at 3.63 V the code-00 threshold rises *into* the LDO ±2 % window, so the detector asserts
`live` with the monitored rail at its nominal 1.8 V — a failure of the block's core
function at a ratified corner, and a row 8 violation.

This DR records the measurement across the whole box and decides whether row 3's
architecture can meet row 5 untrimmed, or whether the bias core needs supply compensation.

## Evidence

All figures **SIMULATED** (not measured), corner **tt / 27 °C**, ngspice-47, open_pdks
`f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7` (`--pdk-root` pinned explicitly, because two
installs provide `sky130A` on the sweep host and resolution is otherwise first-match-wins),
against the tree that contains #84's comparator/flag_logic resize (merge-base `dde826a`; #84
landed on main at `3f52500`, carried into this branch at `1dadde4`; `design/detector_top.spice`
sha256 `c6307eb1…`). The records first filed with this DR ran the **pre-#84** netlist
(`0fca89f6…`) — they stay committed in `sim/` as the evidence of the tree they ran on, and
the figures below cite the post-#84 re-measurement. One corner, untrimmed, **no
Monte Carlo** — the statistical row 5 verdict is #35's under DR-002, not this record's.

### Trip point vs detector supply — `sim/tb_threshold_accuracy`

Real reference + comparator + filter + flag logic, slow 1 mV/µs rail sweep. The figures
below cite the **post-#84** records: `2026-11-15-tb_threshold_accuracy-tt-vsup{2p97,3p63}.txt`
(run on this branch's merged tree) and main's own `2026-11-14-tb_threshold_accuracy-tt.txt`
at 3.3 V, which already is the post-#84 3.3 V record (netlist `c6307eb1…`). The pre-#84
three-record set (`2026-11-14-…-vsup{2p97,3p3,3p63}.txt`, netlist `0fca89f6…`) stays
committed alongside — `sim/` is append-only — as the as-filed evidence; its code-00 trips
sit ~6 mV higher at every corner.

| `VSUP` | code-00 trip | vs nominal 1.728 V | row 5 band | code-00 vs the 1.764 V window edge |
|---|---|---|---|---|
| 2.97 V | 1.66542 V | −62.58 mV (−3.477 %) | **OUTSIDE fallback** | +98.58 mV below |
| 3.30 V | 1.74137 V | +13.37 mV (+0.743 %) | inside target | +22.63 mV below |
| 3.63 V | 1.80935 V | **+81.35 mV (+4.519 %)** | **OUTSIDE fallback** | **−45.35 mV: inside the window** |

- **Two different quantities are quoted below; do not conflate them.** *Total one-sided
  error* at a corner is the trip minus the specified 1.728 V (+81.35 mV = +4.519 % of 1.8 V
  at 3.63 V). *Incremental supply drift* is the trip minus the same netlist's own 3.3 V trip
  (1.80935 − 1.74137 = +67.98 mV = +3.777 % of 1.8 V at 3.63 V). The remaining +13.37 mV
  (+0.743 %) is already present at the nominal 3.3 V supply and is not supply drift.
- **Total code-00 swing across row 2's box: 143.93 mV, i.e. +0.2180 V/V.** That is
  **2.67×** row 5's entire ±27 mV target band (54 mV peak-to-peak) and **1.33×** its
  ±54 mV fallback band (108 mV peak-to-peak) — from the supply term **alone**, at one
  corner, before any process, temperature or mismatch contribution.
- The defect is **two-sided**, not a single bad corner, and the low corner got **worse**
  with #84's resize. At 3.63 V all four levels sit outside the fallback band
  (+81.35 / +79.65 / +77.24 / +74.83 mV); at 2.97 V **all four** are outside it too
  (−62.58 / −61.34 / −59.36 / −57.37 mV) — pre-#84, codes 10 and 11 still sat inside the
  fallback band only. **No level is inside the ±27 mV target band at either end of the
  box.**
- The 6.0 mV discrepancy noted on #83 is settled, in the direction #83 could not see at
  filing time: the as-filed 1.74137 V figure — read then as #84's branch value, with
  `origin/main` still giving 1.74737 V — is what `origin/main` itself gives once #84
  merged (`3f52500`). The comparator/flag_logic resize (tail `mult=4→6`, input pfets
  `W=4→2`, output chain halved) moves the full-chain trip by −6.0 mV. The pre-#84 3.3 V
  re-run filed with this PR (`2026-11-14-…-vsup3p3.txt`, 1.74737 V) reproduces the
  committed `2026-11-05-tb_threshold_accuracy-tt.txt` record **exactly** (all four trip
  points and the immunity line), and that comparison still shows the ngspice 46 → 47
  bump contributes **0.00 mV** to this bench, independently confirming #87's list
  of the four benches whose numbers do move.

### Reference and tap vs detector supply — `sim/tb_ref_droop`

Ideal comparator, so this isolates the reference from the comparator. Two records in
`sim/tb_ref_droop/records/` (`2026-11-14-tb_ref_droop-tt-vsup{2p97,3p63}.txt`):

| `vdd33` | `vref` | `vth` (code 00) |
|---|---|---|
| 2.97 V | 2.28821 V | 1.65536 V |
| 3.30 V | 2.38932 V | 1.72852 V |
| 3.63 V | 2.47994 V | 1.79409 V |

- `vref` moves **+191.74 mV (+0.2905 V/V)**; the code-00 tap **+138.73 mV (+0.2102 V/V)**.
- **The whole error is in the bias core, none in the tap ladder.** The divider ratio
  `vth`/`vref` is constant to 7e-6 across the box, so `XR2`–`XR6` and the select mux
  contribute under 0.02 mV. **Do not resize the ladder.**
- **Decomposition of the 143.93 mV trip swing**: 138.73 mV (96.4 %) is the reference and
  5.20 mV (3.6 %) is the **full-chain residual** (trip minus tap), which grows
  +10.06 → +12.85 → +15.26 mV across the box. It is *not* isolated to the comparator: the
  residual also contains any reference-to-comparator loading, tap-to-input interaction and
  filter/flag-logic threshold shift, and no isolated comparator-offset measurement exists
  in this repo. Attributing it to comparator input offset is a hypothesis, left to #77's
  subsystem; it is small enough not to change this decision.
- **Monitored-rail rejection is already excellent and is not the problem.** For a
  1.8 → 0.9 V rail collapse `vref` moves **−0.0035 mV** DC and at most −0.004 mV during a
  5 ns edge. Row 3's "must not move with the monitored rail" is met; row 2's supply box
  is what the reference fails.

### The row 8 violation, as committed evidence

`sim/tb_threshold_accuracy/records/2026-11-15-tb_threshold_accuracy-tt-vsup3p63.txt` carries
the bench's own line `NO MARGIN: would flag inside the LDO window`. At 3.63 V **two** of the
four levels trip inside the LDO ±2 % window (1.764–1.836 V): code 00 at 1.80935 V and
code 01 at 1.77165 V. Row 8 requires **zero** flags for any excursion inside that window,
and waveform W1 is exactly "static rail anywhere in 1.764–1.836 V".

The direct consequence is committed alongside it as a fail-closed transcript,
`2026-11-15-…-tt-vsup3p63-flag-stuck-high.txt`, re-taken on the post-#84 tree (the pre-#84
`2026-11-14-…-flag-stuck-high.txt` stays committed beside it). **What that transcript does
and does not establish**: its stimulus is *not* a static rail. The PWL holds 1.800 V only
to 1 ns, then ramps down at 1 mV/µs, so `idle_max_l0` (a MAX over 2–20 µs) samples a rail
of 1.798 → 1.780 V — inside the LDO window — and reads **1.69708 V, a logic HIGH for the
1.8 V CMOS consumer of row 10**, at the identical figure pre- and post-#84. That shows the
code-00 live flag is high at some point in that in-window span, consistent with the 3.63 V
code-00 trip (1.80935 V) lying above the whole span. It does **not** establish the flag
state at t = 0, its duration, or its settled level under a constant 1.800 V hold; a MAX
cannot. A settled minimum live voltage under a constant 1.800 V hold is not yet recorded;
it is `sim/tb_false_flag` W1's job (#90 re-runs it). Both transcripts carry an appended
annotation saying so. The in-window trip evidence (1.80935 V and 1.77165 V, table above) is
unaffected. This reproduces #83's headline figure, with that qualification. (The row 8 *verdict* is `sim/tb_false_flag`'s; these records
report.)

### The cost at the low corner is missed detection, not false flagging

At 2.97 V the shallowest level trips at 1.66542 V instead of 1.74137 V, so droops in the
75.95 mV band between those two voltages — real droops, below the LDO window — are **not
flagged** at the 4 % level. The supply term costs false flags at one end of row 2's box and
detection at the other.

## Decision

1. **Row 3's architecture, as built, cannot meet row 5 over row 2's supply box, untrimmed.**
   The supply term alone is 2.67× the target band and 1.33× the fallback band at a single
   nominal corner. There is no process, temperature or mismatch allocation that makes
   143.93 mV fit inside 54 mV. This is a **design conclusion, not a spec problem**: row 3
   anticipated a *residual* sensitivity charged to row 5, and +0.22 V/V at the trip point
   is not residual.

2. **The reference needs supply compensation. The adopted topology is a self-biased
   constant-g_m (beta-multiplier) current reference with a cascoded mirror**, feeding the
   existing tap ladder unchanged.

   *Why the present core fails, from its own netlist*: `XR1` (`res_xhigh_po_1p41`, L = 27)
   sets the core current as roughly (`vdd33` − 2·V_GS)/R, so the current is proportional to
   the supply to first order, and `vref` = 2·V_GS(I) then moves with it through the diode
   stack `XM1`/`XM2`. There is **no supply-rejection term anywhere in the cell** — the
   measured +0.2905 V/V is the topology working as drawn, not a sizing error. This is why
   resizing cannot fix it.

   *Why a beta-multiplier is the in-tree answer*: it sets the core current from a **ratio**
   of like quantities (a resistor and the W/L ratio of two matched nfets) with no `vdd33`
   term to first order, so the residual sensitivity becomes the mirror's output conductance
   rather than a divider ratio — and cascoding the mirror is the standard, untrimmed,
   in-tree way to push that residual down. It remains "generated in-tree from the detector
   supply rail (not ratioed to it)" exactly as row 3 requires: it is still powered from
   `vdd33`, it simply stops tracking it.

   **This topology choice is reasoning from the measured decomposition above plus the
   constraint set below. It is NOT simulated — no beta-multiplier has been netlisted or
   run in this repo.** #90 measures it and may refute it; if it does, #90 supersedes this
   clause with its own DR rather than quietly substituting a different cell.

   *What the topology does not, by itself, settle* (open for #90; none of it is decided
   here): (i) the present core's line gain has two terms — `XR1` and the diode stack's
   incremental resistance — so "no supply term to first order" is a claim about the
   replacement, not proof that no sizing of the present cell could reduce it; (ii) cascoding
   reduces line sensitivity at a headroom cost, and the absolute trip still depends on
   device and resistor variation; (iii) `vref` remains 2·V_GS(I), and V_GS has a threshold
   tempco of order −1 to −2 mV/K per device, which a beta-multiplier does not remove.
   **This DR contains no temperature evidence** (every record is tt / 27 °C), so row 5 over
   −40 to 125 °C is neither addressed nor claimed here.

3. **The constraint set #90 must hold** (this is the operative part of the decision):
   - **Untrimmed** — row 5 and DR-002 clause 3. A trim is a different architecture needing
     a superseding DR; it is not a route to meeting this row.
   - **In-tree, powered from the detector supply**, no sibling `consumes` edge (row 3). An
     external reference pin is row 3's *stretch* and needs an operator decision.
   - **Operational over 2.97–3.63 V** (row 2) using 5 V-class devices where the 3.3 V
     domain needs them. The cascode stack height competes with the `g5v0d10v5` V_GS at the
     2.97 V corner; headroom there is the first thing to check, not the last.
   - **Must not spend quiescent current it does not have.** Row 11's target is < 50 µA. The
     current post-#84 record, `sim/tb_iq/records/2026-11-14-tb_iq-tt.txt` (netlist hash
     `c6307eb1…`, matching `design/detector_top.spice` at this head), reads **47.576 µA at
     code 0** (SIMULATED, tt / 27 °C, 3.3 V, one corner) — inside the target with
     **2.424 µA** of margin. (The earlier 51.592 µA figure, `2026-11-05-tb_iq-tt.txt`,
     predates #84's resize and is superseded for this purpose.) That margin is thin and
     holds at one corner only, so **the compensated core must be no more expensive than the
     resistor bias it replaces** — a zero-increase budget is the conservative choice — and
     #90 re-runs `tb_iq` at all corners. Buying row 5 by breaking row 11 is not a fix.
   - **Must preserve the monitored-rail rejection already achieved** (−0.004 mV for a
     1.8 → 0.9 V collapse). A compensated core that couples the monitored rail into `vref`
     would trade a known defect for a worse one.
   - **Start-up must be explicit.** A self-biased cell has a stable zero-current state; it
     needs a start-up device and a testbench case that proves the core comes up from a cold
     rail. The detector must also still satisfy the row 10 enable statement (live flag high
     while the rail ramps, masked by the consumer).
   - **Re-run and commit rows 5, 6, 8 and 11** at all three supply corners — not 3.3 V
     alone. That is the mistake this DR exists to correct.

4. **Row 5's immunity floor is restated to bind across row 2's supply box**, not at the
   3.3 V point alone (the wording change in `spec/target-spec.md`; **no number moves**).
   The floor requires the shallowest level to sit ≥ 2 % + accuracy below nominal. The
   measured code-00 **total one-sided error** at 3.63 V is **+4.52 %** of 1.8 V (+81.35 mV
   against the specified 1.728 V). Of that, the incremental supply drift against the 3.3 V
   trip is **3.78 %** (+67.98 mV); the other 0.74 % (+13.37 mV) is present at nominal
   supply. The 6.52 % figure uses the *total* error, because the floor bounds where the
   trip may land, not the drift alone. Keeping the trip at or below 1.764 V at that corner
   requires the shallowest level placed **≥ 6.52 % below nominal** — deeper than row 4's ratified 4 % *and* 6 %
   placements, and the measurement agrees: at 3.63 V the 4 % and 6 % levels both trip
   inside the window while the 9 % and 12 % levels (1.71524 / 1.65883 V) clear it. So
   **the floor is not reachable by level placement within row 4's ratified set**; it has to
   be met by reducing the supply term, which is clause 2.

5. **No operator decision is triggered *by this DR*.** Implementation Guidance on #83
   routes a "row 5 is unmeetable untrimmed or the band must widen" conclusion to the
   operator rather than to a DR. That is **not** this conclusion: what is established is
   that the *present* core cannot meet row 5 (clause 1). That row 5 is reachable untrimmed,
   within the ratified rows, by replacing the bias core is a **hypothesis for #90 to
   test**, not a result — it is unsimulated, and #90 must show it, including cold start-up,
   headroom at the 2.97 V corner and quiescent current against clause 3. A design change is
   #90's. The
   condition that *would* trigger an operator decision is named here so #90 does not have
   to improvise one: **if a cascoded, untrimmed, in-tree compensated core cannot bring the
   code-00 trip inside ±27 mV across 2.97–3.63 V without exceeding row 11's < 50 µA**, then
   the trade between rows 5, 2 and 11 is the operator's, and #90 files it with
   `loom-daemon operator-decision apply` instead of relaxing a row.

## Alternatives considered

- **Resize the tap ladder** — rejected on measurement: `vth`/`vref` is already
  supply-independent to 7e-6, so there is nothing to win. The ladder is not the defect.
- **Resize `XR1` or the `XM1`/`XM2` stack** — rejected on topology: the cell has no
  supply-rejection term at all, so sizing moves the operating point, not the +0.29 V/V.
- **Trim the reference** — rejected: row 5 is explicitly untrimmed and DR-002 clause 3
  makes a trimmed design a superseding-DR matter, not a route to a pass.
- **Move the levels deeper than row 4's 4 / 6 / 9 / 12 %** — rejected: it retunes ratified
  row 4 levels to mask a reference defect, and clause 4's arithmetic shows it would take
  ≥ 6.52 % for the shallowest level — abandoning row 4's two shallowest settings, and still
  only at tt / 27 °C with no mismatch allocation. If it is ever the answer it is a spec
  change via DR plus an operator decision, never a quiet retune.
- **External reference pin** — rejected here: row 3's stretch, and the spec says it needs
  an operator decision.
- **Widen row 5's band to fit the measurement** — rejected: agents do not relax the
  ratified spec to make results pass.
- **A bandgap reference** — not adopted: it meets the supply constraint but spends area and
  quiescent current this block has little of (row 11 has 2.424 µA of margin at code 0, one
  corner), and
  the threshold is a *ratio* of the 1.8 V nominal, not an absolute voltage, so absolute
  bandgap accuracy buys nothing here. Noted rather than rejected outright: if #90 finds the
  beta-multiplier's residual PSRR insufficient at the 2.97 V headroom corner, this is the
  next candidate and needs its own DR.

## Carried failure: recorded, not accepted

The market-key review of this PR at `204bb2fd` found the carried behaviour uncompetitive
(a 1.8 V catalog supervisor keeps a healthy rail inside its static window across the same
supply span) and recommended operator escalation. This record does not contest that
finding: at 3.63 V the committed design trips codes 00 and 01 inside the healthy window
(row 8), and at 2.97 V it misses shallow droops (row 5). **This DR does not accept that
behaviour, does not present it as meeting any row, and makes no catalog-competitiveness
claim for the detector as built.** It records the failure and its measured cause and
assigns the corrective design and its verification to #90, which re-runs rows 5, 6, 8 and
11 at all three supply corners. Until #90 closes with measured results, rows 5 and 8 are
carried as **failing**. The operator-decision trigger in clause 5 stands.

## Not relaxed

No fallback, target or stretch value moves. Row 5's immunity floor is **tightened in
reading** — it now explicitly binds at every corner of row 2's supply box rather than
being evaluated at 3.3 V — and nothing in row 2, 3, 4, 5, 8 or 11 is weakened. The
measured figures are recorded as failing the rows they fail.

## Consequences

- #90 has a proposed topology hypothesis and a constraint set, and is no longer blocked on
  an undecided architecture. The topology stays unsimulated until #90 shows it.
- #76 (row 5 error budget) gains the supply-sensitivity term as committed evidence at all
  three corners. It should **read the post-#84 records this DR cites** (the
  `2026-11-15-tb_threshold_accuracy-tt-vsup{2p97,3p63}.txt` set plus main's
  `2026-11-14-tb_threshold_accuracy-tt.txt` at 3.3 V) rather than re-measure; the pre-#84
  `2026-11-14-…-vsup{2p97,3p3,3p63}.txt` set carries a ~6 mV stale supply term and stays
  committed only as as-filed evidence. #92, which already merged, apportioned its budget
  from those pre-#84 figures — whether it needs a correction pass is #76's call, not this
  record's. This DR does not assemble the budget.
- #35 keeps the statistical row 5 verdict (3σ, N ≥ 300 per corner, DR-002). Three static
  operating points cannot and do not produce one.
- The `tb_threshold_accuracy` sweep window is now wide enough to span the levels across the
  whole supply box (1.9 → 1.45 V at 1 mV/µs, both ends parameterised). The former
  1.8 → 1.55 V window could not measure code 11 at 2.97 V or code 00 at 3.63 V at all. Any
  future corner campaign (#34) must check that its window still spans the levels at the
  corner it runs; the bench fails closed (exit 3) when it does not.
- `tb_ref_droop` now takes its perturbed supply corner as a parameter and covers both ends
  of row 2's box. Its committed 2026-10-23 record remains valid: the re-run at the default
  2.97 V reproduces it exactly.
- **Disclosed side effect of the wider sweep window**: `tb_threshold_accuracy`'s pre-ramp
  idle gate (`idle_max_l*` over 2-20 µs, "live flag not idle before the ramp") now samples
  the rail at 1.898-1.880 V, *above* the LDO ±2 % window, where it formerly sampled
  1.800-1.782 V, inside it. That gate is a harness sanity check, not a row 8 verdict, and
  nothing is lost from the record: the bench's immunity line still reports a code-00 trip
  above the 1.764 V edge as `NO MARGIN: would flag inside the LDO window`, which is how the
  3.63 V violation appears in the committed record. The row 8 verdict is and remains
  `sim/tb_false_flag`'s, whose W1 waveform is exactly a static rail inside the window; #90
  re-runs it. The fail-closed transcript committed here preserves the stuck-high evidence
  that the former 1.8 V start produced incidentally.

## Noted, not part of this change

- The comparator's +5.20 mV of supply-dependent offset drift across the box (3.6 % of the
  trip-point swing) is disclosed here and left to #77's subsystem. It is not large enough
  to change this decision.
- `sim/tb_supply_headroom`'s four 2.97 V cases not asserting, and #77's 2.97 V latency
  miss, are both downstream of the same mechanism. They are expected to improve when #90
  lands and are not re-graded here.
- `sim/toolchain.json` still pins ngspice 46 while the host provides 47 (#87). All records
  in this DR were taken on **one** toolchain, and each stamps the version it actually ran.
  Re-pinning is #87's decision, not this one.
