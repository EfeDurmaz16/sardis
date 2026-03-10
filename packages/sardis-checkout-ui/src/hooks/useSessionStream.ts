import { useEffect, useRef } from "react";
import { createSessionStream, getSessionDetails } from "@/lib/api";
import type { CheckoutStep, PaymentResult } from "@/lib/types";

export interface SessionStreamCallbacks {
  onStepChange: (step: CheckoutStep) => void;
  onSuccess: (result: PaymentResult) => void;
  onError: (message: string) => void;
}

/**
 * Connects to the SSE stream for a checkout session and drives UI step
 * transitions in real-time.
 *
 * SSE messages carry `{ status, balance, tx_hash }`. Terminal statuses
 * (paid, settled, failed, expired) close the stream automatically on the
 * server side; we also close it here once we handle them.
 *
 * If the SSE connection drops we fall back to polling
 * GET /sessions/client/{secret}/details every 3 seconds.
 */
export function useSessionStream(
  clientSecret: string | undefined,
  merchantId: string | undefined,
  callbacks: SessionStreamCallbacks,
) {
  const callbacksRef = useRef(callbacks);
  callbacksRef.current = callbacks;

  useEffect(() => {
    if (!clientSecret || !merchantId) return;

    let sseActive = false;
    let pollInterval: ReturnType<typeof setInterval> | undefined;
    let sse: EventSource | null = null;

    const handleStatusUpdate = (
      status: string,
      txHash: string | null | undefined,
    ) => {
      const { onStepChange, onSuccess, onError } = callbacksRef.current;

      if (status === "processing") {
        onStepChange("processing");
        return;
      }

      if (status === "paid" || status === "settled") {
        onSuccess({
          session_id: "",
          status,
          tx_hash: txHash ?? null,
          amount: "",
          currency: "USDC",
          merchant_id: merchantId,
          platform_fee: null,
          net_amount: null,
        });
        return;
      }

      if (status === "failed") {
        onError("Payment failed");
        return;
      }

      if (status === "expired") {
        onStepChange("expired");
      }
    };

    const startPolling = () => {
      if (pollInterval) return; // already polling
      pollInterval = setInterval(async () => {
        try {
          const data = await getSessionDetails(clientSecret);
          handleStatusUpdate(data.status, null);
          if (isTerminal(data.status)) stopAll();
        } catch {
          // silent — polling failure is non-fatal
        }
      }, 3000);
    };

    const stopAll = () => {
      if (sse) {
        sse.close();
        sse = null;
      }
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = undefined;
      }
    };

    // Try SSE first
    sse = createSessionStream(clientSecret);
    if (sse) {
      sseActive = true;

      sse.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as {
            status?: string;
            tx_hash?: string | null;
            balance?: string;
          };
          if (data.status) {
            handleStatusUpdate(data.status, data.tx_hash);
            if (isTerminal(data.status)) stopAll();
          }
        } catch {
          // ignore parse errors
        }
      };

      sse.onerror = () => {
        if (!sseActive) return;
        sseActive = false;
        sse?.close();
        sse = null;
        // Fall back to polling
        startPolling();
      };
    } else {
      // SSE not supported — go straight to polling
      startPolling();
    }

    return () => {
      stopAll();
    };
  }, [clientSecret, merchantId]);
}

function isTerminal(status: string): boolean {
  return ["paid", "settled", "failed", "expired"].includes(status);
}
