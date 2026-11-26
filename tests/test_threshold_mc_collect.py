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
    missing one (count preserved), a non-finite value, a draw filed under another
    supply, an unconverged draw, a missing control report, evidence whose recorded
    input hash is not the current one or is absent, a report that does not echo the
    recorded seed.

Each must fail collection and name the affected group.

Part B runs the real `run.sh` on a scratch tree with `klt` and `klt yield` replaced by
stubs (a fake PDK root satisfies the pin gate), so nothing is simulated or submitted,
and checks resume (reuse only on identical inputs; fresh output when the netlist, the
deck template or one level's request changes), the record's matrix / criterion /
control / hashes against the inputs actually used, and the exit statuses of an
undetected control, a completed failing grade and an unusable netlist.

Repo files are copied, never modified. No PDK, no klt, no fleet.
"""
import hashlib
import json
import os
import pathlib
import random
import re
import shutil
import statistics
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

problems = []


def check(cond, msg):
    if not cond:
        problems.append(msg)


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


KLT_STUB = """#!/usr/bin/env python3
# Test double for tests/test_threshold_mc_collect.py: `klt --version`, `klt pdk find`
# (the fake PDK root) and `klt sim --batch-set` (copies each member's fixture report
# into <outdir>/<member>/ and logs the member). Anything else fails; no real klt runs.
import json, os, shutil, sys
args = sys.argv[1:]
if args[:1] == ["--version"]:
    print("klt 0.0.0 (stub for tests/test_threshold_mc_collect.py)")
    sys.exit(0)
if args[:2] == ["pdk", "find"]:
    print("root: " + (args[args.index("--pdk-root") + 1] if "--pdk-root" in args else ""))
    sys.exit(0)
if args[:2] == ["sim", "--batch-set"]:
    members = []
    for a in args[2:]:
        if a.startswith("--"):
            break
        members.append(a)
    out = args[args.index("-o") + 1]
    pool, log = os.environ["STUB_SIM_POOL"], os.environ["STUB_SIM_LOG"]
    requests = []
    for m in members:
        stem = m[:-len(".request.json")]
        d = os.path.join(out, stem)
        os.makedirs(d, exist_ok=True)
        shutil.copyfile(os.path.join(pool, stem + ".json"), os.path.join(d, "report.json"))
        job = "klt-sim-stub-" + stem
        with open(os.path.join(d, "batch-receipt-" + job + ".json"), "w") as f:
            json.dump({"job_id": job}, f)
        with open(log, "a") as f:
            f.write(stem + "\\n")
        requests.append({"request": m, "status": "pass", "exit_code": 0, "job_id": job,
                         "job_ids": [job], "report": os.path.join(d, "report.json"), "error": None})
    print(json.dumps({"schema_version": 1, "status": "pass", "request_count": len(members),
                      "max_in_flight": 2, "submitted": len(members), "refused": 0,
                      "refused_codes": [], "requests": requests}))
    sys.exit(0)
sys.exit("stub klt: unexpected invocation %r" % (args,))
"""

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
if args[:1] != ["yield"]:
    sys.exit("stub klt yield: unexpected invocation %r" % (args,))
samples = json.load(open(args[1]))
limits_path = args[args.index("--limits") + 1]
limits = json.load(open(limits_path))
with open(os.environ["STUB_YIELD_LOG"], "a") as f:
    f.write(json.dumps(args) + "\\n")
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
    status = forced_status or "pass"
    mean, sd = statistics.fmean(xs), statistics.pstdev(xs)
    sigma = min(mean - lim["min"], lim["max"] - mean) / sd
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
                  "status": forced_status or "pass", "measurement_count": len(measurements),
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
                    "corner_id": "%s/%sV/%sC/mc%d" % (g["process"], g["supply_v"], g["temperature_c"], i),
                    "process": g["process"], "supply_v": {"Vdd": g["supply_v"]},
                    "temperature_c": g["temperature_c"], "status": "pass", "runtime_s": 0.1,
                    "measurements": [{"name": "vtrip", "value": (control_of(g) if is_control else nominal(g))[i],
                                      "unit": "V", "status": "pass", "margin": None}],
                    "diagnostics": [],
                    "monte_carlo": {"sample_index": i, "seed": SEED + pos * 1000003 + i,
                                    "process_seed": 424243, "mismatch_seed": pos * 7919 + i}})
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

    def collect(o=out, s=samples_path, l=limits_path):
        return subprocess.run([sys.executable, "-I", str(bench / "build_yield.py"),
                               str(matrix), str(o), str(s), str(l)],
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
                check(m.get("source_corners") == ["%s/%sV/%sC" % (g["process"], g["supply_v"], g["temperature_c"])],
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
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    for fname, text in (("klt", KLT_STUB), ("klt-yield", YIELD_STUB)):
        (bin_dir / fname).write_text(text)
        (bin_dir / fname).chmod(0o755)
    sim_log, yield_log = tmp / "sim.log", tmp / "yield.log"
    keep, rec = tmp / "keep", tmp / "record"
    env = dict(os.environ, KLT=str(bin_dir / "klt"), KLT_YIELD=str(bin_dir / "klt-yield"), PDK_ROOT=str(pdk),
               KEEP=str(keep), RECORD_DIR=str(rec), STUB_SIM_POOL=str(pool), STUB_SIM_LOG=str(sim_log),
               STUB_YIELD_LOG=str(yield_log), PATH=str(bin_dir) + os.pathsep + os.environ.get("PATH", ""))

    def runner(extra=None):
        before = sim_log.read_text().splitlines() if sim_log.is_file() else []
        proc = subprocess.run(["bash", str(bench / "run.sh")], capture_output=True, text=True,
                              env=dict(env, **(extra or {})), timeout=900)
        submitted = sim_log.read_text().splitlines()[len(before):] if sim_log.is_file() else []
        return proc, sorted(submitted)

    def tail(proc):
        return "\n".join(proc.stderr.strip().splitlines()[-12:])

    def runner_scenarios():
        """The scenarios build on each other: each stops the chain when the runner did not
        leave the state the next one needs, so a broken runner is reported, not crashed on."""
        all_members = sorted(members)

        def step(ok, msg):
            if not ok:
                problems.append(msg)
            return ok

        def record_field(key):
            return next((l.split() for l in record_path.read_text().splitlines() if l.startswith(key + ":")), [])

        proc, submitted = runner()
        if not step(proc.returncode == 0, "fresh run: run.sh exited %d, expected 0\n%s" % (proc.returncode, tail(proc))):
            return
        step(submitted == all_members, "fresh run: submitted %d members, expected all 36 (missing: %s)"
             % (len(submitted), sorted(set(all_members) - set(submitted))[:6]))
        record_path, yield_path = rec / "record.txt", rec / "klt-yield.json"
        if not step(record_path.is_file(), "fresh run: run.sh wrote no record.txt to RECORD_DIR"):
            return
        lines = record_path.read_text().splitlines()
        head = lines[0] if lines else ""
        step("corner box: process {tt,ss,ff,sf,fs}_mm (vary=mismatch) + mc (vary=both), "
             "temperature -40 / 27 / 125 C, detector supply 2.97 / 3.3 / 3.63 V" in head
             and "216 groups" in head, "record does not state the matrix that was run:\n" + head)
        trip = next((l for l in lines if l.startswith("stimulus:")), "")
        step("xdut.flag" in trip and "half the applied detector supply" in trip
             and "1.485 / 1.65 / 1.815 V at 2.97 / 3.3 / 3.63 V" in trip,
             "record does not state the crossing criterion that was measured:\n" + trip)
        mc_line = next((l for l in lines if l.startswith("monte_carlo:")), "")
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
        neg = next((l for l in lines if l.startswith("negative control:")), "")
        step("XR2" in neg and "threshold_ref" in neg and "L=94.073 -> 88" in neg and "tt_mm" in neg,
             "record does not state the control that was run:\n" + neg)
        graded = [l for l in lines if re.match(r"\s+vtrip_l\d_(?:[a-z]+_mm|mc)_m?\d+C_\d+p\d+V: n=%d " % N, l)]
        step(len(graded) == 216, "record lists %d graded groups, expected 216" % len(graded))
        if "batch job ids:" in lines:
            block = lines[lines.index("batch job ids:") + 1: lines.index("batch job ids:") + 1 + 36]
            step([l.split(":")[0].strip() for l in block] == all_members,
                 "record lists %d batch job lines (%r), expected one per request in request order"
                 % (len(block), [l.split(":")[0].strip() for l in block][:4]))
            step(all("klt-sim-stub-" in l for l in block), "a batch job line carries no job id")
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
        step(yield_log.is_file() and len(yield_log.read_text().splitlines()) == 1,
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
      "(10 damaged-evidence refusals), resumes only on identical inputs, and reports its "
      "matrix, criterion, control and hashes (runner exit 0 / 6 / 7 / 2)")
