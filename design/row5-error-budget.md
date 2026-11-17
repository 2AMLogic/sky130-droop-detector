# Row 5 error budget: the threshold trip-point error by contributor

**What this note is.** A reading of the *already committed* records under `sim/`
that splits the threshold trip-point error into named contributors, states which
contributors no committed record measures, and shows the arithmetic for how far
each would have to shrink for the combined error to fit spec row 5's **±27 mV at
3σ, untrimmed** ([`spec/target-spec.md`](../spec/target-spec.md) row 5,
[DR-002](../spec/decision-records/DR-002-threshold-accuracy-statistical-form.md)).

**What this note is not.** It is not a verdict on row 5 — `klt yield` already
records that (`status: fail`, every section). It does not propose a fix, a trim,
a schematic change, or any change to a ratified number. It runs no simulation:
every figure below is quoted out of a committed record. The consequences belong
in a decision record, in #35, or in #83/#90 — not here.

**Every figure in this note is SIMULATED, not measured**, and is quoted with its
corner and its testbench. Signs are kept throughout: the terms partially cancel
in some combinations, and summing magnitudes would misreport which case binds.

## 1. Provenance of this snapshot

This is a **historical reading of committed evidence as of 2026-11-14**, not a
live claim about the current schematics.

| Record | Date | Netlist it measures | `netlist_sha256` |
|---|---|---|---|
| `sim/tb_threshold_mc/records/2026-11-06/record.txt` | 2026-11-06 | `design/detector_top.spice` | `0fca89f6…d7d95f` |
| `sim/tb_threshold_accuracy/records/2026-11-05-tb_threshold_accuracy-tt.txt` | 2026-11-05 | `design/detector_top.spice` | `0fca89f6…d7d95f` |
| `sim/tb_ref_droop/records/2026-10-23-tb_ref_droop-tt.txt` | 2026-10-23 | `design/threshold_ref.spice` | `e3c2fa06…0205ae` |

Both netlist shas above match the netlists committed on `main` at `2c5fdfc`, so the figures
are live-valid against that tree. **They will go stale**: #77 (PR #84) revises
`design/comparator.sch` and `design/flag_logic.sch` and regenerates
`design/detector_top.spice`. When that lands, `0fca89f6…` no longer exists and
contributor (d) in particular has to be re-read — see §6, where most of (d) is
attributed to the comparator. `sim/` is append-only evidence; re-read it, do not
edit this note's figures in place.

## 2. Decomposition convention

The four contributors named in the acceptance criteria are **not independent as
recorded**. A corner mean measured against *nominal* already contains the `tt`
systematic offset, so adding a raw corner shift to a raw systematic offset
double-counts ≈ +19 mV. The same class of error exists at smaller scale: a
supply shift stated against *nominal* already contains the reference-and-ladder
`tt` offset, so quoting the record's `delta … vs nominal` form as `(a)` would
double-count up to 0.52 mV (§3, §6). This note therefore uses:

```
(d) systematic   = mean(tt_mm) − nominal                 [tt offset of the whole detector]
(b) process corner = mean(corner) − mean(tt_mm)          [pure process spread, tt removed]
(c) mismatch     = ±3 × sd(that corner)                  [the only term that is a sigma]
(a) supply       = Δvtrip between the two detector-supply points being summed
                   (a difference of two supply points, not a shift against nominal)
```

With this convention, `(d) + (b) + (c)` reconstructs the record's own raw
`(mean(corner) − nominal) + 3·sd` **exactly** at all 24 level/corner sections
(verified by re-deriving both forms from the record text). The ±27 mV band is
two-sided, so a combination's **upper** edge is `(d)+(b)+(a)+3σ` and its
**lower** edge is `(d)+(b)+(a)−3σ`; the binding case is whichever edge has the
largest magnitude.

`(b)` and `(d)` are systematic shifts, not random variables. Only `(c)` is a
sigma, so the four terms are **not** combined by root-sum-square — they are
summed signed.

## 3. Contributor (a) — detector-supply sensitivity

SIMULATED; testbench `sim/tb_ref_droop`; corner **tt, 27 °C**; stimulus ideal
sources; record `sim/tb_ref_droop/records/2026-10-23-tb_ref_droop-tt.txt`.
Detector supply 3.3 → 2.97 V. The bench's trip point is the selected tap voltage
`vth` read with a bench-side **ideal comparator** — `sim/tb_ref_droop/tb_ref_droop.spice`
says so in its own comment, `ideal-comparator trip = selected tap voltage` — so
this term is the **reference-and-ladder** part of the supply sensitivity only.

