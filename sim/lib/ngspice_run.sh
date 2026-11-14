# Shared ngspice run / result-check helpers for the sim/*/run.sh bench drivers. Source it;
# do not execute it. Fail-closed: every failure prints "FAIL: ..." to stderr plus the last
# 40 lines of the offending log, and exits 3 (bench problems; 2 is reserved for pin / PDK
# problems, see pdk_pin.sh).
# Optional: set NGSPICE_CTX (e.g. "at tap 0.9") to append context to the FAIL messages.
#
# Host-concurrency policy for local ngspice lives here and nowhere else: ngspice_run forces
# SIM_NGSPICE_THREADS into every deck it runs, so all twelve local benches get the same cap
# without each one restating it. Change the one line below when the host policy changes.
#
# Which knob actually works (measured, not assumed — ngspice-47p1, this worker class,
# sampling /proc/<pid>/status Threads across a detector_top transient; see PR for #85):
#   * in-deck `.control` `set num_threads=N`  -> EFFECTIVE, and wins over everything else,
#     because the deck's .control block is sourced last, after every init file.
#   * `OMP_NUM_THREADS=N` in the environment   -> NO EFFECT AT ALL. ngspice calls
#     omp_set_num_threads() from the `num_threads` variable at circuit setup, which
#     overrides the OpenMP environment ICV. Measured: env 8 + no deck setting -> 1 thread;
#     deck 8 + env 1 -> 8 threads. Do not add an OMP_NUM_THREADS export to a bench; it is
#     a knob that reads as policy and does nothing.
#   * `ngspice -D num_threads=N` on the command line -> NO EFFECT; the init files that load
#     afterwards overwrite it, and -n does not suppress ngspice's own scripts/spinit.
#   * `scripts/spinit` (shipped with the ngspice build) sets num_threads=8 here, and an
#     unversioned host `~/.spiceinit` (or a ./.spiceinit in the cwd) overrides that. So a
#     deck that sets nothing does NOT run single-threaded — it runs at whatever this host's
#     init files happen to say, which is not versioned with the evidence it produces.
#     Forcing the value in-deck is what makes a sim/ record reproducible off this host.

# SIM_NGSPICE_THREADS: OpenMP threads per local ngspice process, for every bench. One.
# Justification: this worker class shares 8 cores with up to a dozen concurrent sweeps, so
# the host rule is to keep core use modest; and single-threaded is the only setting under
# which the BSIM4 device load is order-deterministic, which is what lets an appended sim/
# record be reproduced rather than merely re-run. Benches that want more cores belong on
# the batch fleet via `klt sim` (sim/tb_rail_model_check, sim/tb_threshold_mc), not here.
SIM_NGSPICE_THREADS=1

# sim_workdir: create the scratch dir $work (removed on exit) in the caller's scope.
sim_workdir() { work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT; }

# ngspice_log_fail <message> <log>: print FAIL: <message> and the log tail, exit 3.
ngspice_log_fail() { echo "FAIL: $1" >&2; tail -40 "$2" >&2; exit 3; }

# sim_thread_cap <deck>: rewrite <deck> in place so its .control block sets the repo thread
# policy and nothing else does. Drops any `set num_threads=` the deck already carries, then
# inserts SIM_NGSPICE_THREADS as the first line of the first .control block. Idempotent.
# Fail-closed: a deck with no .control block cannot carry the policy at all, so exit 3
# rather than let it inherit the host's init files.
sim_thread_cap() {
  grep -q '^\.control' "$1" \
    || { echo "FAIL: deck has no .control block, so the repo ngspice thread cap cannot be applied${NGSPICE_CTX:+ $NGSPICE_CTX}: $1" >&2; exit 3; }
  awk -v n="$SIM_NGSPICE_THREADS" '
    /^[[:space:]]*set[[:space:]]+num_threads[[:space:]]*=/ { next }
    { print }
    !done && /^\.control/ { print "set num_threads=" n; done = 1 }
  ' "$1" > "$1.capped" && mv "$1.capped" "$1"
}

# ngspice_run <deck> <log>: one batch ngspice run; sets RESULT_LOG=<log> for get.
# The deck is thread-capped first, so the policy above applies whether or not the bench's
# own template mentions threads. Decks are generated into the caller's $work, so the
# in-place rewrite only ever touches scratch.
ngspice_run() {
  RESULT_LOG="$2"
  sim_thread_cap "$1"
  ngspice -b -o "$2" "$1" >/dev/null 2>&1 \
    || ngspice_log_fail "ngspice exited non-zero${NGSPICE_CTX:+ $NGSPICE_CTX}; log:" "$2"
}

# require_results <log> <key>...: every key needs a numeric "RESULT <key> = <number>" line.
require_results() {
  local log="$1" k; shift
  for k in "$@"; do
    grep -Eq "^RESULT $k = [0-9.eE+-]+" "$log" \
      || ngspice_log_fail "no '$k' result${NGSPICE_CTX:+ $NGSPICE_CTX} in ngspice log" "$log"
  done
}

# result_of <log> <key>: the value text of the first "RESULT <key> = ..." line (empty if none).
result_of() { sed -n "s/^RESULT $2 = //p" "$1" | head -n1; }

# get <key>: result_of on the log of the last ngspice_run.
get() { result_of "$RESULT_LOG" "$1"; }
