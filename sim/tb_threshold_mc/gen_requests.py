#!/usr/bin/env python3
"""Write the tb_threshold_mc klt sim requests into <workdir> and print their manifest
(usage: gen_requests.py <workdir>; run.sh saves stdout as matrix.json).

36 requests: for each of the 4 select codes, each of the 3 detector supplies of the
ratified PVT box and each kind
  mm   the five *_mm sections, vary=mismatch, design/detector_top.spice
  mc   the `mc` section, vary=both, design/detector_top.spice
  ctl  the five *_mm sections, vary=mismatch, a control copy of the netlist in which
       the threshold_ref ladder XR2 is shorter by CONTROL_DL
so the campaign is 4 x 6 x 3 x 3 = 216 nominal groups of N draws from SEED. A request
sweeps the 3 temperatures and carries its supply as a one-point axis, so every draw in
its report states the supply it was simulated at. There is one request per supply
because the trip is a .meas WHEN card, whose threshold ngspice accepts only as a
literal: half the applied supply, the same fraction of the comparator output swing at
every supply (the 1.65 V of the earlier bench at 3.3 V). An asserted select bit is
driven at the applied supply, a deasserted one at ground.

The manifest is the one description of the matrix: build_yield.py reads the groups and
their controls back from it, run.sh the per-request input hashes (the request, its deck
and the netlist that deck includes) that decide whether a collected report may be reused.

Seed, N, the corner box and the control offset are constants here and are the recorded
values."""
import hashlib
import json
import pathlib
import re
import sys
from decimal import Decimal, InvalidOperation

SEED = 20261105
N = 300
TEMPS = [-40, 27, 125]
SUPPLIES = [2.97, 3.3, 3.63]
MM = ["tt_mm", "ss_mm", "ff_mm", "sf_mm", "fs_mm"]
SPAN = 0.25   # sweep nominal +/- 250 mV, 0.5 mV steps (static trip, slow ramp)
STEP = 0.0005
SUPPLY_SRC = "Vdd"   # the bench's detector-supply source, the key of corners.supply_v
MEAS = "vtrip"
TOP = "design/detector_top.spice"
NOMINAL_TOP, CONTROL_TOP = "detector_top.spice", "detector_top_ctl.spice"
CONTROL_SUBCKT, CONTROL_INST = "threshold_ref", "XR2"
CONTROL_DL = Decimal("-6.073")   # the recorded control: ladder XR2 L = 94.073 -> 88
KINDS = (("mm", MM, "mismatch", NOMINAL_TOP),
         ("mc", ["mc"], "both", NOMINAL_TOP),
         ("ctl", MM, "mismatch", CONTROL_TOP))
PLACEHOLDER = re.compile(r"__[A-Z0-9]+__")
# Mask quoted values before looking for comments or assignments on xschem cards.
# Preserve columns so the verified value's span also indexes the original line.
SPICE_NON_CODE = re.compile(r"""^\s*\*.*|(?P<value>"[^"]*"|'[^']*'|\{[^{}]*\})|(?:\$|;|//).*""")
L_TOKEN = re.compile(r"(?<!\S)L\s*=\s*(\S+)", re.I)
INCLUDE = re.compile(r"""^\s*\.include\s+(?:"([^"]+)"|'([^']+)'|(\S+))""", re.I | re.M)

here = pathlib.Path(__file__).resolve().parent


def die(msg):
    sys.exit("gen_requests: FAIL: " + msg)


def num(x):
    """Shortest exact decimal text of a Decimal (88.000 -> 88)."""
    return format(Decimal(x).normalize(), "f")


def tags(v):
    return "%.2f" % v


def member(code, kind, v):
    return "l%d_%s_%s" % (code, kind, tags(v).replace(".", "p"))


def group(code, proc, t, v):
    return "vtrip_l%d_%s_%s%dC_%sV" % (code, proc, "m" if t < 0 else "", abs(t), tags(v).replace(".", "p"))


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def cards(lines):
    """(first line, line after the last, tokens) of each uncommented logical card."""
    out = []
    for i, line in enumerate(lines):
        body = line.strip()
        if not body:
            continue
        if body.startswith("+") and out:
            out[-1][1] = i + 1
            out[-1][2].extend(body[1:].split())
        else:
            out.append([i, i + 1, body.split()])
    return out


