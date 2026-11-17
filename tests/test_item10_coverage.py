"""PDK-free: every tracked .sh / .py under sim/, verification/ and tests/ must be in attest/item10.json."""
import json, pathlib, subprocess, sys

root = pathlib.Path(__file__).resolve().parent.parent
tracked = [f for f in subprocess.check_output(
    ["git", "ls-files", "sim", "verification", "tests"], cwd=root, text=True).split()
    if f.endswith((".sh", ".py"))]
covered = {a for c in json.loads((root / "attest/item10.json").read_text())["checks"] for a in c["argv"]}
missing = sorted(set(tracked) - covered)
if missing:
    sys.exit("not covered by attest/item10.json: " + ", ".join(missing))
