#!/usr/bin/env python3
"""Assemble the klt yield sample-set document and limits file from the batch reports.
usage: build_yield.py <matrix.json> <outdir-with-reports> <samples.json> <limits.json>

<matrix.json> is gen_requests.py's manifest: the groups, their coordinates and their
controls. A draw is never selected by process alone. It has to sit inside its own
(select code, process section, temperature, supply) group: the process, temperature and
supply stated on the draw, sample_index 0..N-1 exactly once, a converged corner with a
finite numeric vtrip, a report that echoes the recorded seed, N and variation mode, and
a report produced from the inputs the manifest hashes (run.sh records that hash beside
each collected report). Each group is graded at its own level nominal +/- BAND and
paired with the control population of its own section at the same code, temperature and
supply (the `mc` group with tt_mm). Fails closed (exit 1; run.sh reports 4) on any
missing, short, duplicated, non-finite or misfiled draw, naming every affected group."""
import json
import math
import pathlib
import re
import sys

BAND = 0.027   # +/-1.5 % of 1.8 V (target), spec row 5, around each level's nominal
TARGET_SIGMA = 3
CONFIDENCE = 0.95
SPEC_ROW = "5"
MEAS = "vtrip"
INPUTS = "inputs.json"   # run.sh writes it beside each report it collects
MC_SUFFIX = re.compile(r"/mc\d+$")
GROUP_KEYS = ("code", "process", "temperature_c", "supply_v", "nominal_v", "vary")
SHOWN = 20   # how many sample indices, group names or problems a message lists before "..."

problems = []


def fail(msg):
    problems.append(msg)


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def same(a, b):
    return is_num(a) and is_num(b) and math.isclose(a, b, rel_tol=0.0, abs_tol=1e-9)


def listed(items):
    items = sorted(items)
    return ", ".join(str(i) for i in items[:SHOWN]) + (", ..." if len(items) > SHOWN else "")


def report_path(outdir, member):
    """klt 0.9.3 and later collect a set member into <member>/, through 0.9.2 it was
    <member>.request/."""
    for d in (outdir / member, outdir / (member + ".request")):
        if (d / "report.json").is_file():
            return d / "report.json"
    return None


