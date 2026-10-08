# Every rule, turned off in turn

*Run 2026-10-08 by `python scripts/mutate.py --write
evidence/tests/rule-mutations.md`, which is how to repeat it. The script
restores every file it touched before it exits.*

Green on a first run proves nothing: a test that has never been red tests
nothing. Where a rule is written before its test, the test is run red first.
Where a rule already exists, this is the substitute. Each rule is disabled in
turn, by replacing its one line with something that can never hold, and the
suite is run. A rule whose removal breaks no test is a rule nothing protects.

**Result: 49 of 49 rules turned off the test that names them.** None survived.

| Rule turned off | Tests that went red | The test that names it | Did that one go red? |
|---|---|---|---|
| a voice session may only call a tool it was given | 6 | `test_a_voice_session_may_only_call_a_tool_it_was_given` | yes |
| an approval answered by voice binds one call only | 7 | `test_an_approval_answered_by_voice_binds_one_call_only` | yes |
| a spoken reply is capped, so audio never carries a transcript | 4 | `test_a_spoken_reply_is_capped_so_audio_never_carries_a_transcript` | yes |
| a path argument goes into the URL, never into the body | 29 | `test_a_path_argument_goes_into_the_url_never_into_the_body` | yes |
| a required argument missing is refused before a request is planned | 4 | `test_a_required_argument_missing_is_refused_before_a_request_is_planned` | yes |
| only an HTTP gateway URL is ever opened | 4 | `test_only_an_http_gateway_url_is_ever_opened` | yes |
| a gateway refusal is spoken, not raised | 4 | `test_a_gateway_refusal_is_spoken_not_raised` | yes |
| a refused call says why and exits non-zero | 5 | `test_a_refused_call_says_why_and_exits_non_zero` | yes |
| a run that failed is not a refused request | 4 | `test_a_run_that_failed_is_not_a_refused_request` | yes |
| a session is refused once the monthly ceiling is spent | 6 | `test_a_session_is_refused_once_the_monthly_ceiling_is_spent` | yes |
| the month is checked before a session is opened | 5 | `test_the_month_is_checked_before_a_session_is_opened` | yes |
| a session is never opened without a language rule in its own language | 4 | `test_a_session_is_never_opened_without_a_language_rule_in_its_own_language` | yes |
| a delegation waits for the work rather than reading back a receipt | 7 | `test_a_delegation_waits_for_the_work_rather_than_reading_back_a_receipt` | yes |
| a voice turn asks the gateway to finish inside it | 12 | `test_a_voice_turn_asks_the_gateway_to_finish_inside_it` | yes |
| only a word that is plainly yes or no answers a permission question | 4 | `test_only_a_word_that_is_plainly_yes_or_no_answers_a_permission_question` | yes |
| a permission question is noticed however late it arrives | 4 | `test_a_permission_question_is_noticed_however_late_it_arrives` | yes |
| a remembered turn is a message item, not a bare string | 6 | `test_a_remembered_turn_is_a_message_item_not_a_bare_string` | yes |
| a turn is finished only when the run behind it is | 4 | `test_a_turn_is_finished_only_when_the_run_behind_it_is` | yes |
| separate things said stay separate when they are sent on | 4 | `test_separate_things_said_stay_separate_when_they_are_sent_on` | yes |
| an open microphone is booked while it is open | 4 | `test_an_open_microphone_is_booked_while_it_is_open` | yes |
| a phrase the gateway demanded is said for the person, not by them | 4 | `test_a_phrase_the_gateway_demanded_is_said_for_the_person_not_by_them` | yes |
| a request carries the conversation it came out of | 4 | `test_a_request_carries_the_conversation_it_came_out_of` | yes |
| a question the bridge can answer never travels further | 9 | `test_a_question_the_bridge_can_answer_never_travels_further` | yes |
| only a short question is ever answered without the gateway | 4 | `test_only_a_short_question_is_ever_answered_without_the_gateway` | yes |
| a question for the web is asked of the web, not of an agent | 4 | `test_a_question_for_the_web_is_asked_of_the_web_not_of_an_agent` | yes |
| a position is held in memory and written nowhere | 5 | `test_a_position_is_held_in_memory_and_written_nowhere` | yes |
| the page may only report events in its own name | 4 | `test_the_page_may_only_report_events_in_its_own_name` | yes |
| the bridge calls claude-voice only to hear news and answer one request | 4 | `test_the_bridge_calls_claude_voice_only_to_hear_news_and_answer_one_request` | yes |
| an approval number is never read aloud | 5 | `test_an_approval_number_is_never_read_aloud` | yes |
| old news is never read out | 4 | `test_old_news_is_never_read_out` | yes |
| a spoken answer settles a coding session only when one request waits | 4 | `test_a_spoken_answer_settles_a_coding_session_only_when_one_request_waits` | yes |
| a plain yes or no answers the coding session that asked | 8 | `test_a_plain_yes_or_no_answers_the_coding_session_that_asked` | yes |
| a button answers only a request the bridge was told about | 4 | `test_a_button_answers_only_a_request_the_bridge_was_told_about` | yes |
| a name is switched to only when it matches exactly one session | 4 | `test_a_name_is_switched_to_only_when_it_matches_exactly_one_session` | yes |
| a session that ended hands the conversation back to the voice | 4 | `test_a_session_that_ended_hands_the_conversation_back_to_the_voice` | yes |
| while the voice alone is chosen nothing is forwarded | 5 | `test_while_the_voice_alone_is_chosen_nothing_is_forwarded` | yes |
| a session is chosen from the page only if it is running | 4 | `test_a_session_is_chosen_from_the_page_only_if_it_is_running` | yes |
| the choice survives a restart | 5 | `test_the_choice_survives_a_restart` | yes |
| a long sentence that mentions talking to someone is not a switch | 4 | `test_a_long_sentence_that_mentions_talking_to_someone_is_not_a_switch` | yes |
| a session opens in the voice of the chosen target | 4 | `test_a_session_opens_in_the_voice_of_the_chosen_target` | yes |
| a voice the service does not offer is never sent | 4 | `test_a_voice_the_service_does_not_offer_is_never_sent` | yes |
| a turn to a session says who is speaking and that the answer is read aloud | 5 | `test_a_turn_to_a_session_says_who_is_speaking_and_that_the_answer_is_read_aloud` | yes |
| a chosen session hears everything that is said | 4 | `test_a_chosen_session_hears_everything_that_is_said` | yes |
| news that was not heard is said when the microphone is taken again | 4 | `test_news_that_was_not_heard_is_said_when_the_microphone_is_taken_again` | yes |
| the place in the news survives a restart | 4 | `test_the_place_in_the_news_survives_a_restart` | yes |
| an answer nobody waited for becomes news | 4 | `test_an_answer_nobody_waited_for_becomes_news` | yes |
| measurements are kept for KEPT_DAYS and no longer | 4 | `test_measurements_are_kept_for_kept_days_and_no_longer` | yes |
| every spoken turn is traced and measured | 4 | `test_every_spoken_turn_is_traced_and_measured` | yes |
| the same cause raises at most one alert per QUIET_SECONDS | 4 | `test_the_same_cause_raises_at_most_one_alert_per_quiet_seconds` | yes |

## What this does not prove

That the rules are the right rules, or that a rule catches every case of what
it names. It proves each rule is load-bearing: switch it off and the test that
names it says so. The last column is why that is worth more than a count. A
mutation can break a test for an incidental reason and leave a rule looking
guarded when nothing guards it, so a `NO` in that column fails this script even
though something went red. A new rule follows the order in `CONTRIBUTING.md` instead, a failing
test first, and is added to `scripts/mutations.toml`, which both a test in the
suite and `voicebridge check` require.
