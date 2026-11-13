"""A session spoken to by voice asks out loud, not in a box nobody can answer.

The hook runs in every Claude Code session on the machine, before a choice box
opens. It is a separate script so that a session needs nothing from this
package to run it.
"""

import datetime
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


MARK = "Your reply is read by the voice."


def peer_entry(name, text, minutes_ago, pid=4242):
    """A message from another session as Claude Code writes it into the receiver's transcript."""
    when = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=minutes_ago)
    address = f"uds:/run/user/1000/cc-socks/{pid}.sock"
    return {
        "type": "user",
        "isMeta": True,
        "timestamp": when.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "origin": {"kind": "peer", "name": name, "from": address, "verifiedPeerPid": pid, "body": text},
        "message": {
            "role": "user",
            "content": f'<cross-session-message from="{address}" from-name="{name}">\n{text}\n'
            "</cross-session-message>",
        },
    }


def asked_after(tmp_path, *entries, couriers=()):
    """Ask for a box in a session whose transcript holds `entries`; `couriers` are live courier pids."""
    sessions = tmp_path / "config" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    for pid in couriers:
        (sessions / f"{pid}.json").write_text(
            json.dumps({"pid": pid, "cwd": str(tmp_path / f"claude-voice-msg-{pid}")})
        )
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("".join(json.dumps(e) + "\n" for e in entries))
    env = {**os.environ, "XDG_STATE_HOME": str(tmp_path), "CLAUDE_CONFIG_DIR": str(tmp_path / "config")}
    asked = {
        "session_id": "c3",
        "transcript_path": str(transcript),
        "hook_event_name": "PreToolUse",
        "tool_name": "AskUserQuestion",
    }
    done = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(asked),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert done.returncode == 0
    return json.loads(done.stdout)["hookSpecificOutput"] if done.stdout.strip() else None


def test_a_choice_box_is_refused_for_ten_minutes_after_a_voice_message(tmp_path):
    marked = asked_after(tmp_path, peer_entry("Owner via voice", f"Is it green?\n\n{MARK}", minutes_ago=3))
    assert marked["permissionDecision"] == "deny"
    assert "stemmen" in marked["permissionDecisionReason"]
    assert "svaret" in marked["permissionDecisionReason"]
    by_folder = asked_after(
        tmp_path, peer_entry("Owner via voice", "Is it green?", minutes_ago=9), couriers=[4242]
    )
    assert by_folder["permissionDecision"] == "deny"


def test_a_box_opens_again_once_the_voice_message_is_old_or_was_never_one(tmp_path):
    assert (
        asked_after(tmp_path, peer_entry("Owner via voice", f"Is it green?\n\n{MARK}", minutes_ago=11))
        is None
    )
    assert asked_after(tmp_path, peer_entry("build-7c", "Is it green?", minutes_ago=1)) is None
    assert asked_after(tmp_path) is None


def test_a_transcript_that_cannot_be_read_keeps_the_box(tmp_path):
    env = {**os.environ, "XDG_STATE_HOME": str(tmp_path), "CLAUDE_CONFIG_DIR": str(tmp_path)}
    asked = {"session_id": "c3", "transcript_path": str(tmp_path / "missing.jsonl")}
    done = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(asked),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert (done.returncode, done.stdout) == (0, "")
