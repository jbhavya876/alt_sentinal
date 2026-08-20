import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


# --------------------------------------------------
# Environment
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(
    PROJECT_ROOT / ".env"
)


INDEXER_URL = os.getenv(
    "INDEXER_URL",
    "https://mainnet-idx.algonode.cloud",
)

USDC_ASSET_ID = 31566704

# Base64 encoding of:
# x402-payment-v2
X402_NOTE_PREFIX = "eDQwMi1wYXltZW50LXYy"


# --------------------------------------------------
# Account
# --------------------------------------------------

def get_account(address: str):
    """
    Fetch account information from the Algorand
    MainNet Indexer.

    A 404 means the address has no MainNet
    account record.
    """

    url = (
        f"{INDEXER_URL}/v2/accounts/{address}"
    )

    response = requests.get(
        url,
        timeout=10,
    )

    if response.status_code == 404:
        return {
            "account": None,
            "current-round": None,
            "exists": False,
        }

    response.raise_for_status()

    data = response.json()

    data["exists"] = True

    return data

def get_asset(asset_id: int):
    """
    Fetch ASA metadata from the Algorand MainNet Indexer.
    """
    url = f"{INDEXER_URL}/v2/assets/{asset_id}"

    response = requests.get(
        url,
        timeout=10,
    )

    response.raise_for_status()

    return response.json().get("asset")

def get_clawback_asa_count(account: dict) -> int:
    """
    Count assets held by the account that have
    a configured clawback address.
    """

    count = 0

    for asset in account.get("assets", []):
        asset_id = asset.get("asset-id")

        if not asset_id:
            continue

        try:
            asset_info = get_asset(asset_id)

            params = asset_info.get(
                "params",
                {},
            )

            clawback = params.get("clawback")

            if clawback:
                count += 1

        except requests.RequestException:
            continue

    return count

# --------------------------------------------------
# General account transactions
# --------------------------------------------------

