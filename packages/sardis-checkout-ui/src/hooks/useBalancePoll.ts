import { useEffect, useRef, useState } from "react";
import { getBalance } from "@/lib/api";

export function useBalancePoll(
  sessionId: string | undefined,
  enabled: boolean,
  intervalMs = 5000,
) {
  const [balance, setBalance] = useState<string>("0");
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval>>(undefined);

  useEffect(() => {
    if (!sessionId || !enabled) return;

    setLoading(true);
    const poll = async () => {
      try {
        const data = await getBalance(sessionId);
        setBalance(data.balance);
      } catch {
        // silent — polling failure is non-fatal
      } finally {
        setLoading(false);
      }
    };

    poll();
    timerRef.current = setInterval(poll, intervalMs);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [sessionId, enabled, intervalMs]);

  return { balance, loading };
}
