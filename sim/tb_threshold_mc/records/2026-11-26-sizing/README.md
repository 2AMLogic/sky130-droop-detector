# Code-00 mismatch sizing, 2026-11-26

**SIMULATED, pre-layout.** Widening comparator M3/M4 to 16 µm at L = 0.5 µm is the candidate for the fleet run. The local first-order prediction is σ = 8.318 mV (3σ = 24.96 mV), with 12 µm² of additional gate area. The signed nominal trip error is still +12.43 mV. The batch upload from this worker failed because the `batch-runner-submit` profile was unavailable. The current-netlist Monte Carlo baseline, candidate mean, sample σ and statistical control verdict are pending. The trial geometry is in [input-pair.patch](input-pair.patch).

## Variance by device group

Each row uses the complete detector at tt, 3.3 V, 27 °C, code 00, on main `01db265`. Each trial changes one group. Areas use drawn W × L, excluding contacts, isolation and routing. The variance columns are in mV². The trip column gives the nominal DC rail voltage at the upward 1.65 V crossing of `xdut.flag`.

| Geometry | Added area (µm²) | Ladder R2–R6 | Pair M3/M4 | All other devices | Predicted σ (mV) | Nominal trip (V) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Main, pair 4/0.5 µm | 0 | 5.15 | 68.62 | 68.16 | 11.913 | 1.74137 |
| Wider ladder, pair 4/0.5 µm | 1520.17 | 1.24 | 68.62 | 68.16 | 11.748 | 1.74137 |
| Pair 8/1 µm | 12 | 5.12 | 17.00 | 75.99 | 9.905 | 1.73391 |
| Pair 16/2 µm | 60 | 5.12 | 4.25 | 86.40 | 9.786 | 1.73351 |
| **Pair 16/0.5 µm** | **12** | **5.15** | **17.13** | **46.91** | **8.318** | **1.74043** |

On main, the input pair accounts for 48.4% of predicted variance, the ladder 3.6%, and the remaining devices 48.0%. The load mirror M5/M6 contributes 57.07 mV² of that remainder. Widening the input pair at fixed length halves each input device's threshold mismatch. It also reduces sensitivity to the mirror at the new operating point, bringing the mirror contribution down to 35.82 mV². If the fleet result exceeds 9 mV, the next sizing experiment is a matched-area increase of M5/M6 at fixed mirror ratio, followed by the same comparison. The two longer-channel input-pair trials show how a change in operating point can increase the mirror contribution.

The width-only trial predicts a 30.2% reduction relative to the local main prediction, with 2.04 mV of centered 3σ margin against 27 mV. Its predicted σ is 32.2% below the historical fleet σ of 12.264 mV. The November 6 fleet result used another netlist and gave a signed mean error of +19.57 mV. A same-seed fleet comparison is needed to quantify the actual reduction. The width-only trial's nominal error plus predicted 3σ is +37.38 mV. Centering and the full row 5 corner campaign remain separate measurements. [November 6 fleet record](../2026-11-06/record.txt)

## Ladder loading and four taps

The original fixed width is 1.41 µm. R2–R6 lengths in order are 94.073, 5.123, 7.685, 7.685 and 225.433 µm. The trial uses the 2.85 µm resistor with lengths 194.123, 10.574, 15.860, 15.860 and 465.187 µm. These lengths match the tt zero-bias series resistance of each original segment, including both heads, before rounding to 1 nm. In the pinned xhigh model at 25 °C that resistance is `2000*(L−0.0592)/(W−0.056) + 2*188.2/(W−0.056+1.41)` Ω at zero substrate and terminal bias. The simulations below include bias and temperature effects.

| Ladder | Poly area (µm²) | Loaded Vref (V) | Ladder current (µA) | Vref/current (kΩ) | Tap/Vref, codes 00, 01, 10, 11 |
| --- | ---: | ---: | ---: | ---: | --- |
| Original, including width-only pair trial | 479.40 | 2.3893165 | 4.759881 | 501.9698 | 0.7234366, 0.7082785, 0.6855879, 0.6628966 |
| Wider ladder | 1999.57 | 2.3893168 | 4.759854 | 501.9727 | 0.7234371, 0.7082784, 0.6855884, 0.6628976 |

The larger ladder reduces total predicted σ by 1.4%. The fleet candidate therefore uses the original ladder and reference topology.

