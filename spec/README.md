# spec

- [`target-spec.md`](target-spec.md) — the target specification (every row:
  target, fallback, stretch, binding conditions, planned testbench) and the
  `sky130-ldo` interface rows it binds to.
- [`decision-records/`](decision-records/) — append-only decision records.
  [`DR-001`](decision-records/DR-001-target-spec-ratification.md) ratifies
  the table.

Spec changes go through a new decision record; a ratified row is never
edited to match a result.
