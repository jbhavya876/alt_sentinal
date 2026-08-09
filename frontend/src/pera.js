import { PeraWalletConnect } from "@perawallet/connect";
import algosdk from "algosdk";


export const peraWallet = new PeraWalletConnect({
  chainId: 416002,
});


/**
 * Connect to Pera Wallet
 */
export async function connectWallet() {
  try {
    const accounts = await peraWallet.connect();

    if (!accounts || accounts.length === 0) {
      throw new Error(
        "No Algorand account returned."
      );
    }

    return accounts[0];
  } catch (error) {
    console.error(
      "Pera connection error:",
      error
    );

    throw error;
  }
}


/**
 * Reconnect an existing Pera session
 */
export async function reconnectWallet() {
  try {
    const accounts =
      await peraWallet.reconnectSession();

    if (!accounts || accounts.length === 0) {
      return null;
    }

    return accounts[0];
  } catch (error) {
    console.error(
      "Pera reconnect error:",
      error
    );

    return null;
  }
}


/**
 * Disconnect Pera Wallet
 */
export async function disconnectWallet() {
  await peraWallet.disconnect();
}


/**
 * Create an x402 AVM signer backed by Pera Wallet.
 */
export function createPeraAvmSigner(address) {
  if (!address) {
    throw new Error(
      "No connected Pera address."
    );
  }

  return {
    address,

    async signTransactions(
      txns,
      indexesToSign
    ) {
      if (!txns || txns.length === 0) {
        throw new Error(
          "No transactions received from x402."
        );
      }

      console.log(
        "x402 requested transactions:",
        txns.length
      );

      console.log(
        "x402 requested signing indexes:",
        indexesToSign
      );


      /*
       * Convert x402's unsigned transaction
       * bytes into Pera SignerTransaction objects.
       */
      const peraTransactions =
        txns.map(
          (txnBytes, index) => {
            const txn =
              algosdk.decodeUnsignedTransaction(
                txnBytes
              );

            const shouldSign =
              !indexesToSign ||
              indexesToSign.includes(index);

            return {
              txn,

              signers: shouldSign
                ? [address]
                : [],
            };
          }
        );


      console.log(
        "Sending transaction group to Pera..."
      );


      /*
       * Pera signs the atomic group.
       *
       * IMPORTANT:
       * Pera returns ONLY the signed transactions.
       *
       * Example:
       *
       * x402 group:
       *   [txn0, txn1]
       *
       * indexesToSign:
       *   [1]
       *
       * Pera returns:
       *   [signedTxn1]
       */
      const peraSignedTransactions =
        await peraWallet.signTransaction(
          [peraTransactions],
          address
        );


      console.log(
        "Pera signing completed."
      );

      console.log(
        "Pera returned:",
        peraSignedTransactions.length,
        "signed transaction(s)"
      );


      /*
       * x402 expects one entry for EVERY
       * transaction in the original group.
       *
       * So we rebuild the array using the
       * original indexes.
       *
       * Example:
       *
       * txns = [txn0, txn1]
       * indexesToSign = [1]
       *
       * Pera:
       *   [signedTxn1]
       *
       * Return to x402:
       *   [null, signedTxn1]
       */
      const result =
        new Array(txns.length).fill(null);


      /*
       * Pera returns signed transactions
       * in the same order as the requested
       * signing indexes.
       */
      indexesToSign.forEach(
        (originalIndex, signedIndex) => {
          result[originalIndex] =
            peraSignedTransactions[
              signedIndex
            ];
        }
      );


      console.log(
        "Returning x402 signatures:",
        result.map(
          (txn) =>
            txn === null
              ? "UNSIGNED"
              : "SIGNED"
        )
      );


      return result;
    },
  };
}