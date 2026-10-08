#!/usr/bin/env python3
"""Follow the README's start on an empty machine, and check that the page then talks.

The block the README marks for "the clean-install job" is run as written in a
fresh Ubuntu container, except that the bridge is installed from this checkout
rather than from GitHub, so a pull request tests its own code. A stranger at
that point has everything installed and no OpenAI key yet, so
`voicebridge ready --json` must fail on the key alone and say where to put one.
With a stand-in key in that place, it must be ready, and `voicebridge serve`
must answer with the page. Needs Docker. Usage: python3 scripts/clean_install.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGE = "ubuntu:24.04"
SOURCE = "git+https://github.com/roykollensvendsen/voice-integration"
# What any desktop already has; the README assumes these and nothing more.
BASE = "apt-get update -qq && apt-get install -y -qq curl ca-certificates git >/dev/null"
# After the README's steps: the report a stranger gets, then the same with a key
# in place, then the page. The key is a stand-in, so nothing is asked of OpenAI.
AFTER = """
voicebridge ready --json --offline > /tmp/first.json
printf 'OPENAI_API_KEY=stand-in\\n' > ~/.config/voice-bridge/env 2>/dev/null \\
  || { mkdir -p ~/.config/voice-bridge && printf 'OPENAI_API_KEY=stand-in\\n' > ~/.config/voice-bridge/env; }
voicebridge ready --offline > /tmp/second.txt
voicebridge serve > /tmp/serve.log 2>&1 &
for _ in $(seq 1 30); do curl -sf http://127.0.0.1:8760/ -o /tmp/page.html && break; sleep 1; done
"""


def steps() -> str:
    """The README's marked block, installing from this checkout instead of GitHub."""
    readme = (ROOT / "README.md").read_text()
    marked = r"<!-- not run:[^>]*the clean-install job runs it[^>]*-->\n```bash\n(.*?)```"
    found = re.findall(marked, readme, re.DOTALL)
    if len(found) != 1:
        sys.exit("clean_install: expected exactly one marked block in README.md")
    # The last line is `voicebridge ready`, which fails without a key: that is the point.
    return found[0].replace(SOURCE, "/src").replace("\nvoicebridge ready\n", "\nvoicebridge ready || true\n")


def main() -> int:
    """Run the start in a container and say where it went wrong, if it did."""
    lines = [
        BASE,
        "useradd -m stranger",
        "cp -r /src-ro /src && chown -R stranger /src",
        "su - stranger -c 'bash -s' <<'STEPS'",
        "set -x",
        steps(),
        AFTER,
        "STEPS",
        "echo '=== first'; cat /tmp/first.json",
        "echo '=== second'; cat /tmp/second.txt",
        "echo '=== page'; grep -c 'Take the microphone' /tmp/page.html || echo 0",
    ]
    script = "\n".join(lines)
    run = subprocess.run(  # noqa: S603 — fixed arguments and this checkout's own README
        ["docker", "run", "--rm", "-i", "-v", f"{ROOT}:/src-ro:ro", IMAGE, "bash", "-c", script],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stderr.write(run.stderr[-4000:])
    out = run.stdout
    try:
        first = json.loads(out[out.index("=== first") + 9 : out.index("=== second")])
    except ValueError:
        sys.stderr.write(out[-2000:])
        sys.exit("clean_install: the steps did not get as far as `voicebridge ready --json`")
    failing = [c for c in first["checks"] if c["required"] and not c["ok"]]
    names = [c["name"] for c in failing]
    if names != ["openai_key"] or "~/.config/voice-bridge/env" not in failing[0]["fix"]:
        sys.exit(
            f"clean_install: without a key, only the key should be missing, and where to put it: {failing}"
        )
    second = out[out.index("=== second") : out.index("=== page")]
    if "ready to talk" not in second:
        sys.exit(f"clean_install: with a key in place, `ready` should say so:\n{second}")
    if out[out.index("=== page") :].split()[-1] == "0":
        sys.exit("clean_install: `voicebridge serve` did not answer with the page")
    print("clean_install: the README's start works on an empty machine, up to the key and the page")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
