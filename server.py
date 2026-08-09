import os
from dotenv import load_dotenv
from fastapi import FastAPI
from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI  # <-- Use ASGI Class
from x402.http.types import RouteConfig
from x402.mechanisms.avm import USDC_TESTNET_ASA_ID, ALGORAND_TESTNET_CAIP2
from x402.mechanisms.avm.exact import ExactAvmServerScheme
from x402.server import x402ResourceServer
from x402.schemas import AssetAmount

load_dotenv()

# --- Configuration ---
AVM_ADDRESS = os.getenv("AVM_ADDRESS")
FACILITATOR_URL = os.getenv("FACILITATOR_URL", "https://facilitator.goplausible.xyz")

if not AVM_ADDRESS:
    raise ValueError("AVM_ADDRESS is missing in .env file")

# --- App Setup ---
app = FastAPI(title="Algorand x402 Endpoint")

# 1. Initialize Facilitator & Server (Use Async client for FastAPI)
facilitator = HTTPFacilitatorClient(FacilitatorConfig(url=FACILITATOR_URL))
server = x402ResourceServer(facilitator)

# 2. Register Algorand Scheme
server.register(ALGORAND_TESTNET_CAIP2, ExactAvmServerScheme())

# 3. Define Protected Routes
routes = {
    "GET /data": RouteConfig(
        accepts=PaymentOption(
            scheme="exact",
            pay_to=AVM_ADDRESS,
            # Use simple string price (auto-converts to microUSDC)
            price="$0.01", 
            network=ALGORAND_TESTNET_CAIP2,
        ),
        description="Premium Data Access",
        mime_type="application/json",
    ),
}

# 4. Apply Middleware (Correct Usage with ASGI Class)
app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Server is running"}

@app.get("/data")
async def get_premium_data():
    return {"status": "success", "data": "Here is your premium content!"}

if __name__ == "__main__":
    import uvicorn
    print(f"Starting server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)