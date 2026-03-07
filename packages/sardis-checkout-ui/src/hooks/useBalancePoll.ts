import { useEffect, useRef, useState } from "react";
import { getBalance, createSessionStream } from "@/lib/api";

export function useBalancePoll(
  clientSecret: string | undefined,
  enabled: boolean,
  intervalMs = 5000,
) {
  const [balance, setBalance] = useState<string>("0");
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval>>(undefined);
  const sseRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!clientSecret || !enabled) return;

    setLoading(true);

    // Try SSE first for real-time updates
    const sse = createSessionStream(clientSecret);
    if (sse) {
      sseRef.current = sse;
      sse.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.balance !== undefined) {
            setBalance(data.balance);
            setLoading(false);
          }
        } catch {
          // ignore parse errors
        }
      };
      sse.onerror = () => {
        // SSE failed, fall back to polling
        sse.close();
        sseRef.current = null;
        startPolling();
      };

      return () => {
        sse.close();
        sseRef.current = null;
      };
    }

    // Fallback: polling
    startPolling();

    function startPolling() {
      const poll = async () => {
        if (!clientSecret) return;
        try {
          const data = await getBalance(clientSecret);
          setBalance(data.balance);
        } catch {
          // silent — polling failure is non-fatal
        } finally {
          setLoading(false);
        }
      };

      poll();
      timerRef.current = setInterval(poll, intervalMs);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (sseRef.current) sseRef.current.close();
    };
  }, [clientSecret, enabled, intervalMs]);

  return { balance, loading };
}
