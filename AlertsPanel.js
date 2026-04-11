import React, { useState, useEffect } from 'react';

function AlertsPanel({ alerts = [] }) {
  const [dismissedAlerts, setDismissedAlerts] = useState(new Set());
  const [expandedAlert, setExpandedAlert] = useState(null);

  const activeAlerts = alerts.filter(alert => !dismissedAlerts.has(alert.id));

  const dismissAlert = (alertId) => {
    const newDismissed = new Set(dismissedAlerts);
    newDismissed.add(alertId);
    setDismissedAlerts(newDismissed);
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical':
        return 'var(--color-accent-red)';
      case 'warning':
        return 'var(--color-accent-orange)';
      case 'info':
      default:
        return 'var(--color-accent-cyan)';
    }
  };

  const getSeverityBgColor = (severity) => {
    switch (severity) {
      case 'critical':
        return 'rgba(255, 51, 102, 0.1)';
      case 'warning':
        return 'rgba(255, 107, 53, 0.1)';
      case 'info':
      default:
        return 'rgba(0, 217, 255, 0.1)';
    }
  };

  if (activeAlerts.length === 0) {
    return null;
  }

  return (
    <div className="alerts-panel">
      <div className="alerts-header">
        <h3>Active Alerts ({activeAlerts.length})</h3>
      </div>

      <div className="alerts-list">
        {activeAlerts.map((alert, index) => (
          <div
            key={index}
            className="alert-item"
            style={{
              background: getSeverityBgColor(alert.severity),
              borderLeft: `4px solid ${getSeverityColor(alert.severity)}`,
            }}
          >
            <div className="alert-header">
              <div className="alert-title">
                <span
                  className="alert-severity"
                  style={{
                    background: getSeverityColor(alert.severity),
                    color: 'white',
                  }}
                >
                  {alert.severity.toUpperCase()}
                </span>
                <span className="alert-text">{alert.title}</span>
              </div>
              <button
                className="alert-dismiss"
                onClick={() => dismissAlert(alert.id)}
                title="Dismiss alert"
              >
                ✕
              </button>
            </div>

            <div className="alert-message">{alert.message}</div>

            {alert.details && (
              <div className="alert-details">
                <span>Value: {alert.details.value.toFixed(2)}</span>
                <span>Threshold: {alert.details.threshold.toFixed(2)}</span>
              </div>
            )}

            <div className="alert-time">
              {new Date(alert.timestamp).toLocaleTimeString()}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default AlertsPanel;
