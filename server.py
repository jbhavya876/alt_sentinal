import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.avm import ALGORAND_TESTNET_CAIP2
from x402.mechanisms.avm.exact import ExactAvmServerScheme
from x402.server import x402ResourceServer

load_dotenv()

AVM_ADDRESS = os.getenv("AVM_ADDRESS")
FACILITATOR_URL = os.getenv(
    "FACILITATOR_URL",
    "https://facilitator.goplausible.xyz",
)

if not AVM_ADDRESS:
    raise ValueError("AVM_ADDRESS is missing in .env")

app = FastAPI(title="AlterBlock Sentinel")

# Frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

facilitator = HTTPFacilitatorClient(
    FacilitatorConfig(url=FACILITATOR_URL)
)

server = x402ResourceServer(facilitator)

server.register(
    ALGORAND_TESTNET_CAIP2,
    ExactAvmServerScheme(),
)

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

app.add_middleware(
    PaymentMiddlewareASGI,
    routes=routes,
    server=server,
)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "AlterBlock Sentinel",
    }


@app.get("/data")
async def get_premium_data():
    return {
        "status": "success",
        "data": "Here is your premium content!",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )