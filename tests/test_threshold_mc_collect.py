"""PDK-free guard: sim/tb_threshold_mc/run.sh resolves KEEP before it submits (#180).

run.sh submits inside <KEEP>/req -- the batch client reads each member's request and deck
by basename -- and points the client's stdout, its stderr and its -o directory at $work.
With a relative KEEP (`KEEP=results bash sim/tb_threshold_mc/run.sh`) all three were then
resolved against <KEEP>/req: the redirect to `results/set.json` failed before the client
started, on a first run and on a resume alike.

The guard runs the real run.sh from an empty scratch caller directory with klt and klt
yield replaced by stubs and the PDK faked (a stub root satisfies the pin gate), so nothing
is simulated or submitted, and checks:

  fresh, KEEP=results    the stub, started in <caller>/results/req, reads every member's
                         request, deck and included netlist by basename (their hashes are
                         compared with the files the generator wrote); its stdout and stderr
                         land in <caller>/results/set.json and stderr.log; its reports land
                         under <caller>/results/out/; the caller directory holds nothing
                         else.
  rerun, unchanged       nothing is submitted; the collected reports are reused untouched.
  rerun, one incomplete  a report marked lost_shard: only that member is submitted, and its
                         replacement is written at the same place under results/out/.
  absolute KEEP          the same, under that directory; the caller directory stays empty.
  KEEP unset             a fresh directory under the runner's TMPDIR, gone once it has exited.

No PDK, no klt, no fleet. Repo files are read in place, never modified.
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNNER = ROOT / "sim" / "tb_threshold_mc" / "run.sh"
RELATIVE_KEEP = "results"
INCOMPLETE = "lost_shard"
problems = []


def check(cond, msg):
    if not cond:
        problems.append(msg)
    return bool(cond)


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def real(path):
    return os.path.realpath(str(path))


def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def tree_hashes(dir_path):
    return {str(p.relative_to(dir_path)): sha256(p) for p in sorted(dir_path.rglob("*")) if p.is_file()}


def logged(path):
    if not path.is_file():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()]


def members(call):
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
                     "populations": request["monte_carlo"]["n"] * len(request["corners"]["process"])})
    return want


KLT_STUB = r'''#!/usr/bin/env python3
# Test double for tests/test_threshold_mc_collect.py. `klt --version`, `klt pdk find`
# (answers the fake PDK root) and `klt sim --batch-set`: reads each member's request, deck
# and included netlist by basename from the directory it is started in, as the batch
# client does, writes a synthetic passing report per member under -o, and logs the call.
# A synthetic trip sits on the level the request sweeps, and 60 mV above it -- outside
# the row-5 +/-27 mV band -- for the control copy, so klt yield judges the control detected.
# Anything else, or a member that cannot be read, exits non-zero. No real klt runs.
import hashlib, json, os, sys

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
    lo, hi = sorted(float(t) for t in request["analysis"]["args"].split()[1:3])
    shift = 0.060 if include.endswith("_ctl.spice") else 0.0
    procs, n = request["corners"]["process"], request["monte_carlo"]["n"]
    corners = []
    for p in procs:
        for i in range(n):
            value = round((hi + lo) / 2 + shift + 0.002 * procs.index(p) + ((i * 7) % 11 - 5) * 0.0005, 6)
            corners.append({"corner_id": "%s/mc%d" % (p, i), "process": p, "temperature_c": 27,
                            "supply_v": {"Vdd": 3.3}, "status": "pass", "runtime_s": 0.0,
                            "measurements": [{"name": "vtrip", "unit": "V", "value": value,
                                              "status": "pass", "margin": None}],
                            "monte_carlo": {"sample_index": i}})
    d = os.path.join(out, m[:-len(".json")])
    os.makedirs(d, exist_ok=True)
    report = os.path.abspath(os.path.join(d, "report.json"))
    with open(report, "w") as f:
        json.dump({"schema_version": 3, "netlist": {"path": request["netlist"], "scope": "external"},
                   "status": "pass", "corner_count": len(corners), "passed": len(corners),
                   "failed": 0, "errored": 0, "stub_call": call,
                   "environment": {"engine": "ngspice", "engine_version": "46",
                                   "engine_host": "stub", "models_lib_sha256": "0" * 64,
                                   "monte_carlo": request["monte_carlo"]},
                   "corners": corners}, f)
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

YIELD_STUB = r'''#!/usr/bin/env python3
# Test double for tests/test_threshold_mc_collect.py: `klt --version` and
# `klt yield <samples> --limits <limits> --format json`. Reads the two documents the
# runner wrote, logs the call, and answers in klt yield's report shape with the verdicts
# computed from the samples: a control population that sits inside the limits less often
# than its nominal group is `detected`, and a measurement meets its sigma target when its
# distance to the nearer limit is at least target_sigma standard deviations.
import json, os, statistics, sys

args = sys.argv[1:]
if args[:1] == ["--version"]:
    print("klt 0.0.0 (yield stub for tests/test_threshold_mc_collect.py)")
    sys.exit(0)
if args[:1] != ["yield"] or args[args.index("--format") + 1:] != ["json"]:
    sys.exit("stub klt yield: unexpected invocation %r" % (args,))
samples_path, limits_path = args[1], args[args.index("--limits") + 1]
with open(samples_path) as f:
    samples = json.load(f)
with open(limits_path) as f:
    limits = json.load(f)
with open(os.environ["STUB_YIELD_LOG"], "a") as f:
    f.write(json.dumps({"cwd": os.getcwd(), "samples": samples_path, "limits": limits_path}) + "\n")

measurements = []
for m in samples["measurements"]:
    lim = limits["measurements"][m["name"]]
    xs, cs = m["samples"], m["negative_control"]["samples"]
    inside = lambda vs: sum(1 for v in vs if lim["min"] <= v <= lim["max"]) / len(vs)
    nom, ctl = inside(xs), inside(cs)
    mean, sd = statistics.fmean(xs), statistics.pstdev(xs)
    sigma = min(mean - lim["min"], lim["max"] - mean) / (sd or 1e-12)
    met = sigma >= lim["target_sigma"]
    enough = len(xs) >= lim["min_converged_samples"]
    measurements.append({
        "name": m["name"], "unit": m.get("unit"), "n": len(xs), "errored": 0,
        "limits": {k: lim[k] for k in ("min", "max", "target_sigma", "min_converged_samples")},
        "distribution": {"mean": mean, "stddev": sd},
        "capability": {"sigma_to_spec": sigma},
        "sigma_target": {"k": lim["target_sigma"], "sigma_to_spec": sigma, "met": met},
        "sample_size": {"n": len(xs), "verdict": "sufficient" if enough else "insufficient"},
        "negative_control": {"description": m["negative_control"].get("description"), "n": len(cs),
                             "degradation_detected": ctl < nom,
                             "verdict": "detected" if ctl < nom else "not_detected"},
        "status": "pass" if met and enough else "fail", "warnings": []})
print(json.dumps({
    "schema_version": 1, "samples": samples_path, "limits": limits_path,
    "confidence": limits.get("confidence"),
    "status": "pass" if all(x["status"] == "pass" for x in measurements) else "fail",
    "measurement_count": len(measurements), "measurements": measurements, "warnings": []}, indent=1))
'''

with tempfile.TemporaryDirectory(prefix="tmc-keep-") as d:
    tmp = pathlib.Path(d)
    pin = load(ROOT / "sim" / "pdk.json")
    pdk = tmp / "pdk"
    (pdk / pin["variant"] / "libs.tech" / "combined").mkdir(parents=True)
    (pdk / pin["variant"] / "SOURCES").write_text(pin["sources_line"] + "\n", encoding="utf-8")
    (pdk / pin["variant"] / "libs.tech" / "combined" / "sky130.lib.spice").write_text(
        "* fake model library\n", encoding="utf-8")
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    for name, text in (("klt", KLT_STUB), ("klt-yield", YIELD_STUB)):
        (bin_dir / name).write_text(text, encoding="utf-8")
        (bin_dir / name).chmod(0o755)
    sim_log, yield_log = tmp / "sim.log", tmp / "yield.log"
    DROP = ("KEEP", "RECORD_DIR", "PDK_PIN", "PDK_ROOT", "KLT", "KLT_YIELD",
            "STUB_SIM_LOG", "STUB_YIELD_LOG")

    def scratch(tag):
        """An empty caller directory, and the runner's environment for it: the stubs, the fake
        PDK root and a TMPDIR of its own, so nothing leaks into the host's when a run fails."""
        caller = tmp / ("caller-" + tag)
        caller.mkdir()
        runner_tmp = tmp / ("runner-tmp-" + tag)
        runner_tmp.mkdir()
        env = {k: v for k, v in os.environ.items() if k not in DROP}
        env.update(KLT=str(bin_dir / "klt"), KLT_YIELD=str(bin_dir / "klt-yield"), PDK_ROOT=str(pdk),
                   STUB_SIM_LOG=str(sim_log), STUB_YIELD_LOG=str(yield_log), TMPDIR=str(runner_tmp),
                   PATH=str(bin_dir) + os.pathsep + os.environ.get("PATH", ""))
        return caller, env

    def run(caller, env):
        sim_before, yield_before = len(logged(sim_log)), len(logged(yield_log))
        proc = subprocess.run(["bash", str(RUNNER)], cwd=caller, env=env, capture_output=True,
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
        check(sorted(members(call)) == sorted(w["member"] for w in want),
              "%s: the client received %r, expected exactly the generated requests %r"
              % (label, sorted(members(call)), sorted(w["member"] for w in want)))
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
              % (label, proc.returncode, [m for c in sim_calls for m in members(c)], tail(proc)))
        check(tree_hashes(keep / "out") == before,
              "%s: unchanged rerun: the collected reports changed without a submission" % label)

    caller, env = scratch("relative")
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
        if check(proc.returncode == 0 and len(sim_calls) == 1 and members(sim_calls[0]) == [member["member"]],
                 "rerun, KEEP=%s, %s incomplete: run.sh exited %d and submitted %r, expected exit 0 and "
                 "only %s\n%s" % (RELATIVE_KEEP, member["member"], proc.returncode,
                                  [m for c in sim_calls for m in members(c)], member["member"], tail(proc))):
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
    keep = tmp / "abs-keep"
    env["KEEP"] = str(keep)
    proc, sim_calls, yield_calls = run(caller, env)
    call = first_submission("absolute KEEP", keep, proc, sim_calls, yield_calls)
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

if problems:
    sys.exit("tb_threshold_mc KEEP handling is wrong:\n  - " + "\n  - ".join(problems))
print("ok: tb_threshold_mc keeps a relative KEEP where the caller chose it (fresh run, "
      "unchanged rerun, one incomplete report replaced), and still honours an absolute KEEP "
      "and cleans up without one")
