"""The project's own check: the documents and the code have to say the same thing.

Four facts are written down twice here, because a reader needs them in prose
and the program needs them in code. Each pair is compared, so the copy cannot
quietly go stale:

* the voice tools, in `docs/voice-contract.md` and in `voice_bridge.contract`
* the gateway endpoints, in `docs/hermes-contract.md` and in `voice_bridge.gateway`
* the claude-voice tools, in `docs/claude-voice-contract.md` and in `voice_bridge.sessions`
* the rules, marked `# RULE:` in the source and rowed in `scripts/mutations.toml`
* every rule, against a test in `tests/` named after it

The third is the one that keeps the mutation evidence honest. A rule added
without a row is a rule no mutation ever switches off, and the table becomes a
historical document without anyone noticing.

The fourth is what makes a mutation kill readable. Turning a rule off breaks
whatever it breaks, and a kill only means something if the test that went red is
the one that names the rule. Without a test named after it, a rule can look
guarded by an accident — a documentation example that happened to change — and
nobody would see the difference.
"""

from __future__ import annotations

import pathlib  # noqa: TC003 — a runtime default reads it, not only the annotations
import re
import tomllib

from voice_bridge.contract import BY_NAME
from voice_bridge.gateway import BESIDES_THE_TOOLS
from voice_bridge.sessions import TOOLS as CLAUDE_VOICE_TOOLS

ANCHOR = "<!-- normative: {} -->"
_ROW = re.compile(r"^\|\s*`([^`]+)`")
_PATH_ROW = re.compile(r"^\|[^|]*\|\s*`([^`]+)`")
# Anchored, so that a page or a docstring mentioning the marker is not a rule.
_RULE = re.compile(r"^[ \t]*#\s*RULE:\s*(.+?)\s*$")


class Disagreement(Exception):
    """A document and the code no longer say the same thing."""


def table_after(page: pathlib.Path, anchor: str, pattern: re.Pattern[str]) -> set[str]:
    """Every backticked name in the one table that follows an anchor."""
    if not page.is_file():
        message = f"{page} is gone, and it held the only written copy of the {anchor}"
        raise Disagreement(message)
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


def test_names(root: pathlib.Path) -> set[str]:
    """Every test function the suite defines, by name."""
    found = set()
    for module in sorted((root / "tests").rglob("test_*.py")):
        found.update(re.findall(r"^def (test_\w+)", module.read_text(), re.MULTILINE))
    return found


def test_name_for(rule: str) -> str:
    """The test name a rule requires: its own words, as an identifier."""
    words = re.sub(r"[^a-z0-9]+", "_", rule.lower())
    return "test_" + re.sub(r"_+", "_", words).strip("_")


def rowed_rules(root: pathlib.Path) -> set[str]:
    """Every rule the mutation table claims to switch off."""
    listing = root / "scripts/mutations.toml"
    if not listing.is_file():
        message = f"{listing} is gone, and no rule has evidence without it"
        raise Disagreement(message)
    table = tomllib.loads(listing.read_text())
    return {str(rule["name"]) for rule in table.get("rule", [])}


#: How far below its marker a rule's line may sit: a marker, a comment or two,
#: then the line.
ROW_REACH = 5


def rows_hit_their_rules(root: pathlib.Path) -> str:
    """Every mutation row switches off the line its rule marks, not some other line.

    Rows drift as the code grows: an earlier identical line starts matching
    first, or the line changes and nothing matches at all. Either way the rule
    looks guarded, or the run stops, and nobody notices.
    """
    table = tomllib.loads((root / "scripts/mutations.toml").read_text()).get("rule", [])
    drifted = []
    for row in table:
        lines = (root / row["file"]).read_text().splitlines()
        hits = [i for i, line in enumerate(lines) if re.search(row["find"], line)]
        markers = [
            i
            for i, line in enumerate(lines)
            if _RULE.search(line) and _RULE.search(line).group(1) == row["name"]
        ]
        hit = hits[row.get("occurrence", 1) - 1] if len(hits) >= row.get("occurrence", 1) else None
        # One line above the marker is allowed too: two rules can share one
        # line, with the second marker inside the block that line opens.
        if hit is None or not markers or not -1 <= hit - markers[0] <= ROW_REACH:
            drifted.append(row["name"])
    if drifted:
        message = "mutation rows that miss the line their rule marks — " + ", ".join(sorted(drifted))
        raise Disagreement(message)
    return f"mutation rows: {len(table)}, each on the line its rule marks"


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
            {tool.path for tool in BY_NAME.values()} | set(BESIDES_THE_TOOLS),
            "the code",
        )
    )
    lines.append(
        _compare(
            "claude-voice tools",
            table_after(root / "docs/claude-voice-contract.md", "claude-voice tools", _ROW),
            "docs/claude-voice-contract.md",
            set(CLAUDE_VOICE_TOOLS),
            "the code",
        )
    )
    rules = marked_rules(root)
    lines.append(
        _compare(
            "rules",
            rules,
            "the source",
            rowed_rules(root),
            "scripts/mutations.toml",
        )
    )
    lines.append(_every_rule_has_its_own_test(rules, test_names(root)))
    lines.append(rows_hit_their_rules(root))
    return lines


def _every_rule_has_its_own_test(rules: set[str], tests: set[str]) -> str:
    missing = sorted(rule for rule in rules if test_name_for(rule) not in tests)
    if missing:
        wanted = ", ".join(f"{test_name_for(rule)}()" for rule in missing)
        message = f"rules with no test named after them — write {wanted}"
        raise Disagreement(message)
    return f"rule tests: {len(rules)} rules, each with a test named after it"


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
