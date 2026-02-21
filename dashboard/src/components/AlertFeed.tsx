/**
 * AlertFeed - Real-time alert feed component with WebSocket support
 */
import React, { useEffect, useState, useRef, useCallback } from 'react';

interface Alert {
  id: string;
  alert_type: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  agent_id?: string;
  organization_id?: string;
  timestamp: string;
  data: Record<string, any>;
}

interface AlertFeedProps {
  apiUrl?: string;
  token?: string;
  organizationId?: string;
  enableSound?: boolean;
  maxAlerts?: number;
  onAlert?: (alert: Alert) => void;
}

const AlertFeed: React.FC<AlertFeedProps> = ({
  apiUrl = 'ws://localhost:8000',
  token,
  organizationId,
  enableSound = false,
  maxAlerts = 50,
  onAlert,
}) => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [filter, setFilter] = useState<{
    severity?: 'info' | 'warning' | 'critical';
    agent?: string;
    type?: string;
  }>({});

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Initialize audio for critical alerts
  useEffect(() => {
    if (enableSound && !audioRef.current) {
      audioRef.current = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZizcIG');
    }
  }, [enableSound]);

  // Play sound for critical alerts
  const playCriticalSound = useCallback(() => {
    if (enableSound && audioRef.current) {
      audioRef.current.play().catch(err => {
        console.warn('Failed to play alert sound:', err);
      });
    }
  }, [enableSound]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!token && !organizationId) {
      setConnectionError('Token or organization ID required');
      return;
    }

    const wsUrl = apiUrl.replace(/^http/, 'ws');
    const authToken = token || `org_${organizationId}`;
    const url = `${wsUrl}/api/v2/ws/alerts?token=${encodeURIComponent(authToken)}`;

    console.log('Connecting to WebSocket:', url);

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          if (message.type === 'ping') {
            // Respond to heartbeat
            ws.send(JSON.stringify({ type: 'pong' }));
          } else if (message.type === 'system') {
            console.log('System message:', message.message);
          } else if (message.alert_type) {
            // This is an alert
            const alert: Alert = {
              id: message.id,
              alert_type: message.alert_type,
              severity: message.severity,
              message: message.message,
              agent_id: message.agent_id,
              organization_id: message.organization_id,
              timestamp: message.timestamp,
              data: message.data || {},
            };

            // Play sound for critical alerts
            if (alert.severity === 'critical') {
              playCriticalSound();
            }

            // Add to alerts list
            setAlerts((prev) => {
              const updated = [alert, ...prev];
              return updated.slice(0, maxAlerts);
            });

            // Call callback if provided
            if (onAlert) {
              onAlert(alert);
            }
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionError('Connection error');
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        wsRef.current = null;

        // Auto-reconnect with exponential backoff
        const maxAttempts = 10;
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);

        if (reconnectAttempts.current < maxAttempts) {
          console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current + 1}/${maxAttempts})`);
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current += 1;
            connect();
          }, delay);
        } else {
          setConnectionError('Failed to reconnect after multiple attempts');
        }
      };
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      setConnectionError('Failed to connect');
    }
  }, [apiUrl, token, organizationId, maxAlerts, onAlert, playCriticalSound]);

  // Connect on mount
  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  // Filter alerts
  const filteredAlerts = alerts.filter((alert) => {
    if (filter.severity && alert.severity !== filter.severity) return false;
    if (filter.agent && alert.agent_id !== filter.agent) return false;
    if (filter.type && alert.alert_type !== filter.type) return false;
    return true;
  });

  // Severity color mapping
  const getSeverityColor = (severity: string): string => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 border-red-400 text-red-800';
      case 'warning':
        return 'bg-amber-100 border-amber-400 text-amber-800';
      case 'info':
      default:
        return 'bg-blue-100 border-blue-400 text-blue-800';
    }
  };

  const getSeverityBadgeColor = (severity: string): string => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500 text-white';
      case 'warning':
        return 'bg-amber-500 text-white';
      case 'info':
      default:
        return 'bg-blue-500 text-white';
    }
  };

  // Format timestamp
  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();

    if (diff < 60000) {
      return 'Just now';
    } else if (diff < 3600000) {
      const mins = Math.floor(diff / 60000);
      return `${mins} min${mins > 1 ? 's' : ''} ago`;
    } else if (diff < 86400000) {
      const hours = Math.floor(diff / 3600000);
      return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else {
      return date.toLocaleString();
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Real-time Alerts</h2>
          <div className="flex items-center space-x-2">
            <div className="flex items-center space-x-1">
              <div
                className={`w-2 h-2 rounded-full ${
                  isConnected ? 'bg-green-500' : 'bg-red-500'
                }`}
              />
              <span className="text-xs text-gray-600">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            {connectionError && (
              <span className="text-xs text-red-600">{connectionError}</span>
            )}
          </div>
        </div>

        {/* Filters */}
        <div className="mt-3 flex flex-wrap gap-2">
          <select
            className="text-sm border border-gray-300 rounded-md px-2 py-1"
            value={filter.severity || ''}
            onChange={(e) =>
              setFilter((prev) => ({
                ...prev,
                severity: e.target.value as any,
              }))
            }
          >
            <option value="">All Severities</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="critical">Critical</option>
          </select>

          <button
            className="text-sm text-blue-600 hover:text-blue-800"
            onClick={() => setAlerts([])}
          >
            Clear All
          </button>
        </div>
      </div>

      {/* Alert List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {filteredAlerts.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p>No alerts to display</p>
            <p className="text-sm mt-1">
              {isConnected ? 'Waiting for alerts...' : 'Reconnecting...'}
            </p>
          </div>
        ) : (
          filteredAlerts.map((alert) => (
            <div
              key={alert.id}
              className={`p-4 border-l-4 rounded-r-lg ${getSeverityColor(
                alert.severity
              )}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-1">
                    <span
                      className={`px-2 py-0.5 text-xs font-medium rounded ${getSeverityBadgeColor(
                        alert.severity
                      )}`}
                    >
                      {alert.severity.toUpperCase()}
                    </span>
                    <span className="text-xs text-gray-600">
                      {alert.alert_type.replace(/_/g, ' ').toUpperCase()}
                    </span>
                  </div>
                  <p className="text-sm font-medium text-gray-900 mt-1">
                    {alert.message}
                  </p>
                  {alert.agent_id && (
                    <p className="text-xs text-gray-600 mt-1">
                      Agent: {alert.agent_id}
                    </p>
                  )}
                  {Object.keys(alert.data).length > 0 && (
                    <div className="mt-2 text-xs text-gray-700">
                      {alert.data.amount && (
                        <div>Amount: ${alert.data.amount}</div>
                      )}
                      {alert.data.percentage && (
                        <div>Budget: {alert.data.percentage}%</div>
                      )}
                    </div>
                  )}
                </div>
                <span className="text-xs text-gray-500 ml-2 whitespace-nowrap">
                  {formatTimestamp(alert.timestamp)}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default AlertFeed;