| level | Δvtrip, 3.3 → 2.97 V | as % of 1.8 V | implied slope |
|---|---|---|---|
| l0 (1.728 V) | **−73.16 mV** | −4.064 % | +221.7 mV/V |
| l1 (1.692 V) | −71.62 mV | −3.979 % | +217.0 mV/V |
| l2 (1.638 V) | −69.33 mV | −3.852 % | +210.1 mV/V |
| l3 (1.584 V) | −67.03 mV | −3.724 % | +203.1 mV/V |

The record itself states each 2.97 V trip point *against nominal* — its `delta`
field reads −72.64 / −71.32 / −69.24 / −67.16 mV (l0–l3). That field is **not**
the column above: it is the pure supply change **plus** the reference-and-ladder
tt offset (§6), which contributor (d) already carries, so summing it here would
double-count up to 0.52 mV. The column above is the difference of the record's
own raw tap voltages, `vtrip @2.97 V − vtrip @3.3 V`.

Same record: `vref_nom_v = 2.38932 V`, and `vref` itself moves −101.115 mV for
the same step (≈ 0.306 V/V on the reference, ≈ 0.222 V/V referred to the trip
point). DR-002's "Noted, not part of this change" cites ≈ 0.31 V/V — that is the
`vref` figure, not the trip-point figure.

**The monitored rail contributes nothing measurable.** Same record, monitored
rail 1.8 → 0.9 V: `vref` shifts **−0.00352585 mV** DC (−0.004 mV during a 5 ns
edge). Four orders of magnitude below any other term, so the monitored-rail
coupling is not carried as a contributor below.

## 4. Contributors (b), (c), (d) — process corner, mismatch, systematic

SIMULATED; testbench `sim/tb_threshold_mc`; corner box process
`{tt,ss,ff,sf,fs}_mm` (`vary=mismatch`) + `mc` (`vary=both`), **27 °C, detector
supply 3.3 V**; seed `20261105`, N = 300 per section; record
`sim/tb_threshold_mc/records/2026-11-06/record.txt`. All values mV.

| level | (d) systematic @ tt | (b) `ss` | (b) `ff` | (b) `sf` | (b) `fs` | (b) `mc` |
|---|---|---|---|---|---|---|
| l0 | **+19.57** | +40.18 | −40.87 | −87.37 | **+85.34** | −0.38 |
| l1 | +19.21 | +39.35 | −39.97 | −85.44 | +83.55 | −0.36 |
| l2 | +18.72 | +38.07 | −38.55 | −82.63 | +80.97 | −0.25 |
| l3 | +18.34 | +36.72 | −37.21 | −79.96 | +78.28 | −0.24 |

| level | (c) `tt` | (c) `ss` | (c) `ff` | (c) `sf` | (c) `fs` | (c) `mc` |
|---|---|---|---|---|---|---|
| l0 | ±36.79 | ±37.81 | ±36.64 | ±39.63 | ±37.31 | ±14.12 |
| l1 | ±36.63 | ±37.73 | ±36.67 | ±39.69 | ±37.31 | ±13.98 |
| l2 | ±36.64 | ±37.68 | ±36.76 | ±39.83 | ±37.42 | ±13.78 |
| l3 | ±36.80 | ±37.91 | ±36.73 | ±39.62 | ±37.45 | ±13.57 |

Contributor (d) is independently corroborated by a second bench: SIMULATED,
`sim/tb_threshold_accuracy`, **tt, 27 °C, 3.3 V, one corner, no Monte Carlo**,
record `…/2026-11-05-tb_threshold_accuracy-tt.txt`, a 1 mV/µs DC ramp on the
real `design/detector_top.spice`. It reads **+19.37 / +19.03 / +18.63 /
+18.25 mV** at l0–l3, agreeing with the Monte Carlo means above to within
0.2 mV. Two independent testbenches on the same netlist, agreeing.

### A caveat on (c): the `mc` section disagrees with the `*_mm` sections

`mc` runs `vary=both` (global process **and** mismatch,
`sim/tb_threshold_mc/gen_requests.py:41`) yet its `sd` is 4.52–4.71 mV against
12.21–13.28 mV in the mismatch-only `*_mm` sections — a **superset of variation
sources producing 2.6× less spread**. One of the two families is not varying what
its name implies. Nothing in the committed record resolves which, so this note
quotes the **larger `*_mm` figure** as the mismatch term (the conservative
reading) and flags the inconsistency. Settling it needs a klt-side check that the
requested `vary` mode actually reaches the devices for a `mc` process section —
a `sim/tb_threshold_mc` re-run with a per-device sigma sanity probe, which is
#35's campaign, not this note.

## 5. Combined budget and the binding case

Signed sum per level/corner, both band edges, at the two detector supplies for
which a measurement exists. **Superposition is an assumption here**: (a) was
measured on `design/threshold_ref.spice` alone at tt with an ideal comparator,
while (b)–(d) were measured on `design/detector_top.spice` at 3.3 V. No
committed record measures the process/mismatch box *at* 2.97 V, so the 2.97 V
columns are a **constructed combination of two records, not a measurement.**

Level l0 (the row-8-critical level), all values mV:

| corner | (d) | (b) | (c) | edge lo @3.3 V | edge hi @3.3 V | edge lo @2.97 V | edge hi @2.97 V | worst / 27 mV |
|---|---|---|---|---|---|---|---|---|
| `tt_mm` | +19.57 | +0.00 | ±36.79 | −17.22 | +56.37 | −90.38 | −16.79 | 3.35× |
| `ss_mm` | +19.57 | +40.18 | ±37.81 | +21.95 | +97.56 | −51.21 | +24.40 | 3.61× |
| `ff_mm` | +19.57 | −40.87 | ±36.64 | −57.94 | +15.34 | −131.10 | −57.82 | 4.86× |
| `sf_mm` | +19.57 | −87.37 | ±39.63 | −107.43 | −28.16 | **−180.59** | −101.32 | **6.69×** |
| `fs_mm` | +19.57 | +85.34 | ±37.31 | +67.61 | **+142.23** | −5.55 | +69.07 | 5.27× |
| `mc` | +19.57 | −0.38 | ±14.12 | +5.08 | +33.31 | −68.08 | −39.85 | 2.52× |

The other three levels track l0 closely and are all over the band; worst-case
magnitude per level, over the whole constructed box:

| level | binding case | worst edge | vs ±27 mV |
|---|---|---|---|
| l0 | `sf_mm`, 2.97 V, lower edge | −180.59 mV | 6.69× |
| l1 | `sf_mm`, 2.97 V, lower edge | −177.53 mV | 6.58× |
| l2 | `sf_mm`, 2.97 V, lower edge | −173.08 mV | 6.41× |
| l3 | `sf_mm`, 2.97 V, lower edge | −168.27 mV | 6.23× |

Two readings worth stating explicitly:

- **The binding case is the low side, not the high side.** At `sf` the process
  term and the 2.97 V supply term have the same sign and stack. The widely quoted
  `fs_mm` +142.23 mV is the worst *upper* edge at 3.3 V, and it is not the worst
  case.
- **The +19.6 mV systematic offset currently helps the binding case.** It is
  positive and the binding edge is negative, so removing (d) in isolation makes
  the binding case *worse* (see §8). Any fix aimed at (d) alone must be argued
  against the low-side edge, not the tt offset.

## 6. Where the error actually lives

The two benches together attribute contributor (d) without any new simulation.
`sim/tb_ref_droop` measures the reference and tap ladder with an **ideal**
comparator; `sim/tb_threshold_accuracy` measures the **real** detector. Both at
tt / 27 °C / 3.3 V. The difference is the comparator's systematic input offset:

| level | reference + ladder (`tb_ref_droop`) | full detector (`tb_threshold_accuracy`) | comparator's share |
|---|---|---|---|
| l0 | +0.52 mV | +19.37 mV | **+18.85 mV** (97.3 % of (d)) |
| l1 | +0.30 mV | +19.03 mV | +18.73 mV (98.4 %) |
| l2 | +0.09 mV | +18.63 mV | +18.54 mV (99.5 %) |
| l3 | −0.13 mV | +18.25 mV | +18.38 mV (100.7 %) |

So **(d) is a comparator offset, not a reference or ladder error**, while (a)
is a reference error that the tap ladder passes through unchanged: the same
`tb_ref_droop` record gives `vth`/`vref` = 0.723436 at 3.3 V and 0.723432 at
2.97 V, constant to 4.3 × 10⁻⁶, so the ladder and select mux contribute
essentially none of the supply shift. Two different blocks own the two
systematic terms. Caveats: the two records are
dated 2026-10-23 and 2026-11-05, measure different netlists (`threshold_ref` vs
`detector_top`), ran different `klt` versions, and used different stimuli (DC
operating points vs a 250 µs ramp); the attribution is a difference of two
benches, not a single measurement of the comparator offset.

