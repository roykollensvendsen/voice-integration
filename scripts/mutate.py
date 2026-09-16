#!/usr/bin/env python3
"""Turn every rule off in turn and see which tests notice.

Green on a first run proves nothing: a test that has never been red tests
nothing. Where a rule is written before its test, the test is run red first.
Where a rule already exists, this is the substitute. Every rule lives in
scripts/mutations.toml, one row each. Run it from the repository root:

    python scripts/mutate.py [--write evidence/tests/rule-mutations.md]
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
import subprocess
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TABLE = ROOT / "scripts/mutations.toml"


def line_of(text: str, pattern: str, occurrence: int) -> int:
    """Find the one line a rule lives on, by pattern rather than by number."""
    seen = 0
    for i, line in enumerate(text.splitlines()):
        if re.search(pattern, line):
            seen += 1
            if seen == occurrence:
                return i
    msg = f"no line {occurrence} matching {pattern!r}"
    raise SystemExit(msg)


def run_suite() -> tuple[int, str]:
    """Run the tests and give back how many failed, and the first that did."""
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=no", "-p", "no:cacheprovider"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    m = re.search(r"(\d+) (?:failed|error)", r.stdout)
    failed = re.findall(r"^FAILED (\S+)", r.stdout, re.MULTILINE)
    return int(m.group(1)) if m else 0, (failed[0].split("::")[-1] if failed else "-")


def main() -> int:
    """Mutate every rule in turn, restore the tree, and report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=pathlib.Path, help="write the evidence table here")
    args = parser.parse_args()

    rules = tomllib.loads(TABLE.read_text())["rule"]
    originals = {r["file"]: (ROOT / r["file"]).read_text() for r in rules}
    results = []
    try:
        for rule in rules:
            path = ROOT / rule["file"]
            text = originals[rule["file"]]
            lines = text.splitlines()
            i = line_of(text, rule["find"], rule.get("occurrence", 1))
            # Keep the line's own indentation: a replacement that carries its own
            # would have to be kept in step with the source, and silently would not be.
            indent = lines[i][: len(lines[i]) - len(lines[i].lstrip())]
            lines[i] = indent + rule["replace"].strip()
            path.write_text("\n".join(lines) + "\n")
            count, first = run_suite()
            path.write_text(text)
            results.append((rule["name"], count, first))
            print(f"{'KILLED  ' if count else 'SURVIVED'} {rule['name']}: {count}")  # noqa: T201
    finally:
        for name, text in originals.items():
            (ROOT / name).write_text(text)

    survived = [name for name, count, _ in results if count == 0]
    print(f"\n{len(results) - len(survived)}/{len(results)} rules killed a test")  # noqa: T201
    if survived:
        print("SURVIVED, so nothing protects them:", ", ".join(survived))  # noqa: T201
    if args.write:
        args.write.write_text(report(results, survived))
    return 1 if survived else 0


def report(results: list[tuple[str, int, str]], survived: list[str]) -> str:
    """Render the run as the evidence page."""
    rows = "\n".join(f"| {name} | {count} | `{first}` |" for name, count, first in results)
    verdict = (
        f"**Result: {len(results) - len(survived)} of {len(results)} rules killed at least one test.**"
        + (" None survived." if not survived else f" Survived: {', '.join(survived)}.")
    )
    return f"""# Every rule, turned off in turn

*Run {dt.datetime.now(dt.UTC).date()} by `python scripts/mutate.py --write
evidence/tests/rule-mutations.md`, which is how to repeat it. The script
restores every file it touched before it exits.*

Green on a first run proves nothing: a test that has never been red tests
nothing. Where a rule is written before its test, the test is run red first.
Where a rule already exists, this is the substitute. Each rule is disabled in
turn, by replacing its one line with something that can never hold, and the
suite is run. A rule whose removal breaks no test is a rule nothing protects.

{verdict}

| Rule turned off | Tests that went red | First of them |
|---|---|---|
{rows}

## What this does not prove

That the rules are the right rules, or that a rule catches every case of what
it names. It proves each rule is load-bearing: switch it off and a named test
says so. A new rule follows the order in `CONTRIBUTING.md` instead, a failing
test first, and is added to `scripts/mutations.toml`, which both a test in the
suite and `voicebridge check` require.
"""


if __name__ == "__main__":
    sys.exit(main())
