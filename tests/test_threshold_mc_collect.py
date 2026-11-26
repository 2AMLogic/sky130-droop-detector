#!/usr/bin/env python3
"""PDK-free guard: tb_threshold_mc keeps every row-5 group in its own coordinates.

Guards the collecting half of `sim/tb_threshold_mc` (#169). `build_yield.py` used to
select draws by process alone, so widening the corner box would have pooled different
temperatures and supplies into one population, and `run.sh` reused any collected report
whose status was `pass`, whatever netlist or request had produced it.

Part A drives `build_yield.py` with synthetic `klt sim` reports built from the
generator's own manifest: 36 reports, 216 groups x 300 draws plus their controls, a
different value for every (group, draw), rows shuffled. It checks the sample-set and
limits documents `klt yield` is fed, then one damaged report at a time:

  - a population removed, one draw removed, a duplicate draw substituted for the
    missing one (count preserved), a whole population relabeled to another temperature,
    control IDs with the wrong process, supply or index, a non-finite value, a draw
    filed under another supply, an unconverged draw, a missing control report, a stale
    or absent input hash, a report that does not echo the recorded seed.

Each must fail collection and name the affected group. Two draws that happen to share
a trip value are not a duplicate and must stay accepted.

Part B runs the real `run.sh` on a scratch tree with `klt` and `klt yield` replaced by
stubs (a fake PDK root satisfies the pin gate), so nothing is simulated or submitted,
and checks resume (reuse only on identical inputs; fresh output when the netlist, the
deck template or one level's request changes), the record's matrix / criterion /
control / hashes against the inputs actually used, and the exit statuses of an
undetected control, a completed failing grade and an unusable netlist. It also checks
that batch inputs and outputs resolve correctly for relative and absolute KEEP paths,
including a symlink followed by .., and that an unset KEEP is cleaned up (#180).

Repo files are copied, never modified. No PDK, no klt, no fleet.
"""
import hashlib
import json
import os
import pathlib
import random
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
BENCH = "sim/tb_threshold_mc"
COPIED = ("design/detector_top.spice", "sim/lib/levels.json", "sim/lib/pdk_pin.sh", "sim/pdk.json",
          BENCH + "/gen_requests.py", BENCH + "/build_yield.py", BENCH + "/run.sh",
          BENCH + "/tb_threshold_mc.spice")
SEED, N = 20261105, 300
BAND = 0.027   # spec row 5 target: +/-27 mV around each level's nominal
TEMPS = [-40, 27, 125]
SUPPLIES = [2.97, 3.3, 3.63]
MM = ["tt_mm", "ss_mm", "ff_mm", "sf_mm", "fs_mm"]
SECTIONS = MM + ["mc"]
CTRL_SHIFT = 0.060   # the ladder offset moves the trip about two bands away

RELATIVE_KEEP = "results"
INCOMPLETE = "lost_shard"

problems = []


def check(cond, msg):
    if not cond:
        problems.append(msg)
    return bool(cond)


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def vtag(v):
    return ("%.2f" % v).replace(".", "p")   # 2.97 V -> 2p97, as the generator writes it


def draw_value(g, i):
    """A trip value that depends on every coordinate of group g and on the draw index:
    groups that differ only in process, temperature or supply never share a list."""
    return round(g["nominal_v"] + SECTIONS.index(g["process"]) * 0.004
                 + TEMPS.index(g["temperature_c"]) * 0.0013
                 + SUPPLIES.index(g["supply_v"]) * 0.00037
                 + ((i * 7) % 11 - 5) * 0.00005, 9)


def nominal(g):
    return [draw_value(g, i) for i in range(N)]


def control(g):
    return [round(draw_value(g, i) + CTRL_SHIFT, 9) for i in range(N)]


def load(path):
    return json.loads(path.read_text())


def dump(rep):
    return json.dumps(rep, separators=(",", ":"))


def cell(rep, proc, temp):
    return [c for c in rep["corners"] if c["process"] == proc and c["temperature_c"] == temp]


def draw(rep, proc, temp, index):
    """The draw of a population identified by its sample_index (the rows are shuffled)."""
    return next(c for c in cell(rep, proc, temp) if c["monte_carlo"]["sample_index"] == index)


def real(path):
    return os.path.realpath(str(path))


def tree_hashes(dir_path):
    return {str(p.relative_to(dir_path)): sha256(p) for p in sorted(dir_path.rglob("*")) if p.is_file()}


def logged(path):
    if not path.is_file():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()]


def submitted_files(call):
    return [m["member"] for m in call["members"]]


def tail(proc):
    return "\n".join((proc.stderr.strip().splitlines() + proc.stdout.strip().splitlines())[-12:])


def expected_members(req):
    """One entry per request the runner submits, in its request order: the member name, the
    deck and the netlist the deck includes (all read by basename from the request directory,
    as the batch client reads them), and the populations a complete report must carry."""
    want = []
    for req_path in sorted(req.glob("l*_*.request.json")):
        request = load(req_path)
        deck = req / request["netlist"]
        include = next(ln.split('"')[1] for ln in deck.read_text(encoding="utf-8").splitlines()
                       if ln.startswith(".include "))
        want.append({"member": req_path.name, "deck": deck.name, "include": include,
                     "populations": request["monte_carlo"]["n"] * len(request["corners"]["process"])
                     * len(request["corners"]["temperature_c"])})
    return want


KLT_STUB = r'''#!/usr/bin/env python3
# Test double for tests/test_threshold_mc_collect.py. `klt --version`, `klt pdk find`
# (answers the fake PDK root) and `klt sim --batch-set`: reads each member's request, deck
# and included netlist by basename from the directory it is started in, as the batch
# client does, writes a synthetic passing report per member under -o, and logs the call.
# A synthetic trip sits on the level the request sweeps, and 60 mV above it -- outside
# the row-5 +/-27 mV band -- for the control copy, so klt yield judges the control detected.
# Anything else, or a member that cannot be read, exits non-zero. No real klt runs.
import hashlib, json, os, shutil, sys

args = sys.argv[1:]
if args[:1] == ["--version"]:
    print("klt 0.0.0 (stub for tests/test_threshold_mc_collect.py)")
    sys.exit(0)
if args[:2] == ["pdk", "find"]:
    if "--pdk-root" not in args:
        sys.exit("stub klt: pdk find without --pdk-root")
    print("root: " + args[args.index("--pdk-root") + 1])
    sys.exit(0)
if args[:2] != ["sim", "--batch-set"]:
    sys.exit("stub klt: unexpected invocation %r" % (args,))
members = []
for a in args[2:]:
    if a.startswith("--"):
        break
    members.append(a)
out = args[args.index("-o") + 1]
log = os.environ["STUB_SIM_LOG"]
call = sum(1 for _ in open(log)) + 1 if os.path.exists(log) else 1


def digest(name):
    with open(name, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


entry = {"call": call, "cwd": os.getcwd(), "out": out, "members": [], "requests": []}
for m in members:
    if not m.endswith(".request.json"):
        sys.exit("stub klt: not a request member: %s" % m)
    try:
        with open(m) as f:
            request = json.load(f)
        with open(request["netlist"]) as f:
            deck = f.read()
    except (OSError, ValueError, KeyError) as e:
        sys.exit("stub klt: call %d cannot read %s in %s: %s" % (call, m, os.getcwd(), e))
    include = next((ln.split('"')[1] for ln in deck.splitlines() if ln.startswith(".include ")), None)
    if include is None:
        sys.exit("stub klt: call %d: the deck of %s includes no netlist" % (call, m))
    stem = m[:-len(".request.json")]
    d = os.path.join(out, stem + os.environ["STUB_MEMBER_SUFFIX"])
    os.makedirs(d, exist_ok=True)
    report = os.path.abspath(os.path.join(d, "report.json"))
    shutil.copyfile(os.path.join(os.environ["STUB_SIM_POOL"], stem + ".json"), report)
    job = "klt-sim-stub-%d-%s" % (call, m[:-len(".request.json")])
    with open(os.path.join(d, "batch-receipt-" + job + ".json"), "w") as f:
        json.dump({"job_id": job}, f)
    entry["members"].append({"member": m, "report": report, "request_sha256": digest(m),
                             "deck": request["netlist"], "deck_sha256": digest(request["netlist"]),
                             "include": include, "include_sha256": digest(include)})
    entry["requests"].append({"request": m, "status": "pass", "exit_code": 0, "job_id": job,
                              "job_ids": [job], "report": report, "error": None})
entry["stdout"] = {"schema_version": 1, "status": "pass", "request_count": len(members),
                   "max_in_flight": 2, "submitted": len(members), "refused": 0,
                   "refused_codes": [], "requests": entry["requests"]}
entry["stderr"] = "stub klt sim: call %d, %d member(s) read in %s\n" % (call, len(members), entry["cwd"])
with open(log, "a") as f:
    f.write(json.dumps(entry) + "\n")
print(json.dumps(entry["stdout"], indent=1))
sys.stderr.write(entry["stderr"])
'''

YIELD_STUB = """#!/usr/bin/env python3
# Test double for tests/test_threshold_mc_collect.py: `klt --version` and
# `klt yield <samples> --limits <limits> --format json`. Reads the two documents the
# runner wrote and answers in klt yield's report shape. Verdicts come from the samples
# (a control population that sits inside the limits less often than its nominal group
# is `detected`) unless STUB_YIELD_NEG_CONTROL / STUB_YIELD_STATUS force one. Exits 3
# on a failing grade, as klt yield does.
import json, os, statistics, sys
args = sys.argv[1:]
if args[:1] == ["--version"]:
    print("klt 0.0.0 (yield stub for tests/test_threshold_mc_collect.py)")
    sys.exit(0)
if args[:1] != ["yield"] or args[args.index("--format") + 1:] != ["json"]:
    sys.exit("stub klt yield: unexpected invocation %r" % (args,))
samples = json.load(open(args[1]))
limits_path = args[args.index("--limits") + 1]
limits = json.load(open(limits_path))
with open(os.environ["STUB_YIELD_LOG"], "a") as f:
    f.write(json.dumps({"samples": args[1], "limits": limits_path}) + "\\n")
forced_neg = os.environ.get("STUB_YIELD_NEG_CONTROL")
forced_status = os.environ.get("STUB_YIELD_STATUS")
measurements = []
for m in samples["measurements"]:
    lim = limits["measurements"][m["name"]]
    xs, cs = m["samples"], m["negative_control"]["samples"]
    inside = lambda v: lim["min"] <= v <= lim["max"]
    frac = lambda vs: sum(1 for v in vs if inside(v)) / len(vs)
    nom_yield, ctl_yield = frac(xs), frac(cs)
    detected = ctl_yield < nom_yield and forced_neg != "not_detected"
    mean, sd = statistics.fmean(xs), statistics.pstdev(xs)
    sigma = min(mean - lim["min"], lim["max"] - mean) / (sd or 1e-12)
    met = sigma >= lim["target_sigma"]
    enough = len(xs) >= lim["min_converged_samples"]
    status = forced_status or ("pass" if met and enough else "fail")
    measurements.append({
        "name": m["name"], "unit": m.get("unit"), "n": len(xs), "errored": 0,
        "limits": {k: v for k, v in lim.items()
                   if k in ("min", "max", "target_sigma", "min_converged_samples")},
        "source_corners": m.get("source_corners", []), "spec_row": lim.get("spec_row"),
        "distribution": {"mean": mean, "stddev": sd}, "capability": {"sigma_to_spec": sigma},
        "sigma_target": {"k": lim["target_sigma"], "sigma_to_spec": sigma, "lower_bound": sigma,
                         "gate": "lower_bound", "met": status == "pass"},
        "converged_n": {"n_requested": len(xs), "n_converged": len(xs),
                        "min_converged_samples": lim["min_converged_samples"], "verdict": "sufficient"},
        "sample_size": {"n": len(xs), "verdict": "sufficient"},
        "negative_control": {"description": m["negative_control"].get("description"), "n": len(cs),
                             "errored": 0, "yield": {"empirical": {"estimate": ctl_yield}},
                             "nominal_empirical_estimate": nom_yield, "degradation_detected": detected,
                             "verdict": "detected" if detected else "not_detected"},
        "status": status, "warnings": []})
print(json.dumps({"schema_version": 1, "samples": args[1], "limits": limits_path,
                  "source": {"kind": "sample-set", "netlist": None, "monte_carlo": None,
                             "provenance": samples.get("provenance"),
                             "sample_count": sum(len(m["samples"]) for m in samples["measurements"])},
                  "confidence": limits.get("confidence"), "target_ci_halfwidth": 0.01, "min_samples": 2,
                  "status": "pass" if all(m["status"] == "pass" for m in measurements) else "fail",
                  "measurement_count": len(measurements),
                  "measurements": measurements, "warnings": []}))
sys.exit(3 if forced_status == "fail" else 0)
"""