def main():
    if len(sys.argv) != 5:
        sys.exit("usage: build_yield.py <matrix.json> <outdir-with-reports> <samples.json> <limits.json>")
    matrix_path, outdir = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    try:
        man = json.loads(matrix_path.read_text())
        groups, members = man["groups"], man["members"]
        n, seed, supply_src, temps = man["n"], man["seed"], man["supply_source"], man["temperature_c"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        sys.exit("FAIL: cannot read the manifest %s: %s" % (matrix_path, e))
    if not isinstance(groups, list) or not groups or not isinstance(members, dict):
        sys.exit("FAIL: the manifest %s has no groups or members" % matrix_path)
    for g in groups:
        if not all(k in g for k in ("name", "member", "control") + GROUP_KEYS) \
                or not all(k in g["control"] for k in ("member", "process", "vary")):
            sys.exit("FAIL: the manifest group %r lacks its coordinates or control" % (g.get("name"),))
        for name in (g["member"], g["control"]["member"]):
            m = members.get(name)
            if not isinstance(m, dict) or not isinstance(m.get("process"), list) or not m["process"] \
                    or not is_num(m.get("supply_v")) or "vary" not in m or "sha256" not in m:
                sys.exit("FAIL: the manifest member %r (of group %s) lacks its process list, supply, vary or "
                         "input hash" % (name, g["name"]))
    names = [g["name"] for g in groups]
    if len(set(names)) != len(names):
        sys.exit("FAIL: the manifest names a group twice")
    # who depends on a cell: the group drawn there, and the groups whose control it is
    labels = {}
    for g in groups:
        labels.setdefault((g["member"], g["process"], g["temperature_c"]), []).append(g["name"])
        labels.setdefault((g["control"]["member"], g["control"]["process"], g["temperature_c"]), []).append(
            "control of " + g["name"])

    populations = {}
    for name in sorted({g["member"] for g in groups} | {g["control"]["member"] for g in groups}):
        m = members.get(name)
        if m is None:
            fail("%s: the manifest has no such request" % name)
            continue
        path = report_path(outdir, name)
        users = [g["name"] for g in groups if g["member"] == name] \
            + ["control of " + g["name"] for g in groups if g["control"]["member"] == name]
        if path is None:
            fail("%s: report missing (looked for %s/report.json and %s.request/report.json); it carries %s"
                 % (name, outdir / name, outdir / name, listed(users)))
            continue
        side = path.parent / INPUTS
        try:
            recorded = json.loads(side.read_text()).get("sha256") if side.is_file() else None
        except (OSError, ValueError) as e:
            fail("%s: %s beside report.json is unreadable: %s" % (name, INPUTS, e))
            continue
        if recorded is None:
            fail("%s: no %s beside report.json: cannot tell which request, deck and netlist produced it"
                 % (name, INPUTS))
        elif recorded != m.get("sha256"):
            fail("%s: the report was produced from other inputs (%s records %s, the current request, deck "
                 "and netlist hash to %s)" % (name, INPUTS, recorded, m.get("sha256")))
        try:
            rep = json.loads(path.read_text())
        except (OSError, ValueError) as e:
            fail("%s: report.json is unreadable: %s" % (name, e))
            continue
        echo = (rep.get("environment") or {}).get("monte_carlo")
        if not isinstance(echo, dict) or echo.get("seed") != seed or echo.get("n") != n or echo.get("vary") != m.get("vary"):
            fail("%s: the report echoes monte_carlo %r, expected the recorded seed %s, n %s and vary %s"
                 % (name, echo, seed, n, m.get("vary")))
        corners = rep.get("corners")
        if not isinstance(corners, list):
            fail("%s: the report has no 'corners' list" % name)
            continue

        cells = {(p, t): {} for p in m["process"] for t in temps}
        for c in corners:
            mc = c.get("monte_carlo")
            if mc is None:
                continue   # a deterministic corner is not a draw
            cid = c.get("corner_id")
            proc, temp = c.get("process"), c.get("temperature_c")
            vdd = (c.get("supply_v") or {}).get(supply_src)
            key = next((k for k in cells if k[0] == proc and same(k[1], temp)), None)
            if key is None or not same(vdd, m["supply_v"]):
                fail("%s: draw %s is filed at %s / %s C / %s=%s V, which is not a corner of this request "
                     "(%s, %s C, %s=%s V); it carries %s"
                     % (name, cid, proc, temp, supply_src, vdd, "/".join(m["process"]),
                        "/".join(str(t) for t in temps), supply_src, m["supply_v"], listed(users)))
                continue
            idx = mc.get("sample_index")
            if not isinstance(idx, int) or isinstance(idx, bool) or not 0 <= idx < n:
                fail("%s: draw %s has sample_index %r, expected 0..%d" % (name, cid, idx, n - 1))
                continue
            if idx in cells[key]:
                fail("%s: duplicate sample_index %d (draws %s and %s) in %s at %s C; it carries %s"
                     % (name, idx, cells[key][idx].get("corner_id"), cid, proc, temp,
                        listed(labels.get((name,) + key, []))))
                continue
            cells[key][idx] = c

        for key, draws in cells.items():
            label = ", ".join(labels.get((name,) + key, ["%s %s at %s C" % (name, key[0], key[1])]))
            gone = [i for i in range(n) if i not in draws]
            if gone:
                fail("%s: need %d converged samples, got %d; missing sample_index %s" % (label, n, len(draws), listed(gone)))
            values, seeds, mismatch, origins = [], [], [], set()
            for i in sorted(draws):
                c = draws[i]
                if not isinstance(c.get("corner_id"), str):
                    fail("%s: sample_index %d has no corner_id" % (label, i))
                else:
                    origins.add(MC_SUFFIX.sub("", c["corner_id"]))
                meas = [x for x in c.get("measurements") or [] if isinstance(x, dict) and x.get("name") == MEAS]
                value = meas[0].get("value") if len(meas) == 1 else None
                if c.get("status") != "pass" or len(meas) != 1 or meas[0].get("status") != "pass":
                    fail("%s: sample_index %d did not converge (corner status %s, %s status %s, value %r)"
                         % (label, i, c.get("status"), MEAS, meas[0].get("status") if meas else "absent", value))
                elif not is_num(value) or not math.isfinite(value):
                    fail("%s: sample_index %d %s is not a finite number (%r)" % (label, i, MEAS, value))
                else:
                    values.append(value)
                seeds.append(c["monte_carlo"].get("seed"))
                mismatch.append(c["monte_carlo"].get("mismatch_seed"))
            if len(origins) > 1:
                fail("%s: the draws come from %d corners (%s); a group is one population" % (label, len(origins), listed(origins)))
            twins = {s for s in seeds if seeds.count(s) > 1}
            if twins:
                fail("%s: %d draws share a seed (%s): the same draw was collected twice" % (label, len(twins), listed(twins)))
            populations[(name,) + key] = (values, origins.pop() if len(origins) == 1 else None, seeds, mismatch)

    measurements, limits = [], {}
    ctl = man.get("control") or {}
    for g in groups:
        c = g["control"]
        nom, origin = populations.get((g["member"], g["process"], g["temperature_c"]), ([], None, [], []))[:2]
        con = populations.get((c["member"], c["process"], g["temperature_c"]), ([], None, [], []))[0]
        box = {k: g[k] for k in GROUP_KEYS}
        measurements.append({
            "name": g["name"], "unit": "V", "samples": nom, "source_corners": [origin] if origin else [],
            "spec_row": SPEC_ROW, "group": box,
            "negative_control": {
                "samples": con, "errored": 0,
                "description": "ladder segment %s in %s L=%s -> %s (deliberate offset %s um), generated control "
                               "copy of %s; control section %s, vary=%s, code %s, temperature %s C, %s %s V; "
                               "seed %s, n %s"
                               % (ctl.get("instance"), ctl.get("subckt"), ctl.get("old_l_um"), ctl.get("new_l_um"),
                                  ctl.get("delta_l_um"), ctl.get("source"), c["process"], c["vary"], g["code"],
                                  g["temperature_c"], supply_src, g["supply_v"], seed, n)},
        })
        limits[g["name"]] = {"min": round(g["nominal_v"] - BAND, 6), "max": round(g["nominal_v"] + BAND, 6),
                             "target_sigma": TARGET_SIGMA, "min_converged_samples": n,
                             "spec_row": SPEC_ROW, "group": box}

    if problems:
        sys.exit("FAIL: " + "\nFAIL: ".join(problems[:SHOWN])
                 + ("\nFAIL: ... and %d more" % (len(problems) - SHOWN) if len(problems) > SHOWN else ""))
    provenance = {
        "seed": seed, "draws_per_population": n,
        "rng": "klt sim monte_carlo (ngspice .options seed= from the derived per-sample seed)",
        "corner_matrix": sorted({g["process"] for g in groups}),
        "temperature_c": temps, "supply_v": man["supply_v"],
        "netlist_sha256": man.get("netlist_sha256"), "netlist_control_sha256": man.get("netlist_control_sha256"),
        "inputs_sha256": man.get("inputs_sha256"),
    }
    # How closely each control follows its group's draws, read from the seeds the reports
    # state: the same die (every seed), only the same mismatch component, or different dice.
    def seeds_of(member, proc, temp):
        return populations.get((member, proc, temp), ([], None, [], []))[2:4]

    paired = {"all_seeds": 0, "mismatch_seed_only": 0, "none": 0, "unknown": 0}
    for g in groups:
        a = seeds_of(g["member"], g["process"], g["temperature_c"])
        b = seeds_of(g["control"]["member"], g["control"]["process"], g["temperature_c"])
        if not all(isinstance(s, int) for part in (a, b) for component in part for s in component):
            paired["unknown"] += 1
        elif a[0] == b[0]:
            paired["all_seeds"] += 1
        elif a[1] == b[1]:
            paired["mismatch_seed_only"] += 1
        else:
            paired["none"] += 1
    provenance["control_groups_paired"] = paired
    provenance["common_random_numbers"] = paired["all_seeds"] == len(groups)
    pathlib.Path(sys.argv[3]).write_text(json.dumps({"provenance": provenance, "measurements": measurements}))
    pathlib.Path(sys.argv[4]).write_text(json.dumps({"confidence": CONFIDENCE, "measurements": limits}, indent=1))


if __name__ == "__main__":
    main()