This split applies to the **systematic** term only. It says nothing about how the
*mismatch* term (c) divides between the reference/ladder and the comparator input
pair — see §7.

## 7. What no committed record measures

| Unmeasured contribution | Evidence it is absent | Bench that would measure it |
|---|---|---|
| **Temperature**, −40 °C and 125 °C | of the 38 committed record files under `sim/`, the 16 that state a temperature all read `27 C`; no record mentions −40 °C or 125 °C | `sim/tb_threshold_accuracy` corner grid (#34) and a `sim/tb_threshold_mc` re-run over the temperature axis of the PVT box (#35) |
| **The high supply corner, 3.63 V** | no committed record mentions 3.63 V (the only tree hit is `sim/tb_rail_model_check/src/ldo_3v3in_1v8out.sch`, a source, not a record); `tb_ref_droop` measured the 3.3 → 2.97 V low side only | `sim/tb_ref_droop` extended to the 3.63 V corner spec row 2 requires — now owned by #83 |
| **Split of mismatch (c) between reference/ladder and comparator input pair** | `tb_threshold_mc` varies `design/detector_top.spice` as a whole; sections are per level/corner and `source_corners` is `[]`, so there is no per-subcircuit attribution | a mismatch MC partitioned by subcircuit (reference/ladder vs `design/comparator.sch` input pair), e.g. per-block `vary` sections in `sim/tb_threshold_mc` |
| **The comparator's *supply*-dependent offset** | `tb_ref_droop` reaches 2.97 V but with an ideal comparator; `tb_threshold_accuracy` uses the real comparator but only at 3.3 V; `tb_supply_headroom` runs 2.97 V transiently and records latency/assertion, never a static trip point | `sim/tb_threshold_accuracy` re-run at the supply corners (it already takes `VSUP`) — part of #83's scope |
| **Process/mismatch box at any supply other than 3.3 V** | `tb_threshold_mc`'s request fixes `supply_v: {"Vdd": [3.3]}` (`gen_requests.py:30`) | `sim/tb_threshold_mc` with the supply as a corner axis (#35) |

**The 3.63 V corner is plausibly the binding one and no committed record covers
it.** Supply sensitivity is positive-going with supply and `fs` is also positive,
so at 3.63 V/`fs` the two would *stack* rather than cancel as they do at
2.97 V/`fs`. Extrapolating the measured two-point slope of §3 linearly:

| level | (a) @ 3.63 V, extrapolated | `fs_mm` upper edge | vs ±27 mV |
|---|---|---|---|
| l0 | +73.16 mV | +215.39 mV | 7.98× |
| l1 | +71.62 mV | +211.69 mV | 7.84× |
| l2 | +69.33 mV | +206.44 mV | 7.65× |
| l3 | +67.03 mV | +201.10 mV | 7.45× |

**These four rows are an extrapolation from a single measured two-point slope,
not a measurement.** Treat them as a reason to run the bench, nothing more.
#83 reports a direct 3.63 V probe of `vth` (code 00 = 1.79409 V, i.e. +65.57 mV
on the 3.3 V value — slightly sub-linear against the +73.16 mV above), and that
probe reproduces this note's 2.97 V and 3.3 V tap voltages exactly; but it is a
figure in an issue body, **not a committed record**, so it is cited here as
corroboration only. Committing it is #83's acceptance criterion.

## 8. Reduction needed to fit ±27 mV at 3σ

Taken at the binding case of §5: **level l0, `sf_mm`, detector supply 2.97 V,
lower edge −180.59 mV**. Against a −27 mV bound, **153.59 mV must come out.**

One contributor eliminated entirely at a time:

| remove entirely | remaining edge | fits ±27 mV? |
|---|---|---|
| (a) supply, −73.16 | −107.43 mV | no, over by 80.43 mV |
| (b) corner, −87.37 | −93.22 mV | no, over by 66.22 mV |
| (c) mismatch, ±39.63 | −140.95 mV | no, over by 113.95 mV |
| (d) systematic, +19.57 | **−200.16 mV** | no — **worse by 19.57 mV** |

The (a) row's remaining edge is unchanged by the §3 correction: deleting the
whole term also deletes the reference-and-ladder tt offset the old figure
wrongly carried, so −107.43 mV / 80.43 mV hold before and after.

And at the worst *upper* edge (l0, `fs_mm`, 3.3 V, **+142.23 mV**, 115.23 mV to
remove):

