"""
Sentinel rule-based fraud detection.

Rules are applied before ML inference.
"""

from typing import Dict, List, Tuple


def apply_rules(
    features: Dict,
    amount: int,
    watchlist_score: float = 0,
    amount_ratio: float = 1.0,
    domain_age_days: int = 9999,
    is_in_bazaar: int = 0,
) -> Tuple[str, List[str]]:
    """
    Apply Sentinel's deterministic fraud rules.

    Parameters
    ----------
    features:
        Wallet feature vector produced by indexer.py.

    amount:
        Proposed payment amount in atomic USDC units.

    watchlist_score:
        Watchlist score for the recipient address.

    amount_ratio:
        Proposed payment / category P95 price.

    domain_age_days:
        Age of the resource domain in days.

    is_in_bazaar:
        1 if the endpoint is registered in Bazaar,
        otherwise 0.

    Returns
    -------
    verdict, reasons

    verdict:
        "safe", "suspicious", or "block"
    """

    reasons: List[str] = []

    verdict = "safe"

    # --------------------------------------------------
    # Extract features
    # --------------------------------------------------

    address_age = features.get(
        "address_age_blocks",
        0,
    )

    usdc_inflow_count = features.get(
        "usdc_inflow_count",
        0,
    )

    unique_sender_count = features.get(
        "unique_sender_count",
        0,
    )

    x402_settle_count = features.get(
        "x402_settle_count",
        0,
    )

    # --------------------------------------------------
    # BLOCK RULE 1
    #
    # Very new address + significant payment
    # --------------------------------------------------

    if (
        address_age < 100
        and amount > 5000
    ):
        verdict = "block"

        reasons.append(
            f"New address ({address_age} blocks) "
            f"requesting significant payment"
        )

    # --------------------------------------------------
    # BLOCK RULE 2
    #
    # Known bad actor
    # --------------------------------------------------

    if watchlist_score > 0:

        verdict = "block"

        reasons.append(
            "Recipient address is on the Sentinel watchlist"
        )

    # --------------------------------------------------
    # BLOCK RULE 3
    #
    # No previous USDC inflows + large payment
    # --------------------------------------------------

    if (
        usdc_inflow_count == 0
        and amount > 10000
    ):
        verdict = "block"

        reasons.append(
            "Recipient has no prior USDC inflows "
            "and is requesting a large payment"
        )

    # --------------------------------------------------
    # BLOCK RULE 4
    #
    # Low counterparty diversity + high USDC volume
    # --------------------------------------------------

    if (
        unique_sender_count < 2
        and usdc_inflow_count > 30
    ):
        verdict = "block"

        reasons.append(
            "Possible wash-trading pattern: "
            "high USDC inflow volume with low "
            "counterparty diversity"
        )

    # --------------------------------------------------
    # SUSPICIOUS RULE 5
    #
    # Price anomaly
    # --------------------------------------------------

    if amount_ratio > 3.0:

        if verdict != "block":
            verdict = "suspicious"

        reasons.append(
            f"Payment is {amount_ratio:.2f}x "
            f"the category benchmark"
        )

    # --------------------------------------------------
    # SUSPICIOUS RULE 6
    #
    # Fresh domain
    # --------------------------------------------------

    if domain_age_days < 7:

        if verdict != "block":
            verdict = "suspicious"

        reasons.append(
            f"Resource domain is only "
            f"{domain_age_days} days old"
        )

    # --------------------------------------------------
    # SUSPICIOUS RULE 7
    #
    # Young wallet
    # --------------------------------------------------

    if address_age < 500:

        if verdict != "block":
            verdict = "suspicious"

        reasons.append(
            f"Recipient wallet is young "
            f"({address_age} blocks old)"
        )

    # --------------------------------------------------
    # SUSPICIOUS RULE 8
    #
    # No x402 history + not in Bazaar
    # --------------------------------------------------

    if (
        x402_settle_count == 0
        and is_in_bazaar == 0
    ):

        if verdict != "block":
            verdict = "suspicious"

        reasons.append(
            "Endpoint has no previous x402 "
            "settlement history and is not "
            "registered in Bazaar"
        )

    return verdict, reasons