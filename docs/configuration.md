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

# AI Academic Summary
AI_SUMMARY_OLLAMA_URL=http://127.0.0.1:11434
AI_SUMMARY_MODEL=llama3.2:latest
AI_SUMMARY_TIMEOUT_SECONDS=60

# Supabase account deletion
SUPABASE_URL=                       # backend-only Supabase project URL
SUPABASE_SERVICE_ROLE_KEY=          # backend-only; never expose through Vite

# Aadhaar Link messaging
AADHAAR_MESSAGING_ENABLED=false     # real sending is opt-in; false by default
AADHAAR_MESSAGING_PROVIDER=twilio   # twilio for runtime, fake for automated tests only
AADHAAR_MESSAGE_MAX_CHARS=320
AADHAAR_MESSAGE_RATE_LIMIT_SECONDS=30
TWILIO_ACCOUNT_SID=                  # backend-only; never expose to frontend
TWILIO_AUTH_TOKEN=                   # backend-only; never expose to frontend
TWILIO_PHONE_NUMBER=                 # backend-only Twilio sender/caller number in E.164 format

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
VITE_SUPABASE_URL=
VITE_SUPABASE_PUBLISHABLE_KEY=
```

## Rules

- `config.py` validates: `MAX_UPLOAD_MB > 0`, `MAX_PDF_PAGES > 0`, `ALLOWED_MIME_TYPES` non-empty,
  `LOW_CONFIDENCE_THRESHOLD` in `(0, 1)`, `AI_SUMMARY_TIMEOUT_SECONDS > 0`, and — if `BLOCKCHAIN_ENABLED=true` — that
  `BLOCKCHAIN_RPC_URL`, `BLOCKCHAIN_CONTRACT_ADDRESS`, and `CHAIN_EVENT_SALT` are all non-empty.
- If `BLOCKCHAIN_ENABLED=true` but the contract address is missing, the app must refuse to start
  with a specific error — never silently fall back to `BLOCKCHAIN_ENABLED=false` or fake a
  `CONFIRMED` result.
- Aadhaar Link messaging is disabled unless `AADHAAR_MESSAGING_ENABLED=true`. Runtime sending uses
  `AADHAAR_MESSAGING_PROVIDER=twilio`; automated tests set `fake` and must never contact Twilio.
  Duplicate/rate safeguards are in-memory for the demo and reset on backend restart.
- Twilio credentials are backend-only. They must never be exposed through frontend `VITE_`
  variables, API responses, or logs. Before enabling real sending, confirm the Twilio account,
  sender number, recipient number, geographic permissions, and India SMS/voice requirements allow
  the requested traffic.
- Tests inject their own temporary `DATABASE_URL` (a temp SQLite file or `:memory:`), a temp
  `UPLOAD_DIR`, `fake_adapter` OCR/blockchain implementations, and a throwaway `CHAIN_EVENT_SALT` —
  never the developer's real `.env`.
- No third-party paid API key exists in this list, matching `requirements.md` NFR-01.
- Any new configuration key must be added here, to `.env.example`, and to the validation list in
  the same PR — do not introduce an env var read directly in code without documenting it here first.
