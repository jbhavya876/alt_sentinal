"""Derive an Algorand address from a Pera Universal Wallet (BIP-39) phrase.

Pera's 24-word Universal Wallet phrase is an HD-wallet root, while the
Algorand SDK's ``mnemonic`` helpers accept only an Algo25 account mnemonic.
They are different key formats, so passing the 24 words to ``algosdk.mnemonic``
or using the first 32 bytes of its BIP-39 seed produces the wrong account.
"""

import hashlib
import hmac
import os

from algosdk.encoding import encode_address
from dotenv import load_dotenv
from mnemonic import Mnemonic
from nacl.bindings import crypto_scalarmult_ed25519_base_noclamp


load_dotenv()

# Kept outside source control in .env.
MNEMONIC_24 = os.environ.get("BIP39_MNEMONIC")
if not MNEMONIC_24:
    raise RuntimeError("BIP39_MNEMONIC must be set in the .env file.")
TARGET_ADDRESS = "IK5KDA22DZUX327KOEC7GF34TCTRUXWYESVWSCTJ4AMFNC55XWOQLKEG7E"

HARDENED = 0x80000000


def _hmac_sha512(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha512).digest()


def _truncate_zl(zl: bytes, bits: int = 9) -> bytes:
    """Return trunc256minusg(zL), as defined by ARC-0052."""
    result = bytearray(zl)
    remaining = bits
    for index in range(len(result) - 1, -1, -1):
        if remaining >= 8:
            result[index] = 0
            remaining -= 8
        else:
            result[index] &= (1 << (8 - remaining)) - 1
            break
    return bytes(result)


def _root_key(seed: bytes) -> bytes:
    """Create the 96-byte ARC-0052 extended private root key from BIP-39 seed."""
    key_material = hashlib.sha512(seed).digest()
    kl, kr = key_material[:32], key_material[32:]
    while kl[31] & 0x20:
        key_material = _hmac_sha512(kl, kr)
        kl, kr = key_material[:32], key_material[32:]

    kl = bytearray(kl)
    kl[0] &= 0xF8
    kl[31] &= 0x7F
    kl[31] |= 0x40
    chain_code = hashlib.sha256(b"\x01" + seed).digest()
    return bytes(kl) + kr + chain_code


def _derive_child(extended_private_key: bytes, index: int) -> bytes:
    """Derive one ARC-0052 BIP32-Ed25519 child private key (Peikert, g=9)."""
    kl = extended_private_key[:32]
    kr = extended_private_key[32:64]
    chain_code = extended_private_key[64:]
    index_bytes = index.to_bytes(4, "little")

    if index >= HARDENED:
        data = b"\x00" + kl + kr + index_bytes
        chain_data = b"\x01" + kl + kr + index_bytes
    else:
        public_key = crypto_scalarmult_ed25519_base_noclamp(kl)
        data = b"\x02" + public_key + index_bytes
        chain_data = b"\x03" + public_key + index_bytes

    z = _hmac_sha512(chain_code, data)
    child_chain_code = _hmac_sha512(chain_code, chain_data)[32:]
    left = int.from_bytes(kl, "little") + 8 * int.from_bytes(
        _truncate_zl(z[:32]), "little"
    )
    if left >= 1 << 255:
        raise ValueError("Invalid child key: scalar overflow")
    right = (int.from_bytes(kr, "little") + int.from_bytes(z[32:], "little")) % (1 << 256)
    return left.to_bytes(32, "little") + right.to_bytes(32, "little") + child_chain_code


def derive_address(mnemonic_24: str, account: int = 0) -> str:
    """Derive Pera's Algorand address for ``account`` from a 24-word phrase."""
    mnemonic = Mnemonic("english")
    normalized = " ".join(mnemonic_24.split())
    if len(normalized.split()) != 24 or not mnemonic.check(normalized):
        raise ValueError("Expected a valid 24-word BIP-39 English mnemonic.")

    bip39_seed = mnemonic.to_seed(normalized, passphrase="")
    path = (44 | HARDENED, 283 | HARDENED, account | HARDENED, 0, 0)
    key = _root_key(bip39_seed)
    for index in path:
        key = _derive_child(key, index)
    return encode_address(crypto_scalarmult_ed25519_base_noclamp(key[:32]))


if __name__ == "__main__":
    address = derive_address(MNEMONIC_24)
    print(f"Derived address: {address}")
    if TARGET_ADDRESS:
        print("Address matches target." if address == TARGET_ADDRESS else "Address does not match target.")
    print("\nA 24-word Pera HD phrase cannot be converted to an Algo25 SDK private key or mnemonic.")
    print("Use ARC-0052-compatible signing for this account; algosdk.mnemonic is only for Algo25 accounts.")
