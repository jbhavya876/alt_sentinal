import React, { useEffect, useState } from "react";

import {
  connectWallet,
  disconnectWallet,
  reconnectWallet
} from "./pera";

const API_URL = "http://localhost:8000";

function App() {
  const [address, setAddress] = useState(null);
  const [status, setStatus] = useState("Ready");

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

  return (
    <div
      style={{
        minHeight: "100vh",
        padding: "50px",
        fontFamily: "Arial, sans-serif"
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

          <p>{address}</p>

          <button onClick={handleDisconnect}>
            Disconnect
          </button>
        </div>
      )}

      <br />

      <button onClick={testBackend}>
        Test Backend
      </button>

      <p>
        <strong>Status:</strong> {status}
      </p>
    </div>
  );
}

export default App;