def get_account_transactions(
    address: str,
    limit: int = 100,
):
    """
    Fetch recent transactions involving the
    account from the MainNet Indexer.
    """

    url = (
        f"{INDEXER_URL}/v2/accounts/"
        f"{address}/transactions"
    )

    params = {
        "limit": limit,
    }

    response = requests.get(
        url,
        params=params,
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    return data.get(
        "transactions",
        [],
    )


# --------------------------------------------------
# USDC transactions
# --------------------------------------------------

def get_usdc_transactions(
    address: str,
    limit: int = 100,
):
    """
    Fetch recent MainNet USDC transactions.

    Zero-amount transactions are excluded because
    they represent opt-in-style transactions rather
    than actual USDC transfers.

    Transactions are deduplicated by transaction ID.
    """

    url = (
        f"{INDEXER_URL}/v2/accounts/"
        f"{address}/transactions"
    )

    params = {
        "asset-id": USDC_ASSET_ID,
        "limit": limit,
    }

    response = requests.get(
        url,
        params=params,
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    transactions = data.get(
        "transactions",
        [],
    )

    incoming = []
    outgoing = []

    seen_ids = set()

    for tx in transactions:

        tx_id = tx.get("id")

        if not tx_id:
            continue

        if tx_id in seen_ids:
            continue

        seen_ids.add(tx_id)

        transfer = tx.get(
            "asset-transfer-transaction"
        )

        if not transfer:
            continue

        amount = transfer.get(
            "amount",
            0,
        )

        sender = tx.get(
            "sender"
        )

        receiver = transfer.get(
            "receiver"
        )

        # Ignore zero-value opt-in transactions.
        if amount == 0:
            continue

        if receiver == address:
            incoming.append(tx)

        if sender == address:
            outgoing.append(tx)

    return {
        "incoming": incoming,
        "outgoing": outgoing,
    }


# --------------------------------------------------
# 30-day USDC transactions
# --------------------------------------------------

def get_usdc_transactions_30d(
    address: str,
    limit: int = 100,
):
    """
    Fetch USDC transactions from the last 30 days.

    The Indexer is queried using an ISO-8601
    after-time boundary.
    """

    url = (
        f"{INDEXER_URL}/v2/accounts/"
        f"{address}/transactions"
    )

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(days=30)
    )

    after_time = cutoff.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    params = {
        "asset-id": USDC_ASSET_ID,
        "limit": limit,
        "after-time": after_time,
    }

    response = requests.get(
        url,
        params=params,
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    transactions = data.get(
        "transactions",
        [],
    )

    incoming = []
    outgoing = []

    seen_ids = set()

    for tx in transactions:

        tx_id = tx.get("id")

        if not tx_id:
            continue

        if tx_id in seen_ids:
            continue

        seen_ids.add(tx_id)

        transfer = tx.get(
            "asset-transfer-transaction"
        )

        if not transfer:
            continue

        amount = transfer.get(
            "amount",
            0,
        )

        sender = tx.get(
            "sender"
        )

        receiver = transfer.get(
            "receiver"
        )

        # Ignore opt-ins / zero-value transfers.
        if amount == 0:
            continue

        if receiver == address:
            incoming.append(tx)

        if sender == address:
            outgoing.append(tx)

    return {
        "incoming": incoming,
        "outgoing": outgoing,
    }


# --------------------------------------------------
# Prior x402 settlements
# --------------------------------------------------

def get_x402_settlements(
    address: str,
    limit: int = 100,
):
    """
    Find previous x402 payment transactions involving
    this address.

    The Master Build Guide identifies the x402 v2
    note prefix as the settlement signal.
    """

    url = (
        f"{INDEXER_URL}/v2/accounts/"
        f"{address}/transactions"
    )

    params = {
        "note-prefix": X402_NOTE_PREFIX,
        "limit": limit,
    }

    response = requests.get(
        url,
        params=params,
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    return data.get(
        "transactions",
        [],
    )


def get_x402_settlements_30d(
    address: str,
    limit: int = 100,
):
    """
    Find x402 payment transactions involving
    this address during the last 30 days.
    """

    url = (
        f"{INDEXER_URL}/v2/accounts/"
        f"{address}/transactions"
    )

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(days=30)
    )

    after_time = cutoff.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    params = {
        "note-prefix": X402_NOTE_PREFIX,
        "limit": limit,
        "after-time": after_time,
    }

    response = requests.get(
        url,
        params=params,
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    return data.get(
        "transactions",
        [],
    )


# --------------------------------------------------
# USDC balance
# --------------------------------------------------

def get_usdc_balance(
    account: dict,
):
    """
    Return the account's current USDC balance.

    Returns 0 if the account is not opted into USDC.
    """

    for asset in account.get(
        "assets",
        [],
    ):
        if (
            asset.get("asset-id")
            == USDC_ASSET_ID
        ):
            return asset.get(
                "amount",
                0,
            )

    return 0


# --------------------------------------------------
# USDC opt-in
# --------------------------------------------------

def is_opted_into_usdc(
    account: dict,
):
    """
    Check whether the account is opted into
    MainNet USDC.
    """

    for asset in account.get(
        "assets",
        [],
    ):
        if (
            asset.get("asset-id")
            == USDC_ASSET_ID
        ):
            return True

    return False


# --------------------------------------------------
# USDC statistics
# --------------------------------------------------

def calculate_usdc_statistics(
    address: str,
    incoming: list,
    outgoing: list,
):
    """
    Calculate USDC transfer statistics.
    """

    total_received = 0
    total_sent = 0

    unique_senders = set()
    unique_receivers = set()

    for tx in incoming:

        transfer = tx.get(
            "asset-transfer-transaction",
            {},
        )

        amount = transfer.get(
            "amount",
            0,
        )

        sender = tx.get(
            "sender"
        )

        total_received += amount

        if (
            sender
            and sender != address
        ):
            unique_senders.add(
                sender
            )

    for tx in outgoing:

        transfer = tx.get(
            "asset-transfer-transaction",
            {},
        )

        amount = transfer.get(
            "amount",
            0,
        )

        receiver = transfer.get(
            "receiver"
        )

        total_sent += amount

        if (
            receiver
            and receiver != address
        ):
            unique_receivers.add(
                receiver
            )

    return {
        "total_received": total_received,
        "total_sent": total_sent,
        "unique_senders": unique_senders,
        "unique_receivers": unique_receivers,
    }


# --------------------------------------------------
# Wallet feature engine
# --------------------------------------------------

def build_wallet_features(
    address: str,
    payment_usdc_amount: int = 0,
):
    """
    Build Sentinel's MainNet wallet feature vector.

    payment_usdc_amount:
        The proposed x402 payment in atomic USDC units.

        Example:
            10000 = 0.01 USDC
    """

    # ----------------------------------------
    # Account
    # ----------------------------------------

    account_data = get_account(
        address
    )

    if not account_data.get(
        "exists",
        False,
    ):
        return {
            "address": address,

            "exists_on_mainnet": False,

            "address_age_blocks": 0,

            "created_at_round": None,

            "current_round": None,

            "algo_balance": 0,

            "total_asset_holdings": 0,

            "created_asset_count": 0,

            "created_app_count": 0,

            "usdc_opted_in": False,

            "usdc_balance": 0,

            "usdc_inflow_count": 0,

            "usdc_outflow_count": 0,

            "usdc_total_received": 0,

            "usdc_total_sent": 0,

            "unique_sender_count": 0,

            "unique_receiver_count": 0,

            "usdc_inflow_count_30d": 0,

            "usdc_outflow_count_30d": 0,

            "usdc_received_30d": 0,

            "usdc_sent_30d": 0,

            "unique_senders_30d": 0,

            "unique_receivers_30d": 0,

            "x402_settle_count": 0,

            "x402_settle_count_30d": 0,

            "payment_usdc_amount":
                payment_usdc_amount,

            "total_transaction_count": 0,

            "first_activity_round": None,

            "last_activity_round": None,

            "is_first_mainnet_appearance": True,

            "status": "NEW_MAINNET_ADDRESS",
        }

    account = account_data.get(
        "account",
        {},
    )

    current_round = account_data.get(
        "current-round"
    )


    # ----------------------------------------
    # Address age
    # ----------------------------------------

    created_at_round = account.get(
        "created-at-round"
    )

    address_age_blocks = None

    if (
        created_at_round is not None
        and current_round is not None
    ):
        address_age_blocks = (
            current_round
            - created_at_round
        )


    # ----------------------------------------
    # ALGO balance
    # ----------------------------------------

    algo_balance_micro = account.get(
        "amount",
        0,
    )

    algo_balance = (
        algo_balance_micro / 1_000_000
    )


    # ----------------------------------------
    # Assets / applications
    # ----------------------------------------

    assets = account.get(
        "assets",
        [],
    )

    created_assets = account.get(
        "created-assets",
        [],
    )

    created_apps = account.get(
        "created-apps",
        [],
    )


    # ----------------------------------------
    # USDC account state
    # ----------------------------------------

    usdc_opted_in = (
        is_opted_into_usdc(
            account
        )
    )

    usdc_balance = (
        get_usdc_balance(
            account
        )
    )


    # ----------------------------------------
    # Recent USDC history
    # ----------------------------------------

    usdc_transactions = (
        get_usdc_transactions(
            address
        )
    )

    incoming = (
        usdc_transactions[
            "incoming"
        ]
    )

    outgoing = (
        usdc_transactions[
            "outgoing"
        ]
    )

    usdc_stats = (
        calculate_usdc_statistics(
            address,
            incoming,
            outgoing,
        )
    )


    # ----------------------------------------
    # 30-day USDC history
    # ----------------------------------------

    usdc_30d = (
        get_usdc_transactions_30d(
            address
        )
    )

    incoming_30d = (
        usdc_30d[
            "incoming"
        ]
    )

    outgoing_30d = (
        usdc_30d[
            "outgoing"
        ]
    )

    usdc_stats_30d = (
        calculate_usdc_statistics(
            address,
            incoming_30d,
            outgoing_30d,
        )
    )


    # ----------------------------------------
    # x402 settlement history
    # ----------------------------------------

    x402_transactions = (
        get_x402_settlements(
            address
        )
    )

    x402_transactions_30d = (
        get_x402_settlements_30d(
            address
        )
    )


    # ----------------------------------------
    # General transaction history
    # ----------------------------------------

    all_transactions = (
        get_account_transactions(
            address
        )
    )

    first_activity_round = None
    last_activity_round = None

    if all_transactions:

        rounds = [
            tx.get(
                "confirmed-round"
            )
            for tx in all_transactions
            if tx.get(
                "confirmed-round"
            ) is not None
        ]

        if rounds:
            first_activity_round = min(
                rounds
            )

            last_activity_round = max(
                rounds
            )


    # ----------------------------------------
    # First MainNet appearance
    # ----------------------------------------

    is_first_mainnet_appearance = (
        len(all_transactions) == 0
    )


    # ----------------------------------------
    # Final feature vector
    # ----------------------------------------

    return {
        "address": address,

        "exists_on_mainnet": True,

        # Account age
        "address_age_blocks":
            address_age_blocks,

        "created_at_round":
            created_at_round,

        "current_round":
            current_round,

        # ALGO
        "algo_balance":
            algo_balance,

        "algo_balance_micro":
            algo_balance_micro,

        # Assets
        "total_asset_holdings":
            len(assets),

        "created_asset_count":
            len(created_assets),

        "created_app_count":
            len(created_apps),

        # USDC state
        "usdc_opted_in":
            usdc_opted_in,

        "usdc_balance":
            usdc_balance,

        # USDC historical activity
        "usdc_inflow_count":
            len(incoming),

        "usdc_outflow_count":
            len(outgoing),

        "usdc_total_received":
            usdc_stats[
                "total_received"
            ],

        "usdc_total_sent":
            usdc_stats[
                "total_sent"
            ],

        "unique_sender_count":
            len(
                usdc_stats[
                    "unique_senders"
                ]
            ),

        "unique_receiver_count":
            len(
                usdc_stats[
                    "unique_receivers"
                ]
            ),

        # 30-day USDC activity
        "usdc_inflow_count_30d":
            len(incoming_30d),

        "usdc_outflow_count_30d":
            len(outgoing_30d),

        "usdc_received_30d":
            usdc_stats_30d[
                "total_received"
            ],

        "usdc_sent_30d":
            usdc_stats_30d[
                "total_sent"
            ],

        "unique_senders_30d":
            len(
                usdc_stats_30d[
                    "unique_senders"
                ]
            ),

        "unique_receivers_30d":
            len(
                usdc_stats_30d[
                    "unique_receivers"
                ]
            ),

        # x402
        "x402_settle_count":
            len(x402_transactions),

        "x402_settle_count_30d":
            len(
                x402_transactions_30d
            ),

        # Proposed payment
        "payment_usdc_amount":
            payment_usdc_amount,

        # General activity
        "total_transaction_count":
            len(all_transactions),

        "first_activity_round":
            first_activity_round,

        "last_activity_round":
            last_activity_round,

        # Status
        "is_first_mainnet_appearance":
            is_first_mainnet_appearance,

        "status":
            "ACTIVE_MAINNET_ADDRESS",
    }