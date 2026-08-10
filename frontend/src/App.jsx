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


const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";


function App() {
  const [address, setAddress] = useState(null);
  const [status, setStatus] = useState("Ready");

  const [paymentRequirements, setPaymentRequirements] =
    useState(null);

  const [sentinelResult, setSentinelResult] =
    useState(null);

  const [showVerification, setShowVerification] =
    useState(false);

  const [data, setData] = useState(null);


  // ----------------------------------------
  // Reconnect wallet
  // ----------------------------------------

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


  // ----------------------------------------
  // Connect
  // ----------------------------------------

  async function handleConnect() {
    try {
      setStatus("Opening Pera...");

      const account = await connectWallet();

      setAddress(account);
      setStatus("Wallet connected");
    } catch (error) {
      console.error(error);
      setStatus(
        "Wallet connection cancelled or failed."
      );
    }
  }


  // ----------------------------------------
  // Disconnect
  // ----------------------------------------

  async function handleDisconnect() {
    try {
      await disconnectWallet();

      setAddress(null);
      setData(null);
      setSentinelResult(null);
      setPaymentRequirements(null);

      setStatus("Wallet disconnected");
    } catch (error) {
      console.error(error);
      setStatus("Disconnect failed");
    }
  }


  // ----------------------------------------
  // Test backend
  // ----------------------------------------

  async function testBackend() {
    try {
      setStatus("Testing backend...");

      const response =
        await fetch(`${API_URL}/health`);

      const result =
        await response.json();

      console.log(result);

      setStatus(
        `Backend: ${result.status}`
      );
    } catch (error) {
      console.error(error);
      setStatus(
        "Backend connection failed"
      );
    }
  }


  // ----------------------------------------
  // Decode x402 PAYMENT-REQUIRED
  // ----------------------------------------

  function decodePaymentRequired(header) {
    try {
      const decoded = atob(header);

      const bytes = Uint8Array.from(
        decoded,
        (char) => char.charCodeAt(0)
      );

      const json =
        new TextDecoder().decode(bytes);

      return JSON.parse(json);
    } catch (error) {
      console.error(
        "Failed to decode PAYMENT-REQUIRED:",
        error
      );

      throw new Error(
        "Could not decode x402 payment requirements."
      );
    }
  }


  // ----------------------------------------
  // Get payment requirements
  // ----------------------------------------

  async function requestPayment() {
    if (!address) {
      setStatus(
        "Connect Pera Wallet first."
      );

      return;
    }

    try {
      setData(null);
      setSentinelResult(null);
      setPaymentRequirements(null);

      setStatus(
        "Checking payment security..."
      );


      /*
       * IMPORTANT:
       *
       * This is a normal fetch.
       *
       * We intentionally DO NOT use
       * wrapFetchWithPayment here.
       *
       * We need to see the 402 BEFORE
       * Pera opens.
       */
      const response =
        await fetch(`${API_URL}/data`);


      if (response.status !== 402) {
        if (!response.ok) {
          throw new Error(
            `Unexpected response: ${response.status}`
          );
        }

        const result =
          await response.json();

        setData(result);
        setStatus(
          "Data received."
        );

        return;
      }


      // ----------------------------------
      // Decode payment requirements
      // ----------------------------------

      const header =
        response.headers.get(
          "PAYMENT-REQUIRED"
        );

      if (!header) {
        throw new Error(
          "PAYMENT-REQUIRED header missing."
        );
      }

      const requirements =
        decodePaymentRequired(header);


      console.log(
        "x402 payment requirements:",
        requirements
      );


      const payment =
        requirements.accepts?.[0];


      if (!payment) {
        throw new Error(
          "No payment option found."
        );
      }


      setPaymentRequirements(
        payment
      );


      // ----------------------------------
      // Ask Sentinel to analyze it
      // ----------------------------------

      setStatus(
        "AlterBlock Sentinel is analyzing the payment..."
      );


      const sentinelResponse =
        await fetch(
          `${API_URL}/sentinel/analyze`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              recipient:
                payment.payTo,

              network:
                payment.network,

              asset:
                payment.asset,

              amount:
                payment.amount,
            }),
          }
        );


      if (!sentinelResponse.ok) {
        throw new Error(
          "Sentinel analysis failed."
        );
      }


      const result =
        await sentinelResponse.json();


      console.log(
        "Sentinel result:",
        result
      );


      setSentinelResult(result);

      setStatus(
        "Payment analyzed. Review the result before signing."
      );

      setShowVerification(true);

    } catch (error) {
      console.error(
        "Sentinel error:",
        error
      );

      setStatus(
        error.message ||
        "Payment verification failed."
      );
    }
  }


  // ----------------------------------------
  // Continue to Pera
  // ----------------------------------------

  async function continueToPayment() {
    if (!address) {
      setStatus(
        "Connect Pera Wallet first."
      );

      return;
    }

    if (!sentinelResult) {
      setStatus(
        "Payment has not been analyzed."
      );

      return;
    }


    // NEVER open Pera for BLOCK.
    if (
      sentinelResult.decision ===
      "BLOCK"
    ) {
      setStatus(
        "Payment blocked by AlterBlock Sentinel."
      );

      return;
    }


    try {
      setShowVerification(false);

      setStatus(
        "Preparing secure payment..."
      );


      // ----------------------------------
      // Create Pera-backed x402 signer
      // ----------------------------------

      const signer =
        createPeraAvmSigner(address);


      // ----------------------------------
      // Create x402 client
      // ----------------------------------

      const client =
        new x402Client();


      client.register(
        ALGORAND_TESTNET_CAIP2,
        new ExactAvmScheme(
          signer
        )
      );


      // ----------------------------------
      // Automatic x402 payment flow
      // ----------------------------------

      const fetchWithPayment =
        wrapFetchWithPayment(
          fetch,
          client
        );


      setStatus(
        "Waiting for Pera approval..."
      );


      const response =
        await fetchWithPayment(
          `${API_URL}/data`,
          {
            method: "GET",
          }
        );


      console.log(
        "Final response status:",
        response.status
      );


      if (!response.ok) {
        const errorText =
          await response.text();

        throw new Error(
          `Payment failed (${response.status}): ${errorText}`
        );
      }


      const result =
        await response.json();


      setData(result);

      setStatus(
        "Payment successful. Data received!"
      );


    } catch (error) {
      console.error(
        "x402 payment error:",
        error
      );

      setStatus(
        error.message ||
        "Payment failed."
      );
    }
  }


  // ----------------------------------------
  // UI
  // ----------------------------------------

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#f5f7fb",
        padding: "50px",
        fontFamily:
          "Arial, sans-serif",
      }}
    >

      <div
        style={{
          maxWidth: "760px",
          margin: "0 auto",
        }}
      >

        <h1>
          AlterBlock Sentinel
        </h1>

        <p>
          AI-powered fraud verification
          for x402 payments on Algorand.
        </p>


        {/* Wallet */}

        <div
          style={{
            background: "white",
            padding: "24px",
            borderRadius: "12px",
            marginTop: "30px",
          }}
        >

          <h2>
            Wallet
          </h2>


          {!address ? (

            <button
              onClick={handleConnect}
            >
              Connect Pera Wallet
            </button>

          ) : (

            <>
              <p>
                <strong>
                  Connected
                </strong>
              </p>

              <code
                style={{
                  wordBreak:
                    "break-all",
                }}
              >
                {address}
              </code>

              <br />
              <br />

              <button
                onClick={
                  handleDisconnect
                }
              >
                Disconnect
              </button>
            </>
          )}

        </div>


        {/* Actions */}

        <div
          style={{
            marginTop: "20px",
          }}
        >

          <button
            onClick={testBackend}
          >
            Test Backend
          </button>


          <button
            onClick={requestPayment}
            disabled={!address}
            style={{
              marginLeft: "10px",
            }}
          >
            Access Protected Data
          </button>

        </div>


        {/* Status */}

        <p
          style={{
            marginTop: "20px",
          }}
        >
          <strong>
            Status:
          </strong>{" "}
          {status}
        </p>


        {/* Sentinel Verification */}

        {showVerification &&
          sentinelResult &&
          paymentRequirements && (

          <div
            style={{
              position: "fixed",
              inset: 0,
              background:
                "rgba(0,0,0,0.55)",
              display: "flex",
              alignItems: "center",
              justifyContent:
                "center",
              padding: "20px",
            }}
          >

            <div
              style={{
                background: "white",
                borderRadius: "16px",
                padding: "30px",
                width: "100%",
                maxWidth: "520px",
              }}
            >

              <h2>
                AlterBlock Sentinel
              </h2>

              <p>
                Payment security analysis
              </p>


              {/* Risk */}

              <div
                style={{
                  padding: "20px",
                  borderRadius: "12px",
                  background:
                    sentinelResult.decision ===
                    "ALLOW"
                      ? "#eaf8ef"
                      : "#fff0f0",
                  marginBottom:
                    "20px",
                }}
              >

                <h2>
                  {sentinelResult.decision ===
                  "ALLOW"
                    ? "🟢 SAFE TO PAY"
                    : "🔴 PAYMENT BLOCKED"}
                </h2>

                <p>
                  Risk Score:{" "}
                  <strong>
                    {
                      sentinelResult.risk_score
                    }
                    /100
                  </strong>
                </p>

              </div>


              {/* Payment */}

              <div
                style={{
                  marginBottom:
                    "20px",
                }}
              >

                <p>
                  <strong>
                    Recipient
                  </strong>
                </p>

                <code
                  style={{
                    fontSize: "12px",
                    wordBreak:
                      "break-all",
                  }}
                >
                  {
                    paymentRequirements.payTo
                  }
                </code>


                <p>
                  <strong>
                    Amount
                  </strong>
                  <br />

                  {(
                    Number(
                      paymentRequirements.amount
                    ) / 1_000_000
                  ).toFixed(6)}{" "}
                  USDC
                </p>


                <p>
                  <strong>
                    Network
                  </strong>
                  <br />

                  Algorand TestNet
                </p>

              </div>


              {/* Checks */}

              <div>

                {sentinelResult.checks.map(
                  (check, index) => (

                    <div
                      key={index}
                      style={{
                        display:
                          "flex",
                        justifyContent:
                          "space-between",
                        padding:
                          "8px 0",
                        borderBottom:
                          "1px solid #eee",
                      }}
                    >

                      <span>
                        {check.passed
                          ? "✓"
                          : "⚠"}{" "}
                        {check.name}
                      </span>

                      <span>
                        {check.message}
                      </span>

                    </div>

                  )
                )}

              </div>


              {/* Buttons */}

              <div
                style={{
                  marginTop: "25px",
                  display: "flex",
                  gap: "10px",
                }}
              >

                {sentinelResult.decision !==
                  "BLOCK" && (

                  <button
                    onClick={
                      continueToPayment
                    }
                  >
                    Continue to Pera
                  </button>

                )}


                <button
                  onClick={() =>
                    setShowVerification(
                      false
                    )
                  }
                >
                  Cancel
                </button>

              </div>

            </div>

          </div>
        )}


        {/* Protected Data */}

        {data && (

          <div
            style={{
              background: "white",
              padding: "24px",
              borderRadius: "12px",
              marginTop: "30px",
            }}
          >

            <h2>
              Protected Data
            </h2>

            <pre>
              {JSON.stringify(
                data,
                null,
                2
              )}
            </pre>

          </div>

        )}

      </div>

    </div>
  );
}


export default App;
