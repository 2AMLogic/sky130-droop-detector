"""PDK-free guard: pdk_record_header's ngspice_threads: field stays coupled to ngspice_run.

Guards the cross-file coupling PR #113 added: pdk_record_header
(sim/lib/pdk_pin.sh) emits `ngspice_threads:` from SIM_NGSPICE_THREADS_USED,
which ngspice_run (sim/lib/ngspice_run.sh) sets as it starts a local run.
Nothing else in the repo asserts the field -- the coupling is invisible to
static analysis (shellcheck SC2034) and no other test reads a record header --
so a dropped or renamed assignment would make every later record for a bench
that *did* run local ngspice read `ngspice_threads: none (no local ngspice
run; see backend:)`: a false statement in an append-only evidence repo, with
nothing red.

Two cases, each driven in its own bash process: SIM_NGSPICE_THREADS_USED is an
ordinary shell variable that stays set once ngspice_run assigns it, so a
single shell would only pass both assertions in one fixed order -- separate
processes make the guard order-independent, which is the property a regression
guard needs.

  case 1: pdk_record_header with no ngspice_run call emits exactly one
          ngspice_threads: line, valued `none (no local ngspice run; see
          backend:)`.
  case 2: after ngspice_run over a trivial .control deck, exactly one line,
          valued with the sourced library's own SIM_NGSPICE_THREADS (captured
          from the sourcing shell, not hard-coded here, so a thread-policy
          change cannot turn this guard into a false statement).

ngspice and klt are stubbed on PATH (stubs first, so a host tool cannot
answer); the PDK is faked through $got/$root as pdk_pin_resolve would set
them; $work/files exists and is empty, so the model-file loop emits only its
header line. No PDK, no real ngspice, no klt needed.
"""

import os
import pathlib
import subprocess
import sys
import tempfile

root = pathlib.Path(__file__).resolve().parent.parent
NONE_VALUE = "none (no local ngspice run; see backend:)"
FIELD = "ngspice_threads:"

NGSPICE_STUB = """\
#!/bin/sh
# Test double for tests/test_record_header_threads.py.
# --version must satisfy pdk_record_header's `ngspice-[0-9.]*` grep;
# the batch form must exit 0 so ngspice_run does not trip ngspice_log_fail.
case "$1" in
  --version) echo "ngspice-47.1 (stub for tests/test_record_header_threads.py)" ;;
esac
exit 0
"""

KLT_STUB = """\
#!/bin/sh
# Test double: pdk_record_header only needs `$KLT --version` to succeed.
case "$1" in
  --version) echo "klt 0.8.0 (stub for tests/test_record_header_threads.py)" ;;
esac
exit 0
"""

# Mirror the bench drivers' source order (sim/*/run.sh: pdk_pin.sh first).
# $got/$root/$work are what pdk_pin_resolve + sim_workdir leave behind; calling
# pdk_record_header with no trailing arguments skips its [ -r "$2" ] triple loop.
DRIVER_PRE = """\
. {lib}/pdk_pin.sh
. {lib}/ngspice_run.sh
KLT={bin}/klt
got=stub-pdk-sources
root={fakeroot}
work={work}
"""

DRIVER_CASE1_BODY = ""

DRIVER_CASE2_BODY = """\
cat > "$work/deck.spice" <<'DECK'
* trivial deck: the stub ignores the content, but the .control block is
* required so sim_thread_cap can apply the repo thread policy in place.
.control
quit
DECK
ngspice_run "$work/deck.spice" "$work/run.log"
printf '%s\\n' "$SIM_NGSPICE_THREADS" > "$work/expected_threads.txt"
"""

DRIVER_END = "pdk_record_header\n"


def build_scratch(tmp):
    """Scratch dir: bin/ with the two stubs, a fake PDK root, a work dir with
    an empty files list (the model-file loop then emits only its header)."""
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    for name, body in (("ngspice", NGSPICE_STUB), ("klt", KLT_STUB)):
        stub = bin_dir / name
        stub.write_text(body, encoding="utf-8")
        stub.chmod(0o755)
    (tmp / "fakeroot").mkdir()
    work = tmp / "work"
    work.mkdir()
    (work / "files").write_text("", encoding="utf-8")
    return bin_dir, work


def run_case(tmp, case_body):
    """One fresh bash process: source both libs, run the case body, then call
    pdk_record_header."""
    bin_dir, work = build_scratch(tmp)
    script = (DRIVER_PRE + case_body + DRIVER_END).format(
        lib=root / "sim" / "lib", bin=bin_dir, fakeroot=tmp / "fakeroot", work=work)
    env = dict(os.environ, PATH=f"{bin_dir}:{os.environ.get('PATH', '')}")
    proc = subprocess.run(["bash", "-c", script], env=env,
                          capture_output=True, text=True, timeout=120, cwd=root)
    return proc, work


def check(label, proc, expected):
    problems = []
    if proc.returncode != 0:
        problems.append(f"{label}: bash exited {proc.returncode}\n"
                        f"stderr:\n{proc.stderr.rstrip()}")
    lines = [l for l in proc.stdout.splitlines() if l.startswith(FIELD)]
    if len(lines) != 1:
        problems.append(f"{label}: expected exactly one ^{FIELD} line in the "
                        f"record header, got {len(lines)}\nstdout:\n{proc.stdout.rstrip()}")
    else:
        value = lines[0][len(FIELD):].strip()
        if value != expected:
            problems.append(f"{label}: ngspice_threads value is {value!r}, "
                            f"expected {expected!r} -- the record header no longer "
                            f"states the thread policy ngspice_run applied.")
    return problems


errors = []

# Case 1: no local ngspice run -> the field must say so explicitly.
with tempfile.TemporaryDirectory(prefix="record-header-threads-case1-") as d:
    proc, _ = run_case(pathlib.Path(d), DRIVER_CASE1_BODY)
    errors += check("case 1 (no ngspice_run call)", proc, NONE_VALUE)

# Case 2: after ngspice_run -> the field must carry the library's thread count.
with tempfile.TemporaryDirectory(prefix="record-header-threads-case2-") as d:
    proc, work = run_case(pathlib.Path(d), DRIVER_CASE2_BODY)
    expected_file = work / "expected_threads.txt"
    if expected_file.is_file():
        expected = expected_file.read_text(encoding="utf-8").strip()
        errors += check("case 2 (after ngspice_run)", proc, expected)
    else:
        errors.append("case 2 (after ngspice_run): SIM_NGSPICE_THREADS was never "
                      "captured from the sourcing shell -- ngspice_run failed before "
                      f"the driver reached the capture line.\nstderr:\n{proc.stderr.rstrip()}")

if errors:
    sys.exit("ngspice_threads record-header coupling broken:\n" + "\n".join(errors))
print("ok: ngspice_threads: record-header field is still coupled to ngspice_run "
      "(case 1 none-marker, case 2 library thread count; separate processes)")
