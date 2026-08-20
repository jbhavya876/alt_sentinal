from .indexer import build_wallet_features
from .resource import analyze_resource
from .rules import apply_rules


def analyze_recipient(
    recipient: str,
    payment_usdc_amount: int = 0,
    watchlist_score: float = 0,
    amount_ratio: float = 1.0,
    domain_age_days: int = 9999,
    resource_url: str | None = None,
):
    """
    Analyze an Algorand recipient using:

    1. MainNet wallet features
    2. x402 resource/Bazaar features
    3. Sentinel deterministic fraud rules

    payment_usdc_amount is expressed in atomic USDC units.

    Example:
        10000 = 0.01 USDC
    """

    # ----------------------------------------
    # Get MainNet wallet features
    # ----------------------------------------

    features = build_wallet_features(
        recipient,
        payment_usdc_amount=payment_usdc_amount,
    )

    # ----------------------------------------
    # Analyze resource independently
    # ----------------------------------------

    resource = None

    bazaar_registered = None

    if resource is not None:
        features["bazaar_registered"] = resource.get(
            "bazaar_registered"
        )

        features["bazaar_verify_count"] = resource.get(
            "verify_count"
        )

        features["bazaar_settle_count"] = resource.get(
            "settle_count"
        )

    if resource_url:
        resource = analyze_resource(
            resource_url=resource_url,
            recipient=recipient,
        )

    if resource is not None:
        domain_age_days = resource.get(
            "domain_age_days"
        )

        if domain_age_days is None:
            domain_age_days = 9999

    # ----------------------------------------
    # Apply deterministic rules
    # ----------------------------------------

    verdict, reasons = apply_rules(
        features=features,
        amount=payment_usdc_amount,
        watchlist_score=watchlist_score,
        amount_ratio=amount_ratio,
        domain_age_days=domain_age_days,
        bazaar_registered=bazaar_registered,
    )

    # ----------------------------------------
    # Convert verdict into a temporary
    # human-readable risk score.
    #
    # This is NOT the final ML score.
    # ----------------------------------------

    if verdict == "block":
        risk_score = 90

    elif verdict == "suspicious":
        risk_score = 50

    else:
        risk_score = 10

    # ----------------------------------------
    # Return complete analysis
    # ----------------------------------------

    return {
        "recipient": recipient,
        "verdict": verdict,
        "risk_score": risk_score,
        "reasons": reasons,
        "features": features,
        "resource": resource,
    }


# --------------------------------------------------
# Backward-compatible wrapper
# --------------------------------------------------

def analyze_payment(
    recipient: str,
    network: str,
    asset: str,
    amount: str,
):
    """
    Compatibility wrapper for the older API.

    The new Sentinel analysis should use
    analyze_recipient() directly.
    """

    try:
        payment_amount = int(
            float(amount)
        )
    except (
        ValueError,
        TypeError,
    ):
        payment_amount = 0

    result = analyze_recipient(
        recipient=recipient,
        payment_usdc_amount=payment_amount,
    )

    return {
        "risk_score":
            result["risk_score"],

        "decision":
            result["verdict"].upper(),

        "checks": [
            {
                "name": "recipient_analysis",
                "status":
                    result["verdict"].upper(),
                "reasons":
                    result["reasons"],
            }
        ],

        "features":
            result["features"],

        "resource":
            result["resource"],
    }
