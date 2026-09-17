# Developer Setup

## Before installing (Task 01 does this once, for the whole team)

Confirm on the actual development machines (Windows and macOS/Linux, since the team is mixed):
Python version (3.11+ target), Node.js LTS version, npm version, Git version. Confirm the installed
Python version and OS/architecture actually have working `paddlepaddle`/`paddleocr` wheels available
**before** pinning versions in `backend/requirements.txt` — this is the single most likely
environment blocker and must be checked first, not assumed.

## Setup steps

1. Clone the repository; create your task's feature branch (`git-workflow.md`).
2. Backend:
   ```bash
   cd backend
   python -m venv .venv
   # Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   ```
3. Frontend:
   ```bash
   cd frontend
   npm install
   cp .env.example .env
   ```
4. Blockchain (only needed for tasks touching chain integration, or full end-to-end demo):
   ```bash
   cd chain
   npm install
   npx hardhat node                       # keep running in its own terminal
   npx hardhat run scripts/deploy.js --network localhost
   # copy the printed contract address into backend/.env BLOCKCHAIN_CONTRACT_ADDRESS
   ```
5. Generate a local `CHAIN_EVENT_SALT` and put it in `backend/.env`:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
6. Initialize the database and seed synthetic fixtures:
   ```bash
   cd backend
   python -m app.fixtures.seed_registry
   ```
7. Start the backend:
   ```bash
   cd backend && uvicorn app.main:app --reload --port 8000
   ```
8. Start the frontend:
   ```bash
   cd frontend && npm run dev
   ```
9. Verify: open `http://127.0.0.1:8000/api/v1/health` and the Vite dev server URL; both should load.
10. Run tests:
    ```bash
    cd backend && pytest
    cd frontend && npm test
    ```

## Windows notes

Use PowerShell for all commands above (the activation command differs, shown inline). Do not
introduce bash-only syntax into any committed script — either provide both, or use a
cross-platform tool (Python script) instead of a shell script for anything beyond the commands
above.

## PaddleOCR first run

The first `paddleocr` import downloads model weights (a few hundred MB) — this requires internet
once, during setup, and should be done **before** running tests offline. If a teammate's machine
cannot download the weights, flag it immediately as an environment blocker per `AI-CONTEXT.md`
rather than silently skipping OCR tests.

## Acceptance

A new teammate, following this file exactly on a clean, supported machine, can seed the same demo
data, run both test suites, and reproduce the full upload → verify → review → blockchain-receipt
flow from `deployment-demo.md`, without any third-party paid API credentials.
