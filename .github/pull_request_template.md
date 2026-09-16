<!-- Four parts, in this order. The `write-commit` skill has the detail.
     1. The ground: what this part is for, and where it stood before.
     2. What changed, and why this way rather than another way.
     3. What a reviewer should push on: the weakest parts of your own change.
     4. The checklist below.
     Leave out what CI already reports on this page. -->

## The rules no script can measure

- [ ] Every rule this change adds names the check, CI job or review step that
      enforces it, or says plainly that it is not enforced yet and when it will be.
- [ ] The specification changed before the code, or this change only implements
      a line that was already there.
- [ ] Every new test was seen red before the code that turns it green, or the
      rule it guards was turned off and the test was seen red that way, with the
      run recorded under `evidence/tests/`.
- [ ] A decision that costs more to reverse than to take is a record under
      `decisions/`, linked here.
- [ ] Nothing here copies text that lives somewhere else; it links to it instead.
- [ ] A lesson this change taught is written where the next person doing this
      task will read it: a test or a check where the mistake is checkable, a
      skill or a rule where it is not. Not only in the commit message.
