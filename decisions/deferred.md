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
| Making the repository public | The Linux client works end to end and the specification has survived contact with it | A specification with open premises reads as a claim, and publishing cannot be undone |
| The Android client | The Linux client has been used enough to say whether the interaction is worth a second client | ADR-VI-014: the premise is cheaper to test on the machine the person is already sitting at |
| The laptop view over `/v1/runs/{run_id}/events` | The Linux client works end to end | It is the screen the voice layer defers detail to, and deferring to a screen that does not exist is just losing the detail |
| Rooms where agents talk to each other | The Linux client works end to end | The shape is decided in ADR-VI-012; nothing else about it is |
| Rooms with more than one person | Voice identity, which ADR-VI-011 deliberately does not provide | The device is the identity, and a shared room has no device |
| Calling `GET /v1/capabilities` before assuming the contract | The first time Hermes changes an endpoint under us | Hermes publishes it, so the break should be a message rather than a mystery |
| Revisiting ADR-VI-002 | ChatGPT voice gains tool calling on a plan that is held | The whole reason for owning the client is that this does not exist today |
| Budgeting the agents' own cost, not only the audio | Anthropic unpauses the change that moves `claude -p` to a metered credit pool | Today it draws from the subscription quota, so there is nothing to meter; the day that changes, the ceiling in ADR-VI-007 stops covering most of the bill |
