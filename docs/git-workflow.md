# Git Workflow

## Branching

One feature branch per task: `feature/task-<NN>-<short-name>` (e.g., `feature/task-05-ocr-adapter`),
branched from the team's agreed integration branch (`main`, unless the team decides otherwise in
Task 01) after pulling the latest changes.

## Contributor steps

1. Confirm the task file and its "Source of truth" documents (`tasks/<NN>-*.md`).
2. Create/switch to the assigned branch.
3. Make small, focused commits — one logical change each, with a message readable without opening
   the diff (`feat(ocr): add PaddleOCR adapter with fake-adapter test double`).
4. Run the task's required tests plus any directly-related regression tests (`testing.md`).
5. Run `git diff` and `git status`; remove unrelated files, debug prints, and anything from
   `security-privacy.md`'s "never commit" list before proceeding.
6. Update the task's handoff notes (files changed, commands run, results, limitations).
7. Push the branch and open a PR only when the task's acceptance criteria are met.

## PR content

Summary of what changed and why, files changed, exact test commands + results, screenshots for any
UI change, known limitations, and which task/doc this closes.

## Conflict handling

Never resolve a merge conflict by silently changing an API schema, status enum, database column, or
blockchain payload field to make the conflict go away — those are shared contracts
(`api.md`, `data-model.md`, `verification-rules.md`, `blockchain.md`, `category-schemas.md`). If a
conflict touches one of those files, stop and get the project lead to arbitrate the correct version
before continuing.

## Never commit

`.env` files, `CHAIN_EVENT_SALT` or any secret, real personal documents, PaddleOCR model weight
files, `node_modules`/`.venv`, or the local SQLite DB file (`data/app.db`). `.gitignore` must cover
all of these from Task 01 onward.

## AI coding-agent rules

An AI working on a task branch may prepare commits, tests, and a suggested commit message, but does
not itself run `git commit`, `git push`, or open/merge a PR unless the human contributor explicitly
authorizes that specific action in that session. See `AI-CONTEXT.md` for the full operating
procedure.
