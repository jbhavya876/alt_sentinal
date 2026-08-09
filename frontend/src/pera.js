import { PeraWalletConnect } from "@perawallet/connect";

export const peraWallet = new PeraWalletConnect({
  chainId: 416002
});

export async function connectWallet() {
  try {
    const accounts = await peraWallet.connect();

    if (!accounts || accounts.length === 0) {
      throw new Error("No Algorand account returned.");
    }

    return accounts[0];
  } catch (error) {
    console.error("Pera connection error:", error);
    throw error;
  }
}

export async function reconnectWallet() {
  try {
    const accounts = await peraWallet.reconnectSession();

    if (!accounts || accounts.length === 0) {
      return null;
    }

    return accounts[0];
  } catch (error) {
    console.error("Pera reconnect error:", error);
    return null;
  }
}

export async function disconnectWallet() {
  await peraWallet.disconnect();
}