"""The command line: three verbs, each one a thing you would want before trusting the bridge.

`tools` shows the surface the voice model is given, `dispatch` makes or
rehearses one call across it, and `check` is what continuous integration runs
to prove the documents and the code still agree.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import TYPE_CHECKING, ClassVar

from voice_bridge import budget, gateway
from voice_bridge import check as drift
from voice_bridge.contract import DEFAULT_GATEWAY
from voice_bridge.policy import Capabilities, Refused

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


def _tools(args: argparse.Namespace) -> int:
    """Print the tool surface handed to a realtime session."""
    schemas = gateway.tool_schemas()
    if args.names:
        for schema in schemas:
            print(schema["name"])
    else:
        print(json.dumps(schemas, indent=2))
    return 0


def _dispatch(args: argparse.Namespace) -> int:
    """Make one voice tool call, or show the request it would make."""
    arguments = json.loads(args.arguments) if args.arguments else {}
    capabilities = Capabilities()
    try:
        # The narrowest layer answers first, so `--dry-run` shows a refusal
        # rather than a request that would never have been sent.
        capabilities.permit(args.name, arguments)
        if args.dry_run:
            print(gateway.plan(args.name, arguments, args.gateway).rendered())
        else:
            print(gateway.call(args.name, arguments, args.gateway, capabilities))
    except Refused as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        # RULE: a refused call says why and exits non-zero
        return 2
    return 0


def _budget(args: argparse.Namespace) -> int:
    """Say what is left of this month's voice budget."""
    ledger = budget.Ledger(pathlib.Path(args.ledger) if args.ledger else None)
    try:
        ledger.authorise()
    except Refused as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 2
    print(
        f"${ledger.remaining_usd():.2f} left of ${budget.ceiling_usd():.2f} this month "
        f"— {ledger.remaining_minutes()} minutes"
    )
    return 0


def _check(args: argparse.Namespace) -> int:
    """Compare every fact the documents and the code both state."""
    try:
        for line in drift.report(pathlib.Path(args.root)):
            print(line)
    except drift.Disagreement as disagreement:
        print(str(disagreement), file=sys.stderr)
        return 1
    return 0


class Main:
    """The command, and the verbs it has, so a test can ask for the list."""

    commands: ClassVar[dict[str, Callable[[argparse.Namespace], int]]] = {
        "budget": _budget,
        "check": _check,
        "dispatch": _dispatch,
        "tools": _tools,
    }

    def parser(self) -> argparse.ArgumentParser:
        """Every verb and flag this command accepts."""
        parser = argparse.ArgumentParser(prog="voicebridge", description=__doc__.splitlines()[0])
        verbs = parser.add_subparsers(dest="verb", required=True)

        tools = verbs.add_parser("tools", help=_tools.__doc__)
        tools.add_argument("--names", action="store_true", help="just the names, one a line")

        dispatch = verbs.add_parser("dispatch", help=_dispatch.__doc__)
        dispatch.add_argument("name", help="the voice tool to call")
        dispatch.add_argument("arguments", nargs="?", default="", help="its arguments, as JSON")
        dispatch.add_argument("--gateway", default=DEFAULT_GATEWAY, help="the Hermes gateway")
        dispatch.add_argument("--dry-run", action="store_true", help="show the request, send nothing")

        spend = verbs.add_parser("budget", help=_budget.__doc__)
        spend.add_argument("--ledger", default="", help="where the spend is kept")

        check = verbs.add_parser("check", help=_check.__doc__)
        check.add_argument("root", nargs="?", default=".", help="the repository to check")
        return parser

    def __call__(self, argv: Sequence[str] | None = None) -> int:
        """Run one verb and return its exit status."""
        args = self.parser().parse_args(argv)
        return self.commands[args.verb](args)


main = Main()


def run() -> int:
    """The console entry point."""
    return main()


if __name__ == "__main__":
    raise SystemExit(run())
