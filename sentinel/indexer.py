import os
from pathlib import Path

import requests
from dotenv import load_dotenv


# Load the project's root .env file.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(
    PROJECT_ROOT / ".env"
)


INDEXER_URL = os.getenv(
    "INDEXER_URL",
    "https://mainnet-idx.algonode.cloud",
)

USDC_ASSET_ID = 31566704


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


def get_usdc_balance(account: dict):
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


def is_opted_into_usdc(account: dict):
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


def calculate_usdc_statistics(
    address: str,
    incoming: list,
    outgoing: list,
):
    """
    Calculate USDC transfer statistics from
    the transactions returned by the Indexer.
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


def build_wallet_features(
    address: str,
):
    """
    Build Sentinel's MainNet wallet feature vector.

    This function combines account-level data,
    general transaction activity, and USDC activity.
    """

    # ----------------------------------------
    # Account data
    # ----------------------------------------

    account_data = get_account(
        address
    )

    # ----------------------------------------
    # Address does not exist on MainNet
    # ----------------------------------------

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

            "usdc_inflow_tx_count": 0,

            "usdc_outflow_tx_count": 0,

            "usdc_total_received": 0,

            "usdc_total_sent": 0,

            "unique_usdc_senders": 0,

            "unique_usdc_receivers": 0,

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


    # ----------------------------------------
    # Account age
    # ----------------------------------------

    created_at_round = account.get(
        "created-at-round"
    )

    current_round = account_data.get(
        "current-round"
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
    #
    # Account amount is in microALGO.
    # ----------------------------------------

    algo_balance_micro = account.get(
        "amount",
        0,
    )

    algo_balance = (
        algo_balance_micro / 1_000_000
    )


    # ----------------------------------------
    # Asset / application activity
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
    # USDC
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
    # USDC transactions
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


    # ----------------------------------------
    # USDC statistics
    # ----------------------------------------

    usdc_stats = (
        calculate_usdc_statistics(
            address,
            incoming,
            outgoing,
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
    # Return feature vector
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

        # Assets / applications
        "total_asset_holdings":
            len(assets),

        "created_asset_count":
            len(created_assets),

        "created_app_count":
            len(created_apps),

        # USDC account state
        "usdc_opted_in":
            usdc_opted_in,

        "usdc_balance":
            usdc_balance,

        # USDC activity
        "usdc_inflow_tx_count":
            len(incoming),

        "usdc_outflow_tx_count":
            len(outgoing),

        "usdc_total_received":
            usdc_stats[
                "total_received"
            ],

        "usdc_total_sent":
            usdc_stats[
                "total_sent"
            ],

        "unique_usdc_senders":
            len(
                usdc_stats[
                    "unique_senders"
                ]
            ),

        "unique_usdc_receivers":
            len(
                usdc_stats[
                    "unique_receivers"
                ]
            ),

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