| remove entirely | remaining edge | fits ±27 mV? |
|---|---|---|
| (b) corner, +85.34 | +56.88 mV | no, over by 29.88 mV |
| (c) mismatch, ±37.31 | +104.92 mV | no, over by 77.92 mV |
| (d) systematic, +19.57 | +122.65 mV | no, over by 95.65 mV |

**No single contributor can be eliminated to meet the row, at either edge.** A
uniform scaling of all terms needs `k = 27 / 180.59 = 0.150` — **every
contributor cut by 85 %** (`k = 27 / 142.23 = 0.190`, an 81 % cut, for the upper
edge alone).

There is also a floor below which no amount of work on (a) and (b) helps.
Suppose the reference were made perfectly supply-independent and the design
perfectly process-independent, so `(a) = (b) = 0`. What remains at tt is
`(d) + (c) = +19.57 ± 36.79 mV`, i.e. a −17.22 … +56.37 mV band — still
**2.09×** the row. Stronger still: **the mismatch term alone busts the row.**
`(c)` at `tt_mm`/l0 is ±36.79 mV against a ±27 mV bound — **1.36× over with
every other contributor set to zero.** Any route to row 5 untrimmed must shrink
device mismatch by at least 27 %; no combination of supply, process and
systematic fixes can substitute for it.

**That is the conclusion of this note.** It reports the gap; it does not close
it. Row 5's ±27 mV, its 3σ form, N ≥ 300, and its untrimmed status are ratified
(row 5, DR-002) and are not relaxed here. The consequences — a trim (which
DR-002 §3 says needs a superseding decision record), a reference topology with a
supply-rejection term (#83 decides, #90 implements), a larger comparator input
pair, or an operator decision to move the band — belong in a decision record or
in those issues.

## 9. Reading the record's two validity flags correctly

Both flags in `sim/tb_threshold_mc/records/2026-11-06/record.txt` are easy to
misreport as DR-002 shortfalls. Neither is one.

- **`sample_size=insufficient` (14 of 24 sections) is not a DR-002 shortfall.**
  DR-002 §1 requires N ≥ 300 per corner, and the sibling `klt-yield.json`'s
  `converged_n` reads `verdict: sufficient` (300 / 300) in **all 24** sections.
  The
  `insufficient` flag is klt's *yield-confidence-interval tightness* check
  against a requested `target_ci_halfwidth: 0.01`. In the 14 flagged sections
  N = 300 resolves the yield *fraction* only to `observed_ci_halfwidth`
  0.0134–0.0532, and `required_n` to tighten that runs 381–8016 (e.g.
  `vtrip_l0_tt_mm`: ±0.0528 observed, `required_n: 7910`). The campaign is
  adequately sampled for the 3σ bound DR-002 grades; it is under-sampled only
  for a tight *yield-fraction* estimate, which row 5 does not ask for.
- **`neg_control=not_detected` (12 of 24 — exactly the `ss`/`sf`/`fs` sections at
  every level) is a floor artifact, not an inert harness.** In each of those 12
  sections the *nominal* yield is already 0.000–0.013 while the control's is
  0.033–0.057: there is no headroom left to degrade. The control does show
  degradation in all 12 sections that have headroom (`tt`/`ff`/`mc`: nominal
  0.70–0.98 → control 0.033–0.057). DR-002 §2 asks for a control that *fails the
  grade*, and it fails in all 24.

All 24 sections also read `normality.verdict: consistent` (Anderson–Darling),
which is what makes quoting a 3σ bound from `sd` legitimate at all.

One wording note for anyone citing the record: it carries **one**
`klt yield status: fail` header line plus **24** per-section lines reading
`status=fail`. `grep -c 'klt yield status'` returns 1, not 24; quote the
per-section `status=fail` when citing "all 24 sections". `klt-yield.json`
confirms `measurement_count: 24`, `sample_count: 7200` (24 × 300).

## 10. Related work

- **#35** — runs the row 5 campaign; parked on a row-5 design/spec decision. This
  note is the numeric input that decision needs. #35 stays parked; nothing here
  changes that.
- **#34** — the corner grid that would add the temperature axis of §7.
- **#83** — the 3.63 V supply corner and the decision on whether a reference
  "generated from the detector supply" can meet row 5 untrimmed. §3 and §7 are
  its direct inputs.
- **#77 / PR #84** — revises the comparator and regenerates
  `design/detector_top.spice`. §6 attributes 97–101 % of contributor (d) to the
  comparator, so (d) is the term most likely to move when #84 lands. Re-read it
  against the new netlist sha rather than carrying these figures forward.
