import os
from pathlib import Path

import requests
from dotenv import load_dotenv


# Supports running Sentinel independently while preserving root-level settings
# when it is imported by the API server.
load_dotenv(Path(__file__).with_name(".env"))


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


def get_usdc_transactions(
    address: str,
    limit: int = 100,
):
    """
    Fetch recent MainNet USDC transactions.

    Returns actual USDC transfers while excluding
    zero-amount opt-in transactions.
    """

    url = (
        f"{INDEXER_URL}/v2/accounts/"
        f"{address}/transactions"
    )

    # ----------------------------------------
    # Fetch transactions involving the address
    # ----------------------------------------

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


    # ----------------------------------------
    # Separate incoming/outgoing transfers
    # ----------------------------------------

    incoming = []
    outgoing = []

    seen_ids = set()

    for tx in transactions:

        tx_id = tx.get("id")

        # Deduplicate
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


        # ------------------------------------
        # Ignore zero-amount transactions
        #
        # These are generally opt-ins,
        # not actual USDC payments.
        # ------------------------------------

        if amount == 0:
            continue


        # ------------------------------------
        # Incoming
        # ------------------------------------

        if receiver == address:
            incoming.append(tx)


        # ------------------------------------
        # Outgoing
        # ------------------------------------

        if sender == address:
            outgoing.append(tx)


    return {
        "incoming": incoming,
        "outgoing": outgoing,
    }


def build_wallet_features(
    address: str,
):
    """
    Build the first version of Sentinel's
    MainNet wallet feature vector.
    """

    account_data = get_account(address)

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

            "usdc_inflow_tx_count": 0,

            "usdc_outflow_tx_count": 0,

            "unique_sender_count": 0,

            "is_opted_in_usdc": False,

            "is_first_mainnet_appearance": True,

            "status": "NEW_MAINNET_ADDRESS",
        }

    account = account_data.get(
        "account",
        {},
    )


    # ----------------------------------------
    # USDC transactions
    # ----------------------------------------

    transactions = get_usdc_transactions(
        address
    )

    incoming = transactions[
        "incoming"
    ]

    outgoing = transactions[
        "outgoing"
    ]


    # ----------------------------------------
    # USDC inflow analysis
    # ----------------------------------------

    unique_senders = set()

    for tx in incoming:
        sender = tx.get("sender")

        if (
            sender
            and sender != address
        ):
            unique_senders.add(sender)


    # ----------------------------------------
    # USDC opt-in
    # ----------------------------------------

    is_opted_in_usdc = False

    for asset in account.get(
        "assets",
        [],
    ):
        if (
            asset.get("asset-id")
            == USDC_ASSET_ID
        ):
            is_opted_in_usdc = True
            break


    # ----------------------------------------
    # Account creation / age
    # ----------------------------------------

    created_at_round = account.get(
        "created-at-round"
    )


    # ----------------------------------------
    # Current round
    # ----------------------------------------

    current_round = account_data.get(
        "current-round"
    )


    # ----------------------------------------
    # Address age
    # ----------------------------------------

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
    # First appearance
    # ----------------------------------------

    is_first_mainnet_appearance = (
        len(incoming) == 0
        and len(outgoing) == 0
    )


    # ----------------------------------------
    # Return feature vector
    # ----------------------------------------

    return {
        "address": address,

        "exists_on_mainnet": True,

        "address_age_blocks":
            address_age_blocks,

        "created_at_round":
            created_at_round,

        "current_round":
            current_round,

        "usdc_inflow_tx_count":
            len(incoming),

        "usdc_outflow_tx_count":
            len(outgoing),

        "unique_sender_count":
            len(unique_senders),

        "is_opted_in_usdc":
            is_opted_in_usdc,

        "is_first_mainnet_appearance":
            is_first_mainnet_appearance,

        "status": "ACTIVE_MAINNET_ADDRESS",
    }