def ladder_target(text):
    """Locate the line and value span of the one ladder resistor
    CONTROL_INST inside .subckt CONTROL_SUBCKT. Exits naming the target when it is
    missing, ambiguous or not a resistor with a plain L. Lines are split on "\n" only,
    so joining them back reproduces the input byte for byte."""
    lines = text.split("\n")
    active = [SPICE_NON_CODE.sub(lambda m: "?" * len(m[0]) if m["value"] else "", line)
              for line in lines]
    deck = cards(active)
    definitions = [i for i, (_, _, tokens) in enumerate(deck)
                   if [t.lower() for t in tokens[:2]] == [".subckt", CONTROL_SUBCKT]]
    if not definitions:
        die("negative-control target not found: %s has no .subckt %s (looking for ladder "
            "resistor %s)" % (TOP, CONTROL_SUBCKT, CONTROL_INST))
    if len(definitions) != 1:
        die("negative-control target is ambiguous: %d .subckt %s definitions in %s "
            "(looking for ladder resistor %s)" % (len(definitions), CONTROL_SUBCKT, TOP, CONTROL_INST))
    opened = definitions[0]
    closed = next((i for i in range(opened + 1, len(deck))
                   if deck[i][2][0].lower() in (".ends", ".subckt")), len(deck))
    if closed == len(deck) or deck[closed][2][0].lower() != ".ends":
        die("negative-control target not usable: .subckt %s containing %s in %s is never closed"
            % (CONTROL_SUBCKT, CONTROL_INST, TOP))
    hits = [c for c in deck[opened + 1:closed] if c[2][0].lower() == CONTROL_INST.lower()]
    where = "inside .subckt %s of %s" % (CONTROL_SUBCKT, TOP)
    if not hits:
        die("negative-control target not found: no %s card %s" % (CONTROL_INST, where))
    if len(hits) > 1:
        die("negative-control target is ambiguous: %d %s cards %s, at lines %s"
            % (len(hits), CONTROL_INST, where, ", ".join(str(h[0] + 1) for h in hits)))
    first, last, tok = hits[0]
    # xschem writes X<name> <nodes...> <model> <param=value...>: the model is the token before the first parameter
    header = re.split(r"\s+\w+\s*=", " ".join(tok), maxsplit=1)[0].split()
    model = header[-1].lower() if len(header) >= 3 else ""
    if "res" not in model:
        die("negative-control target is not a resistor: %s %s is %s" % (CONTROL_INST, where, " ".join(tok)))
    # Parse assignments across continuations, preserving physical lines and columns.
    body = "\n".join(re.sub(r"^(\s*)\+", r"\1 ", line) for line in active[first:last])
    found = list(L_TOKEN.finditer(body))
    if len(found) != 1:
        die("negative-control target carries %d L= value(s), expected one: %s %s"
            % (len(found), CONTROL_INST, where))
    m = found[0]
    try:
        old = Decimal(m.group(1))
    except InvalidOperation:
        die("negative-control target has a non-numeric length: %s %s is L=%s"
            % (CONTROL_INST, where, m.group(1)))
    if not old.is_finite() or old <= 0:
        die("negative-control target has a non-positive length: %s %s is L=%s"
            % (CONTROL_INST, where, m.group(1)))
    start, end = m.span(1)
    line = first + body.count("\n", 0, start)
    line_start = body.rfind("\n", 0, start) + 1
    return old, line, (start - line_start, end - line_start), lines


def offset_ladder(text):
    """A copy of `text` in which the threshold_ref ladder XR2 is shorter by CONTROL_DL,
    with (old L, new L); exits unless the copy re-parses to that one change."""
    old, line, (start, end), lines = ladder_target(text)
    new = old + CONTROL_DL
    if not new.is_finite() or new <= 0:
        die("the deliberate offset %s um leaves no positive length on the ladder %s "
            "inside %s (L=%s)" % (CONTROL_DL, CONTROL_INST, CONTROL_SUBCKT, num(old)))
    lines[line] = lines[line][:start] + num(new) + lines[line][end:]
    edited = "\n".join(lines)
    if ladder_target(edited)[0] != new:
        die("the deliberate offset did not take effect on the ladder %s inside %s"
            % (CONTROL_INST, CONTROL_SUBCKT))
    moved = [i for i, (a, b) in enumerate(zip(text.split("\n"), edited.split("\n"))) if a != b]
    if moved != [line] or len(text.split("\n")) != len(edited.split("\n")):
        die("the deliberate offset changed lines %s of %s, expected only line %d"
            % (moved, TOP, line + 1))
    return edited, num(old), num(new)


