# How to Use These Task Files

Read this once, then never again. Everything after it is a work order.

---

## What a task file is

A task file is a **work order** for one contributor and their AI coding assistant. It is written so
that a competent assistant with no prior knowledge of PS21 can read `AGENTS.md`, `docs/AI-CONTEXT.md`,
the documents the task cites, and the task itself — and then implement the whole thing correctly
without asking you a single question.

That is the bar. If a task file leaves an assistant guessing, the task file is defective and should
be fixed before anyone writes code against it.

## What a task file is not

It is not a suggestion, an outline, or a starting point for interpretation. The Allowed Files
section is a boundary, not a hint. The Acceptance Criteria are the definition of done, not a wish
list.

---

## The thirteen sections, and what each one is for

| § | Section | Purpose |
|---|---|---|
| 1 | **Goal** | What to build, and why it exists in the plan |
| 2 | **Authoritative Documentation** | The exact docs that define this task's contracts. Read all of them |
| 3 | **Scope** | In scope and — just as binding — out of scope |
| 4 | **Allowed Files** | The only files you may create or modify |
| 5 | **Dependencies** | What must exist first, and what can proceed in parallel |
| 6 | **Contracts That Must Be Preserved** | The shared agreements you may not change |
| 7 | **Implementation Requirements** | Numbered, testable requirements including error handling |
| 8 | **Testing Requirements** | Exact tests, exact commands, expected results |
| 9 | **Acceptance Criteria** | The checklist. Every box ticked, or the task is not done |
| 10 | **Known Risks** | Traps identified in advance so you don't discover them at 2 a.m. |
| 11 | **Open Questions** | Anything genuinely unresolved — with who decides |
| 12 | **Handoff Notes** | What the next task needs from you |
| 13 | **Definition of Done** | The full gate, including diff review and log update |

---

## How to run a task with an AI assistant

**Give it, in this order:**

1. `AGENTS.md`
2. `docs/AI-CONTEXT.md`
3. Every document listed in the task's §2
4. The task file itself
5. The relevant `logs/task-NN-*.md` if one exists

**Then say something like:**

> Read all of these completely before writing any code. Then tell me your implementation plan,
> which files you will create or modify, and any place where the documentation is ambiguous.
> Do not write code until I confirm the plan.

**The plan review is the step people skip, and it is the step that saves the most time.** An
assistant that has misread a contract will say so in its plan, cheaply, before it has written four
hundred lines against the wrong schema.

**During implementation, watch for these four failure signals:**

- It edits a file outside §4 → stop it, that is a scope violation
- It invents a field, status, or endpoint not in the docs → stop it, that violates `AGENTS.md` Rule 1
- It says "tests pass" without showing the command and output → ask for both
- It resolves a documentation ambiguity by picking one side → stop it, escalate to the project lead

**At the end, require:**

- The exact test command and its exact output
- `git diff --stat` showing only allowed files
- The §9 checklist, walked one box at a time
- The `logs/task-NN-*.md` updated

---

## Rules for the project lead

- **Assign one task per person at a time.** Two people inside overlapping file sets is how this
  project breaks.
- **You are the only one who marks a task complete.** Not the contributor, and certainly not the
  assistant.
- **You are the only one who resolves a §11 open question.** When you do, record it in
  `docs/decisions.md` with a new `D-NN` and update the affected contract document in the same pull
  request.
- **A contract change is never a local decision.** If Task 07 needs a field that Task 06 does not
  produce, that is a conversation and a doc update, not an inline fix in Task 07.
- **Read the logs daily.** They are the only early warning you get.

---

## If a task file is wrong

It happens. Documentation written before implementation always contains some errors.

The correct response is: stop, state precisely what is wrong, propose the fix, get approval, update
the documentation, then continue. Ten minutes.

The incorrect response is: implement something reasonable, mention it in the handoff notes, and
leave the next three tasks building against a contract that no longer describes reality. That costs
a day, and it always surfaces during integration.
