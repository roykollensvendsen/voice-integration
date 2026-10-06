# Every rule, turned off in turn

*Run 2026-10-06 by `python scripts/mutate.py --write
evidence/tests/rule-mutations.md`, which is how to repeat it. The script
restores every file it touched before it exits.*

Green on a first run proves nothing: a test that has never been red tests
nothing. Where a rule is written before its test, the test is run red first.
Where a rule already exists, this is the substitute. Each rule is disabled in
turn, by replacing its one line with something that can never hold, and the
suite is run. A rule whose removal breaks no test is a rule nothing protects.

**Result: 30 of 33 rules turned off the test that names them.** None survived. Killed only by other tests: a delegation waits for the work rather than reading back a receipt, a remembered turn is a message item, not a bare string, a question the bridge can answer never travels further.

| Rule turned off | Tests that went red | The test that names it | Did that one go red? |
|---|---|---|---|
| a voice session may only call a tool it was given | 4 | `test_a_voice_session_may_only_call_a_tool_it_was_given` | yes |
| an approval answered by voice binds one call only | 5 | `test_an_approval_answered_by_voice_binds_one_call_only` | yes |
| a spoken reply is capped, so audio never carries a transcript | 2 | `test_a_spoken_reply_is_capped_so_audio_never_carries_a_transcript` | yes |
| a path argument goes into the URL, never into the body | 22 | `test_a_path_argument_goes_into_the_url_never_into_the_body` | yes |
| a required argument missing is refused before a request is planned | 2 | `test_a_required_argument_missing_is_refused_before_a_request_is_planned` | yes |
| only an HTTP gateway URL is ever opened | 2 | `test_only_an_http_gateway_url_is_ever_opened` | yes |
| a gateway refusal is spoken, not raised | 2 | `test_a_gateway_refusal_is_spoken_not_raised` | yes |
| a refused call says why and exits non-zero | 3 | `test_a_refused_call_says_why_and_exits_non_zero` | yes |
| a run that failed is not a refused request | 2 | `test_a_run_that_failed_is_not_a_refused_request` | yes |
| a session is refused once the monthly ceiling is spent | 4 | `test_a_session_is_refused_once_the_monthly_ceiling_is_spent` | yes |
| the month is checked before a session is opened | 3 | `test_the_month_is_checked_before_a_session_is_opened` | yes |
| a session is never opened without a language rule in its own language | 2 | `test_a_session_is_never_opened_without_a_language_rule_in_its_own_language` | yes |
| a delegation waits for the work rather than reading back a receipt | 2 | `test_a_delegation_waits_for_the_work_rather_than_reading_back_a_receipt` | NO |
| a voice turn asks the gateway to finish inside it | 6 | `test_a_voice_turn_asks_the_gateway_to_finish_inside_it` | yes |
| only a word that is plainly yes or no answers a permission question | 2 | `test_only_a_word_that_is_plainly_yes_or_no_answers_a_permission_question` | yes |
| a permission question is noticed however late it arrives | 2 | `test_a_permission_question_is_noticed_however_late_it_arrives` | yes |
| a remembered turn is a message item, not a bare string | 1 | `test_a_remembered_turn_is_a_message_item_not_a_bare_string` | NO |
| a turn is finished only when the run behind it is | 2 | `test_a_turn_is_finished_only_when_the_run_behind_it_is` | yes |
| separate things said stay separate when they are sent on | 2 | `test_separate_things_said_stay_separate_when_they_are_sent_on` | yes |
| an open microphone is booked while it is open | 2 | `test_an_open_microphone_is_booked_while_it_is_open` | yes |
| a phrase the gateway demanded is said for the person, not by them | 2 | `test_a_phrase_the_gateway_demanded_is_said_for_the_person_not_by_them` | yes |
| a request carries the conversation it came out of | 2 | `test_a_request_carries_the_conversation_it_came_out_of` | yes |
| a question the bridge can answer never travels further | 1 | `test_a_question_the_bridge_can_answer_never_travels_further` | NO |
| only a short question is ever answered without the gateway | 2 | `test_only_a_short_question_is_ever_answered_without_the_gateway` | yes |
| a question for the web is asked of the web, not of an agent | 2 | `test_a_question_for_the_web_is_asked_of_the_web_not_of_an_agent` | yes |
| a position is held in memory and written nowhere | 3 | `test_a_position_is_held_in_memory_and_written_nowhere` | yes |
| the page may only report events in its own name | 2 | `test_the_page_may_only_report_events_in_its_own_name` | yes |
| the bridge calls claude-voice only to hear news and answer one request | 2 | `test_the_bridge_calls_claude_voice_only_to_hear_news_and_answer_one_request` | yes |
| an approval number is never read aloud | 2 | `test_an_approval_number_is_never_read_aloud` | yes |
| old news is never read out | 2 | `test_old_news_is_never_read_out` | yes |
| a spoken answer settles a coding session only when one request waits | 2 | `test_a_spoken_answer_settles_a_coding_session_only_when_one_request_waits` | yes |
| a plain yes or no answers the coding session that asked | 5 | `test_a_plain_yes_or_no_answers_the_coding_session_that_asked` | yes |
| a button answers only a request the bridge was told about | 2 | `test_a_button_answers_only_a_request_the_bridge_was_told_about` | yes |

## What this does not prove

That the rules are the right rules, or that a rule catches every case of what
it names. It proves each rule is load-bearing: switch it off and the test that
names it says so. The last column is why that is worth more than a count. A
mutation can break a test for an incidental reason and leave a rule looking
guarded when nothing guards it, so a `NO` in that column fails this script even
though something went red. A new rule follows the order in `CONTRIBUTING.md` instead, a failing
test first, and is added to `scripts/mutations.toml`, which both a test in the
suite and `voicebridge check` require.
