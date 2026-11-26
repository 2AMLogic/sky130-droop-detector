#!/usr/bin/env python3
"""PDK-free guard: tb_threshold_mc generates the whole ratified row 5 corner box.

Guards what `sim/tb_threshold_mc/gen_requests.py` emits (#169). It used to ask for
27 C and Vdd = 3.3 V only, and found its negative-control target by searching the
netlist for a literal `L=94.073`, so a resized ladder would have stopped the bench.
The generator now emits, and describes in a manifest that `build_yield.py` and
`run.sh` read back:

  - 36 requests = 4 select codes x {mm, mc, ctl} x 3 supplies, each sweeping the 3
    temperatures: 4 x 6 x 3 x 3 = 216 nominal groups, seed 20261105, N = 300, mismatch
    variation in the five *_mm sections and combined variation in `mc`;
  - decks that drive an asserted select bit at the applied supply and a deasserted one
    at ground, and a trip measurement at half the applied supply (a .meas WHEN card
    takes only a literal, hence one request per supply);
  - a control copy in which exactly the threshold_ref ladder XR2 is shortened,
    whatever length the input carries, with the second XR2 (flag_logic) untouched,
    and a refusal before anything is written when that target is missing or ambiguous;
  - a per-request input hash over the request, its deck and the included netlist, which
    `run.sh` compares before reusing a collected report.

The generator is run on scratch copies of the four files it reads, so the repo's own
design netlist, level table and template are never modified. No PDK, no klt.
"""
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
COPIED = ("design/detector_top.spice", "sim/lib/levels.json",
          "sim/tb_threshold_mc/gen_requests.py", "sim/tb_threshold_mc/tb_threshold_mc.spice")
SEED, N = 20261105, 300
TEMPS = [-40, 27, 125]
SUPPLIES = [2.97, 3.3, 3.63]
MM = ["tt_mm", "ss_mm", "ff_mm", "sf_mm", "fs_mm"]
SECTIONS = MM + ["mc"]
KINDS = {"mm": (MM, "mismatch", "detector_top.spice"),
         "mc": (["mc"], "both", "detector_top.spice"),
         "ctl": (MM, "mismatch", "detector_top_ctl.spice")}
LADDER = "XR2 t0 vref gnd sky130_fd_pr__res_xhigh_po_1p41 L=94.073 mult=1 m=1"
FLAG_XR2 = "XR2 gnd vlim gnd sky130_fd_pr__res_xhigh_po_1p41 L=1200 mult=1 m=1"
OFFSET = -6.073   # the recorded control: L = 94.073 -> 88

with (ROOT / "sim/lib/levels.json").open() as _f:
    LEVELS = json.load(_f)["levels"]


def vtag(v):
    return ("%.2f" % v).replace(".", "p")   # 2.97 V -> 2p97, as the generator writes it


def ttag(t):
    return ("m" if t < 0 else "") + str(abs(int(t))) + "C"


def member(code, kind, v):
    return "l%d_%s_%s" % (code, kind, vtag(v))


def group(code, proc, t, v):
    return "vtrip_l%d_%s_%s_%sV" % (code, proc, ttag(t), vtag(v))


def expected_groups():
    return {group(row["code"], p, t, v)
            for row in LEVELS for p in SECTIONS for t in TEMPS for v in SUPPLIES}


def expected_tuples():
    return {(row["code"], p, t, v)
            for row in LEVELS for p in SECTIONS for t in TEMPS for v in SUPPLIES}


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def scratch(tmp, top=None, template=None, levels=None):
    """Copy the four generator inputs into <tmp> at their repo-relative paths and
    apply the overrides; returns the scratch generator's path."""
    for rel in COPIED:
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    if top is not None:
        (tmp / "design/detector_top.spice").write_text(top)
    if template is not None:
        (tmp / "sim/tb_threshold_mc/tb_threshold_mc.spice").write_text(template)
    if levels is not None:
        (tmp / "sim/lib/levels.json").write_text(json.dumps(levels))
    return tmp / "sim/tb_threshold_mc/gen_requests.py"


def generate(script, outdir):
    return subprocess.run([sys.executable, "-I", str(script), str(outdir)],
                          capture_output=True, text=True, timeout=120)


def run(tmp, **overrides):
    """Generate into a fresh scratch tree; returns (proc, manifest or None, reqdir)."""
    script = scratch(pathlib.Path(tmp), **overrides)
    reqdir = pathlib.Path(tmp) / "req"
    proc = generate(script, reqdir)
    try:
        man = json.loads(proc.stdout)
    except ValueError:
        man = None
    return proc, man, reqdir


