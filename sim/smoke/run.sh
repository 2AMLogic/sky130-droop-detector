#!/usr/bin/env bash
# Smoke run: verify the PDK revision pin, run one ngspice bench, write a record.
# Fails closed: any missing/unreadable SOURCES or sha mismatch exits non-zero.
# Env: PDK_ROOT (optional, passed to klt), KLT (default: klt), RECORD (output path).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
sim="$here/.."
. "$sim/lib/pdk_pin.sh"
pdk_pin_resolve
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
sed "s#__PDK_LIB__#$lib#" "$here/smoke.spice" > "$work/smoke.spice"
ngspice -b -o "$work/ngspice.log" "$work/smoke.spice" >/dev/null 2>&1 || {
  echo "FAIL: ngspice exited non-zero; log:" >&2; cat "$work/ngspice.log" >&2; exit 3; }

for k in "RESULT id_nfet_ua" tphl tplh; do
  grep -Eq "^$k *= *[0-9.eE+-]+" "$work/ngspice.log" || { echo "FAIL: no '$k' result in ngspice log" >&2; cat "$work/ngspice.log" >&2; exit 3; }
done

# Model files the netlist pulls in: the lib itself plus the tt-section includes.
pdk_model_files tt "$work/files"
rec="${RECORD:-/dev/stdout}"
{
  echo "label: SIMULATED (not measured); testbench sim/smoke/smoke.spice; corner tt, 27 C, 1.8 V"
  pdk_record_header
  echo "results:"
  grep -E '^RESULT |^tphl|^tplh' "$work/ngspice.log" | sed 's/^/  /'
} > "$work/record"
cat "$work/record" > "$rec"
