# Shared PDK-pin gate for the sim/*/run.sh bench drivers. Source it; do not execute it.
# The driver must already have set `sim` (the sim/ directory). It is fail-closed:
# every failure prints "FAIL: ..." to stderr and exits 2 (pin / PDK problems).
# Env: PDK_ROOT (optional, passed to klt), KLT (default: klt),
#      PDK_PIN (pin file, default $sim/pdk.json; overridden for negative controls).

# pdk_pin_resolve: read the pin, resolve the PDK with klt, check the SOURCES first
# line against the pin and the model lib is readable. Sets (unexported, caller scope):
# pin variant want KLT found root src got lib.
pdk_pin_resolve() {
  pin="${PDK_PIN:-$sim/pdk.json}"
  variant="$(jq -er .variant "$pin")"
  want="$(jq -er .sources_line "$pin")"
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
}

# pdk_model_files <process-section> <outfile>: the model files the netlist pulls in:
# the lib itself plus the includes of the given section (tt, ss, ...). Needs $lib.
pdk_model_files() {
  local cdir; cdir="$(dirname "$lib")"
  { echo "$lib"; sed -n "/^\\.lib $1\$/,/^\\.endl $1\$/p" "$lib" | sed -n 's/^\.include *//p' | sed "s#^#$cdir/#"; } > "$2"
}

# pdk_record_header [<key> <path> <display>]...: print the provenance block of a record:
# the ngspice / klt / pdk_sources lines, one "<key>: <sha256 of path>  <display>" line per
# triple (netlists, checkers; in the given order), then model_files_sha256 with the hash of
# every model file listed in $work/files. Fail-closed: an unreadable model file or an
# unreadable triple path exits 2, so a record never carries an incomplete hash list.
# Needs $KLT, $got, $root and $work/files (pdk_pin_resolve + pdk_model_files).
pdk_record_header() {
  echo "ngspice: $(ngspice --version | grep -m1 -o 'ngspice-[0-9.]*')"
  echo "klt: $($KLT --version)"
  echo "pdk_sources: $got"
  while [ "$#" -ge 3 ]; do
    echo "$1: $(sha256sum "$2" | cut -d' ' -f1)  $3"
    shift 3
  done
  echo "model_files_sha256:"
  local f
  while read -r f; do [ -r "$f" ] || { echo "FAIL: unreadable model file $f" >&2; exit 2; }
    printf '  %s  %s\n' "$(sha256sum "$f" | cut -d' ' -f1)" "${f#"$root"/}"; done < "$work/files"
}
