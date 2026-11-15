# Shared four-level threshold table reader for the sim/*/run.sh bench drivers. Source it;
# do not execute it. Reads sim/lib/levels.json -- the ratified spec/target-spec.md row 4
# trip points (4 / 6 / 9 / 12 % below the 1.8 V nominal) -- with jq -er and hands the
# driver the shapes it already uses, so the table exists once. Fail-closed: every failure
# prints "FAIL: ..." to stderr and exits 2 (data problems, the pdk_pin.sh tier), so a
# driver never runs on a partial or malformed table. Needs $sim (the sim/ directory).

# levels_load: parse the table. Sets (unexported, caller scope):
#   lv_rows  one "l<code> <v> <s0> <s1>" line per level, select order 0..3 (the bash
#            LEVELS=() record shape: name nominal-trip select-s0 select-s1)
#   lv_v     the four nominal trip points, select order (lv_v[0]..lv_v[3])
levels_load() {
  local f="$sim/lib/levels.json" r x v r_s0 r_s1 _
  [ -r "$f" ] || { echo "FAIL: level table unreadable: $f" >&2; exit 2; }
  lv_rows=()
  while read -r r; do lv_rows+=("$r"); done < <(
    jq -er '.levels[] | "l\(.code) \(.v) \(.s0) \(.s1)"' "$f")
  [ "${#lv_rows[@]}" -eq 4 ] || { echo "FAIL: level table malformed (need 4 levels): $f" >&2; exit 2; }
  lv_v=()
  for r in "${lv_rows[@]}"; do
    read -r _ v r_s0 r_s1 <<<"$r"
    for x in "$v" "$r_s0" "$r_s1"; do
      case $x in ''|*[!0-9.]*) echo "FAIL: level table malformed (bad number '$x' in '$r'): $f" >&2; exit 2;; esac
    done
    lv_v+=("$v")
  done
}
