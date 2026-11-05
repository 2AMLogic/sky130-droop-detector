# sim

Testbenches and PVT corner results (ngspice). Results here are append-only
evidence.

- `pdk.json` — pinned PDK revision (open_pdks commit).
- `toolchain.json` — ngspice / xschem / klayout-tools versions.
- `smoke/` — one-command check that the pinned PDK and toolchain run:
  `sim/smoke/run.sh`. It fails closed on a missing or mismatched PDK
  revision. Smoke is tt / 27 C / 1.8 V by design; PVT corners belong to the
  spec benches, not here. Records and negative-control output are in
  `smoke/records/`. `package.json`'s `check:ci`, `check:all` and `test` run it
  with `RECORD=/dev/null`, so routine checks never touch `smoke/records/`.
- `tb_rail_model_check/` — the rail model checked before any detector row
  relies on it (target-spec row 1): `sim/tb_rail_model_check/run.sh`. It
  asserts the behavioural envelope (W1–W5, the LDO-compliant transient, the
  row 6/7 fast-edge droops) and reports, without grading, the `sky130-ldo`
  netlist at its pinned commit under the four C_out/ESR corner points. The
  four points are `klt sim --batch-set` requests and run on the batch fleet.
  tt / 27 C / 3.3 V only; not part of `npm test`. Records and negative
  controls are in `tb_rail_model_check/records/`.
- `tb_threshold_select/` — static trip level per 2-bit select code of
  `design/threshold_ref.spice` against an ideal comparator and an ideal
  monitored-rail source: `sim/tb_threshold_select/run.sh`.
- `tb_ref_droop/` — reference/level shift with the monitored rail collapsing
  1.8 → 0.9 V and the detector supply at 2.97 V, ideal sources (coupling check
  only; the rail-model re-run waits on `tb_rail_model_check`):
  `sim/tb_ref_droop/run.sh`. Both benches are tt / 27 C, fail closed on the PDK
  pin (`PDK_PIN` points a negative control at a different pin file), write the
  record to `$RECORD` (stdout by default) and are not wired into
  `package.json` checks because they write records. Records, including the
  wrong-`sources_line` negative controls, are in each bench's `records/`.
- `tb_comparator/` — nominal-corner (tt / 27 C / 3.3 V) latency at 100 mV
  overdrive, input-referred offset and idle supply current of
  `design/comparator.spice` at the 1.728 V and 1.584 V taps, ideal rail source,
  comparator only: `sim/tb_comparator/run.sh`. Same PDK-pin fail-closed
  behaviour and `PDK_PIN` negative control as the benches above; records in
  `tb_comparator/records/`. Not wired into `package.json` checks.
- `tb_latency/`, `tb_min_width/`, `tb_supply_headroom/` — the dynamic benches of
  `design/detector_top.spice` (spec rows 6, 7, 2) against the behavioural-envelope
  rail (1 ns edges, 1 kohm load; an assumption, not a measurement), tt / 27 C /
  3.3 V single corner, one local ngspice process each (cases play inside it):
  `sim/tb_latency/run.sh` (100 mV overdrive, 4 levels x 3 start points plus the
  ideal step alongside, t = 0 at full overdrive, `live` at 50% of swing),
  `sim/tb_min_width/run.sh` (2 / 10 / 50 ns droops, every level, `live` must
  reach VOH), `sim/tb_supply_headroom/run.sh` (detector supply 3.3 / 2.97 V and
  2.97 V sagging by an assumed 0.1 / 0.3 V, droop must flag, sag alone must not).
  Same PDK-pin fail-closed behaviour and `PDK_PIN` negative control as the
  benches above, plus `NEGCTL_DROP_KEY=<result key>` for the missing-result
  control. A row the design misses is reported in the record, not relaxed;
  corner campaigns are #34/#35. Records and negative controls in each
  `records/`. Not wired into `package.json` checks.
