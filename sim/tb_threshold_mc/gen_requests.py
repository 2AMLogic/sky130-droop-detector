#!/usr/bin/env python3
"""Write the klt sim requests for tb_threshold_mc into <workdir> (usage: gen_requests.py <workdir>).

12 requests: for each of the 4 select codes, a mismatch request (5 *_mm process
sections, vary=mismatch), a process-MC request (`mc` section, vary=both), and a
negative-control request (ladder segment XR2 lengthened-shortened, tt_mm, vary=mismatch).
Seed, N and the corner box are constants here and are the recorded values."""
import json, pathlib, re, sys

SEED = 20261105
N = 300
LEVELS = [(0, 0, 0, 1.728), (1, 3.3, 0, 1.692), (2, 0, 3.3, 1.638), (3, 3.3, 3.3, 1.584)]
MM = ["tt_mm", "ss_mm", "ff_mm", "sf_mm", "fs_mm"]
SPAN = 0.25   # sweep nominal +/- 250 mV, 0.5 mV steps (static trip, slow ramp)
CTL_FROM, CTL_TO = "XR2 t0 vref gnd sky130_fd_pr__res_xhigh_po_1p41 L=94.073", "XR2 t0 vref gnd sky130_fd_pr__res_xhigh_po_1p41 L=88"

work = pathlib.Path(sys.argv[1]); work.mkdir(parents=True, exist_ok=True)
here = pathlib.Path(__file__).resolve().parent
top = (here / ".." / ".." / "design" / "detector_top.spice").read_text()
assert CTL_FROM in top, "ladder segment line not found in design/detector_top.spice"
(work / "detector_top.spice").write_text(top)
(work / "detector_top_ctl.spice").write_text(top.replace(CTL_FROM, CTL_TO))
body = (here / "tb_threshold_mc.spice").read_text()

def request(name, tb, procs, vary, nominal):
    return {
        "netlist": tb,
        "models": {"pdk": "sky130A", "lib": "libs.tech/combined/sky130.lib.spice"},
        "corners": {"process": procs, "temperature_c": [27], "supply_v": {"Vdd": [3.3]}},
        "monte_carlo": {"n": N, "seed": SEED, "vary": vary},
        "analysis": {"kind": "dc", "args": f"Vrail {nominal + SPAN:.4f} {nominal - SPAN:.4f} -0.0005"},
        "measurements": [{"name": "vtrip", "unit": "V",
                          "spice": ".meas dc vtrip WHEN v(xdut.flag)=1.65 RISE=1"}],
        "options": {"timeout_s": 90},
        "batch": {"job_ceiling_check": "split"},
    }

for k, v0, v1, nom in LEVELS:
    for tag, net, procs, vary in (("mm", "detector_top.spice", MM, "mismatch"),
                                  ("mc", "detector_top.spice", ["mc"], "both"),
                                  ("ctl", "detector_top_ctl.spice", ["tt_mm"], "mismatch")):
        tb = f"tb_l{k}_{tag}.spice"
        (work / tb).write_text(body.replace("__NETLIST__", net).replace("__S0__", str(v0)).replace("__S1__", str(v1)))
        (work / f"l{k}_{tag}.request.json").write_text(json.dumps(request(f"l{k}_{tag}", tb, procs, vary, nom), indent=1))
print(json.dumps({"seed": SEED, "n": N, "levels": [l[3] for l in LEVELS], "process_mm": MM, "process_mc": ["mc"]}))
