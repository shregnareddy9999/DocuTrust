# AGENTS.md — Rules for Every Contributor (Human or AI)

> **This file is read first, before any task file, by every AI coding assistant and every human
> contributor on PS21. It is short on purpose. If any other document appears to contradict a rule
> here, stop and ask the project lead — do not pick a side yourself.**

Place this file at the **repository root** (`AGENTS.md`), not only inside `docs/`. Most coding
agents look for a root-level `AGENTS.md` automatically.

---

## 1. What this project is, in one sentence

PS21 is a hackathon MVP that accepts a document, reads it with OCR, compares selected fields
against a **synthetic demo registry**, applies **deterministic** rules, supports human review, and
records a **minimal non-identifying event** on a **local** blockchain.

It is not a government service, it has no access to any real registry, and it never proves a real
document is authentic.

---

## 2. Reading order before you write any code

1. `AGENTS.md` (this file)
2. `docs/AI-CONTEXT.md` — full-project summary
3. `docs/project-context.md` and `docs/problem-statement-mapping.md` — scope and honest framing
4. `docs/architecture.md` — layers and dependency direction
5. `docs/backend.md` **or** `docs/frontend.md` — whichever side you are touching
6. The specific contract docs your task cites (`api.md`, `data-model.md`, `category-schemas.md`,
   `verification-rules.md`, `document-processing.md`, `blockchain.md`, `configuration.md`,
   `security-privacy.md`)
7. Your assigned `tasks/NN-*.md` file, completely
8. The existing repository code, tests, `.env.example`, and `logs/` entries for your area

Skipping step 7 and guessing from step 2 is the single most common way this project gets broken.

---

## 3. The twelve hard rules

**Rule 1 — Never invent a contract.**
Field names, status names, endpoint paths, database columns, error codes, environment variables,
and the on-chain payload are all already written down. If what you need is not in the docs, it is
not yours to define. Stop and ask.

**Rule 2 — Never claim verification you did not perform.**
`VERIFIED_MATCH` means "matched our synthetic demo reference." It never becomes "authentic,"
"genuine," "government verified," or "validated." This applies to code comments, log lines, API
response text, UI strings, README badges, and anything you say in a PR description.

**Rule 3 — Never treat a technical failure as a verdict.**
OCR crashed, the database errored, the chain node is down — these are `PROCESSING_FAILED` or a
blockchain status, never `INTEGRITY_MISMATCH` and never `NO_TRUSTED_RECORD`.

**Rule 4 — "No record found" is not "forged."**
`NO_TRUSTED_RECORD` is a neutral outcome. No code path, log message, or UI string may imply
otherwise.

**Rule 5 — OCR confidence is not authenticity confidence.**
It describes character recognition only. Never convert it into a fraud score, a percentage of
authenticity, or a risk rating.

**Rule 6 — Nothing personal ever goes on-chain, and no document digest either.**
No document bytes, no raw OCR text, no extracted field value, no name, no date of birth, no ID
number. Only the payload defined in `docs/blockchain.md`. `blockchain_service.py`'s payload builder
is the single chokepoint; if you find yourself adding a field to it, you are about to violate this
rule. This includes `documents.sha256` — a document digest on a permanent ledger claims integrity it
cannot deliver and creates a confirmation oracle (`docs/decisions.md` D-22).

**Rule 7 — Never use real personal data.**
Not a teammate's marksheet, not a real PAN number, not a realistic-looking fabricated one. Every
fixture identifier is `DEMO-` prefixed or an obviously fictional name (`Aarav Demo`). The
`pan_like_demo` category deliberately uses a 6-character code that cannot be confused with the real
10-character PAN pattern.

**Rule 8 — Deterministic means deterministic.**
No rule may output a weighted score, a probability, or an opaque "AI fraud score." Every rule is a
boolean with a fixed human-readable reason string. Identical inputs plus identical config must
always produce an identical result.

**Rule 9 — Corrections are additive, never destructive.**
A reviewer correction adds a new field entry with `source: "corrected"` and creates a **new**
`verification_results` row. The original OCR value and the original verification outcome stay in
history, always.

**Rule 10 — Adapters are the only place external libraries live.**
`paddleocr` is imported only inside `adapters/ocr/`. `web3` is imported only inside
`adapters/blockchain/`. `domain/` imports none of FastAPI, PaddleOCR, or Web3 — that is what makes
it unit-testable, and it is checked in review.

**Rule 11 — No test may require a live PaddleOCR run or a running chain node.**
The default suite uses `fake_adapter.py` on both sides. Real-dependency tests exist, are marked
`@pytest.mark.integration`, and are excluded from the default run.

**Rule 12 — Never say something works if you did not run it.**
"Tests pass" means you ran them in this session and saw them pass. Report the exact command and the
exact output. An unverified claim is worse than an honest "I could not run this."

---

## 4. Scope discipline

Your task file has an **Allowed Files** section. Touching a file outside it is a scope violation,
even if the change is obviously correct, even if it is one line.

If your task genuinely cannot be completed within its allowed files:

1. Stop.
2. Write down exactly which file outside your scope needs to change and why.
3. Ask the project lead.
4. Wait.

Do not "just quickly fix" a neighbouring module. Two agents silently fixing the same shared file in
different ways is the most expensive failure mode this project has, and it always surfaces at the
worst possible moment — during integration, the night before the demo.

---

## 5. Things that always require project-lead approval

- Adding, renaming, or removing a field in `category-schemas.md`
- Adding, renaming, or removing a verification status or blockchain status
- Changing any request/response shape in `api.md`
- Changing a database column in `data-model.md`
- Changing the on-chain event, the digest construction, or the `outcomeCode` mapping
- Adding a new dependency to `requirements.txt` or `package.json`
- Adding a new environment variable
- Adding any ML model or LLM anywhere in the pipeline (`decisions.md` D-06)
- Adding a fifth document category
- Creating a new top-level folder

The rule for all of these is the same: **the documentation change and the code change ship in the
same pull request.** Never code first and document later.

---

## 6. Git rules

- Work on your task's named branch. Never commit directly to `main`.
- **Never run `git commit`, `git push`, `git merge`, or approve a PR without explicit human
  authorization in that same session.** An AI assistant may stage and prepare; a human decides.
- Never mark a task's status as complete yourself. The project lead does that.
- Keep commits focused. `git diff` and `git status` must show only your task's work before handoff.

Full branching and PR conventions: `docs/git-workflow.md`.

---

## 7. The development log

Every task keeps a running log at `logs/task-NN-<slug>.md` using the template in
`docs/development-log-template.md`. Update it as you go, not at the end. When the next contributor
or the next AI session picks up your area, this log — not your memory — is what they read.

---

## 8. When you are stuck or uncertain

Say so plainly and stop. The correct behaviour on encountering an ambiguity is:

> "`docs/X.md` says A, but `docs/Y.md` implies B. I have not implemented either. Which is correct?"

The incorrect behaviour is picking one, implementing it, and mentioning it in passing at the end.
A five-minute question to the project lead costs less than an integration failure discovered during
the demo.

---

## 9. The honesty standard, stated once more

This project's entire credibility — technically and in front of judges — rests on it describing
itself accurately. A demo that says "matched our synthetic demo reference, here is exactly why" is
stronger than one that says "VERIFIED ✓" and cannot explain itself.

Every overclaim you remove makes the project better. Every overclaim you add makes it worse, no
matter how impressive it looks in a screenshot.
