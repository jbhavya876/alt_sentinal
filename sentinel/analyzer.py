from .rules import (
    check_recipient,
    check_network,
    check_asset,
    check_amount,
)


def analyze_payment(
    recipient: str,
    network: str,
    asset: str,
    amount: str,
):
    checks = [
        check_recipient(recipient),
        check_network(network),
        check_asset(asset),
        check_amount(amount),
    ]

    risk_score = sum(
        check["score"]
        for check in checks
    )

    risk_score = min(risk_score, 100)

    if risk_score >= 70:
        decision = "BLOCK"
    elif risk_score >= 40:
        decision = "REVIEW"
    else:
        decision = "ALLOW"

    return {
        "risk_score": risk_score,
        "decision": decision,
        "checks": checks,
    }