| SIMULATED tt, 27 °C, 3.3 V | Code 00 | Code 01 | Code 10 | Code 11 |
| --- | ---: | ---: | ---: | ---: |
| Selected tap, both main and width-only trial (V) | 1.72852 | 1.69229 | 1.63810 | 1.58386 |
| Main live-output trip (V) | 1.74137 | 1.70507 | 1.65073 | 1.59640 |
| Width-only trial live-output trip (V) | 1.74043 | 1.70412 | 1.64976 | 1.59542 |
| Change in nominal trip (mV) | −0.94 | −0.95 | −0.97 | −0.98 |

The selected-tap and live-output rows use the repo's `tb_threshold_select/run.sh` and `tb_threshold_accuracy/run.sh` respectively. Both passed. The comparator and top schematic exports for the width-only trial also passed `klt netlist --block --check` with `design/xschemrc` and xschem 3.4.7. The patch preserves main's netlist source-path comments so its bytes reproduce across checkout locations.

## Sensitivity method

Local simulations used ngspice 47, one thread, open_pdks `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7`, and the combined model library with SHA-256 `48de7c677e2c6e7d09b2559279de9f818be71010a4aa933d728eb4db3b133c84`. The calculation measures the DC response to each independent mismatch term using the nominal tt operating point and the coefficients used by tt_mm. It takes the square root of the sum of all squared one-sigma trip shifts, including the residual devices. The signed shifts for all 84 terms are in [sensitivities.csv](sensitivities.csv).

- For each MOS instance, perturb BSIM4 `delvto` by ±0.05 times the model's σ. The 5 V NMOS and PMOS coefficients are 8.2 and 12 mV·µm respectively, divided by √(W·L·mult).
- For each xhigh resistor, the relative body σ is 0.0464/√(W·L·mult). Each head has relative σ = 0.063/√(W·mult). At fixed terminal voltages, a fractional increase ε in resistance changes the branch current by −ε·I to first order. A DC test source across each element applies that derivative using its nominal current at the trip. With the actual R2 body model perturbed by ±1σ, the two DC crossings on main were 1.7394884 and 1.7432569 V. Their half-difference is −1.8843 mV, matching the current-injection estimate.
- Each perturbation uses a descending 10 µV DC step around the crossing. Capacitors are open at DC. Repeating the width-only calculation at ±0.10σ gives 8.31835 mV total, versus 8.31836 mV at ±0.05σ.

To reproduce a column, export that geometry's block and top with xschem and run the following command. `TOP` is the top netlist, `LIB` is the pinned combined `sky130.lib.spice`, and `OUT` is a CSV filename. The adjacent log contains the DC crossings and tap voltages.

```sh
python3 sensitivity.py "$TOP" "$LIB" "$OUT"
```

## Fleet comparison for issue 167

Run from the repository root with a fresh output path. The preparation script reads the generator and design from `01db265`, applies the trial patch in scratch, and verifies that each control differs from its own nominal copy only by XR2 L = 94.073 → 88 µm. A local nominal DC check moves the crossing by +30.75 mV on main and +30.76 mV on the candidate. All four batch dry runs expanded to the same 300 sample indices and seeds.

```sh
set -e
rec=sim/tb_threshold_mc/records/2026-11-26-sizing
work=$(mktemp -d)
bash "$rec/prepare-fleet.sh" "$work/requests"
for variant in baseline wide; do
    (
        cd "$work/requests/$variant"
        klt sim --backend batch --batch-set l0_mm.request.json l0_ctl.request.json \
            --max-in-flight 2 --max-concurrent-jobs 3 --capacity-retries 3 \
            --wait-for-capacity 900 -o out --format json > set.json
    )
done
```

| Fleet input | Main SHA-256 | Width-only trial SHA-256 |
| --- | --- | --- |
| Nominal | `c6307eb13bb46c8c3d150dbf57605ec9716e35da9f6c8b69191695a79740ee93` | `e033d5e328828c3dd36831f21ddd251ecb49392d649f43e9c887ec1a2d07a3bd` |
| XR2 control | `d20d7e8561ea1c00a9b4fe306ba37e36cd3767efc3ed7d97683255cce20030d4` | `221749e7910aadf072c2df5c48411cba49c47e9173e589ae55e02bec50893fd6` |

The fleet requests use tt_mm mismatch only, code 00, 27 °C, 3.3 V, seed 20261105, and the original 1.978 → 1.478 V down-sweep in 0.5 mV steps. Require 300 converged finite `vtrip` values per request, identical per-draw seeds and worker model/engine identities, and a detected negative control for each nominal sample set. Record the job receipts, signed mean error relative to 1.728 V, sample spread and 3σ before selecting production geometry.
