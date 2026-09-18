| Machine | OS | Python | Node | paddlepaddle | paddleocr | OCR smoke | Hardhat | compile | vite build | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| Lead's laptop | Windows 11 | 3.14.6 | 24.16.0 | ❌ No wheel for Python 3.14 | 3.7.0 ⚠️ (imports but fails at runtime) | ❌ RuntimeError: Engine 'paddle_static' unavailable - paddlepaddle not installed | 3.17.0 ✅ | ⚠️ Config stub only (Task 09) | ✅ | Demo machine candidate - Python version too new for PaddlePaddle |

## Pinned Versions

| Package | Version | Notes |
|---|---|---|
| Python | 3.11.x | **Required** - Python 3.14 has no PaddlePaddle wheel. Team must use 3.11.x for real OCR. |
| Node.js | 20.x LTS | Current 24.16.0 works for Vite/Hardhat, recommend pinning to 20.x LTS |
| fastapi | 0.115.0 | Pinned in requirements.txt |
| uvicorn | 0.30.6 | Pinned in requirements.txt |
| sqlalchemy | 2.0.32 | Pinned in requirements.txt |
| pydantic | 2.8.2 | Pinned in requirements.txt |
| pydantic-settings | 2.4.0 | Pinned in requirements.txt |
| pytest | 8.3.2 | Pinned in requirements.txt |
| httpx | 0.27.2 | Pinned in requirements.txt |
| react | 18.x | In package.json |
| vite | 8.3.0 | In package.json |
| hardhat | 3.17.0 | For Task 09; local install required in chain/ |

## Detailed Findings

### PaddlePaddle / PaddleOCR
- **Python 3.14.6**: No PaddlePaddle wheel available on PyPI. `pip install paddlepaddle` fails with "No matching distribution found".
- **PaddleOCR 3.7.0**: Installs and imports successfully, but fails at runtime with `RuntimeError: Engine 'paddle_static' unavailable because dependency 'paddlepaddle' is not installed` because PaddleOCR 3.x uses PaddleX which requires the actual `paddlepaddle` package.
- **Recommendation**: Team must use Python 3.11.x for real OCR. This machine (Python 3.14) cannot run real PaddleOCR and must work against `fake_adapter.py` only (per AGENTS.md Rule 11).
- **Demo machine**: Must be a machine with Python 3.11.x where PaddlePaddle installs and OCR smoke test passes.

### Hardhat
- **Hardhat 3.17.0**: `npx hardhat --version` works ✅
- **Compile**: Requires local `npm install hardhat` in `chain/` and `"type": "module"` in package.json. Config file is a stub (owned by Task 09).
- **Node**: Works from plain terminal.

### Vite / Frontend
- **npm run dev**: Serves frontend ✅
- **npm run build**: Production build succeeds ✅

### Backend Tests
- **pytest**: 18/18 tests pass ✅ (test_config.py: 11, test_health.py: 7)

## Recommendation

1. **Pin Python to 3.11.x** for all team members who need to run real OCR. This is a hard requirement from `docs/decisions.md` D-02.
2. **Demo machine must have Python 3.11.x** with working PaddlePaddle/PaddleOCR.
3. Team members on Python 3.12+ without PaddlePaddle wheels must develop against `fake_adapter.py` (architecture supports this by design).
4. Report D-02 (PaddleOCR), D-05 (Hardhat), D-09 (Node) back to project lead for promotion from "Accepted — verify environment" to plain "Accepted" with pinned versions recorded.

## Windows-Specific Checks

| Check | Result | Notes |
|---|---|---|
| PaddlePaddle wheel for installed Python | ❌ | No wheel for Python 3.14 |
| `import paddleocr` without DLL error | ⚠️ | Imports but fails at pipeline creation due to missing paddlepaddle |
| First-run model weight download | N/A | Could not test - pipeline creation fails |
| Second run (no re-download) | N/A | Could not test |
| Thread-based timeout works | N/A | Could not test OCR |
| Long-path support (node_modules) | ✅ | Vite build succeeds, path length OK |
| `npx hardhat node` from plain terminal | ⚠️ | Requires local install + ESM config; config is Task 09 stub |

## Demo Machine Designation

**This machine (Lead's laptop, Python 3.14) is NOT suitable as demo machine** for real OCR.
A demo machine with Python 3.11.x must be identified and verified before the hackathon.