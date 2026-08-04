import { useEffect, useRef, useCallback, useState } from 'react';

const RECONNECT_DELAY_MS = 3000;

export function useWebSocket<T = unknown>(
  url: string,
  onMessage: (data: T) => void,
  enabled: boolean = true
) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const enabledRef = useRef(enabled);
  const [isConnected, setIsConnected] = useState(false);

  // Keep enabledRef in sync so onclose reads the latest value
  useEffect(() => {
    enabledRef.current = enabled;
  }, [enabled]);

  // Stabilize the onMessage callback using a ref so reconnect
  // always calls the latest version without re-running connect
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (!enabledRef.current) return;
    try {
      // Close previous socket if any
      if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
        wsRef.current.close();
      }
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as T;
          onMessageRef.current(data);
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        if (enabledRef.current) {
          clearTimeout(reconnectTimer.current);
          reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // Ignore connection errors; onerror → close → onclose will retry
    }
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  // Stabilize send via ref so callers don't re-subscribe on every render
  const wsRefForSend = useRef(wsRef.current);
  wsRefForSend.current = wsRef.current ?? null;

  const send = useCallback((data: unknown) => {
    if (wsRefForSend.current?.readyState === WebSocket.OPEN) {
      wsRefForSend.current.send(JSON.stringify(data));
    }
  }, []);

  return { send, isConnected };
}