def include_closure(files, name, seen=None):
    """{file name: sha256} of `name` (a text in `files`) and of every generated file it
    .includes, recursively."""
    seen = set() if seen is None else seen
    if name in seen or name not in files:
        return {}
    seen.add(name)
    out = {name: sha256(files[name].encode())}
    for m in INCLUDE.finditer(files[name]):
        out.update(include_closure(files, m.group(1) or m.group(2) or m.group(3), seen))
    return out


def main():
    if len(sys.argv) != 2:
        die("usage: gen_requests.py <workdir>")
    work = pathlib.Path(sys.argv[1])
    try:
        top = (here / ".." / ".." / TOP).read_text()
        template = (here / "tb_threshold_mc.spice").read_text()
        with (here.parent / "lib" / "levels.json").open() as f:
            levels = json.load(f)["levels"]
    except (OSError, ValueError) as e:
        die("cannot read the generator inputs: %s" % e)
    if sorted(r["code"] for r in levels) != [0, 1, 2, 3]:
        die("sim/lib/levels.json must hold the four select codes 0..3")
    control_top, old_l, new_l = offset_ladder(top)

    files, members, groups = {}, {}, []
    for row in levels:
        code = row["code"]
        for v in SUPPLIES:
            vtxt, half = str(v), num(Decimal(str(v)) / 2)
            # an asserted bit follows the applied supply, a deasserted one sits at ground
            hi = {pin: (vtxt if Decimal(str(row[pin])) != 0 else "0") for pin in ("s0", "s1")}
            for pin, bit in (("s0", 1), ("s1", 2)):
                if (hi[pin] != "0") != bool(code & bit):
                    die("sim/lib/levels.json: code %d disagrees with %s=%s" % (code, pin, row[pin]))
            for kind, procs, vary, net in KINDS:
                name = member(code, kind, v)
                deck = "tb_%s.spice" % name
                body = (template.replace("__NETLIST__", net).replace("__S0__", hi["s0"])
                        .replace("__S1__", hi["s1"]).replace("__VDD__", vtxt))
                if PLACEHOLDER.search(body):
                    die("%s still carries the placeholder %s" % (deck, PLACEHOLDER.search(body).group(0)))
                req = {
                    "netlist": deck,
                    "models": {"pdk": "sky130A", "lib": "libs.tech/combined/sky130.lib.spice"},
                    "corners": {"process": procs, "temperature_c": TEMPS, "supply_v": {SUPPLY_SRC: [v]}},
                    "monte_carlo": {"n": N, "seed": SEED, "vary": vary},
                    "analysis": {"kind": "dc", "args": "Vrail %.4f %.4f %s" % (row["v"] + SPAN, row["v"] - SPAN, num(-Decimal(str(STEP))))},
                    "measurements": [{"name": MEAS, "unit": "V",
                                      "spice": ".meas dc %s WHEN v(xdut.flag)=%s RISE=1" % (MEAS, half)}],
                    "options": {"timeout_s": 90},
                    "batch": {"job_ceiling_check": "split"},
                }
                files[name + ".request.json"] = json.dumps(req, indent=1)
                files[deck] = body
                members[name] = {"kind": kind, "code": code, "supply_v": v, "process": procs, "vary": vary,
                                 "deck": deck, "units": len(procs) * len(TEMPS) * N}
    files[NOMINAL_TOP], files[CONTROL_TOP] = top, control_top
    for name, m in members.items():
        # the simulated inputs of a request: itself, the deck its `netlist` field names, and what that deck includes
        m["inputs"] = {name + ".request.json": sha256(files[name + ".request.json"].encode())}
        m["inputs"].update(include_closure(files, m["deck"]))
        need = {m["deck"], CONTROL_TOP if m["kind"] == "ctl" else NOMINAL_TOP}
        if not need <= set(m["inputs"]):
            die("%s: the input hash would not cover %s" % (name, sorted(need - set(m["inputs"]))))
        m["sha256"] = sha256(json.dumps(sorted(m["inputs"].items())).encode())
    for row in levels:
        for proc in MM + ["mc"]:
            for t in TEMPS:
                for v in SUPPLIES:
                    kind, ctl_proc = ("mc", "tt_mm") if proc == "mc" else ("mm", proc)
                    groups.append({
                        "name": group(row["code"], proc, t, v), "code": row["code"], "process": proc,
                        "temperature_c": t, "supply_v": v, "nominal_v": row["v"], "vary": "both" if proc == "mc" else "mismatch",
                        "member": member(row["code"], kind, v),
                        "control": {"member": member(row["code"], "ctl", v), "process": ctl_proc, "vary": "mismatch"}})
    supplies_txt = " / ".join(str(v) for v in SUPPLIES)
    manifest = {
        "bench": "sim/tb_threshold_mc",
        "seed": SEED, "n": N,
        "levels": [r["v"] for r in levels], "level_codes": [r["code"] for r in levels],
        "process_mm": MM, "process_mc": ["mc"],
        "temperature_c": TEMPS, "supply_v": SUPPLIES, "supply_source": SUPPLY_SRC,
        "sweep": {"span_v": SPAN, "step_v": -STEP},
        "crossing": {"node": "xdut.flag", "edge": "RISE=1", "fraction_of_supply": 0.5,
                     "thresholds_v": {str(v): float(Decimal(str(v)) / 2) for v in SUPPLIES}},
        "control": {"subckt": CONTROL_SUBCKT, "instance": CONTROL_INST, "delta_l_um": str(CONTROL_DL),
                    "old_l_um": old_l, "new_l_um": new_l, "source": TOP, "netlist": CONTROL_TOP},
        "netlist": TOP, "netlist_control": CONTROL_TOP,
        "netlist_sha256": sha256(top.encode()), "netlist_control_sha256": sha256(control_top.encode()),
        "request_count": len(members), "unit_count": sum(m["units"] for m in members.values()),
        "group_count": len(groups),
        "inputs_sha256": sha256(json.dumps(sorted((n, m["sha256"]) for n, m in members.items())).encode()),
        "record": {
            "corner_box": "process {%s}_mm (vary=mismatch) + mc (vary=both), temperature %s C, detector "
                          "supply %s V; %d groups (%d select codes x %d process sections x %d temperatures "
                          "x %d supplies), N = %d draws each"
                          % (",".join(p[:-3] for p in MM), " / ".join(str(t) for t in TEMPS), supplies_txt,
                             len(groups), len(levels), len(MM) + 1, len(TEMPS), len(SUPPLIES), N),
            "stimulus": "monitored rail = IDEAL SOURCE, DC sweep %s mV steps, nominal trip + %s mV down to "
                        "nominal - %s mV (static trip, spec row 5); trip = rail where %s internal comparator "
                        "output xdut.flag first rises through half the applied detector supply (%s V at %s V); "
                        "asserted select bits at the applied supply, deasserted at 0 V; value resolution "
                        "0.1 mV (klt measureprec)"
                        % (num(Decimal(str(STEP)) * 1000), num(Decimal(str(SPAN)) * 1000),
                           num(Decimal(str(SPAN)) * 1000), TOP,
                           " / ".join(num(Decimal(str(v)) / 2) for v in SUPPLIES), supplies_txt),
            "negative_control": "ladder segment %s in %s L=%s -> %s (deliberate offset %s um) in a generated "
                                "copy of %s; each *_mm group is graded against the control in its own section "
                                "and the mc group against tt_mm, at the same code, temperature and supply "
                                "(vary=mismatch, same seed and N)"
                                % (CONTROL_INST, CONTROL_SUBCKT, old_l, new_l, CONTROL_DL, TOP),
        },
        "members": members,
        "groups": groups,
    }

    work.mkdir(parents=True, exist_ok=True)
    for rel, text in files.items():
        (work / rel).write_bytes(text.encode())
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