def source_texts():
    top = (ROOT / "design/detector_top.spice").read_text()
    template = (ROOT / "sim/tb_threshold_mc/tb_threshold_mc.spice").read_text()
    return top, template


def subckt_span(text, name):
    """Line-number span [start, end) of `.subckt <name>` ... `.ends`."""
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.split()[:2] == [".subckt", name])
    end = next(i for i in range(start, len(lines)) if lines[i].split()[:1] == [".ends"])
    return start, end + 1


problems = []


def check(cond, msg):
    if not cond:
        problems.append(msg)


# ---------------------------------------------------------------- the real matrix
with tempfile.TemporaryDirectory(prefix="tmc-req-") as d:
    proc, man, reqdir = run(d)
    check(proc.returncode == 0, "generator exited %d on the repo netlist:\n%s"
          % (proc.returncode, proc.stderr.strip()))
    if man is not None:
        members = man.get("members")
        if not isinstance(members, dict):
            problems.append("manifest has no 'members' table: gen_requests.py does not "
                            "describe the requests it wrote (keys: %s)" % sorted(man))
        else:
            want_members = {member(row["code"], k, v)
                            for row in LEVELS for k in KINDS for v in SUPPLIES}
            check(set(members) == want_members,
                  "manifest members are not the 4 codes x {mm,mc,ctl} x 3 supplies set:\n"
                  "  missing: %s\n  unexpected: %s"
                  % (sorted(want_members - set(members)), sorted(set(members) - want_members)))
            on_disk = {p.name[:-len(".request.json")] for p in reqdir.glob("*.request.json")}
            check(on_disk == set(members),
                  "request files on disk %s do not match the manifest %s" % (sorted(on_disk), sorted(members)))

            tuples, ctl_tuples = [], []
            for name, m in sorted(members.items()):
                req_path = reqdir / (name + ".request.json")
                if not req_path.is_file():
                    continue
                req = json.loads(req_path.read_text())
                code, kind, vtag_ = name.split("_")
                code, v = int(code[1:]), float(vtag_.replace("p", "."))
                procs, vary, net = KINDS[kind]
                where = "%s: " % name
                check(m.get("kind") == kind and m.get("code") == code and m.get("supply_v") == v,
                      where + "manifest says kind=%r code=%r supply=%r"
                      % (m.get("kind"), m.get("code"), m.get("supply_v")))
                check(req.get("corners", {}).get("process") == procs,
                      where + "corners.process is %r, expected %r" % (req.get("corners", {}).get("process"), procs))
                check(req.get("corners", {}).get("temperature_c") == TEMPS,
                      where + "temperature_c is %r, expected %r" % (req.get("corners", {}).get("temperature_c"), TEMPS))
                check(req.get("corners", {}).get("supply_v") == {"Vdd": [v]},
                      where + "supply_v is %r, expected the single applied supply {'Vdd': [%s]}" % (req.get("corners", {}).get("supply_v"), v))
                mc = req.get("monte_carlo") or {}
                check(mc.get("seed") == SEED and mc.get("n") == N and mc.get("vary") == vary,
                      where + "monte_carlo is %r, expected seed %d, n %d, vary %r" % (mc, SEED, N, vary))
                check(m.get("vary") == vary and m.get("process") == procs,
                      where + "manifest vary/process %r/%r disagree with the request" % (m.get("vary"), m.get("process")))
                check(m.get("units") == len(procs) * len(TEMPS) * N,
                      where + "manifest units is %r, expected %d" % (m.get("units"), len(procs) * len(TEMPS) * N))

                level = next(r for r in LEVELS if r["code"] == code)
                deck = reqdir / str(req.get("netlist"))
                check(req.get("netlist") == "tb_%s.spice" % name,
                      where + "request netlist is %r, expected the generated deck" % req.get("netlist"))
                if deck.is_file():
                    text = deck.read_text()
                    check('.include "%s"' % net in text,
                          where + "deck does not include %s" % net)
                    check(not re.search(r"__[A-Z0-9]+__", text),
                          where + "deck still carries a placeholder: %s"
                          % sorted(set(re.findall(r"__[A-Z0-9]+__", text))))
                    hi = {False: "0", True: str(v)}
                    for src, pin, asserted in (("Vs0", "s0", level["s0"] != 0), ("Vs1", "s1", level["s1"] != 0)):
                        m_ = re.search(r"^%s %s 0 (\S+)$" % (src, pin), text, re.M)
                        check(m_ is not None and m_.group(1) == hi[asserted],
                              where + "%s drives %s; code %d has %s=%r, so the bit must sit at %s"
                              % (src, m_.group(1) if m_ else "<no card>", code, pin, level[pin],
                                 "the applied supply" if asserted else "ground"))
                    m_ = re.search(r"^Vdd vdd33 0 (\S+)$", text, re.M)
                    check(m_ is not None and m_.group(1) == str(v),
                          where + "deck Vdd literal is %s, expected the applied supply %s"
                          % (m_.group(1) if m_ else "<no card>", v))

                meas = req.get("measurements") or [{}]
                check(len(meas) == 1 and meas[0].get("name") == "vtrip" and meas[0].get("unit") == "V",
                      where + "measurements are %r, expected one: vtrip in V" % (req.get("measurements"),))
                want_meas = ".meas dc vtrip WHEN v(xdut.flag)=%s RISE=1" % (v / 2)
                check(meas[0].get("spice") == want_meas,
                      where + "trip card is %r, expected %r (first rising crossing of the internal "
                      "comparator output at half the applied supply)" % (meas[0].get("spice"), want_meas))
                nom = level["v"]
                want_args = "Vrail %.4f %.4f -0.0005" % (nom + 0.25, nom - 0.25)
                check(req.get("analysis", {}).get("kind") == "dc" and req.get("analysis", {}).get("args") == want_args,
                      where + "analysis is %r, expected the descending nominal +/- 250 mV sweep %r"
                      % (req.get("analysis"), want_args))

                cells = {(code, p, t, v) for p in procs for t in TEMPS}
                (tuples if kind != "ctl" else ctl_tuples).extend(sorted(cells))

            check(len(tuples) == 216 and set(tuples) == expected_tuples(),
                  "the nominal requests expand to %d (code, process, temperature, supply) tuples "
                  "with %d distinct; expected exactly the 216 of the ratified box (missing: %s)"
                  % (len(tuples), len(set(tuples)), sorted(expected_tuples() - set(tuples))[:6]))
            check(sorted(ctl_tuples) == sorted(t for t in tuples if t[1] != "mc"),
                  "the control requests must cover exactly the five *_mm populations of the "
                  "nominal requests at the same code, temperature and supply")

            groups = man.get("groups")
            if not isinstance(groups, list):
                problems.append("manifest has no 'groups' list naming the nominal yield groups")
            else:
                names = [g.get("name") for g in groups]
                check(len(names) == 216 and set(names) == expected_groups(),
                      "manifest names %d groups with %d distinct; expected the 216 group names "
                      "(missing: %s)" % (len(names), len(set(names)),
                                         sorted(expected_groups() - set(names))[:6]))
                for g in groups:
                    name = g.get("name", "?")
                    m_ = re.match(r"vtrip_l(\d)_([a-z]+_mm|mc)_(m?\d+)C_(\d+p\d+)V$", str(name))
                    if not m_:
                        problems.append("group name %r does not encode code, section, temperature and supply" % name)
                        continue
                    code, proc, t, v = int(m_.group(1)), m_.group(2), int(m_.group(3).replace("m", "-")), float(m_.group(4).replace("p", "."))
                    level = next(r for r in LEVELS if r["code"] == code)
                    kind = "mc" if proc == "mc" else "mm"
                    ctl_proc = "tt_mm" if proc == "mc" else proc
                    check(g.get("code") == code and g.get("process") == proc
                          and g.get("temperature_c") == t and g.get("supply_v") == v,
                          "%s: manifest coordinates are %r" % (name, {k: g.get(k) for k in ("code", "process", "temperature_c", "supply_v")}))
                    check(g.get("nominal_v") == level["v"],
                          "%s: nominal_v is %r, levels.json says %r" % (name, g.get("nominal_v"), level["v"]))
                    check(g.get("vary") == KINDS[kind][1] and g.get("member") == member(code, kind, v),
                          "%s: member/vary are %r/%r, expected %s/%s" % (name, g.get("member"), g.get("vary"), member(code, kind, v), KINDS[kind][1]))
                    ctl = g.get("control") or {}
                    check(ctl.get("member") == member(code, "ctl", v) and ctl.get("process") == ctl_proc
                          and ctl.get("vary") == "mismatch",
                          "%s: control is %r, expected the %s mismatch population of %s (same code, "
                          "temperature and supply)" % (name, ctl, ctl_proc, member(code, "ctl", v)))

            ctl_edit = man.get("control") or {}
            check(str(ctl_edit.get("old_l_um")) in ("94.073", "94.0730") and str(ctl_edit.get("new_l_um")) in ("88", "88.0")
                  and ctl_edit.get("subckt") == "threshold_ref" and ctl_edit.get("instance") == "XR2",
                  "manifest control record is %r, expected the threshold_ref XR2, L 94.073 -> 88"
                  % (ctl_edit,))
            check(man.get("seed") == SEED and man.get("n") == N and man.get("levels") == [r["v"] for r in LEVELS],
                  "manifest seed/n/levels are %r" % ({k: man.get(k) for k in ("seed", "n", "levels")},))
            check(man.get("group_count") == 216 and man.get("request_count") == 36
                  and man.get("unit_count") == (216 + 180) * N,
                  "manifest counts are %r, expected 216 groups, 36 requests and %d simulated draws"
                  % ({k: man.get(k) for k in ("group_count", "request_count", "unit_count")}, (216 + 180) * N))
            check(man.get("temperature_c") == TEMPS and man.get("supply_v") == SUPPLIES
                  and man.get("process_mm") == MM and man.get("process_mc") == ["mc"],
                  "manifest corner box is %r" % ({k: man.get(k) for k in ("temperature_c", "supply_v", "process_mm", "process_mc")},))

            # nominal copy is the input, byte for byte; the control differs in one ladder line
            top, _ = source_texts()
            nominal, control = reqdir / "detector_top.spice", reqdir / "detector_top_ctl.spice"
            if nominal.is_file() and control.is_file():
                lo, hi = subckt_span(top, "threshold_ref")
                nom_lines, ctl_lines = nominal.read_text().splitlines(), control.read_text().splitlines()
                check(nominal.read_text() == top, "the nominal netlist copy is not the input netlist")
                diffs = [i for i, (a, b) in enumerate(zip(nom_lines, ctl_lines)) if a != b]
                check(len(nom_lines) == len(ctl_lines) and diffs == [lo + next(
                    i for i, l in enumerate(top.splitlines()[lo:hi]) if l == LADDER)],
                    "nominal vs control differ at lines %r of %d/%d; expected exactly the threshold_ref "
                    "ladder XR2 line" % (diffs, len(nom_lines), len(ctl_lines)))
                for i in diffs:
                    if lo <= i < hi:
                        check(nom_lines[i] == LADDER and ctl_lines[i] == LADDER.replace("L=94.073", "L=88"),
                              "control line %d is %r, expected the ladder XR2 with L=88" % (i + 1, ctl_lines[i]))
                check(FLAG_XR2 in ctl_lines and ctl_lines.count(FLAG_XR2) == top.count(FLAG_XR2),
                      "the flag_logic XR2 was modified in the control copy")
                check(man.get("netlist_sha256") == sha256(nominal)
                      and man.get("netlist_control_sha256") == sha256(control),
                      "manifest netlist hashes do not match the two generated copies")
            else:
                problems.append("generator did not write detector_top.spice and detector_top_ctl.spice")

            # per-request input hash: covers the request, its deck and the included netlist
            for name, m in sorted(members.items()):
                inputs = m.get("inputs")
                if not isinstance(inputs, dict) or not inputs:
                    problems.append("%s: manifest has no per-input hashes" % name)
                    continue
                req = json.loads((reqdir / (name + ".request.json")).read_text())
                need = {name + ".request.json", str(req.get("netlist"))}
                inc = re.search(r'^\.include\s+"?([^"\s]+)"?', (reqdir / str(req.get("netlist"))).read_text(), re.M)
                if inc:
                    need.add(inc.group(1))
                for f in sorted(need):
                    check(f in inputs, "%s: input hash does not cover %s" % (name, f))
                for f, h in sorted(inputs.items()):
                    p = reqdir / f
                    check(p.is_file() and isinstance(h, str) and sha256(p) == h,
                          "%s: recorded hash of %s does not match the file" % (name, f))
                check(isinstance(m.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", m.get("sha256") or ""),
                      "%s: no sha256 input fingerprint" % name)
            check(re.fullmatch(r"[0-9a-f]{64}", man.get("inputs_sha256") or "") is not None,
                  "manifest has no inputs_sha256 over the whole request set")
            base = {n: m.get("sha256") for n, m in members.items()}
            base_all = man.get("inputs_sha256")

    # ------------------------------------------------------ a resized ladder XR2
    top, _ = source_texts()
    lo, hi = subckt_span(top, "threshold_ref")
    resized = top.splitlines()
    resized[lo + next(i for i, l in enumerate(top.splitlines()[lo:hi]) if l == LADDER)] = LADDER.replace("L=94.073", "L=120.5")
    proc2, man2, req2 = run(d, top="\n".join(resized) + "\n")
    check(proc2.returncode == 0, "generator exited %d on a top whose ladder XR2 is L=120.5:\n%s"
          % (proc2.returncode, proc2.stderr.strip()))
    if man2 is not None:
        want = "L=" + ("%f" % (120.5 + OFFSET)).rstrip("0")
        text = (req2 / "detector_top_ctl.spice").read_text() if (req2 / "detector_top_ctl.spice").is_file() else ""
        diff = [(a, b) for a, b in zip(resized, text.splitlines()) if a != b]
        check(len(diff) == 1 and diff[0][0] == LADDER.replace("L=94.073", "L=120.5") and diff[0][1] == LADDER.replace("L=94.073", want),
              "resized ladder: nominal-vs-control diff is %r, expected only the threshold_ref XR2 line "
              "carrying %s" % (diff, want))
        check(FLAG_XR2 in text, "resized ladder: the flag_logic XR2 did not keep its geometry")
        edit = man2.get("control") or {}
        check(str(edit.get("old_l_um")) in ("120.5",) and str(edit.get("new_l_um")) in (want[2:],),
              "resized ladder: manifest control record is %r, expected L 120.5 -> %s" % (edit, want[2:]))
        check((req2 / "detector_top.spice").read_text() == "\n".join(resized) + "\n",
              "resized ladder: the nominal copy is not the fixture top")

    # ------------------------------------------------- missing / ambiguous target
    bad_tops = {
        "no threshold_ref subckt": top.replace(".subckt threshold_ref ", ".subckt threshold_rex "),
        "no XR2 in threshold_ref": top.replace(LADDER, LADDER.replace("XR2", "XR9")),
        "two XR2 in threshold_ref": top.replace("XR3 t1 t0 gnd", "XR2 t1 t0 gnd"),
        "ladder XR2 without L": top.replace(LADDER, LADDER.replace(" L=94.073", "")),
    }
    for label, bad in bad_tops.items():
        with tempfile.TemporaryDirectory(prefix="tmc-req-bad-") as bd:
            proc3, _, req3 = run(bd, top=bad)
            written = sorted(p.name for p in req3.glob("*.request.json")) if req3.is_dir() else []
            check(proc3.returncode != 0, "%s: generator succeeded (%d requests)" % (label, len(written)))
            check("FAIL" in proc3.stderr and "XR2" in proc3.stderr and "threshold_ref" in proc3.stderr,
                  "%s: failure message does not name the control target:\n%s" % (label, proc3.stderr.strip()[-400:]))
            check(not written and not proc3.stdout.strip(),
                  "%s: generator wrote %d request(s) before failing; nothing may be submitted" % (label, len(written)))

    # ------------------------------------------- input hash follows each simulated input
    _, template = source_texts()
    with (ROOT / "sim/lib/levels.json").open() as f:
        levels = json.load(f)
    levels["levels"][2]["v"] = 1.639
    variants = {
        "an identical tree": {},
        "a changed netlist": {"top": top.replace("L=225.433", "L=225.43")},
        "a changed deck template": {"template": template.replace("Cl live 0 5f", "Cl live 0 6f")},
        "a changed level nominal": {"levels": levels},
    }
    if man is not None and isinstance(man.get("members"), dict):
        for label, over in variants.items():
            with tempfile.TemporaryDirectory(prefix="tmc-req-hash-") as hd:
                proc4, man4, _ = run(hd, **over)
                if proc4.returncode != 0 or man4 is None:
                    problems.append("%s: generator exited %d:\n%s" % (label, proc4.returncode, proc4.stderr.strip()[-400:]))
                    continue
                got = {n: m.get("sha256") for n, m in man4.get("members", {}).items()}
                changed = {n for n in base if got.get(n) != base[n]}
                want_changed = {"an identical tree": set(), "a changed level nominal": {n for n in base if n.startswith("l2_")},
                                }.get(label, set(base))
                check(changed == want_changed,
                      "%s: input hash changed for %s; expected %s"
                      % (label, sorted(changed) if len(changed) < 12 else "%d members" % len(changed),
                         sorted(want_changed) if len(want_changed) < 12 else "%d members" % len(want_changed)))
                check((man4.get("inputs_sha256") == base_all) == (label == "an identical tree"),
                      "%s: inputs_sha256 %s changed" % (label, "did not" if label != "an identical tree" else "did"))

if problems:
    sys.exit("tb_threshold_mc request generation is wrong:\n  - " + "\n  - ".join(problems[:25])
             + ("\n  - ... and %d more" % (len(problems) - 25) if len(problems) > 25 else ""))
print("ok: tb_threshold_mc generates 216 row-5 groups as 36 corner-specific requests with a "
      "geometry-derived ladder control and per-request input hashes (4 malformed-target "
      "refusals, 4 input-hash variants)")
