#!/usr/bin/env python3
"""Turn every rule off in turn and see which tests notice.

Green on a first run proves nothing: a test that has never been red tests
nothing. Where a rule is written before its test, the test is run red first.
Where a rule already exists, this is the substitute. Every rule has one row,
in a file of its own under scripts/mutations/. Run it from the repository root:

    uv run python scripts/mutate.py [--json mutations.json] [--write evidence/tests/rule-mutations.md]

`--json` writes the run's figures for the checks to keep, as `quality-mutations`
on main; in a check, the readable table also goes to the run's summary page.

A kill is not enough on its own. A mutation can break a test for an incidental
reason — a documented example whose output happened to change — and leave a rule
looking guarded when nothing guards it. So this also checks that the test named
after the rule is one of the ones that went red, and fails when it is not.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
from typing import Any

from voice_bridge.check import Disagreement, all_rows, test_name_for

ROOT = pathlib.Path(__file__).resolve().parent.parent


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


def run_suite() -> tuple[int, list[str]]:
    """Run the tests and give back how many failed, and which ones."""
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=no", "--color=no", "-p", "no:cacheprovider"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    m = re.search(r"(\d+) (?:failed|error)", r.stdout)
    failed = re.findall(r"^FAILED (\S+)", r.stdout, re.MULTILINE)
    return int(m.group(1)) if m else 0, [f.split("::")[-1].split("[")[0] for f in failed]


def main() -> int:
    """Mutate every rule in turn, restore the tree, and report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, help="write the run's figures here, for the checks")
    parser.add_argument("--write", type=pathlib.Path, help="write the evidence table here")
    args = parser.parse_args()

    # Stopped from outside, the run still puts every file back: a SIGTERM
    # otherwise skips the `finally` below and leaves a rule switched off.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(1))
    try:
        rules = all_rows(ROOT)
    except Disagreement as refused:
        raise SystemExit(str(refused)) from None
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
            count, failed = run_suite()
            path.write_text(text)
            # A kill by some other test is not evidence about this rule.
            own = test_name_for(rule["name"])
            by_its_own = own in failed
            results.append((rule["name"], rule["file"], count, own, by_its_own))
            verdict = "KILLED  " if by_its_own else ("BY LUCK " if count else "SURVIVED")
            print(f"{verdict} {rule['name']}: {count}")  # noqa: T201
    finally:
        for name, text in originals.items():
            (ROOT / name).write_text(text)

    survived = [name for name, _, count, _, _ in results if count == 0]
    lucky = [name for name, _, count, _, own in results if count and not own]
    # Written before a failing run exits: a run where a rule survived is exactly
    # what the code-health page has to show, not the last run that passed.
    publish(args.json, results, survived, lucky)
    proven = len(results) - len(survived) - len(lucky)
    print(f"\n{proven}/{len(results)} rules turned off their own test")  # noqa: T201
    if survived:
        print("SURVIVED, so nothing protects them:", ", ".join(survived))  # noqa: T201
    if lucky:
        print("KILLED BY ANOTHER TEST, so the evidence is not about them:", ", ".join(lucky))  # noqa: T201
    if args.write:
        args.write.write_text(report(results, survived, lucky))
    return 1 if survived or lucky else 0


Result = tuple[str, str, int, str, bool]


def publish(to: pathlib.Path | None, results: list[Result], survived: list[str], lucky: list[str]) -> None:
    """Give the run to the checks: its figures to `to`, its table to the run's summary page."""
    if to:
        to.write_text(json.dumps(figures(results), indent=2) + "\n")
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with pathlib.Path(summary).open("a") as page:
            page.write(report(results, survived, lucky))


def figures(results: list[Result]) -> dict[str, Any]:
    """The run as numbers: per rule, its name, file, tests gone red and whether its own was one.

    The same shape in every voice repository, for the bridge's code-health page to read.
    """
    rules = [
        {"name": name, "file": file, "tests_red": count, "own_test_red": own_red}
        for name, file, count, _, own_red in results
    ]
    return {"killed": sum(rule["own_test_red"] for rule in rules), "total": len(rules), "rules": rules}


def report(results: list[Result], survived: list[str], lucky: list[str]) -> str:
    """Render the run as the evidence page."""
    rows = "\n".join(
        f"| {name} | {count} | `{own}` | {'yes' if by_own else 'NO'} |"
        for name, _, count, own, by_own in results
    )
    proven = len(results) - len(survived) - len(lucky)
    verdict = (
        f"**Result: {proven} of {len(results)} rules turned off the test that names them.**"
        + (" None survived." if not survived else f" Survived: {', '.join(survived)}.")
        + ("" if not lucky else f" Killed only by other tests: {', '.join(lucky)}.")
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

| Rule turned off | Tests that went red | The test that names it | Did that one go red? |
|---|---|---|---|
{rows}

## What this does not prove

That the rules are the right rules, or that a rule catches every case of what
it names. It proves each rule is load-bearing: switch it off and the test that
names it says so. The last column is why that is worth more than a count. A
mutation can break a test for an incidental reason and leave a rule looking
guarded when nothing guards it, so a `NO` in that column fails this script even
though something went red. A new rule follows the order in `CONTRIBUTING.md` instead, a failing
test first, and gets a row of its own under `scripts/mutations/`, which both a
test in the suite and `voicebridge check` require.
"""


if __name__ == "__main__":
    sys.exit(main())
