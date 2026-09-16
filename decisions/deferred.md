# What is deliberately not done yet

A thing left undone with no trigger is a thing forgotten. Each row names what
would make it worth doing, so the question comes back on its own rather than
depending on someone remembering it. Nothing enforces a trigger; the list is
read whenever a decision record is written and when a phase ends.

| Not done | The trigger | Why not now |
|---|---|---|
| A coverage threshold in CI | Two months of measured coverage to set it below | A number picked before there is data is a guess with a gate on it |
| A code of conduct and issue templates | A second contributor, or the first outside issue | Boilerplate answering questions nobody has asked |
| A release workflow and publishing | The first release someone outside will install | A published name is claimed and a published version cannot be reused |
| `CODEOWNERS` | A second person who reviews | It would name one person as the owner of everything |
| `pre-commit` as a requirement rather than an option | A second contributor | The gates run in CI, and a hook one person installs is a hook one person maintains |
| The realtime audio client | Question 1 in `docs/open-questions.md` answered with a funded account and a ceiling | Every line of it is wasted if the answer is "no budget", and Hermes' push-to-talk mode is the fallback |
| The laptop view over `/v1/runs/{run_id}/events` | The audio client works end to end | It is the screen the voice layer defers detail to, and deferring to a screen that does not exist is just losing the detail |
| Rooms where agents talk to each other | A bound on the discussion — turns, tokens or a person — decided first | Two agents arguing is two token streams with no natural end |
| Rooms with more than one person | Voice identity answered, question 6 in `docs/open-questions.md` | Today the bridge knows a session, not a speaker, and an approval from an unidentified voice is not an approval |
| Calling `GET /v1/capabilities` before assuming the contract | The first time Hermes changes an endpoint under us | Hermes publishes it, so the break should be a message rather than a mystery |
| Revisiting ADR-VI-002 | ChatGPT voice gains tool calling on a plan that is held | The whole reason for owning the client is that this does not exist today |
| A second language for the voice client | Question 11 in `docs/open-questions.md` answered "browser" | Python is right for the part that talks to Hermes and wrong for the part holding a microphone in a page, and both ends now need that part |
| Microphone handover between the phone and the laptop | Question 10 in `docs/open-questions.md` answered | Two live sessions answer one sentence twice and bill twice while idle |
