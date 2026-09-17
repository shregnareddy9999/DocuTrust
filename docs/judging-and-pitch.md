# Judging and Pitch Guide

For the project lead and whoever presents. This maps what the team built to what judges actually
score, and gives tested answers to the questions this specific project attracts.

`deployment-demo.md` covers the mechanical run order. This file covers what you *say*.

---

## 1. The core strategic bet

Most teams attacking a "detect forged documents with AI + blockchain" statement will demo a green
**VERIFIED ✓** badge and hope nobody asks what it was checked against. When a judge asks, the
answer is usually some version of "we have a sample database" delivered uncomfortably, and the score
drops — not because the build was bad, but because the team looked like it did not understand its
own limits.

PS21 takes the opposite position: **be the team that states its limits before the judge finds
them.** Every honest boundary is documented, visible in the UI, and said out loud in the demo.

This works because it is genuinely the more sophisticated engineering position, and judges with
real domain experience recognise it immediately. It converts your biggest weakness — no access to
real government data — from something to survive into something you look deliberate about.

It only works if the build is actually solid underneath. Honesty about limits is a multiplier on
real work, not a substitute for it.

---

## 2. Typical criteria, and where your evidence lives

Weightings vary by event. Map these to your actual rubric before the presentation.

| Criterion | What judges look for | Your evidence |
|---|---|---|
| **Problem understanding** | Do they know why this is hard? | `problem-statement-mapping.md` — line-by-line mapping of the statement to what is built, simplified, or deferred, with reasons |
| **Technical depth** | Real architecture or a demo shell? | Layered backend with enforced dependency direction; swappable adapters; deterministic pure-function domain; a test suite that runs with zero external dependencies |
| **Working demo** | Does it run, reliably, live? | Five rehearsed scenarios covering match, mismatch, no-record, review-and-correct, and chain receipt |
| **Innovation** | Is anything here non-obvious? | Explainable field-level comparison instead of an opaque score; failure isolation between verification and chain layers; corrections that create new records instead of overwriting |
| **Completeness** | End-to-end, or one impressive slice? | Upload → OCR → extract → match → rules → review → chain → dashboard, all working |
| **Security / privacy** | Was this considered or bolted on? | `security-privacy.md`; nothing personal on-chain by construction; content-based upload validation; documented retention |
| **Scalability / production path** | Do they know what real deployment needs? | Every simplification is logged in `decisions.md` with what production would require instead |
| **Presentation** | Can they explain it clearly? | The wording table below |

---

## 3. The demo narrative (five minutes)

**Minute 1 — Frame the real problem.**
Government departments verify high volumes of documents by hand. It is slow, it does not scale, and
forged submissions get through. Say what makes it genuinely hard: verification requires a trusted
reference to check against, and that reference has to be one you are actually authorised to query.

**Minute 2 — State your boundary immediately.**
"We have no authorised access to a government registry, so we built against a clearly labelled
synthetic one. Everything else in the pipeline is exactly what you would deploy against a real
registry — swap the registry adapter, the rest is unchanged."

Doing this in minute two, unprompted, is the single highest-value thirty seconds of the pitch. It
disarms the obvious attack and signals that you understand the domain.

**Minute 3 — Run the happy path.**
Upload the matching academic certificate. Show extracted fields with per-field confidence, the
field-by-field comparison table, and the status. Say: *"matched our synthetic demo reference"* —
never "verified."

**Minute 4 — Run the interesting paths.** This is where you win.
- **Mismatch:** upload the deliberately wrong fixture. The system names the exact field, expected
  versus observed. Contrast with a system that just says "suspicious."
- **No record:** upload the unregistered fixture. Show that the UI explicitly says this is *not*
  evidence of forgery. Explain why conflating those two is a real-world harm — a citizen with a
  genuine document that simply is not in the registry should not be flagged as a fraudster.
- **Review:** upload the degraded scan. Show `REVIEW_REQUIRED`, correct the OCR error, show that the
  original value is preserved and a **new** verification record is created. Audit trails that can be
  edited are not audit trails.

**Minute 5 — Blockchain, honestly.**
Show the transaction and the receipt. Say precisely what it proves: *"this records that our system
reached this outcome at this time, and that record cannot be silently altered. It does not prove the
document is genuine, and it does not make our registry authoritative."*

Then show the payload and point out there is no personal data in it — three values, one of them an
opaque digest. Privacy by construction, not by policy.

**Optional closer, if the room is technical:** kill the chain node and re-run a verification. It
still completes; only the blockchain badge changes to `FAILED`. Failure isolation as a live demo
lands harder than any slide about it.

---

## 4. Wording that must not slip

Rehearse these. Under stage pressure people revert to the shorter, wronger phrase.

| Never say | Always say |
|---|---|
| "Verified" / "Authentic" / "Genuine" | "Matched our synthetic demo reference" |
| "Government verified" | "Matched the demo registry we seeded" |
| "We detect forged documents" | "We detect mismatches against a trusted reference, and we report exactly which field disagreed" |
| "Blockchain-verified document" | "The verification outcome is recorded on-chain and cannot be silently altered" |
| "AI decides if it is fake" | "Deterministic rules compare fields; a human reviews anything uncertain" |
| "99% accurate" | "OCR confidence per field — which measures character recognition, not authenticity" |
| "No record means it's fake" | "No record means we have no reference to check against — that is not evidence of anything" |

