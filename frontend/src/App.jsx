import React, { useEffect, useState } from "react";

import {
  connectWallet,
  disconnectWallet,
  reconnectWallet,
  createPeraAvmSigner,
} from "./pera";

import {
  wrapFetchWithPayment,
  x402Client,
} from "@x402/fetch";

import {
  ExactAvmScheme,
  ALGORAND_TESTNET_CAIP2,
} from "@x402/avm";

const API_URL = "http://localhost:8000";

function App() {
  const [address, setAddress] = useState(null);
  const [status, setStatus] = useState("Ready");
  const [data, setData] = useState(null);
  const [paymentInfo, setPaymentInfo] = useState(null);

  useEffect(() => {
    reconnectWallet()
      .then((account) => {
        if (account) {
          setAddress(account);
          setStatus("Wallet reconnected");
        }
      })
      .catch((error) => {
        console.error(error);
      });
  }, []);

  async function handleConnect() {
    try {
      setStatus("Opening Pera...");

      const account = await connectWallet();

      setAddress(account);
      setStatus("Wallet connected!");
    } catch (error) {
      console.error(error);
      setStatus("Wallet connection cancelled or failed.");
    }
  }

  async function handleDisconnect() {
    try {
      await disconnectWallet();

      setAddress(null);
      setData(null);
      setPaymentInfo(null);
      setStatus("Wallet disconnected");
    } catch (error) {
      console.error(error);
      setStatus("Disconnect failed");
    }
  }

  async function testBackend() {
    try {
      setStatus("Testing backend...");

      const response = await fetch(`${API_URL}/health`);
      const result = await response.json();

      console.log(result);

      setStatus(`Backend: ${result.status}`);
    } catch (error) {
      console.error(error);
      setStatus("Backend connection failed");
    }
  }

  async function accessProtectedData() {
    if (!address) {
      setStatus("Connect Pera Wallet first.");
      return;
    }

    try {
      setData(null);
      setPaymentInfo(null);
      setStatus("Preparing x402 payment...");

      /*
       * Create a signer backed by the user's
       * connected Pera Wallet.
       */
      const signer = createPeraAvmSigner(address);

      /*
       * Create the x402 client.
       */
      const client = new x402Client();

      /*
       * Tell x402:
       *
       * For Algorand TestNet payments,
       * use our Pera-backed signer.
       */
      client.register(
        ALGORAND_TESTNET_CAIP2,
        new ExactAvmScheme(signer)
      );

      /*
       * Wrap fetch.
       *
       * The wrapper:
       *
       * 1. Calls /data
       * 2. Receives 402
       * 3. Reads PAYMENT-REQUIRED
       * 4. Creates an AVM payment
       * 5. Calls our Pera signer
       * 6. Builds PAYMENT-SIGNATURE
       * 7. Retries /data
       */
      const fetchWithPayment = wrapFetchWithPayment(
        fetch,
        client
      );

      setStatus("Checking payment requirement...");

      const response = await fetchWithPayment(
        `${API_URL}/data`,
        {
          method: "GET",
        }
      );

      console.log(
        "Final response status:",
        response.status
      );

      /*
       * x402 v2 should now have handled the 402
       * automatically.
       */
      if (!response.ok) {
  const errorText = await response.text();

  console.error(
    "Final x402 response status:",
    response.status
  );

  console.error(
    "Final x402 response body:",
    errorText
  );

  console.error(
    "PAYMENT-REQUIRED:",
    response.headers.get("PAYMENT-REQUIRED")
  );

  console.error(
    "PAYMENT-RESPONSE:",
    response.headers.get("PAYMENT-RESPONSE")
  );

  console.error(
    "All response headers:",
    [...response.headers.entries()]
  );

  throw new Error(
    `Payment request failed (${response.status}): ${errorText}`
  );
}

      const result = await response.json();

      setData(result);
      setStatus("Payment successful. Data received.");

      /*
       * x402 v2 settlement information.
       */
      const paymentResponse =
        response.headers.get("PAYMENT-RESPONSE");

      if (paymentResponse) {
        setPaymentInfo(paymentResponse);

        console.log(
          "Payment settlement response:",
          paymentResponse
        );
      }
    } catch (error) {
      console.error("x402 payment error:", error);

      setStatus(
        error?.message ||
          "Payment failed or was rejected."
      );
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        padding: "50px",
        fontFamily: "Arial, sans-serif",
      }}
    >
      <h1>AlterBlock Sentinel</h1>

      <p>
        AI-powered fraud verification for x402
        payments on Algorand.
      </p>

      <hr />

      {!address ? (
        <button onClick={handleConnect}>
          Connect Pera Wallet
        </button>
      ) : (
        <div>
          <p>
            <strong>Connected Wallet</strong>
          </p>

          <code>{address}</code>

          <br />
          <br />

          <button onClick={handleDisconnect}>
            Disconnect
          </button>
        </div>
      )}

      <br />
      <br />

      <button onClick={testBackend}>
        Test Backend
      </button>

      <button
        onClick={accessProtectedData}
        disabled={!address}
        style={{ marginLeft: "10px" }}
      >
        Pay & Access Data
      </button>

      <p>
        <strong>Status:</strong> {status}
      </p>

      {data && (
        <div>
          <h2>Protected Data</h2>

          <pre>
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      )}

      {paymentInfo && (
        <div>
          <h3>Settlement</h3>

          <p>
            Payment settlement response received.
          </p>

          <code
            style={{
              wordBreak: "break-all",
            }}
          >
            {paymentInfo}
          </code>
        </div>
      )}
    </div>
  );
}

export default App;