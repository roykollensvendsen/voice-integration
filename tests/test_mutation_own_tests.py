"""Each mutation runs only the test files that hold the rule's own test.

`scripts/mutate.py` switches every rule off in turn and runs the tests, and a
rule counts as proven only when its own test, named after it, goes red. Running
the whole suite for each of sixty-odd rules took over three hours in the checks,
so each mutation now runs just the files that define that one test.
"""

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent


def _mutate():
    spec = importlib.util.spec_from_file_location("mutate_own", ROOT / "scripts/mutate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tree(tmp_path):
    """A scratch tree with one rule, a test file holding its own test, and one that does not."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src/rule.py").write_text("if guarded:\n    pass\n")
    rows = tmp_path / "scripts/mutations/src/rule.py"
    rows.mkdir(parents=True)
    (rows / "a-guard-holds.toml").write_text(
        '[[rule]]\nname = "a guard holds"\nfile = "src/rule.py"\n'
        "find = 'if guarded:'\nreplace = 'if True:'\n"
    )
    (tmp_path / "tests/deeper").mkdir(parents=True)
    (tmp_path / "tests/deeper/test_guard.py").write_text("def test_a_guard_holds():\n    pass\n")
    (tmp_path / "tests/test_other.py").write_text("def test_something_else():\n    pass\n")


def test_a_mutation_runs_only_the_test_files_that_hold_the_rule_s_own_test(tmp_path, monkeypatch):
    mutate = _mutate()
    _tree(tmp_path)
    ran = []
    monkeypatch.setattr(mutate, "ROOT", tmp_path)
    # Its own: the real one holds the temporary files of the mutation run this may be inside.
    monkeypatch.setattr(mutate, "MUTATE_TMP", tmp_path / "mutate-tmp")
    monkeypatch.setattr(
        mutate, "run_suite", lambda targets=None: (ran.append(targets), (1, ["test_a_guard_holds"]))[1]
    )
    monkeypatch.setattr(sys, "argv", ["mutate.py"])
    assert mutate.main() == 0
    assert ran == [["tests/deeper/test_guard.py"]]


def test_a_rule_whose_own_test_no_file_holds_runs_the_whole_suite(tmp_path, monkeypatch):
    mutate = _mutate()
    _tree(tmp_path)
    monkeypatch.setattr(mutate, "ROOT", tmp_path)
    assert mutate.files_naming("test_nobody_wrote") == []
    assert mutate.files_naming("test_a_guard_holds") == ["tests/deeper/test_guard.py"]


def test_the_suite_is_given_the_files_to_run(tmp_path, monkeypatch):
    mutate = _mutate()
    monkeypatch.setattr(mutate, "MUTATE_TMP", tmp_path / "mutate-tmp")
    seen = []

    class Done:
        stdout = "1 passed\n"

    monkeypatch.setattr(mutate.subprocess, "run", lambda argv, **_: (seen.append(argv), Done())[1])
    mutate.run_suite(["tests/test_a.py"])
    mutate.run_suite([])
    assert seen[0][-1] == "tests/test_a.py"
    assert seen[1][-1].startswith("--basetemp=")