---

## 5. Hard questions, with answers

**"So it only works against fake data?"**
The pipeline works against any registry exposed through the same interface. The registry sits behind
`registry_repo.py`, so swapping a synthetic table for a real API is one adapter. What we cannot do
is obtain authorisation for a real government registry in a hackathon — and building against a real
one without authorisation would be the wrong thing to do regardless of feasibility.

**"Where is the AI? This looks like string comparison."**
OCR is the ML component and it does the genuinely hard part — reading degraded scans. We
deliberately did not add a fraud classifier, and that is a considered decision, not a gap. A
classifier trained on the handful of synthetic samples we could generate would produce a
confident-looking number with nothing behind it. For a system that can affect whether someone's
certificate is accepted, an unexplainable score is worse than no score. Our decision log records
exactly what we would need before adding one: a real labelled corpus, and a human-review path that
the model cannot bypass.

**"Why blockchain at all? A database with an audit log does the same thing."**
For a single trusted operator, largely yes — and we should be honest about that. Blockchain earns
its place when multiple mutually distrusting parties need to agree that a record was not altered
after the fact: the issuing institution, the verifying department, and the citizen. We use a local
chain because a public one adds cost and latency without changing what the demo proves.

**"Are you putting a hash of the document on the blockchain?"**
No, deliberately. What we record binds the verification *outcome*, not the document. Hashing the
document would look like proof of authenticity and provide none — a hash of a file someone hands you
proves only that you received that file, since we have no trusted digest from the issuer to compare
against. It would also be actively harmful to privacy: a document digest on a permanent public
ledger is a confirmation oracle, letting anyone holding a candidate file test whether that exact
document passed through our system. Real document integrity needs the issuer to publish a signed
digest at issuance, and the chain to anchor *their* commitment rather than ours.

**"What stops someone uploading a photoshopped certificate that matches the registry?"**
Nothing in this system, and we do not claim otherwise. Field matching checks that the *content*
agrees with a trusted reference. It does not check the *artifact*. Detecting pixel-level
manipulation is image forensics — a different discipline, explicitly out of scope, and listed in our
deferred work. What our approach does catch is the far more common case: fabricated or altered
*values* that no trusted record supports.

**"How does this scale to millions of documents?"**
The processing path is stateless per document, so it scales horizontally. The honest constraints
are CPU-bound OCR — which is why real deployment would move it to a worker queue with GPU inference
instead of running synchronously as we do for demo predictability — and the registry lookup, which
becomes a network call subject to the real registry's rate limits. Both are in `decisions.md` as
known MVP simplifications with named production alternatives.

**"What if OCR reads a character wrong and rejects a genuine document?"**
That is the specific failure we designed the review path around, and we demo it deliberately. Below
the confidence threshold, the system refuses to conclude anything and routes to a human. The
reviewer's correction is stored alongside the original — never replacing it — and the rules re-run
unchanged. The system never quietly decides on a value it could not read.

**"Is any of this actually secure?"**
Parts are, parts are explicitly not, and we have written down which is which. Upload validation is
content-based, uploads live outside any public route, nothing personal reaches the chain, and
retention is bounded. There is no authentication, no encryption at rest, and no key management —
all documented as MVP-only, none of it production-acceptable. We would rather show you that list
than have you find it.

---

## 6. Presentation checklist

**Twenty-four hours before**
- [ ] Full rehearsal from a clean checkout, following `deployment-demo.md` exactly
- [ ] All five scenarios pass end to end
- [ ] Screen recording of a successful run saved as a fallback
- [ ] Screenshots of each key screen saved, in case the laptop dies
- [ ] Every presenter has read the wording table in §4

**One hour before**
- [ ] Fresh `data/app.db`, seed re-run
- [ ] Contract redeployed, new address in `.env`
- [ ] Backend, frontend, and Hardhat node all running in their own terminals
- [ ] One full silent pass, no talking, just clicking
- [ ] Fixture files pre-staged in an obvious folder — no hunting for a file on stage
- [ ] Browser zoom set for projector legibility, console closed

**During**
- [ ] State the synthetic-registry boundary in the first ninety seconds
- [ ] Never say "verified" without "matched our synthetic demo reference"
- [ ] Show at least one failure path — that is where the differentiation is
- [ ] If something breaks, say what broke and move to the next scenario. Composure scores; panic
      does not.

---

## 7. What to put on slides

Keep it to five.

1. **The problem** — manual verification, at government volume, with real fraud exposure
2. **Our boundary** — synthetic registry, and why that is a sourcing constraint rather than a
   design one
3. **Architecture** — the diagram from `architecture.md`
4. **The six statuses** — with the point that "no record" and "mismatch" are deliberately different
5. **What production needs** — the deferred list from `decisions.md`

Slide 5 is unusual and it is the one judges remember. Most teams end on "future scope" as vague
ambition. Ending on a specific, technically literate list of what you deliberately did not build,
and what you would need to build it properly, reads as engineering maturity rather than hedging.
