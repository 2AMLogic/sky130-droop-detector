#!/usr/bin/env python3
"""Sequence check for the row 10 flag logic against an executable reference.

Reads a trace file written by sim/tb_flag_logic (columns: time, live_in, clr, live,
sticky; ngspice `wrdata`, volts / seconds), digitises it with the 1.8 V CMOS
levels of spec/target-spec.md "Output" (VOH >= 1.44 V, VOL <= 0.36 V; anything between is
an invalid level and fails), and steps a reference model of the spec:

  live   = live_in                              (after a settling window)
  sticky : set when live_in, else cleared by clr, else holds
           (set-dominant: a CLR while live_in persists does not clear it)

Each output sample is compared with the model except within SETTLE ns after any
input edge (propagation delay is graded by tb_latency, not here). A cold start is
required: sticky must be 0 once the first CLR has been seen.

usage: check.py TRACE [--live-in-high V] [--settle NS] [--break MODE]
  --break clr-ignored|sticky-follows-live|clr-dominant
      deliberately broken sequence (negative control): the OBSERVED sticky column is
      rewritten to a broken behaviour before checking; the check must then fail.
Exit 0 = sequence ok, 1 = sequence violation, 2 = bad input.
"""
import argparse
import sys

VOH, VOL = 1.44, 0.36


def load(path):
    rows = []
    with open(path) as f:
        head = f.readline().split()
        if len(head) < 5:
            sys.exit("check.py: trace header needs 5 columns")
        for ln in f:
            c = ln.split()
            if len(c) >= 5:
                rows.append([float(x) for x in c[:5]])
    if len(rows) < 100:
        print("check.py: trace too short", file=sys.stderr)
        sys.exit(2)
    return rows


def digital(v, lo, hi):
    if v >= hi:
        return 1
    if v <= lo:
        return 0
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace")
    ap.add_argument("--live-in-high", type=float, default=1.65)
    ap.add_argument("--settle", type=float, default=5.0)
    ap.add_argument("--break", dest="brk", choices=["clr-ignored", "sticky-follows-live", "clr-dominant"])
    a = ap.parse_args()
    rows = load(a.trace)
    settle = a.settle * 1e-9
    # resample on a 0.5 ns grid (rows are non-uniform)
    step = 0.5e-9
    t_end = rows[-1][0]
    samples = []
    j = 0
    t = 0.0
    while t <= t_end:
        while j + 1 < len(rows) and rows[j + 1][0] <= t:
            j += 1
        samples.append((t, rows[j][1], rows[j][2], rows[j][3], rows[j][4]))
        t += step

    ok = True
    errs = []
    sticky_m = None          # reference sticky state (None until the cold-start CLR)
    last_edge = -1.0
    prev_in = prev_clr = None
    n_checked = 0
    saw_set = saw_clear = saw_persist_clr = saw_live_fall_hold = False
    obs_sticky_broken = 0    # state for --break modes
    for (t, li_v, clr_v, live_v, st_v) in samples:
        li = digital(li_v, 0.3, a.live_in_high)
        clr = digital(clr_v, 0.3, 1.65)
        if li is None or clr is None:
            continue         # input mid-edge
        if (prev_in is not None and li != prev_in) or (prev_clr is not None and clr != prev_clr):
            last_edge = t
        prev_in, prev_clr = li, clr
        # reference sticky
        if li:
            sticky_m = 1
        elif clr:
            sticky_m = 0
        # observed sticky, possibly broken for the negative control
        obs = digital(st_v, VOL, VOH)
        if a.brk == "clr-ignored":
            obs_sticky_broken = 1 if (li or obs_sticky_broken) else 0
            obs = obs_sticky_broken
        elif a.brk == "sticky-follows-live":
            obs = li
        elif a.brk == "clr-dominant":
            obs_sticky_broken = 0 if clr else (1 if (li or obs_sticky_broken) else 0)
            obs = obs_sticky_broken
        if sticky_m is None:
            continue         # before the first CLR / flag: cold start, state unknown
        if t - last_edge < settle:
            continue
        # live is combinational from live_in
        lv = digital(live_v, VOL, VOH)
        n_checked += 1
        if lv is None:
            errs.append(f"t={t*1e9:.1f} ns: live = {live_v:.3f} V is an invalid level (between VOL and VOH)")
        elif lv != li:
            errs.append(f"t={t*1e9:.1f} ns: live = {lv}, expected {li} (live_in = {li})")
        if obs is None:
            errs.append(f"t={t*1e9:.1f} ns: sticky = {st_v:.3f} V is an invalid level (between VOL and VOH)")
        elif obs != sticky_m:
            errs.append(f"t={t*1e9:.1f} ns: sticky = {obs}, expected {sticky_m} (live_in = {li}, clr = {clr})")
        if sticky_m:
            saw_set = True
        if sticky_m == 0 and saw_set:
            saw_clear = True
        if clr and li and sticky_m == 1:
            saw_persist_clr = True
        if (not li) and sticky_m == 1 and obs == 1:
            saw_live_fall_hold = True
    for name, seen in (("sticky set", saw_set), ("sticky clear", saw_clear),
                       ("CLR while the condition persists", saw_persist_clr),
                       ("sticky held after the condition ended", saw_live_fall_hold)):
        if not seen:
            errs.append(f"coverage: sequence never exercised: {name}")
    if n_checked < 50:
        errs.append(f"coverage: only {n_checked} samples checked")
    if errs:
        for e in errs[:20]:
            print("VIOLATION:", e)
        print(f"check.py: FAIL ({len(errs)} violation(s), {n_checked} samples checked)")
        return 1
    print(f"check.py: ok ({n_checked} samples checked; set, clear, CLR-while-persisting, hold all exercised)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
