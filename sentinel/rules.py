def check_recipient(address: str):
    if not address:
        return {
            "name": "Recipient address",
            "passed": False,
            "score": 100,
            "message": "Recipient address is missing",
        }

    if len(address) != 58:
        return {
            "name": "Recipient address",
            "passed": False,
            "score": 100,
            "message": "Invalid Algorand address",
        }

    return {
        "name": "Recipient address",
        "passed": True,
        "score": 0,
        "message": "Valid Algorand address",
    }


def check_network(network: str):
    if not network:
        return {
            "name": "Network",
            "passed": False,
            "score": 100,
            "message": "Network information is missing",
        }

    # The payment requirements already came from
    # our Algorand TestNet x402 server.
    if network.startswith("algorand:"):
        return {
            "name": "Network",
            "passed": True,
            "score": 0,
            "message": "Algorand network verified",
        }

    return {
        "name": "Network",
        "passed": False,
        "score": 80,
        "message": "Unknown payment network",
    }


def check_asset(asset: str):
    if asset != "10458941":
        return {
            "name": "Payment asset",
            "passed": False,
            "score": 70,
            "message": "Unexpected payment asset",
        }

    return {
        "name": "Payment asset",
        "passed": True,
        "score": 0,
        "message": "TestNet USDC verified",
    }


def check_amount(amount: str):
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return {
            "name": "Payment amount",
            "passed": False,
            "score": 100,
            "message": "Invalid payment amount",
        }

    # TestNet USDC has 6 decimals.
    # 10000 = 0.01 USDC.

    if amount <= 0:
        return {
            "name": "Payment amount",
            "passed": False,
            "score": 100,
            "message": "Invalid payment amount",
        }

    if amount > 1_000_000:
        return {
            "name": "Payment amount",
            "passed": False,
            "score": 70,
            "message": "Unusually large payment",
        }

    return {
        "name": "Payment amount",
        "passed": True,
        "score": 0,
        "message": f"Payment amount is {amount / 1_000_000:.6f} USDC",
    }