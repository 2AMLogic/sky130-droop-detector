"""PDK-free: every tracked .sh / .py under sim/, verification/ and tests/ must be in attest/item10.json."""
import json, os, pathlib, subprocess, sys

root = pathlib.Path(__file__).resolve().parent.parent
out = subprocess.check_output(
    ["git", "ls-files", "-z", "--", "sim", "verification", "tests"], cwd=root)
tracked = [p for p in map(os.fsdecode, out.split(b"\0")) if p.endswith((".sh", ".py"))]
covered = {a for c in json.loads((root / "attest/item10.json").read_text())["checks"] for a in c["argv"]}
missing = sorted(set(tracked) - covered)
if missing:
    sys.exit("not covered by attest/item10.json: " + ", ".join(missing))
