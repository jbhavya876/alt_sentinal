from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import requests
from x402.mechanisms.avm import ALGORAND_MAINNET_CAIP2


def validate_resource_url(resource_url: str) -> bool:
    """Return True if the resource URL is a valid HTTP(S) URL."""

    try:
        parsed = urlparse(resource_url)

        return (
            parsed.scheme in {"http", "https"}
            and bool(parsed.netloc)
        )

    except Exception:
        return False


def extract_domain(resource_url: str) -> str | None:
    """Extract the hostname from a resource URL."""

    try:
        parsed = urlparse(resource_url)
        return parsed.hostname
    except Exception:
        return None


def _find_algorand_accept(
    item: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Find an Algorand MainNet payment requirement
    inside a Bazaar resource.
    """

    accepts = item.get("accepts", [])

    if not isinstance(accepts, list):
        return None

    for payment in accepts:
        if not isinstance(payment, dict):
            continue

        if payment.get("network") == ALGORAND_MAINNET_CAIP2:
            return payment

    return None


def lookup_bazaar(
    resource_url: str,
    recipient: str | None = None,
) -> dict[str, Any]:
    """
    Look up a resource in the GoPlausible x402 Bazaar.

    bazaar_registered:
        True  -> exact resource found for Algorand MainNet
        False -> Bazaar was queried successfully but resource was not found
        None  -> Bazaar lookup was unavailable or not configured
    """

    bazaar_url = os.getenv("BAZAAR_URL")

    if not bazaar_url:
        return {
            "bazaar_registered": None,
            "bazaar_checked": False,
            "bazaar_error": "BAZAAR_URL is not configured",
            "bazaar_resource": None,
            "verify_count": None,
            "settle_count": None,
            "first_seen": None,
            "last_seen": None,
            "payment_requirement": None,
        }

    params = {
        "limit": 100,
    }

    if recipient:
        params["filter"] = f"payTo:{recipient}"

    try:
        response = requests.get(
            f"{bazaar_url.rstrip('/')}/discovery/resources",
            params=params,
            timeout=5,
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            raise ValueError("Bazaar response is not a JSON object")

        items = data.get("items", [])

        if not isinstance(items, list):
            raise ValueError("Bazaar response 'items' is not a list")

        for item in items:
            if not isinstance(item, dict):
                continue

            discovered_url = item.get("resourceUrl")

            if discovered_url != resource_url:
                continue

            # Resource URL matches, now make sure it actually
            # supports Algorand MainNet.
            payment_requirement = _find_algorand_accept(item)

            if payment_requirement is None:
                continue

            return {
                "bazaar_registered": True,
                "bazaar_checked": True,
                "bazaar_error": None,
                "bazaar_resource": item,
                "verify_count": item.get("verifyCount"),
                "settle_count": item.get("settleCount"),
                "first_seen": item.get("firstSeen"),
                "last_seen": item.get("lastSeen"),
                "payment_requirement": payment_requirement,
            }

        return {
            "bazaar_registered": False,
            "bazaar_checked": True,
            "bazaar_error": None,
            "bazaar_resource": None,
            "verify_count": None,
            "settle_count": None,
            "first_seen": None,
            "last_seen": None,
            "payment_requirement": None,
        }

    except requests.RequestException as exc:
        return {
            "bazaar_registered": None,
            "bazaar_checked": False,
            "bazaar_error": str(exc),
            "bazaar_resource": None,
            "verify_count": None,
            "settle_count": None,
            "first_seen": None,
            "last_seen": None,
            "payment_requirement": None,
        }

    except (ValueError, TypeError, AttributeError) as exc:
        return {
            "bazaar_registered": None,
            "bazaar_checked": False,
            "bazaar_error": str(exc),
            "bazaar_resource": None,
            "verify_count": None,
            "settle_count": None,
            "first_seen": None,
            "last_seen": None,
            "payment_requirement": None,
        }


def analyze_resource(
    resource_url: str,
    recipient: str | None = None,
) -> dict[str, Any]:
    """
    Analyze an x402 resource independently from wallet analysis.
    """

    if not validate_resource_url(resource_url):
        return {
            "url": resource_url,
            "valid_url": False,
            "domain": None,
            "bazaar_registered": None,
            "bazaar_checked": False,
            "bazaar_error": "Invalid resource URL",
            "verify_count": None,
            "settle_count": None,
            "first_seen": None,
            "last_seen": None,
            "payment_requirement": None,
            "bazaar_resource": None,
        }

    domain = extract_domain(resource_url)

    bazaar = lookup_bazaar(
        resource_url=resource_url,
        recipient=recipient,
    )

    return {
        "url": resource_url,
        "valid_url": True,
        "domain": domain,
        "bazaar_registered": bazaar["bazaar_registered"],
        "bazaar_checked": bazaar["bazaar_checked"],
        "bazaar_error": bazaar["bazaar_error"],
        "verify_count": bazaar["verify_count"],
        "settle_count": bazaar["settle_count"],
        "first_seen": bazaar["first_seen"],
        "last_seen": bazaar["last_seen"],
        "payment_requirement": bazaar["payment_requirement"],
        "bazaar_resource": bazaar["bazaar_resource"],
    }