with tempfile.TemporaryDirectory(prefix="tmc-col-") as d:
    tmp = pathlib.Path(d)
    for rel in COPIED:
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    bench = tmp / BENCH
    top_path = tmp / "design" / "detector_top.spice"
    top = top_path.read_text()
    template_path = bench / "tb_threshold_mc.spice"
    template = template_path.read_text()
    levels_path = tmp / "sim" / "lib" / "levels.json"
    levels = load(levels_path)

    req = tmp / "gen" / "req"
    gen = subprocess.run([sys.executable, "-I", str(bench / "gen_requests.py"), str(req)],
                         capture_output=True, text=True, timeout=120)
    man = json.loads(gen.stdout) if gen.returncode == 0 else None
    if not isinstance(man, dict) or not isinstance(man.get("groups"), list) or not isinstance(man.get("members"), dict):
        sys.exit("tb_threshold_mc collection cannot be tested: gen_requests.py did not emit a manifest "
                 "with groups and members (exit %d)\n%s" % (gen.returncode, gen.stderr.strip()[-600:]))
    matrix = tmp / "matrix.json"
    matrix.write_text(gen.stdout)
    groups, members = man["groups"], man["members"]
    names = [g["name"] for g in groups]
    by_name = {g["name"]: g for g in groups}
    tt_group = {(g["code"], g["temperature_c"], g["supply_v"]): g
                for g in groups if g["process"] == "tt_mm"}

    def control_of(g):
        """The control population of group g. An `mc` group is graded against the tt_mm
        control of its own code, temperature and supply: the same draws the tt_mm group
        of that member is graded against."""
        return control(tt_group[(g["code"], g["temperature_c"], g["supply_v"])]) if g["process"] == "mc" \
            else control(g)

    # ------------------------------------------------------------ fixture reports
    pool = tmp / "pool"
    pool.mkdir()
    rng = random.Random(169)
    for name in sorted(members):
        procs = members[name]["process"]
        if members[name].get("kind") == "ctl":
            cells = [g for g in groups if g["control"]["member"] == name and g["process"] != "mc"]
        else:
            cells = [g for g in groups if g["member"] == name]
        is_control = members[name].get("kind") == "ctl"
        corners = []
        for g in cells:
            pos = procs.index(g["process"]) * len(TEMPS) + TEMPS.index(g["temperature_c"])
            for i in range(N):
                corners.append({
                    "corner_id": "%s/%.3fV/%sC/mc%d" % (g["process"], g["supply_v"], g["temperature_c"], i),
                    "process": g["process"], "supply_v": {"Vdd": g["supply_v"]},
                    "temperature_c": g["temperature_c"], "status": "pass", "runtime_s": 0.1,
                    "measurements": [{"name": "vtrip", "value": (control_of(g) if is_control else nominal(g))[i],
                                      "unit": "V", "status": "pass", "margin": None}],
                    "diagnostics": [],
                    # klt's seed keying as its dry run states it: mismatch_seed follows the
                    # corner's position, process_seed its section, the combined seed both
                    "monte_carlo": {"sample_index": i, "process_seed": 424243 + SECTIONS.index(g["process"]),
                                    "mismatch_seed": pos * 7919 + i,
                                    "seed": (424243 + SECTIONS.index(g["process"])) * 1000003 + pos * 7919 + i}})
        rng.shuffle(corners)
        (pool / (name + ".json")).write_text(dump({
            "schema_version": 3, "netlist": {"path": None, "scope": "external"}, "status": "pass",
            "corner_count": len(corners), "passed": len(corners), "failed": 0, "errored": 0,
            "inconclusive": 0, "diagnostic_counts": {"by_code": {}, "by_severity": {},
                                                      "corners_with_diagnostics": 0},
            "environment": {"engine": "ngspice", "engine_version": "46", "engine_host": "worker",
                            "models_lib_sha256": "0" * 64, "netlist_sha256": "0" * 64,
                            "monte_carlo": {"n": N, "seed": SEED, "vary": members[name]["vary"]}},
            "corners": corners}))
    pool_draws = {p.name[:-5]: len(load(p)["corners"]) for p in pool.glob("*.json")}
    check(sorted(pool_draws) == sorted(members) and sum(pool_draws.values()) == (216 + 180) * N,
          "fixture pool holds %d reports / %d draws, expected 36 / %d"
          % (len(pool_draws), sum(pool_draws.values()), (216 + 180) * N))

    def install(outdir, name, layout="new"):
        d = outdir / (name if layout == "new" else name + ".request")
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pool / (name + ".json"), d / "report.json")
        (d / "inputs.json").write_text(json.dumps(
            {"sha256": members[name]["sha256"], "inputs": members[name]["inputs"]}))
        return d

    out = tmp / "out"
    for name in members:
        install(out, name)
    samples_path, limits_path = tmp / "samples.json", tmp / "limits.json"

    def collect(o=out, s=samples_path, lim=limits_path):
        return subprocess.run([sys.executable, "-I", str(bench / "build_yield.py"),
                               str(matrix), str(o), str(s), str(lim)],
                              capture_output=True, text=True, timeout=300)

    def must_fail(label, needles):
        proc = collect()
        text = proc.stderr + proc.stdout
        check(proc.returncode != 0, "%s: collection succeeded" % label)
        check(all(n in text for n in needles),
              "%s: the failure does not identify the affected group (expected %r):\n%s"
              % (label, needles, text.strip()[-700:]))

    proc = collect()
    check(proc.returncode == 0, "collection of the intact fixture failed (exit %d):\n%s"
          % (proc.returncode, proc.stderr.strip()[-1800:]))
    if proc.returncode == 0:
        samples, limits = load(samples_path), load(limits_path)
        check("corners" not in samples, "samples.json carries a top-level 'corners' key: klt yield would "
                                        "read it as a klt sim report, not a sample set")
        meas = samples.get("measurements")
        if not isinstance(meas, list):
            problems.append("samples.json has no 'measurements' list")
        else:
            got = [m.get("name") for m in meas]
            check(len(got) == 216 and set(got) == set(names) and len(set(got)) == len(got),
                  "samples.json names %d measurements (%d distinct); expected the 216 manifest groups "
                  "(missing: %s)" % (len(got), len(set(got)), sorted(set(names) - set(got))[:6]))
            for m in meas:
                name = m.get("name")
                g = by_name.get(name)
                if g is None:
                    continue
                ctl = g["control"]
                check(m.get("samples") == nominal(g),
                      "%s: samples are not this group's %d draws in sample order" % (name, N))
                check(m.get("unit") == "V", "%s: unit is %r" % (name, m.get("unit")))
                check(m.get("source_corners") == ["%s/%.3fV/%sC" % (g["process"], g["supply_v"], g["temperature_c"])],
                      "%s: source_corners is %r, expected the one corner this population was drawn at"
                      % (name, m.get("source_corners")))
                nc = m.get("negative_control") or {}
                check(nc.get("samples") == control_of(g),
                      "%s: the negative-control samples are not the %s population at %s C / %s V "
                      "(the control pairing crossed groups)" % (name, ctl["process"], g["temperature_c"], g["supply_v"]))
                desc = str(nc.get("description"))
                for token in ("control section %s" % ctl["process"], "vary=%s" % ctl["vary"],
                              "code %d" % g["code"], "temperature %s C" % g["temperature_c"],
                              "Vdd %s V" % g["supply_v"], str(SEED)):
                    check(token in desc, "%s: control description %r lacks %r" % (name, desc, token))
        lim = limits.get("measurements")
        if not isinstance(lim, dict):
            problems.append("limits.json has no 'measurements' object")
        else:
            check(set(lim) == set(names), "limits.json is keyed by %d names, expected the 216 groups" % len(lim))
            check(limits.get("confidence") == 0.95, "limits.json confidence is %r" % (limits.get("confidence"),))
            for name, g in by_name.items():
                L = lim.get(name) or {}
                check(L.get("min") == round(g["nominal_v"] - BAND, 6)
                      and L.get("max") == round(g["nominal_v"] + BAND, 6),
                      "%s: limits are %r, expected its own nominal %s +/- %s V" % (name, L, g["nominal_v"], BAND))
                check(L.get("target_sigma") == 3 and L.get("min_converged_samples") == N,
                      "%s: target_sigma / min_converged_samples are %r" % (name, L))
        prov = samples.get("provenance") or {}
        check(prov.get("seed") == SEED and prov.get("draws_per_population") == N
              and sorted(prov.get("corner_matrix") or []) == sorted(SECTIONS)
              and prov.get("temperature_c") == TEMPS
              and prov.get("supply_v") == SUPPLIES and prov.get("inputs_sha256") == man.get("inputs_sha256"),
              "samples.json provenance is %r, expected the seed, N, corner box and input hash" % (prov,))
        check(prov.get("control_groups_paired") == {"all_seeds": 180, "mismatch_seed_only": 36, "none": 0, "unknown": 0}
              and prov.get("common_random_numbers") is False,
              "control pairing read from the seeds is %r, common_random_numbers %r; expected the 180 *_mm controls "
              "to repeat their group's draws, the 36 mc controls to repeat only the mismatch component, and "
              "common_random_numbers false" % (prov.get("control_groups_paired"), prov.get("common_random_numbers")))
        # a report collected by klt <= 0.9.2 lives in <member>.request/
        old = tmp / "out-old"
        for name in members:
            install(old, name, layout="old")
        old_samples = tmp / "samples-old.json"
        proc_old = collect(old, old_samples, tmp / "limits-old.json")
        check(proc_old.returncode == 0 and old_samples.read_bytes() == samples_path.read_bytes(),
              "collection through the klt <= 0.9.2 layout <member>.request/report.json failed or "
              "differs (exit %d):\n%s" % (proc_old.returncode, proc_old.stderr.strip()[-600:]))

    # ---------------------------------------------------------- damaged evidence
    victim, vproc, vtemp = "l2_mm_3p63", "ss_mm", 125
    vgroup = "vtrip_l2_%s_%dC_%sV" % (vproc, vtemp, vtag(3.63))
    check(vgroup in by_name, "guard bug: victim group %s is not in the manifest" % vgroup)

    def edit(name, fn):
        rep = load(pool / (name + ".json"))
        fn(rep)
        rep["corner_count"] = rep["passed"] = len(rep["corners"])
        (out / name / "report.json").write_text(dump(rep))

    def restore(name):
        install(out, name)

    def drop_one(rep):
        rep["corners"].remove(draw(rep, vproc, vtemp, 17))
    edit(victim, drop_one)
    must_fail("one draw removed", [vgroup, "missing sample_index 17"])
    restore(victim)

    def duplicate_one(rep):
        copy = json.loads(json.dumps(draw(rep, vproc, vtemp, 4)))
        lost = draw(rep, vproc, vtemp, 17)
        lost.clear()
        lost.update(copy)   # a copy of draw 4 where draw 17 was
    edit(victim, duplicate_one)
    must_fail("duplicate draw substituted for the missing one", [vgroup, "duplicate sample_index 4"])
    restore(victim)

    def repeat_value(rep):   # two dice landing on the same trip is legitimate, not a duplicated draw
        draw(rep, vproc, vtemp, 5)["measurements"][0]["value"] = draw(rep, vproc, vtemp, 4)["measurements"][0]["value"]
    edit(victim, repeat_value)
    proc = collect()
    check(proc.returncode == 0, "two draws of %s that share a trip value were refused (exit %d); only a repeated "
          "sample index or seed is a duplicate\n%s" % (vgroup, proc.returncode, proc.stderr.strip()[-400:]))
    restore(victim)

    def non_finite(rep):
        draw(rep, vproc, vtemp, 3)["measurements"][0]["value"] = float("nan")
    edit(victim, non_finite)
    must_fail("non-finite value", [vgroup, "sample_index 3", "finite"])
    restore(victim)

    def drop_population(rep):
        rep["corners"] = [c for c in rep["corners"] if not (c["process"] == "ff_mm" and c["temperature_c"] == -40)]
    edit("l1_mm_2p97", drop_population)
    must_fail("a population removed", ["vtrip_l1_ff_mm_m40C_2p97V"])
    restore("l1_mm_2p97")

    def relabel_population(rep):
        cold = cell(rep, "tt_mm", -40)
        rep["corners"] = [c for c in rep["corners"] if (c["process"], c["temperature_c"]) != ("tt_mm", 27)]
        rep["corners"].extend(dict(c, temperature_c=27) for c in cold)
    edit("l0_mm_2p97", relabel_population)
    must_fail("300 cold draws relabeled to 27 C", ["vtrip_l0_tt_mm_27C_2p97V", "tt_mm/2.970V/-40C/"])
    restore("l0_mm_2p97")

    def misidentify_controls(rep):
        wrong_ids = ("ss_mm/2.970V/27C/mc0", "tt_mm/3.630V/27C/mc1", "tt_mm/2.970V/27C/mc3")
        for i, wrong_id in enumerate(wrong_ids):
            draw(rep, "tt_mm", 27, i)["corner_id"] = wrong_id
    edit("l0_ctl_2p97", misidentify_controls)
    must_fail("wrong process, supply and sample index in control IDs",
              ["control of vtrip_l0_tt_mm_27C_2p97V", "tt_mm/2.970V/27C/mc0",
               "tt_mm/2.970V/27C/mc1", "tt_mm/2.970V/27C/mc2"])
    restore("l0_ctl_2p97")

    def misfiled(rep):
        draw(rep, "tt_mm", 27, 9)["supply_v"]["Vdd"] = 3.63
    edit("l0_mm_2p97", misfiled)
    must_fail("a draw filed under another supply", ["l0_mm_2p97", "Vdd=3.63", "vtrip_l0_tt_mm_27C_2p97V"])
    restore("l0_mm_2p97")

    def unconverged(rep):
        c = draw(rep, vproc, vtemp, 21)
        c["status"] = "error"
        c["measurements"][0].update(value=None, status="error")
    edit(victim, unconverged)
    must_fail("an unconverged draw", [vgroup, "sample_index 21", "converge"])
    restore(victim)

    missing_ctl = "l3_ctl_3p30"
    shutil.rmtree(out / missing_ctl)
    must_fail("control report missing", [missing_ctl, "vtrip_l3_tt_mm_27C_3p30V"])
    restore(missing_ctl)

    stale = "l1_mc_3p63"
    (out / stale / "inputs.json").write_text(json.dumps(
        {"sha256": "0" * 64, "inputs": members[stale]["inputs"]}))
    must_fail("evidence produced from other inputs", [stale, "inputs"])
    restore(stale)

    (out / "l0_ctl_3p30" / "inputs.json").unlink()
    must_fail("evidence with no recorded inputs", ["l0_ctl_3p30", "inputs.json"])
    restore("l0_ctl_3p30")

    def wrong_seed(rep):
        rep["environment"]["monte_carlo"]["seed"] = 1
    edit("l2_mm_2p97", wrong_seed)
    must_fail("report that does not echo the recorded seed", ["l2_mm_2p97", "seed"])
    restore("l2_mm_2p97")

    proc = collect()
    check(proc.returncode == 0, "collection did not recover after the damaged reports were restored "
          "(exit %d):\n%s" % (proc.returncode, proc.stderr.strip()[-600:]))

    # ----------------------------------------------------------- the real runner
    pdk = tmp / "pdk"
    pin = load(tmp / "sim" / "pdk.json")
    (pdk / pin["variant"] / "libs.tech" / "combined").mkdir(parents=True)
    (pdk / pin["variant"] / "SOURCES").write_text(pin["sources_line"] + "\n")
    (pdk / pin["variant"] / "libs.tech" / "combined" / "sky130.lib.spice").write_text("* fake model library\n")
    bin_dir = tmp / "stub bin"
    bin_dir.mkdir()
    # The stubs are modules run as `python3 -m <name>`, found through PYTHONPATH: no PATH lookup of
    # `klt`/`klt-yield` and no executable bit, so a noexec TMPDIR or an installed client on the
    # caller's PATH can never stand in for them and submit real jobs.
    for name, text in (("tmc_stub_klt", KLT_STUB), ("tmc_stub_klt_yield", YIELD_STUB)):
        (bin_dir / (name + ".py")).write_text(text, encoding="utf-8")
    sim_log, yield_log = tmp / "sim.log", tmp / "yield.log"
    DROP = ("KEEP", "RECORD_DIR", "PDK_PIN", "PDK_ROOT", "KLT", "KLT_YIELD",
            "STUB_SIM_LOG", "STUB_YIELD_LOG", "STUB_YIELD_NEG_CONTROL", "STUB_YIELD_STATUS", "PYTHONPATH")

    def scratch(tag, member_suffix=".request"):
        """An empty caller directory, and the runner's environment for it: the stubs, the fake
        PDK root and a TMPDIR of its own, so nothing leaks into the host's when a run fails."""
        caller = tmp / ("caller-" + tag)
        caller.mkdir()
        runner_tmp = tmp / ("runner-tmp-" + tag)
        runner_tmp.mkdir()
        env = {k: v for k, v in os.environ.items() if k not in DROP}
        env.update(KLT="python3 -m tmc_stub_klt", KLT_YIELD="python3 -m tmc_stub_klt_yield",
                   PYTHONPATH=str(bin_dir), PDK_ROOT=str(pdk),
                   STUB_MEMBER_SUFFIX=member_suffix, STUB_SIM_POOL=str(pool),
                   STUB_SIM_LOG=str(sim_log), STUB_YIELD_LOG=str(yield_log), TMPDIR=str(runner_tmp))
        return caller, env

    def run(caller, env):
        sim_before, yield_before = len(logged(sim_log)), len(logged(yield_log))
        proc = subprocess.run(["bash", str(bench / "run.sh")], cwd=caller, env=env, capture_output=True,
                              text=True, timeout=600, check=False)
        return proc, logged(sim_log)[sim_before:], logged(yield_log)[yield_before:]

    def first_submission(label, keep, proc, sim_calls, yield_calls):
        """A first run into `keep`: one batch client call, made from <keep>/req, that read every
        request the generator wrote, redirected and collected under `keep`. Returns the call,
        or None when the run cannot be checked further."""
        req = keep / "req"
        want = expected_members(req) if req.is_dir() else []
        if not check(proc.returncode == 0 and len(sim_calls) == 1,
                     "%s: run.sh exited %d with %d batch client call(s), expected exit 0 and 1 "
                     "(%d requests generated)\n%s"
                     % (label, proc.returncode, len(sim_calls), len(want), tail(proc))):
            return None
        call = sim_calls[0]
        check(real(call["cwd"]) == real(req),
              "%s: the client ran in %s, expected %s" % (label, call["cwd"], req))
        check(sorted(submitted_files(call)) == sorted(w["member"] for w in want),
              "%s: the client received %r, expected exactly the generated requests %r"
              % (label, sorted(submitted_files(call)), sorted(w["member"] for w in want)))
        read = {m["member"]: m for m in call["members"]}
        for w in want:
            g = read.get(w["member"]) or {}
            check(g.get("request_sha256") == sha256(req / w["member"])
                  and g.get("deck") == w["deck"] and g.get("deck_sha256") == sha256(req / w["deck"])
                  and g.get("include") == w["include"]
                  and g.get("include_sha256") == sha256(req / w["include"]),
                  "%s: the client did not read the request, deck and included netlist of %s as "
                  "the generator wrote them in %s" % (label, w["member"], req))
        set_json, err_log = keep / "set.json", keep / "stderr.log"
        if check(set_json.is_file() and err_log.is_file(),
                 "%s: the client's stdout and stderr must land in %s and %s; run.sh exited %d\n%s"
                 % (label, set_json, err_log, proc.returncode, tail(proc))):
            try:
                check(load(set_json) == call["stdout"],
                      "%s: %s is not what the client printed" % (label, set_json))
            except ValueError:
                problems.append("%s: %s is not JSON" % (label, set_json))
            check(err_log.read_text(encoding="utf-8") == call["stderr"],
                  "%s: %s is not what the client wrote to stderr" % (label, err_log))
        check(real(call["out"]) == real(keep / "out"),
              "%s: the client collected into %s, expected %s" % (label, call["out"], keep / "out"))
        out = real(keep / "out") + os.sep
        for w in want:
            g = read.get(w["member"]) or {}
            report = pathlib.Path(g.get("report", ""))
            if check(str(real(report)).startswith(out) and report.is_file(),
                      "%s: no report of %s under %s (the client wrote %s)"
                      % (label, w["member"], keep / "out", g.get("report"))):
                rep = load(report)
                check(rep.get("status") == "pass" and len(rep.get("corners") or []) == w["populations"],
                      "%s: the report of %s is %s with %d corners, expected pass and %d"
                      % (label, w["member"], rep.get("status"), len(rep.get("corners") or []),
                         w["populations"]))
        check(len(yield_calls) == 1 and real(yield_calls[0]["samples"]) == real(keep / "samples.json")
              and real(yield_calls[0]["limits"]) == real(keep / "limits.json"),
              "%s: klt yield was called %d time(s) with %r, expected once on the documents in %s"
              % (label, len(yield_calls), yield_calls and yield_calls[0], keep))
        return call

    def unchanged_rerun(label, caller, env, keep):
        """A second run over collected reports: nothing submitted, nothing rewritten."""
        before = tree_hashes(keep / "out")
        proc, sim_calls, _ = run(caller, env)
        check(proc.returncode == 0 and sim_calls == [],
              "%s: unchanged rerun: run.sh exited %d and submitted %r, expected exit 0 and nothing\n%s"
              % (label, proc.returncode, [m for c in sim_calls for m in submitted_files(c)], tail(proc)))
        check(tree_hashes(keep / "out") == before,
              "%s: unchanged rerun: the collected reports changed without a submission" % label)

    caller, env = scratch("relative")
    env["CDPATH"] = "."
    env["KEEP"] = RELATIVE_KEEP
    keep = caller / RELATIVE_KEEP
    proc, sim_calls, yield_calls = run(caller, env)
    call = first_submission("fresh run, KEEP=%s" % RELATIVE_KEEP, keep, proc, sim_calls, yield_calls)
    check(sorted(p.name for p in caller.iterdir()) == [RELATIVE_KEEP],
          "fresh run, KEEP=%s: the caller directory %s holds %r, expected only %s"
          % (RELATIVE_KEEP, caller, sorted(p.name for p in caller.iterdir()), RELATIVE_KEEP))
    if call is not None:
        unchanged_rerun("KEEP=%s" % RELATIVE_KEEP, caller, env, keep)

        before = tree_hashes(keep / "out")
        member = call["members"][len(call["members"]) // 2]
        target = pathlib.Path(member["report"])
        want = {w["member"]: w for w in expected_members(keep / "req")}[member["member"]]
        partial = load(target)
        partial.update(status=INCOMPLETE, corners=partial["corners"][:7])
        target.write_text(json.dumps(partial, indent=1), encoding="utf-8")
        proc, sim_calls, yield_calls = run(caller, env)
        if check(proc.returncode == 0 and len(sim_calls) == 1 and submitted_files(sim_calls[0]) == [member["member"]],
                 "rerun, KEEP=%s, %s incomplete: run.sh exited %d and submitted %r, expected exit 0 and "
                 "only %s\n%s" % (RELATIVE_KEEP, member["member"], proc.returncode,
                                  [m for c in sim_calls for m in submitted_files(c)], member["member"], tail(proc))):
            again = sim_calls[0]["members"][0]
            check(real(again["report"]) == real(target),
                  "rerun, KEEP=%s: the replacement of %s was written to %s, expected %s"
                  % (RELATIVE_KEEP, member["member"], again["report"], target))
            rep = load(target)
            check(rep.get("status") == "pass" and len(rep.get("corners") or []) == want["populations"],
                  "rerun, KEEP=%s: the replacement of %s is %s with %d corners, expected pass and %d"
                  % (RELATIVE_KEEP, member["member"], rep.get("status"), len(rep.get("corners") or []),
                     want["populations"]))
            moved = [p for p in (keep / "out").iterdir()
                     if p.name.startswith(target.parent.name + ".attempt-")]
            check(len(moved) == 1 and load(moved[0] / "report.json").get("status") == INCOMPLETE,
                  "rerun, KEEP=%s: the incomplete report of %s is kept as %r, expected one %s.attempt-* "
                  "directory" % (RELATIVE_KEEP, member["member"], [p.name for p in moved],
                                 target.parent.name))

            def others(hashes):
                return {k_: v for k_, v in hashes.items() if not k_.startswith(target.parent.name)}

            check(others(tree_hashes(keep / "out")) == others(before),
                  "rerun, KEEP=%s: reports other than the one replaced changed" % RELATIVE_KEEP)

    caller, env = scratch("absolute")
    physical = tmp / "physical"
    (physical / "run").mkdir(parents=True)
    link = tmp / "current"
    link.symlink_to(physical / "run", target_is_directory=True)
    neighbor = tmp / "results"
    neighbor.mkdir()  # A logical cd that collapses current/.. could succeed here.
    keep = physical / "results"
    env["KEEP"] = str(link / ".." / "results")
    proc, sim_calls, yield_calls = run(caller, env)
    call = first_submission("absolute KEEP", keep, proc, sim_calls, yield_calls)
    check(not any(neighbor.iterdir()), "absolute KEEP: runner wrote into %s" % neighbor)
    check(sorted(p.name for p in caller.iterdir()) == [],
          "absolute KEEP: the caller directory %s holds %r, expected nothing"
          % (caller, sorted(p.name for p in caller.iterdir())))
    if call is not None:
        check((keep / "record.txt").is_file() and (keep / "yield.json").is_file(),
              "absolute KEEP: the run left no record.txt / yield.json in %s" % keep)

    caller, env = scratch("unset")
    proc, sim_calls, yield_calls = run(caller, env)
    if check(proc.returncode == 0 and len(sim_calls) == 1,
             "KEEP unset: run.sh exited %d with %d batch client call(s), expected exit 0 and 1\n%s"
             % (proc.returncode, len(sim_calls), tail(proc))):
        work = pathlib.Path(sim_calls[0]["cwd"]).parent
        runner_tmp = pathlib.Path(env["TMPDIR"])
        check(str(real(work)).startswith(real(runner_tmp) + os.sep),
              "KEEP unset: the client ran in %s, expected inside the runner's TMPDIR %s"
              % (work, runner_tmp))
        check(not work.exists(),
              "KEEP unset: the work directory %s is still there after the runner exited" % work)
        check(not any(runner_tmp.iterdir()),
              "KEEP unset: the runner left %r behind in %s"
              % (sorted(p.name for p in runner_tmp.iterdir()), runner_tmp))
        check(sorted(p.name for p in caller.iterdir()) == [],
              "KEEP unset: the caller directory %s holds %r, expected nothing"
              % (caller, sorted(p.name for p in caller.iterdir())))

    # Exercise both batch-client layouts: older clients used <member>.request above.
    caller, env = scratch("matrix", member_suffix="")
    keep, rec = tmp / "keep", tmp / "record"
    env.update(KEEP=str(keep), RECORD_DIR=str(rec))

    def runner(extra=None):
        proc, calls, _ = run(caller, dict(env, **(extra or {})))
        submitted = [name[:-len(".request.json")] for call in calls for name in submitted_files(call)]
        return proc, sorted(submitted)

    def runner_scenarios():
        """The scenarios build on each other: each stops the chain when the runner did not
        leave the state the next one needs, so a broken runner is reported, not crashed on."""
        all_members = sorted(members)

        def step(ok, msg):
            if not ok:
                problems.append(msg)
            return ok

        def record_field(key):
            return next((ln.split() for ln in record_path.read_text().splitlines() if ln.startswith(key + ":")), [])

        # The previous bench left one request per code and kind, without a supply suffix.
        reqdir = keep / "req"
        reqdir.mkdir(parents=True)
        for code in range(4):
            for kind in ("mm", "mc", "ctl"):
                (reqdir / ("l%d_%s.request.json" % (code, kind))).write_text("{}\n")
        yield_before = len(logged(yield_log))
        proc, submitted = runner()
        if not step(proc.returncode == 0, "legacy KEEP: run.sh exited %d, expected 0\n%s" % (proc.returncode, tail(proc))):
            return
        step(submitted == all_members, "legacy KEEP: expected exactly the 36 current members, submitted %r" % submitted)
        record_path, yield_path = rec / "record.txt", rec / "klt-yield.json"
        if not step(record_path.is_file(), "fresh run: run.sh wrote no record.txt to RECORD_DIR"):
            return
        lines = record_path.read_text().splitlines()
        head = lines[0] if lines else ""
        step("corner box: process {tt,ss,ff,sf,fs}_mm (vary=mismatch) + mc (vary=both), "
             "temperature -40 / 27 / 125 C, detector supply 2.97 / 3.3 / 3.63 V" in head
             and "216 groups" in head, "record does not state the matrix that was run:\n" + head)
        trip = next((ln for ln in lines if ln.startswith("stimulus:")), "")
        step("xdut.flag" in trip and "half the applied detector supply" in trip
             and "1.485 / 1.65 / 1.815 V at 2.97 / 3.3 / 3.63 V" in trip,
             "record does not state the crossing criterion that was measured:\n" + trip)
        mc_line = next((ln for ln in lines if ln.startswith("monte_carlo:")), "")
        try:
            mc = json.loads(mc_line[len("monte_carlo:"):])
        except ValueError:
            mc = None
        step(isinstance(mc, dict) and mc.get("seed") == SEED and mc.get("n") == N
             and mc.get("temperature_c") == TEMPS and mc.get("supply_v") == SUPPLIES
             and mc.get("levels") == [r["v"] for r in levels["levels"]],
             "record monte_carlo line is %r, expected the seed, N, level nominals and both corner axes" % mc_line)
        net = record_field("netlist_sha256")
        step(net[1:2] == [sha256(top_path)] and net[2:3] == ["design/detector_top.spice"],
             "record netlist hash is %r, expected the hash of the netlist the decks included" % net)
        step(record_field("netlist_control_sha256")[1:2] == [sha256(keep / "req" / "detector_top_ctl.spice")],
             "record control-netlist hash is %r, expected the hash of the generated control copy"
             % record_field("netlist_control_sha256"))
        step(record_field("inputs_sha256")[1:2] == [man.get("inputs_sha256")],
             "record inputs hash is %r, expected the generator's %r"
             % (record_field("inputs_sha256"), man.get("inputs_sha256")))
        neg = next((ln for ln in lines if ln.startswith("negative control:")), "")
        step("XR2" in neg and "threshold_ref" in neg and "L=94.073 -> 88" in neg and "tt_mm" in neg,
             "record does not state the control that was run:\n" + neg)
        grade = next((ln for ln in lines if ln.startswith("grading:")), "")
        step("target_sigma 3 " in grade and "min_converged_samples 300," in grade and "+/-27 mV" in grade
             and "confidence 0.95" in grade,
             "record does not state the grade that was applied (read back from limits.json):\n" + grade)
        graded = [ln for ln in lines if re.match(r"\s+vtrip_l\d_(?:[a-z]+_mm|mc)_m?\d+C_\d+p\d+V: n=%d " % N, ln)]
        step(len(graded) == 216, "record lists %d graded groups, expected 216" % len(graded))
        if "batch job ids:" in lines:
            block = lines[lines.index("batch job ids:") + 1: lines.index("batch job ids:") + 1 + 36]
            step([ln.split(":")[0].strip() for ln in block] == all_members,
                 "record lists %d batch job lines (%r), expected one per request in request order"
                 % (len(block), [ln.split(":")[0].strip() for ln in block][:4]))
            step(all("klt-sim-stub-" in ln for ln in block), "a batch job line carries no job id")
        else:
            problems.append("record has no 'batch job ids:' block")
        if step(yield_path.is_file(), "fresh run: run.sh wrote no klt-yield.json to RECORD_DIR"):
            y = load(yield_path)
            ym = y.get("measurements") or []
            step(len(ym) == 216 and all(m["negative_control"]["verdict"] == "detected" for m in ym)
                 and y.get("status") == "pass",
                 "graded record holds %d measurements / status %r, expected 216 detected controls and a pass"
                 % (len(ym), y.get("status")))
            step(all(by_name[m["name"]]["control"]["process"] in str(m["negative_control"].get("description"))
                     for m in ym if m["name"] in by_name),
                 "the graded record does not identify each group's control section in that group's own entry")
            step(all(m.get("source_corners") and m["source_corners"][0].split("/")[0] == by_name[m["name"]]["process"]
                     for m in ym if m["name"] in by_name),
                 "the graded record does not carry each group's own source corner")
        step(len(logged(yield_log)) == yield_before + 1,
             "klt yield was not called exactly once")

        proc, submitted = runner()
        if not step(proc.returncode == 0 and submitted == [], "identical re-run: exit %d, submitted %r; "
                     "expected exit 0 and every collected report reused\n%s"
                     % (proc.returncode, submitted, tail(proc))):
            return
        stamped = keep / "out" / "l1_mm_3p30" / "inputs.json"
        if not step(stamped.is_file(), "resume scenarios cannot continue: the fresh run left no inputs.json "
                     "beside out/l1_mm_3p30/report.json, so the runner does not record which inputs "
                     "produced a report"):
            return
        stamped.unlink()
        proc, submitted = runner()
        step(proc.returncode == 0 and submitted == ["l1_mm_3p30"], "a report with no recorded inputs: exit %d, "
             "submitted %r; expected only that member to run again\n%s" % (proc.returncode, submitted, tail(proc)))

        partial = keep / "out" / "l2_ctl_2p97" / "report.json"
        if not step(partial.is_file(), "resume scenarios cannot continue: out/l2_ctl_2p97/report.json is missing"):
            return
        partial.write_text(dump({**load(partial), "status": "error"}))
        proc, submitted = runner()
        step(proc.returncode == 0 and submitted == ["l2_ctl_2p97"], "a collected report that is not a pass: "
             "exit %d, submitted %r; expected only that member to run again\n%s"
             % (proc.returncode, submitted, tail(proc)))
        step((keep / "out").is_dir()
             and any(p.name.startswith("l2_ctl_2p97.attempt-") for p in (keep / "out").iterdir()),
             "the superseded report of l2_ctl_2p97 was not kept as .attempt-* evidence")

        top_path.write_text(top.replace("L=225.433", "L=225.43"))
        proc, submitted = runner()
        if not step(proc.returncode == 0 and submitted == all_members, "netlist changed: exit %d, %d submitted; "
                     "expected all 36 to run again, none of the earlier design's reports reused\n%s"
                     % (proc.returncode, len(submitted), tail(proc))):
            return
        step(record_field("netlist_sha256")[1:2] == [sha256(top_path)],
             "after the netlist change the record still cites the earlier netlist's hash %r"
             % record_field("netlist_sha256"))

        template_path.write_text(template.replace("Cl live 0 5f", "Cl live 0 6f"))
        proc, submitted = runner()
        if not step(proc.returncode == 0 and submitted == all_members, "deck template changed: exit %d, %d "
                     "submitted; expected all 36 to run again\n%s"
                     % (proc.returncode, len(submitted), tail(proc))):
            return

        levels["levels"][2]["v"] = 1.639
        levels_path.write_text(json.dumps(levels))
        proc, submitted = runner()
        if not step(proc.returncode == 0 and submitted == sorted(n for n in all_members if n.startswith("l2_")),
                     "one level's request changed (level table): exit %d, submitted %r; expected only that "
                     "level's 6 members\n%s" % (proc.returncode, submitted, tail(proc))):
            return
        lim = load(keep / "limits.json")["measurements"]
        step(all(lim[n]["min"] == round(1.639 - BAND, 6) for n in lim if n.startswith("vtrip_l2_")),
             "the re-collected limits do not follow the changed level nominal")

        proc, submitted = runner({"STUB_YIELD_NEG_CONTROL": "not_detected"})
        step(proc.returncode == 6 and submitted == [], "undetected control: run.sh exited %d, expected 6\n%s"
             % (proc.returncode, tail(proc)))
        proc, submitted = runner({"STUB_YIELD_STATUS": "fail"})
        step(proc.returncode == 7 and submitted == [], "completed failing grade: run.sh exited %d, expected 7\n%s"
             % (proc.returncode, tail(proc)))

        # Simulate an incomplete generation in the scratch copy. A cached report
        # must not hide a missing file named by the fresh manifest.
        missing = "l3_mm_3p63.request.json"
        with (bench / "gen_requests.py").open("a") as f:
            f.write("\n(pathlib.Path(sys.argv[1]) / %r).unlink()\n" % missing)
        proc, submitted = runner()
        step(proc.returncode == 2 and submitted == [] and missing in proc.stderr,
             "missing manifest request: exit %d, submitted %r, expected exit 2 naming %s\n%s"
             % (proc.returncode, submitted, missing, tail(proc)))

        top_path.write_text(top.replace(".subckt threshold_ref ", ".subckt threshold_rex "))
        proc, submitted = runner()
        step(proc.returncode == 2 and submitted == [], "netlist without the control target: run.sh exited %d and "
             "submitted %r; expected exit 2 and nothing submitted\n%s"
             % (proc.returncode, submitted, tail(proc)))

    runner_scenarios()

if problems:
    sys.exit("tb_threshold_mc collection/runner is wrong:\n  - " + "\n  - ".join(problems[:25])
             + ("\n  - ... and %d more" % (len(problems) - 25) if len(problems) > 25 else ""))
print("ok: tb_threshold_mc collects 216 coordinate-specific groups with paired controls "
      "(damaged evidence refused, repeated values accepted), resumes only on identical "
      "inputs, resolves relative and absolute KEEP paths and cleans up temporary runs, "
      "and reports its matrix, criterion, control and hashes (runner exit 0 / 6 / 7 / 2)")
