# verification

Truth-table / sequence checks that are not analog benches. See the repo README for scope.

- `flag_logic/` — spec row 10 (sticky flag, CLR, live flag): `verification/flag_logic/run.sh`
  runs `sim/tb_flag_logic` and grades its traces with `check.py`, an executable reference of
  the spec's Output section (live follows the filtered flag; sticky sets on the first
  assertion, CLR clears it, a CLR while the condition persists re-sets it; VOH >= 1.44 V,
  VOL <= 0.36 V). Negative control: the same traces with a deliberately broken flag sequence
  (CLR ignored, sticky follows live, CLR dominant) must fail. Records, including the
  negative-control output, are in `flag_logic/records/`. Simulated, tt / 27 C / 3.3 V.
