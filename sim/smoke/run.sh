#!/usr/bin/env bash
# Smoke run: verify the PDK revision pin, run one ngspice bench, write a record.
# Fails closed: any missing/unreadable SOURCES or sha mismatch exits non-zero.
# Env: PDK_ROOT (optional, passed to klt), KLT (default: klt), RECORD (output path).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
sim="$here/.."
variant="$(jq -er .variant "$sim/pdk.json")"
want="$(jq -er .sources_line "$sim/pdk.json")"
KLT="${KLT:-klt}"

found="$($KLT pdk find --pdk "$variant" ${PDK_ROOT:+--pdk-root "$PDK_ROOT"} 2>&1)" || {
  echo "FAIL: klt pdk find could not resolve $variant (PDK_ROOT=${PDK_ROOT:-unset}); pin is: $want" >&2
  echo "$found" >&2; exit 2; }
root="$(sed -n 's/^root: //p' <<<"$found")"
src="$root/$variant/SOURCES"
[ -n "$root" ] && [ -s "$src" ] || { echo "FAIL: SOURCES missing or empty at '$src'; pin is: $want" >&2; exit 2; }
got="$(head -n1 "$src")"
[ "$got" = "$want" ] || { echo "FAIL: PDK revision mismatch; pin is '$want', found '$got' in $src" >&2; exit 2; }

lib="$root/$variant/libs.tech/combined/sky130.lib.spice"
[ -r "$lib" ] || { echo "FAIL: model lib unreadable: $lib" >&2; exit 2; }
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
sed "s#__PDK_LIB__#$lib#" "$here/smoke.spice" > "$work/smoke.spice"
ngspice -b -o "$work/ngspice.log" "$work/smoke.spice" >/dev/null 2>&1 || {
  echo "FAIL: ngspice exited non-zero; log:" >&2; cat "$work/ngspice.log" >&2; exit 3; }

for k in "RESULT id_nfet_ua" tphl tplh; do
  grep -Eq "^$k *= *[0-9.eE+-]+" "$work/ngspice.log" || { echo "FAIL: no '$k' result in ngspice log" >&2; cat "$work/ngspice.log" >&2; exit 3; }
done

# Model files the netlist pulls in: the lib itself plus the tt-section includes.
cdir="$(dirname "$lib")"
{ echo "$lib"; sed -n '/^\.lib tt$/,/^\.endl tt$/p' "$lib" | sed -n 's/^\.include *//p' | sed "s#^#$cdir/#"; } > "$work/files"
rec="${RECORD:-/dev/stdout}"
{
  echo "label: SIMULATED (not measured); testbench sim/smoke/smoke.spice; corner tt, 27 C, 1.8 V"
  echo "ngspice: $(ngspice --version | grep -m1 -o 'ngspice-[0-9.]*')"
  echo "klt: $($KLT --version)"
  echo "pdk_sources: $got"
  echo "model_files_sha256:"
  while read -r f; do [ -r "$f" ] || { echo "FAIL: unreadable model file $f" >&2; exit 2; }
    printf '  %s  %s\n' "$(sha256sum "$f" | cut -d' ' -f1)" "${f#"$root"/}"; done < "$work/files"
  echo "results:"
  grep -E '^RESULT |^tphl|^tplh' "$work/ngspice.log" | sed 's/^/  /'
} > "$work/record"
cat "$work/record" > "$rec"
