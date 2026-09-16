# Every rule, turned off in turn

*Run 2026-09-16 by `python scripts/mutate.py --write
evidence/tests/rule-mutations.md`, which is how to repeat it. The script
restores every file it touched before it exits.*

Green on a first run proves nothing: a test that has never been red tests
nothing. Where a rule is written before its test, the test is run red first.
Where a rule already exists, this is the substitute. Each rule is disabled in
turn, by replacing its one line with something that can never hold, and the
suite is run. A rule whose removal breaks no test is a rule nothing protects.

**Result: 3 of 3 rules killed at least one test.** None survived.

| Rule turned off | Tests that went red | First of them |
|---|---|---|
| a voice session may only call a tool it was given | 2 | `test_a_voice_session_may_only_call_a_tool_it_was_given` |
| an approval answered by voice binds one call only | 4 | `test_a_documented_command_prints_what_the_page_says[voicebridge` |
| a spoken reply is capped, so audio never carries a transcript | 1 | `test_a_spoken_reply_is_capped_so_audio_never_carries_a_transcript` |

## What this does not prove

That the rules are the right rules, or that a rule catches every case of what
it names. It proves each rule is load-bearing: switch it off and a named test
says so. A new rule follows the order in `CONTRIBUTING.md` instead, a failing
test first, and is added to `scripts/mutations.toml`, which both a test in the
suite and `voicebridge check` require.
