#!/usr/bin/env python3
"""Assemble the klt yield sample document and limits file from the batch reports.
usage: build_yield.py <outdir-with-reports> <samples.json> <limits.json>
Fails closed (exit 3) if any sample lacks a numeric vtrip or a report is missing/short."""
import json, pathlib, sys

LEVELS = [1.728, 1.692, 1.638, 1.584]
BAND = 0.027  # +/-1.5 % of 1.8 V (target), spec row 5
N = 300
out = pathlib.Path(sys.argv[1])

def load(name):
    p = out / f"{name}.request" / "report.json"
    if not p.is_file():
        sys.exit(f"FAIL: missing report {p}")
    return json.loads(p.read_text())

def samples(rep, proc):
    vals = [c["measurements"][0]["value"] for c in rep["corners"] if c.get("process") == proc]
    if len(vals) != N or any(not isinstance(v, (int, float)) for v in vals):
        sys.exit(f"FAIL: {proc}: need {N} numeric samples, got {len(vals)} ({sum(isinstance(v,(int,float)) for v in vals)} numeric)")
    return vals

meas, limits = [], {}
for k, nom in enumerate(LEVELS):
    mm, mc, ctl = load(f"l{k}_mm"), load(f"l{k}_mc"), load(f"l{k}_ctl")
    ctl_s = samples(ctl, "tt_mm")
    groups = {p: samples(mm, p) for p in ("tt_mm", "ss_mm", "ff_mm", "sf_mm", "fs_mm")}
    groups["mc"] = samples(mc, "mc")
    for g, s in groups.items():
        name = f"vtrip_l{k}_{g}"
        meas.append({"name": name, "samples": s,
                     "negative_control": {"samples": ctl_s, "description": "ladder segment XR2 L=88 (was 94.073), tt_mm mismatch MC, same seed/N"}})
        limits[name] = {"min": round(nom - BAND, 6), "max": round(nom + BAND, 6), "target_sigma": 3,
                        "min_converged_samples": N, "spec_row": "5"}
pathlib.Path(sys.argv[2]).write_text(json.dumps({"measurements": meas}))
pathlib.Path(sys.argv[3]).write_text(json.dumps({"confidence": 0.95, "measurements": limits}, indent=1))
