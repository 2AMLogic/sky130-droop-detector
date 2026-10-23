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
