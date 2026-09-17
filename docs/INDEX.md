# PS21 Documentation Index

Read in this order. Items marked **contract** are locked — changing one needs project-lead approval
and a doc update in the same pull request as the code change.

## Start here

1. [AGENTS](AGENTS.md) — the hard rules; read before anything else
2. [AI-CONTEXT](AI-CONTEXT.md) — whole project in one file
3. [README](README.md) — documentation map

## Understand the problem

4. [project-context](project-context.md) — scope, users, limitations
5. [problem-statement-mapping](problem-statement-mapping.md) — statement vs. what we built, and why
6. [requirements](requirements.md) — FR/NFR and system-level acceptance criteria
7. [glossary](glossary.md) — shared vocabulary, and banned words

## Understand the system

8. [architecture](architecture.md) — layers, dependency direction, failure isolation
9. [workflow](workflow.md) — the 10 stages end to end, narratively
10. [backend](backend.md) — locked backend folder structure
11. [frontend](frontend.md) — locked frontend folder structure
11b. [repo-structure](repo-structure.md) — the exact tree to scaffold before Task 01, plus `.gitignore`

## The locked contracts

12. [data-model](data-model.md) — **contract** — 6 entities, relationships, retention
13. [category-schemas](category-schemas.md) — **contract** — fields + fixtures for 4 categories
14. [api](api.md) — **contract** — every endpoint's request/response schema
15. [document-processing](document-processing.md) — **contract** — upload validation, OCR pipeline
16. [verification-rules](verification-rules.md) — **contract** — matching, rules, status precedence
17. [blockchain](blockchain.md) — **contract** — contract shape, digest, chain states
18. [configuration](configuration.md) — **contract** — every environment variable
19. [security-privacy](security-privacy.md) — threat model and safeguards

## Build and run

20. [setup](setup.md) — developer environment, step by step
21. [testing](testing.md) — test layers, required scenarios, commands
22. [api-manual-testing-guide](api-manual-testing-guide.md) — curl walkthrough, no frontend needed
23. [deployment-demo](deployment-demo.md) — startup order and the rehearsed demo script
24. [troubleshooting](troubleshooting.md) — when it breaks
25. [git-workflow](git-workflow.md) — branches, commits, PRs
26. [development-log-template](development-log-template.md) — the `logs/` format

## Plan and present

27. [implementation-plan](implementation-plan.md) — 12 tasks, dependency graph, allocation
28. [decisions](decisions.md) — full decision log (D-01 … D-18)
29. [judging-and-pitch](judging-and-pitch.md) — demo narrative and hard-question answers

## Tasks

Work orders live in [`../tasks/`](../tasks/). Start with
[`../tasks/00-HOW-TO-USE-TASKS.md`](../tasks/00-HOW-TO-USE-TASKS.md), then the index at
[`../tasks/ALL-TASKS.md`](../tasks/ALL-TASKS.md).
