import { useState, useEffect, useCallback } from 'react';

export interface LiveEvent {
  type: string;
  timestamp: string;
  data: Record<string, unknown>;
}

export function useEventStream(apiUrl?: string) {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [connected, setConnected] = useState(false);

  const baseUrl = apiUrl || process.env.NEXT_PUBLIC_API_URL || '';

  useEffect(() => {
    const token = localStorage.getItem('sardis_api_key') || '';
    const url = `${baseUrl}/api/v2/events/stream`;

    // SSE doesn't support custom headers, so use query param for auth
    const source = new EventSource(`${url}?token=${encodeURIComponent(token)}`);

    source.onopen = () => setConnected(true);

    source.onmessage = (e) => {
      try {
        const event: LiveEvent = JSON.parse(e.data);
        setEvents((prev) => [event, ...prev].slice(0, 200));
      } catch {
        // ignore malformed events
      }
    };

    source.onerror = () => {
      setConnected(false);
    };

    return () => {
      source.close();
      setConnected(false);
    };
  }, [baseUrl]);

  const clearEvents = useCallback(() => setEvents([]), []);

  return { events, connected, clearEvents };
}
