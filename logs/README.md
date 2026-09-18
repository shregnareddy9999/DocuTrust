# Development Log Template

Every task keeps a log at `logs/task-NN-<slug>.md`. Copy the template below when you start.

**Why this exists:** context does not survive between sessions. The next contributor — human or a
fresh AI session — reads this file, not your memory. A log written at the end of the task, from
recollection, is worth roughly nothing. Write it as you go.

---

## Template

```markdown
# Task NN — <Task Name> — Development Log

**Owner:** <name>
**Branch:** `feature/task-NN-<slug>`
**Started:** YYYY-MM-DD
**Status:** In progress | Blocked | Ready for review

---

## Contracts this task implements

- `docs/<file>.md` § <section> — <what it defines for me>

## Decisions I made inside my own scope

| Date | Decision | Why | Reversible? |
|---|---|---|---|
| | | | |

> Anything here that touches a **shared** contract does not belong here — it belongs in a question
> to the project lead and, once answered, in `docs/decisions.md`.

## Interfaces I published for other tasks

Describe the exact shape other people can now build against, and when it stabilised.

```python
# example
```

## Progress

### YYYY-MM-DD
- Did: …
- Verified by running: `<exact command>` → `<exact result>`
- Next: …

## Blockers and open questions

| # | Question | Asked on | Answer | Resolved |
|---|---|---|---|---|
| 1 | | | | ☐ |

## Tests

| Command | Last run | Result |
|---|---|---|
| `cd backend && pytest tests/test_x.py` | | |

## Known limitations at handoff

- …

## Handoff notes

- Files changed: …
- What the next task needs to know: …
- What I did **not** do, that someone might assume I did: …
```

---

## Rules for logs

1. Record the **exact command** and **exact result**, never "tests pass."
2. Record blockers the moment you hit them, with the timestamp — not after they're resolved.
3. Record what you deliberately did *not* do. Silent omissions are what break integration.
4. If you change something another task depends on, publish it in "Interfaces I published" and tell
   the project lead the same day.
5. Never delete a log entry. Append a correction instead.