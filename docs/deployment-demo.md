# Local Deployment and Demo Choreography

## Deployment target

Local development/demo machine only. No public deployment, no cloud hosting, no production
authentication — this is explicit (`security-privacy.md`).

## Startup order (each in its own terminal)

```bash
# terminal 1 — local chain
cd chain && npx hardhat node

# terminal 2 — deploy contract (one-time per chain restart)
cd chain && npx hardhat run scripts/deploy.js --network localhost
# copy printed address into backend/.env BLOCKCHAIN_CONTRACT_ADDRESS if it changed

# terminal 3 — backend
cd backend && python -m app.fixtures.seed_registry   # only if data/app.db is fresh
cd backend && uvicorn app.main:app --reload --port 8000

# terminal 4 — frontend
cd frontend && npm run dev
```

Confirm `GET /api/v1/health` returns `"status": "ok"` before starting the demo.

## Demo script (rehearse this exact sequence)

1. **Open with the disclaimer:** "Every registry record and document you'll see is synthetic —
   fictional names, fictional IDs. This demonstrates the workflow, not a connection to any real
   government database." (See `problem-statement-mapping.md` for backup talking points if asked
   about the AI/ML or forgery-detection clauses.)
2. **Matching fixture:** upload `academic_certificate_match.png` → show extracted fields → run
   verify → show `VERIFIED_MATCH` with the field-by-field comparison table.
3. **Mismatching fixture:** upload `academic_certificate_mismatch.png` → show `INTEGRITY_MISMATCH`
   with the exact field/reason called out.
4. **No-record fixture:** upload a document from a category/key with no seeded registry entry →
   show `NO_TRUSTED_RECORD` and say explicitly: "this does not mean forged — it means we have no
   reference to compare against."
5. **Review flow:** upload a deliberately degraded/low-confidence scan → show `REVIEW_REQUIRED` →
   walk through the reviewer correcting a field → show the new `VERIFIED_MATCH` (or whatever the
   corrected outcome is) plus the fact that the original OCR value is still visible in history.
6. **Blockchain receipt:** show the confirmed transaction hash/chain ID for one of the above → state
   plainly what it proves ("our app recorded this outcome, unmodified, at this time") and what it
   does not ("it does not prove the registry itself is authoritative").
7. **Resilience moment (optional but strong):** stop the Hardhat node (`Ctrl+C` in terminal 1),
   upload one more fixture, verify → show the verification result completing normally while the
   blockchain status shows `FAILED`/`PENDING` — this directly demonstrates the "chain outage never
   changes verification status" invariant from `requirements.md`.

## Reset between rehearsals

```bash
# stop all four terminals, then:
rm backend/data/app.db          # or del on Windows
rm -rf backend/data/uploads/*
cd backend && python -m app.fixtures.seed_registry
# restart hardhat node + redeploy contract + update BLOCKCHAIN_CONTRACT_ADDRESS if it changed
```
Local chain history is lost on Hardhat restart — this is expected and fine for a demo; document it
if a judge asks why the chain "resets."

## Presenter wording (say this, not the alternative)

| Say | Don't say |
|---|---|
| "Matched our synthetic demo reference" | "Verified" / "Authentic" |
| "No matching reference found — not evidence of forgery" | "Could not verify" (implies suspicion) |
| "Our application recorded this outcome on a tamper-evident local ledger" | "Blockchain verified" / "Government verified" |
| "This is a hackathon MVP demonstrating the workflow" | "This is production-ready" |
