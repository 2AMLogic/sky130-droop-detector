#!/usr/bin/env bash
# Prepare four fleet requests for the dated sizing comparison.
set -euo pipefail
if (( $# != 1 )); then echo "usage: $0 NEW_OUTPUT_DIRECTORY" >&2; exit 2; fi
here=$(cd "$(dirname "$0")" && pwd)
root=$(git -C "$here" rev-parse --show-toplevel)
mkdir -- "$1"
out=$(cd "$1" && pwd)
snapshot=$(mktemp -d)
trap 'rm -rf "$snapshot"' EXIT
base=01db265c5e98353700f710f94d0a96373d569086
git -C "$root" archive "$base" design sim/lib/levels.json sim/tb_threshold_mc/{gen_requests.py,tb_threshold_mc.spice} |
    tar -x -C "$snapshot"

for variant in baseline wide; do
    if [[ "$variant" == wide ]]; then
        patch -d "$snapshot" -p1 --fuzz=0 --batch < "$here/input-pair.patch"
    fi
    generated="$snapshot/requests-$variant"
    python3 -I "$snapshot/sim/tb_threshold_mc/gen_requests.py" "$generated" > /dev/null
    dest="$out/$variant"
    mkdir "$dest"
    cp "$generated"/{detector_top,detector_top_ctl,tb_l0_mm,tb_l0_ctl}.spice "$dest"
    python3 - "$generated" "$dest" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

source, dest = map(Path, sys.argv[1:])
expected = {
    "baseline": "c6307eb13bb46c8c3d150dbf57605ec9716e35da9f6c8b69191695a79740ee93",
    "wide": "e033d5e328828c3dd36831f21ddd251ecb49392d649f43e9c887ec1a2d07a3bd",
}
nominal = (dest / "detector_top.spice").read_bytes()
control = (dest / "detector_top_ctl.spice").read_bytes()
xr2 = b"XR2 t0 vref gnd sky130_fd_pr__res_xhigh_po_1p41 L=94.073 "
if hashlib.sha256(nominal).hexdigest() != expected[dest.name]:
    sys.exit(f"{dest.name}: unexpected nominal netlist")
if nominal.count(xr2) != 1 or control != nominal.replace(xr2, xr2.replace(b"94.073", b"88")):
    sys.exit(f"{dest.name}: unexpected XR2 control difference")
for tag in ("mm", "ctl"):
    name = f"l0_{tag}.request.json"
    request = json.loads((source / name).read_text())
    request["corners"]["process"] = ["tt_mm"]
    (dest / name).write_text(json.dumps(request, indent=1) + "\n")
PY
done
