# Every rule, turned off in turn

*Run 2026-09-16 by `python scripts/mutate.py --write
evidence/tests/rule-mutations.md`, which is how to repeat it. The script
restores every file it touched before it exits.*

Green on a first run proves nothing: a test that has never been red tests
nothing. Where a rule is written before its test, the test is run red first.
Where a rule already exists, this is the substitute. Each rule is disabled in
turn, by replacing its one line with something that can never hold, and the
suite is run. A rule whose removal breaks no test is a rule nothing protects.

**Result: 8 of 8 rules turned off the test that names them.** None survived.

| Rule turned off | Tests that went red | The test that names it | Did that one go red? |
|---|---|---|---|
| a voice session may only call a tool it was given | 3 | `test_a_voice_session_may_only_call_a_tool_it_was_given` | yes |
| an approval answered by voice binds one call only | 4 | `test_an_approval_answered_by_voice_binds_one_call_only` | yes |
| a spoken reply is capped, so audio never carries a transcript | 1 | `test_a_spoken_reply_is_capped_so_audio_never_carries_a_transcript` | yes |
| a path argument goes into the URL, never into the body | 4 | `test_a_path_argument_goes_into_the_url_never_into_the_body` | yes |
| a required argument missing is refused before a request is planned | 1 | `test_a_required_argument_missing_is_refused_before_a_request_is_planned` | yes |
| only an HTTP gateway URL is ever opened | 1 | `test_only_an_http_gateway_url_is_ever_opened` | yes |
| a gateway refusal is spoken, not raised | 1 | `test_a_gateway_refusal_is_spoken_not_raised` | yes |
| a refused call says why and exits non-zero | 2 | `test_a_refused_call_says_why_and_exits_non_zero` | yes |

## What this does not prove

That the rules are the right rules, or that a rule catches every case of what
it names. It proves each rule is load-bearing: switch it off and the test that
names it says so. The last column is why that is worth more than a count. A
mutation can break a test for an incidental reason and leave a rule looking
guarded when nothing guards it, so a `NO` in that column fails this script even
though something went red. A new rule follows the order in `CONTRIBUTING.md` instead, a failing
test first, and is added to `scripts/mutations.toml`, which both a test in the
suite and `voicebridge check` require.
