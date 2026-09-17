# Configuration

All configuration is environment variables, loaded and validated at startup by
`backend/app/config.py` into a typed `Settings` object. `.env` is never committed; `.env.example`
lists every variable with a safe default or placeholder. Fail fast — an invalid/missing required
value must stop the app at startup with a clear message, never a runtime surprise mid-demo.

## Backend (`.env.example`)

```env
# App
APP_ENV=development                 # development | test | demo
API_HOST=127.0.0.1
API_PORT=8000

# Database
DATABASE_URL=sqlite:///./data/app.db

# Uploads
UPLOAD_DIR=./data/uploads
MAX_UPLOAD_MB=10
MAX_PDF_PAGES=5
ALLOWED_MIME_TYPES=image/jpeg,image/png,application/pdf

# OCR
OCR_ENGINE=paddleocr
OCR_LANGUAGE=en
OCR_TIMEOUT_SECONDS=30
LOW_CONFIDENCE_THRESHOLD=0.70

# Registry
REGISTRY_MODE=synthetic_demo        # only value supported in MVP

# Blockchain
BLOCKCHAIN_ENABLED=true
BLOCKCHAIN_RPC_URL=http://127.0.0.1:8545
BLOCKCHAIN_CHAIN_ID=31337
BLOCKCHAIN_CONTRACT_ADDRESS=        # filled in after `chain/scripts/deploy.js` runs
BLOCKCHAIN_TX_TIMEOUT_SECONDS=30
BLOCKCHAIN_MAX_RETRIES=2
CHAIN_EVENT_SALT=                   # generate once with: python -c "import secrets; print(secrets.token_hex(32))"

# Retention
RETENTION_DAYS=7

# Logging
LOG_LEVEL=INFO
```

## Frontend (`frontend/.env.example`)

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## Rules

- `config.py` validates: `MAX_UPLOAD_MB > 0`, `MAX_PDF_PAGES > 0`, `ALLOWED_MIME_TYPES` non-empty,
  `LOW_CONFIDENCE_THRESHOLD` in `(0, 1)`, and — if `BLOCKCHAIN_ENABLED=true` — that
  `BLOCKCHAIN_RPC_URL`, `BLOCKCHAIN_CONTRACT_ADDRESS`, and `CHAIN_EVENT_SALT` are all non-empty.
- If `BLOCKCHAIN_ENABLED=true` but the contract address is missing, the app must refuse to start
  with a specific error — never silently fall back to `BLOCKCHAIN_ENABLED=false` or fake a
  `CONFIRMED` result.
- Tests inject their own temporary `DATABASE_URL` (a temp SQLite file or `:memory:`), a temp
  `UPLOAD_DIR`, `fake_adapter` OCR/blockchain implementations, and a throwaway `CHAIN_EVENT_SALT` —
  never the developer's real `.env`.
- No third-party paid API key exists in this list, matching `requirements.md` NFR-01.
- Any new configuration key must be added here, to `.env.example`, and to the validation list in
  the same PR — do not introduce an env var read directly in code without documenting it here first.
