# sky130-droop-detector — agent instructions

Open-source canary block: a fast supply-droop detector on the SkyWater
sky130 PDK, the companion to `sky130-ldo`, designed and verified by AI
agents.

- **PDK**: SkyWater sky130 (open PDK, google/skywater-pdk). Analog: xschem +
  ngspice. If the flag logic grows past a few cells: cocotb + Icarus, Yosys,
  OpenROAD. Layout, DRC, and LVS through klayout-tools (`klt`).
- **Deciding while the rail collapses is the point, and the risk.** The
  detector must resolve a nanosecond-scale droop while the monitored rail,
  and possibly its own supply, is moving. The reference must not droop with
  the rail, the comparator must not slow down when its headroom shrinks, and
  the glitch filter must not hide a real droop or flag ordinary regulation
  ripple. Which rail powers the detector is the first architectural
  decision; argue it in a decision record. Never verify against an ideal
  stepped source alone — the rail model is part of every testbench.
- **Scope discipline.** The regulator comes from `sky130-ldo`. Do not design
  one here. Take its ratified output behaviour (1.8 V ±2%, 0–50 mA, its load
  transient and C_out/ESR window) as the interface, cite that repo at a
  named commit in `spec/`, and stop. If a finding
  here bears on the LDO (a droop it should not allow, an interface gap),
  file it on `sky130-ldo`. `sky130-comparator` builds a clocked comparator on
  this PDK: record it in `reuse.lock.json`'s `in_tree` ledger with
  `status: evaluate`, and adopt it or record why not once it is
  simulation-validated. The POR in `sky130-temp-por` is a different block;
  say so in the spec by name.
- **Friction protocol (the canary's job)**: every time klayout-tools is
  awkward, missing a capability, or wrong for what you need, file an issue at
  `2AMLogic/klayout-tools` describing the tool gap generically — that tracker
  is scoped to the tool, so keep design-specific detail out of it and describe
  the gap, not the design.
- **Verification is the product**: no claim without a testbench. PVT corners
  on every recorded result; `sim/` results are append-only evidence. Every
  simulated figure is labelled as simulated, with its corner and testbench.
- Spec changes go through `spec/` with a decision record; agents do not relax
  the ratified spec to make results pass.
- **Four thresholds at < 5 ns is the target.** One fixed threshold at < 20 ns
  is the fallback and < 1 ns is a stretch. Do not let the stretch drive the
  comparator architecture before the target closes.

<!-- BEGIN LOOM ORCHESTRATION -->
This repository uses [Loom](https://github.com/rjwalters/loom) for AI-powered development orchestration — see the Loom repository for the full guide (roles, labels, worktrees, configuration). When installed, Loom also writes a locally-substituted copy of that guide to `.loom/CLAUDE.md`.

Work is coordinated through `loom:` labels on issues and pull requests, and the same roles run either under `loom-daemon` or by hand in an attended session — daemon mode is optional. Create the labels once with `.loom/scripts/sync-labels.sh` (an install ships `.github/labels.yml` but does not create the labels on the forge). A pull request ready for review carries `loom:review-requested`; Judge reviews it and applies `loom:pr` (approved) or `loom:changes-requested`; Doctor fixes a `loom:changes-requested` pull request and returns it to `loom:review-requested`. Only a `loom:pr` pull request gets merged, and always via this repo's merge script (`.loom/scripts/merge-pr.sh`) — never a raw forge merge command such as `gh pr merge`. Full state machine: `.loom/docs/label-state-machine.md`.
<!-- END LOOM ORCHESTRATION -->

<!-- BEGIN REPO-SKILLS -->
This repository has [Repo Skills](https://github.com/rjwalters/repo) v0.24.3 installed —
general repository hygiene and environment commands invoked as `/repo:<command>`. Run
`/repo:help` for the command list, or see `.claude/skills/repo/SKILL.md` for the full
guide. Hygiene commands apply safe, reversible fixes by default and report each
change; run with `--ask` to review first, and `--prune` to allow irreversible
removals. Managed by `install.sh` — edit outside the markers only.
<!-- END REPO-SKILLS -->
