import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from x402.http import (
    FacilitatorConfig,
    HTTPFacilitatorClient,
    PaymentOption,
)
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.avm import ALGORAND_TESTNET_CAIP2
from x402.mechanisms.avm.exact import ExactAvmServerScheme
from x402.server import x402ResourceServer
from sentinel.analyzer import analyze_payment


load_dotenv()


AVM_ADDRESS = os.getenv("AVM_ADDRESS")

FACILITATOR_URL = os.getenv(
    "FACILITATOR_URL",
    "https://facilitator.goplausible.xyz",
)


if not AVM_ADDRESS:
    raise ValueError("AVM_ADDRESS is missing in .env")


app = FastAPI(
    title="AlterBlock Sentinel"
)


# -----------------------------
# x402 Facilitator
# -----------------------------

facilitator = HTTPFacilitatorClient(
    FacilitatorConfig(
        url=FACILITATOR_URL
    )
)


# -----------------------------
# x402 Resource Server
# -----------------------------

server = x402ResourceServer(
    facilitator
)


server.register(
    ALGORAND_TESTNET_CAIP2,
    ExactAvmServerScheme(),
)


# -----------------------------
# Protected Routes
# -----------------------------

routes = {
    "GET /data": RouteConfig(
        accepts=PaymentOption(
            scheme="exact",
            pay_to=AVM_ADDRESS,
            price="$0.01",
            network=ALGORAND_TESTNET_CAIP2,
        ),
        description="Premium Data Access",
        mime_type="application/json",
    ),
}


# -----------------------------
# x402 Payment Middleware
# -----------------------------

app.add_middleware(
    PaymentMiddlewareASGI,
    routes=routes,
    server=server,
)


# -----------------------------
# CORS
# -----------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "PAYMENT-REQUIRED",
        "PAYMENT-SIGNATURE",
        "PAYMENT-RESPONSE",
    ],
)


# -----------------------------
# Health Check
# -----------------------------

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "AlterBlock Sentinel",
    }


# -----------------------------
# Protected Data
# -----------------------------

@app.get("/data")
async def get_premium_data():
    return {
        "status": "success",
        "data": "Here is your premium content!",
    }


@app.post("/sentinel/analyze")
async def sentinel_analyze(payment: dict):
    recipient = payment.get("recipient")
    network = payment.get("network")
    asset = payment.get("asset")
    amount = payment.get("amount")

    if not recipient or not network or not asset or amount is None:
        return {
            "decision": "BLOCK",
            "risk_score": 100,
            "checks": [
                {
                    "name": "Payment request",
                    "passed": False,
                    "score": 100,
                    "message": "Incomplete payment requirements",
                }
            ],
        }

    return analyze_payment(
        recipient=recipient,
        network=network,
        asset=asset,
        amount=amount,
    )


# -----------------------------
# Run Server
# -----------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )