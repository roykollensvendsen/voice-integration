"""A session spoken to by voice asks out loud, not in a box nobody can answer.

The hook runs in every Claude Code session on the machine, before a choice box
opens. It is a separate script so that a session needs nothing from this
package to run it.
"""

import json
import os
import pathlib
import subprocess
import sys

HOOK = pathlib.Path(__file__).parent.parent / "scripts" / "hooks" / "no_choice_box_while_spoken_to.py"


def run(tmp_path, session_id, chosen=None):
    if chosen is not None:
        (tmp_path / "voice-bridge").mkdir(exist_ok=True)
        (tmp_path / "voice-bridge" / "target.json").write_text(json.dumps(chosen))
    env = {**os.environ, "XDG_STATE_HOME": str(tmp_path)}
    asked = {"session_id": session_id, "hook_event_name": "PreToolUse", "tool_name": "AskUserQuestion"}
    command = [sys.executable, str(HOOK)]
    done = subprocess.run(
        command, input=json.dumps(asked), capture_output=True, text=True, env=env, check=False
    )
    return done.returncode, done.stdout


def test_a_choice_box_is_refused_in_the_session_spoken_to_by_voice(tmp_path):
    status, said = run(tmp_path, "a1", {"kind": "session", "name": "build-7c", "claude_session_id": "a1"})
    assert status == 0
    decided = json.loads(said)["hookSpecificOutput"]
    assert decided["permissionDecision"] == "deny"
    assert "stemmen" in decided["permissionDecisionReason"]


def test_every_other_session_keeps_its_choice_boxes(tmp_path):
    assert run(tmp_path, "b2", {"kind": "session", "name": "build-7c", "claude_session_id": "a1"}) == (0, "")
    assert run(tmp_path, "a1", {"kind": "hermes"}) == (0, "")
    assert run(tmp_path, "a1") == (0, "")
