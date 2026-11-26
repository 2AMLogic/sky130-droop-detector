"""Estimate code-00 trip variance by central DC differences on the pinned SKY130 models.

Usage: python3 sensitivity.py TOP.spice SKY130_LIB.spice OUT.csv [fraction_of_sigma]
One local ngspice process. This computes deterministic derivatives, not a sample SD.
"""

import csv
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

if len(sys.argv) not in (4, 5):
    sys.exit(__doc__)
top, lib, output = (Path(s).resolve() for s in sys.argv[1:4])
fraction = float(sys.argv[4]) if len(sys.argv) > 4 else 0.05
if not math.isfinite(fraction) or fraction <= 0:
    sys.exit("fraction_of_sigma must be positive and finite")
text = re.sub(r"\n\+\s*", " ", top.read_text()).lower()
global_model = (lib.parent / "continuous/models_global.spice").read_text()


def coefficient(name):
    return float(re.search(rf"(?m)^\+ {name} = ([\d.eE+-]+)", global_model)[1])


def subckt(name):
    block = re.search(rf"(?m)^\.subckt {name} (.*)\n([\s\S]*?)^\.ends", text)
    return block[1].split(), block[2].splitlines()


def instances(lines):
    return [line.split() for line in lines if line.startswith("x")]


sources, probes = [], []
pins, lines = subckt("detector_top")
top_nodes = dict(
    zip(pins, ["rail", "0", "0", "0", "vdd33", "0", "live", "sticky"], strict=True)
)
for instance, *nets, block in instances(lines):
    pins, lines = subckt(block)
    prefix = f"xdut.{instance}."
    ports = {p: top_nodes.get(n, f"xdut.{n}") for p, n in zip(pins, nets, strict=True)}
    for name, *args in instances(lines):
        if name.startswith("xc"):  # purely capacitive at DC
            continue
        model = next(arg for arg in args if arg.startswith("sky130_fd_pr__"))
        geom = dict(arg.split("=") for arg in args if "=" in arg)
        length, mult = float(geom["l"]), float(geom["mult"])
        path = prefix + name
        if name.startswith("xm"):
            area = float(geom["w"]) * length * mult
            sigma = coefficient("sw_mm_vth0_" + model) / math.sqrt(area)
            param = f"@m.{path}.m{model}[delvto]"
            probes.append((block, name, "delvto", param, param, str(sigma)))
        elif name.startswith("xr") and "__res_xhigh_po_" in model:
            width = float(model.rsplit("_", 1)[1].replace("p", "."))
            r0, r1 = (ports.get(n, prefix + n) for n in args[:2])
            inner = path + ".x0."
            t1, t2 = inner + "t1", inner + "t2"
            head = coefficient("sw_mm_sky130_fd_pr__res_generic_po_head") / math.sqrt(
                width * mult
            )
            body = coefficient("sw_mm_sky130_fd_pr__res_xhigh_po") / math.sqrt(
                width * length * mult
            )
            # dI for a fractional increase of R at fixed terminal voltages is -I*dR/R.
            # DC current is common to all three series elements. The pinned model
            # draws independently for the two heads (rend1, rend2) and the body.
            current = f"@r.{inner}rend1[i]"
            for part, a, b, scale in (
                ("head1", r0, t1, head),
                ("body", t1, t2, body),
                ("head2", t2, r1, head),
            ):
                source = f"i{len(sources)}"
                sources.append(f"{source} {a} {b} 0")
                probes.append((block, name, part, source, "0", f"(-{scale})*{current}"))
        else:
            raise ValueError(f"unsupported DC device {block}/{name}: {model}")

control = [
    "set num_threads=1",
    "set numdgt=12",
    "set measureprec=12",
    "set noaskquit",
    "dc Vrail 1.978 1.478 -0.0005",
    "meas dc centre when v(xdut.flag)=1.65 rise=1",
    "let hi=centre+0.002",
    "let lo=centre-0.002",
    "set hi=$&hi",
    "set lo=$&lo",
    "dc Vrail $hi $lo -0.00001",
    "meas dc trip when v(xdut.flag)=1.65 rise=1",
    "echo nominal $&trip",
    "alter Vrail=$&trip",
    "op",
    "print v(xdut.vref) v(xdut.xref.t0) v(xdut.xref.t1) v(xdut.xref.t2) v(xdut.xref.t3) @r.xdut.xref.xr2.x0.rend1[i]",
]
for i, (_, _, _, _, base, sigma) in enumerate(probes):
    control += [
        f"let pre{i}={base}",
        f"let step{i}=({sigma})*{fraction}",
        f"let hi{i}=pre{i}+step{i}",
        f"let lo{i}=pre{i}-step{i}",
        f"set plus{i}=$&hi{i}",
        f"set minus{i}=$&lo{i}",
        f"set orig{i}=$&pre{i}",
    ]

for i, (_, _, _, param, _, _) in enumerate(probes):
    for sign in ("minus", "plus"):
        control += [
            f"alter {param}=${sign}{i}",
            "dc Vrail $hi $lo -0.00001",
            f"meas dc probe_{i}_{sign} when v(xdut.flag)=1.65 rise=1",
        ]
    control += [f"alter {param}=$orig{i}"]

with tempfile.TemporaryDirectory() as tmp:
    deck = Path(tmp) / "test.cir"
    deck.write_text(
        "\n".join(
            [
                "* Static mismatch sensitivity of v(xdut.flag)=1.65 crossing",
                f'.lib "{lib}" tt',
                f'.include "{top}"',
                ".temp 27",
                ".options reltol=1e-7 abstol=1e-14",
                "Vdd vdd33 0 3.3",
                "Vrail rail 0 1.9",
                "Xdut rail 0 0 0 vdd33 0 live sticky detector_top",
                "Cl live 0 5f",
                *sources,
                ".control",
                *control,
                "quit",
                ".endc",
                ".end",
                "",
            ]
        )
    )
    run = subprocess.run(
        ["ngspice", "-b", str(deck)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=tmp,
    )
    log = output.with_suffix(".log")
    log.write_text(run.stdout)
    if run.returncode or re.search(
        r"(?im)^\s*(error|fatal|warning:.*failed)\b", run.stdout
    ):
        sys.exit(f"ngspice failed, see {log}")
    values = dict(
        re.findall(r"(?m)^(probe_\d+_(?:minus|plus))\s*=\s*(\S+)$", run.stdout)
    )

if len(values) != 2 * len(probes):
    sys.exit(f"incomplete trip crossings, see {log}")
with output.open("w", newline="") as f:
    rows = csv.writer(f, lineterminator="\n")
    rows.writerow(
        ("block", "device", "parameter", "minus_V", "plus_V", "signed_1sigma_mV")
    )
    for i, (block, name, part, *_) in enumerate(probes):
        minus = float(values[f"probe_{i}_minus"])
        plus = float(values[f"probe_{i}_plus"])
        if not all(math.isfinite(value) for value in (minus, plus)):
            sys.exit(f"nonfinite crossing at {block}/{name}/{part}")
        signed_sigma = (plus - minus) * 1000 / (2 * fraction)
        rows.writerow((block, name, part, minus, plus, f"{signed_sigma:.6f}"))
