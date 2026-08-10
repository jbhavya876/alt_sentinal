# AlterBlock Sentinel

AlterBlock Sentinel is a payment-safety layer for x402 payments on Algorand. Before a user signs a payment in Pera Wallet, the frontend retrieves the x402 payment requirements and asks Sentinel to assess the recipient, network, asset, and amount. Sentinel returns an `ALLOW`, `REVIEW`, or `BLOCK` decision.

## Project layout

- `server.py` — FastAPI API, x402 payment middleware, and protected routes.
- `sentinel/` — payment rules and Algorand Indexer helpers.
- `frontend/` — React/Vite app with Pera Wallet and x402 client integration.

## Prerequisites

- Python 3.10 or later
- Node.js 20 or later and pnpm
- A Pera Wallet account on Algorand TestNet

## Configure the backend

Copy the root environment template and set the receiving Algorand TestNet address:

```bash
cp .env.example .env
```

Required configuration:

| Variable | Purpose |
| --- | --- |
| `AVM_ADDRESS` | Algorand TestNet address that receives x402 payments. |
| `FACILITATOR_URL` | x402 facilitator endpoint. |
| `INDEXER_URL` | Algorand MainNet Indexer for Sentinel wallet analysis. |

`sentinel/.env.example` is a focused reference for running the Sentinel package independently. When starting `server.py`, the root `.env` takes precedence, so keep `INDEXER_URL` there.

Install the backend dependencies and start the API:

```bash
python -m venv .venv
source .venv/bin/activate
pip install fastapi "uvicorn[standard]" python-dotenv requests x402
python server.py
```

The API is available at `http://localhost:8000`. Visit `http://localhost:8000/docs` for the interactive API documentation.

## Configure and run the frontend

Copy the frontend environment template if the API is not running at the default address:

```bash
cp frontend/.env.example frontend/.env
```

Then install and start the Vite application:

```bash
cd frontend
pnpm install
pnpm dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`), connect Pera Wallet, and request the protected data. The app inspects the `402 Payment Required` response with Sentinel before opening the wallet approval flow.

## API endpoints

| Endpoint | Description |
| --- | --- |
| `GET /health` | Health check for the backend. |
| `GET /data` | x402-protected premium data endpoint. |
| `POST /sentinel/analyze` | Analyzes payment requirements and returns a risk assessment. |

## Environment and ignored files

Real `.env` files, virtual environments, Python caches, Node dependencies, build output, and editor files are ignored. Commit the provided `.env.example` files instead so collaborators can configure their own local environment without exposing wallet addresses or other deployment-specific values.
