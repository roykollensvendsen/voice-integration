"""The project's own check: the documents and the code have to say the same thing.

Three facts are written down twice here, because a reader needs them in prose
and the program needs them in code. Each pair is compared, so the copy cannot
quietly go stale:

* the voice tools, in `docs/voice-contract.md` and in `voice_bridge.contract`
* the gateway endpoints, in `docs/hermes-contract.md` and in `voice_bridge.gateway`
* the rules, marked `# RULE:` in the source and rowed in `scripts/mutations.toml`

The third is the one that keeps the mutation evidence honest. A rule added
without a row is a rule no mutation ever switches off, and the table becomes a
historical document without anyone noticing.
"""

from __future__ import annotations

import pathlib  # noqa: TC003 — a runtime default reads it, not only the annotations
import re
import tomllib

from voice_bridge.contract import BY_NAME

ANCHOR = "<!-- normative: {} -->"
_ROW = re.compile(r"^\|\s*`([^`]+)`")
_PATH_ROW = re.compile(r"^\|[^|]*\|\s*`([^`]+)`")
# Anchored, so that a page or a docstring mentioning the marker is not a rule.
_RULE = re.compile(r"^[ \t]*#\s*RULE:\s*(.+?)\s*$")


class Disagreement(Exception):
    """A document and the code no longer say the same thing."""


def table_after(page: pathlib.Path, anchor: str, pattern: re.Pattern[str]) -> set[str]:
    """Every backticked name in the one table that follows an anchor."""
    text = page.read_text()
    marker = ANCHOR.format(anchor)
    if marker not in text:
        message = f"{page.name} has lost its `{anchor}` anchor"
        raise Disagreement(message)
    names = set()
    for line in text.split(marker, 1)[1].splitlines():
        if line.startswith("|"):
            found = pattern.match(line)
            if found:
                names.add(found.group(1))
        elif names and line.strip() == "":
            break
    return names


def marked_rules(root: pathlib.Path) -> set[str]:
    """Every rule the source marks, by the words the marker gives it."""
    found = set()
    for module in sorted((root / "src").rglob("*.py")):
        for line in module.read_text().splitlines():
            match = _RULE.search(line)
            if match:
                found.add(match.group(1))
    return found


def rowed_rules(root: pathlib.Path) -> set[str]:
    """Every rule the mutation table claims to switch off."""
    table = tomllib.loads((root / "scripts/mutations.toml").read_text())
    return {str(rule["name"]) for rule in table.get("rule", [])}


def report(root: pathlib.Path) -> list[str]:
    """Compare every pair, and return the lines to print. Raise on disagreement."""
    lines = []
    lines.append(
        _compare(
            "voice tools",
            table_after(root / "docs/voice-contract.md", "voice tools", _ROW),
            "docs/voice-contract.md",
            set(BY_NAME),
            "the code",
        )
    )
    lines.append(
        _compare(
            "gateway paths",
            table_after(root / "docs/hermes-contract.md", "gateway paths", _PATH_ROW),
            "docs/hermes-contract.md",
            {tool.path for tool in BY_NAME.values()},
            "the code",
        )
    )
    lines.append(
        _compare(
            "rules",
            marked_rules(root),
            "the source",
            rowed_rules(root),
            "scripts/mutations.toml",
        )
    )
    return lines


def _compare(subject: str, left: set[str], left_name: str, right: set[str], right_name: str) -> str:
    if left != right:
        only_left = sorted(left - right)
        only_right = sorted(right - left)
        parts = []
        if only_left:
            parts.append(f"only in {left_name}: {', '.join(only_left)}")
        if only_right:
            parts.append(f"only in {right_name}: {', '.join(only_right)}")
        message = f"{subject} disagree — " + "; ".join(parts)
        raise Disagreement(message)
    return f"{subject}: {len(left)} in {left_name}, {len(right)} in {right_name}, agreed"
