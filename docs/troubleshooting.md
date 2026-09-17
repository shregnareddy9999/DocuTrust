# Troubleshooting

Known failure modes, ordered roughly by how often they bite hackathon teams. Check here before
spending an hour on something that has a one-line fix.

**Rule for this file:** when you hit a problem not listed here and solve it, add it. The version of
you that hits it again at 2 a.m. the night before the demo will be grateful.

---

## 1. Environment and install

### PaddleOCR / PaddlePaddle will not install

By far the most common blocker on this stack.

- Check your Python version first. PaddlePaddle's wheel availability lags new Python releases —
  Python 3.11 is the safe target for this project. Python 3.13 frequently has no wheel yet.
- On Windows, install `paddlepaddle` (CPU) **before** `paddleocr`, and install it from the official
  index rather than letting pip resolve it transitively.
- If a wheel genuinely does not exist for a teammate's machine, that teammate can still do almost
  all of Tasks 05–06 against `fake_adapter.py` — the default test suite never needs a real
  PaddleOCR run (`AGENTS.md` Rule 11). Do not block the whole team on one laptop.
- Record whatever combination works in `logs/task-01-foundation.md` and pin it in
  `requirements.txt`. Do not leave the next person to rediscover it.

### PaddleOCR tries to download models on first run

Expected — it fetches detection/recognition weights on first use. Run it once, online, during
setup, before demo day. Then verify the default test suite still passes with networking off, which
it will, because the default suite uses the fake adapter.

### Hardhat / Node issues

- Use an LTS Node version. Hardhat is sensitive to very new Node releases.
- On Windows, run Hardhat from a normal terminal, not an unusual shell wrapper; path-separator
  issues in config resolution are a recurring time sink.
- `npx hardhat node` must stay running in its own terminal for the whole demo. Closing that terminal
  wipes chain state.

### `pip install` succeeds but imports fail at startup

Usually a virtual environment that isn't actually activated. Confirm with `which python` /
`where python` and check it points inside your venv, not the system interpreter.

---

## 2. Backend startup

### App refuses to start with a configuration error

That is working as designed (`configuration.md` — fail fast). Read the message; it names the
variable. The usual culprits:

- `BLOCKCHAIN_ENABLED=true` with an empty `BLOCKCHAIN_CONTRACT_ADDRESS` — you have not run
  `chain/scripts/deploy.js` yet this session, or you did and forgot to paste the address back into
  `.env`.
- Empty `CHAIN_EVENT_SALT` — generate one:
  `python -c "import secrets; print(secrets.token_hex(32))"`.
- `LOW_CONFIDENCE_THRESHOLD` outside `(0, 1)`.

The app must never quietly fall back to `BLOCKCHAIN_ENABLED=false` to get past this. If you find
code doing that, it is a bug — it would let a demo silently run without the chain layer.

### `data/app.db` does not exist / tables missing

`Base.metadata.create_all()` runs at startup (`backend.md`). If the file is missing, the `data/`
directory probably does not exist or is not writable. Create it and restart.

### Schema changed and now queries fail

There is no migration tool at MVP scale. During development, delete `data/app.db`, restart to
recreate tables, and re-run the seed script. Never do this without telling the team — everyone
loses their local demo state.

---

## 3. Upload and OCR

### Every upload returns `415 UNSUPPORTED_MEDIA_TYPE`

Check `ALLOWED_MIME_TYPES` in `.env` against what the browser is actually sending. Also confirm
you are validating the **sniffed** signature, not the client-declared header — a mismatch between
those two is a legitimate rejection, and the error message should say which check failed.

### `422 EMPTY_OR_CORRUPT_FILE` on a file that opens fine locally

Usually an encrypted or password-protected PDF. These are rejected by design; we do not prompt for
a password (`document-processing.md`). Re-export the fixture without encryption.

### OCR returns nothing at all

`status: SUCCEEDED` with `no_text_detected` is a legitimate outcome, not a crash
(`document-processing.md`). If it happens on a fixture that should work:

- Check the rendered page image, not the PDF. Write the preprocessed image to disk temporarily and
  look at it. Nine times out of ten the PDF rendered blank, upside down, or at a useless resolution.
- Check the language setting. `OCR_LANGUAGE=en` only; non-Latin script will not be read.
- Check preprocessing hasn't over-thresholded the image into solid white.

### OCR reads text but extraction returns all `null`

The OCR worked; the **mapping** in `extraction_service.py` is not finding your labels. Compare the
raw `OcrResult` text against the label patterns the mapper looks for. Fixture documents and mapper
expectations drifting apart is the single most common Task 06 bug — keep them in sync, and keep a
test that asserts the fixture maps cleanly.

### OCR is slow enough to stall the demo

Expected range is a few seconds per page on CPU. If it is much worse:

- Lower the render resolution (cap long edge at 2000px, per `document-processing.md`).
- Reduce `MAX_PDF_PAGES` for demo fixtures — a one-page fixture is fine for the stage.
- Do **not** fix this by removing the loading state. `frontend.md` requires one.

---

## 4. Verification results

### A fixture that should match returns `NO_TRUSTED_RECORD`

`NO_TRUSTED_RECORD` means no registry record shares the **identifying key**. So:

1. Did the seed script actually run? Check `registry_records` has rows.
2. Is the record `active = true`?
3. Is the extracted identifying key exactly right? `DEMO-STU-OO1` (letter O) versus `DEMO-STU-001`
   (zero) is the classic OCR failure, and it is exactly the failure the review flow exists to
   demonstrate. Consider showing it deliberately instead of fixing it.

### A fixture that should match returns `INTEGRITY_MISMATCH`

Good news: matching found the reference record, so the key is right. One match field disagrees —
the response names it. Compare the extracted value against the fixture. Usually whitespace, casing,
or a trailing character that normalization is not meant to strip.

Do **not** widen the normalization rules to force the match. That is explicitly forbidden
(`AGENTS.md` Rule 8 / `workflow.md` Stage 5). Fix the fixture or fix the mapper.

### Everything returns `REVIEW_REQUIRED`

Your `LOW_CONFIDENCE_THRESHOLD` (default `0.70`) is being crossed, or a required field is missing.
Check the extraction response's `warnings` array — it tells you which. Raising the threshold to make
this go away is hiding a real extraction problem.

### Status looks wrong and you are not sure which rule won

Check the precedence order in `verification-rules.md`. The first matching condition wins, and
failure beats review beats no-record beats mismatch beats match. If your expectation disagrees with
that order, your expectation is what needs updating.

---

## 5. Blockchain

### `recording_status` stuck at `PENDING`

The transaction was submitted but no receipt arrived within `BLOCKCHAIN_TX_TIMEOUT_SECONDS`.
Check the Hardhat node terminal is still running and shows the transaction. If the node was
restarted, its state is gone and the contract address in `.env` is stale.

### `recording_status: FAILED` but verification status is fine

That is correct behaviour, not a bug (`blockchain.md`). Chain failure never changes a verification
result. If you see a verification status change because the chain went down, **that** is the bug.

### Contract address invalid after restarting the node

Hardhat local network state resets on restart. Re-run `chain/scripts/deploy.js`, copy the new
address into `.env`, restart the backend. Follow the exact order in `deployment-demo.md` — this is
why that file specifies a startup sequence rather than a list of services.

### Transaction reverts

The contract has one function and no `require` statements, so a genuine revert is almost always a
malformed argument — usually a `bytes32` that was passed as a plain string instead of being
`keccak256`-hashed first.

---

## 6. Frontend

### CORS errors in the browser console

Add the frontend origin to the FastAPI CORS middleware in `main.py`. Note that
`http://localhost:5173` and `http://127.0.0.1:5173` are *different* origins — allow whichever the
browser actually shows in the address bar.

### Category form renders with no fields

The frontend must render fields from `GET /document-types` (`frontend.md`, hard rule). An empty
form means that call failed or returned an empty array. Check the network tab. Do **not** fix it by
hardcoding the field list — that breaks the single-source-of-truth guarantee and will silently
diverge from the backend.

### Status badge shows a raw enum string

`StatusBadge.tsx` is the only place status-to-label mapping lives. A raw `INTEGRITY_MISMATCH` on
screen means something bypassed it.

### Page is blank while OCR runs

A missing loading state. `frontend.md` treats this as a bug, not an acceptable gap — a judge
watching a blank white screen for eight seconds assumes the app crashed.

---

## 7. Demo-day emergencies

Work through these in order. Do not improvise a new startup sequence under pressure.

| Symptom | First response |
|---|---|
| Chain node died mid-demo | Keep going. Verification still works; the blockchain badge shows `FAILED`. Say out loud that this is deliberate isolation — it is a *feature*, and judges notice. |
| Backend won't start | Check `.env` against `.env.example`; the error message names the variable. |
| OCR hangs on a live-uploaded file | Switch to a known fixture. Live uploads from unknown sources are not the demo; the rehearsed fixtures are. |
| A fixture stopped matching | Re-run the seed script. Local DB state drifts after a day of testing. |
| Frontend shows stale data | Hard refresh. Vite dev-server caching, not a backend bug. |
| Everything is broken and time is short | Run the backend only and walk through `api-manual-testing-guide.md` with curl. It demonstrates the entire pipeline without the frontend. |

**Before the demo, always:** fresh `data/app.db`, re-run seed, redeploy contract, paste the new
address, restart backend, restart frontend, and do one full rehearsal pass. `deployment-demo.md`
has the exact sequence. Doing this once, an hour before, prevents nearly every item on this page.
