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

from sentinel.analyzer import (
    analyze_payment,
    analyze_recipient,
)


# --------------------------------------------------
# Environment
# --------------------------------------------------

load_dotenv()

AVM_ADDRESS = os.getenv(
    "AVM_ADDRESS"
)

FACILITATOR_URL = os.getenv(
    "FACILITATOR_URL",
    "https://facilitator.goplausible.xyz",
)


if not AVM_ADDRESS:
    raise ValueError(
        "AVM_ADDRESS is missing in .env"
    )


# --------------------------------------------------
# FastAPI
# --------------------------------------------------

app = FastAPI(
    title="AlterBlock Sentinel"
)


# --------------------------------------------------
# x402 Facilitator
# --------------------------------------------------

facilitator = HTTPFacilitatorClient(
    FacilitatorConfig(
        url=FACILITATOR_URL
    )
)


# --------------------------------------------------
# x402 Resource Server
# --------------------------------------------------

server = x402ResourceServer(
    facilitator
)


server.register(
    ALGORAND_TESTNET_CAIP2,
    ExactAvmServerScheme(),
)


# --------------------------------------------------
# Protected Routes
# --------------------------------------------------

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


# --------------------------------------------------
# x402 Payment Middleware
# --------------------------------------------------

app.add_middleware(
    PaymentMiddlewareASGI,
    routes=routes,
    server=server,
)


# --------------------------------------------------
# CORS
# --------------------------------------------------

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


# ==================================================
# HEALTH
# ==================================================

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "AlterBlock Sentinel",
    }


# ==================================================
# EXISTING PROTECTED DATA
# ==================================================

@app.get("/data")
async def get_premium_data():
    return {
        "status": "success",
        "data": "Here is your premium content!",
    }


# ==================================================
# NEW SENTINEL VERIFICATION API
# ==================================================

@app.post("/api/v1/verify")
async def verify_recipient(payment: dict):
    """
    Analyze an Algorand recipient using MainNet
    wallet history and Sentinel's rule engine.

    Expected request:

    {
        "recipient": "...",
        "payment_usdc_amount": 10000
    }

    10000 atomic USDC = 0.01 USDC.
    """

    recipient = payment.get(
        "recipient"
    )

    payment_usdc_amount = payment.get(
        "payment_usdc_amount",
        0,
    )


    # ------------------------------------------
    # Validate recipient
    # ------------------------------------------

    if not recipient:
        return {
            "verdict": "block",
            "risk_score": 100,
            "reasons": [
                "Recipient address is required"
            ],
        }


    # ------------------------------------------
    # Validate amount
    # ------------------------------------------

    try:
        payment_usdc_amount = int(
            payment_usdc_amount
        )

    except (
        ValueError,
        TypeError,
    ):
        return {
            "verdict": "block",
            "risk_score": 100,
            "reasons": [
                "Invalid USDC payment amount"
            ],
        }


    if payment_usdc_amount < 0:
        return {
            "verdict": "block",
            "risk_score": 100,
            "reasons": [
                "Payment amount cannot be negative"
            ],
        }


    # ------------------------------------------
    # Run Sentinel analysis
    # ------------------------------------------

    result = analyze_recipient(
        recipient=recipient,
        payment_usdc_amount=payment_usdc_amount,
    )


    # ------------------------------------------
    # Return analysis
    # ------------------------------------------

    return result


# ==================================================
# LEGACY ANALYSIS ENDPOINT
# ==================================================

@app.post("/sentinel/analyze")
async def sentinel_analyze(payment: dict):

    recipient = payment.get(
        "recipient"
    )

    network = payment.get(
        "network"
    )

    asset = payment.get(
        "asset"
    )

    amount = payment.get(
        "amount"
    )


    if (
        not recipient
        or not network
        or not asset
        or amount is None
    ):
        return {
            "decision": "BLOCK",
            "risk_score": 100,
            "checks": [
                {
                    "name": "Payment request",
                    "passed": False,
                    "score": 100,
                    "message":
                        "Incomplete payment requirements",
                }
            ],
        }


    return analyze_payment(
        recipient=recipient,
        network=network,
        asset=asset,
        amount=amount,
    )


# ==================================================
# RUN SERVER
# ==================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )