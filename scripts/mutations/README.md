# One row per rule

Every rule this project enforces is a line marked `# RULE:` in the source, and
each has a row here: the one line that carries it, and what replaces it.

A rule nothing catches is a rule nothing protects. `scripts/mutate.py` turns
each rule off in turn and runs the suite; a rule whose removal breaks no test
has no test. `voicebridge check` counts the rules in the source against the
rows here, so this folder cannot fall behind.

Each row is a file of its own, named after the rule, in a folder that is the
whole path of the file it switches off. `# RULE: a spoken reply is capped` in
`src/voice_bridge/speech.py` goes in
`src/voice_bridge/speech.py/a-spoken-reply-is-capped.toml` here:

```toml
[[rule]]
name = "a spoken reply is capped"
file = "src/voice_bridge/speech.py"
find = 'if limit_exceeded:'
replace = 'if False:'
```

`find` is a regular expression matching the single line to replace; `replace`
is what replaces it, keeping the file valid. The line's own indentation is
kept, so do not write indentation here. Where two rules share a line, an
`occurrence` field says which match is meant.
