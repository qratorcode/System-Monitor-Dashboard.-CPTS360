"""
Alert System for System Monitoring

Generates alerts when system metrics exceed configured thresholds.
Supports email, webhooks, and in-app notifications.
"""

import json
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts"""
    CPU_HIGH = "cpu_high"
    MEMORY_HIGH = "memory_high"
    DISK_READ_HIGH = "disk_read_high"
    DISK_WRITE_HIGH = "disk_write_high"
    NETWORK_HIGH = "network_high"
    PROCESS_NEW = "process_new"
    PROCESS_DIED = "process_died"


@dataclass
class Alert:
    """Single alert notification"""
    type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    metric_name: str
    metric_value: float
    threshold: float
    duration_seconds: float = 0.0


class AlertManager:
    """
    Manages alert rules and generates notifications.
    
    Example:
        manager = AlertManager()
        manager.set_threshold('cpu_percent', 80, AlertSeverity.WARNING)
        manager.set_threshold('memory_percent', 90, AlertSeverity.CRITICAL)
        
        # Check metrics
        alerts = manager.check_metrics({
            'cpu_percent': 85,
            'memory_percent': 92
        })
    """

    def __init__(self):
        """Initialize alert manager"""
        self.thresholds: Dict[str, tuple] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        self.alert_history: List[Alert] = []
        self.max_history = 1000
        
        # Set default thresholds
        self._set_default_thresholds()

    def _set_default_thresholds(self):
        """Set sensible default thresholds"""
        self.thresholds = {
            'cpu_percent': (80.0, AlertSeverity.WARNING, 60),      # 80% for 60 seconds
            'cpu_percent_critical': (95.0, AlertSeverity.CRITICAL, 30),
            'memory_percent': (85.0, AlertSeverity.WARNING, 60),
            'memory_percent_critical': (95.0, AlertSeverity.CRITICAL, 30),
            'disk_read_rate': (500_000_000, AlertSeverity.INFO, 10),  # 500 MB/s
            'disk_write_rate': (500_000_000, AlertSeverity.INFO, 10),
            'net_sent_rate': (1_000_000_000, AlertSeverity.INFO, 10),   # 1 GB/s
            'net_recv_rate': (1_000_000_000, AlertSeverity.INFO, 10),
        }

    def set_threshold(self, metric: str, value: float, 
                     severity: AlertSeverity = AlertSeverity.WARNING,
                     duration: float = 60.0):
        """
        Set or update a threshold for a metric.
        
        Args:
            metric: Metric name (e.g., 'cpu_percent')
            value: Threshold value
            severity: Alert severity level
            duration: How long metric must exceed threshold (seconds)
        """
        self.thresholds[metric] = (value, severity, duration)
        logging.info(f"Alert threshold set: {metric}={value} ({severity.value})")

    def register_callback(self, callback: Callable[[Alert], None]):
        """
        Register a callback to be called when alerts are generated.
        
        Args:
            callback: Function that takes an Alert object
        """
        self.alert_callbacks.append(callback)

    def check_metrics(self, metrics: Dict[str, float]) -> List[Alert]:
        """
        Check current metrics against thresholds.
        
        Args:
            metrics: Dictionary of metric names and values
            
        Returns:
            List of new alerts triggered
        """
        new_alerts = []

        for metric_name, metric_value in metrics.items():
            threshold_key = metric_name
            
            if threshold_key not in self.thresholds:
                continue

            threshold_value, severity, required_duration = self.thresholds[threshold_key]

            # Check if metric exceeds threshold
            if metric_value > threshold_value:
                alert_key = f"{metric_name}_{severity.value}"

                if alert_key not in self.active_alerts:
                    # New alert
                    alert = Alert(
                        type=self._metric_to_alert_type(metric_name),
                        severity=severity,
                        title=f"{metric_name.replace('_', ' ').title()} High",
                        message=f"{metric_name} is {metric_value:.1f}%, exceeds threshold of {threshold_value:.1f}%",
                        timestamp=datetime.now(),
                        metric_name=metric_name,
                        metric_value=metric_value,
                        threshold=threshold_value,
                    )

                    self.active_alerts[alert_key] = {
                        'alert': alert,
                        'start_time': datetime.now(),
                    }
                else:
                    # Existing alert - update duration
                    start_time = self.active_alerts[alert_key]['start_time']
                    duration = (datetime.now() - start_time).total_seconds()
                    
                    if duration >= required_duration:
                        # Duration threshold met - trigger alert
                        alert = self.active_alerts[alert_key]['alert']
                        alert.duration_seconds = duration
                        new_alerts.append(alert)

            else:
                # Metric is back to normal - clear alert
                alert_key = f"{metric_name}_{severity.value}"
                if alert_key in self.active_alerts:
                    logging.info(f"Alert cleared: {metric_name}")
                    del self.active_alerts[alert_key]

        # Execute callbacks for new alerts
        for alert in new_alerts:
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logging.error(f"Error in alert callback: {e}")

            # Add to history
            self.alert_history.append(alert)
            if len(self.alert_history) > self.max_history:
                self.alert_history.pop(0)

        return new_alerts

    def _metric_to_alert_type(self, metric: str) -> AlertType:
        """Convert metric name to alert type"""
        mapping = {
            'cpu_percent': AlertType.CPU_HIGH,
            'memory_percent': AlertType.MEMORY_HIGH,
            'disk_read_rate': AlertType.DISK_READ_HIGH,
            'disk_write_rate': AlertType.DISK_WRITE_HIGH,
            'net_sent_rate': AlertType.NETWORK_HIGH,
            'net_recv_rate': AlertType.NETWORK_HIGH,
        }
        return mapping.get(metric, AlertType.CPU_HIGH)

    def get_active_alerts(self) -> List[Alert]:
        """Get all currently active alerts"""
        return [item['alert'] for item in self.active_alerts.values()]

    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history"""
        return self.alert_history[-limit:]

    def clear_all_alerts(self):
        """Clear all active alerts"""
        self.active_alerts.clear()
        logging.info("All alerts cleared")

    def to_dict(self) -> Dict:
        """Serialize alert state to dictionary"""
        return {
            'active_alerts': [
                {
                    'type': alert.type.value,
                    'severity': alert.severity.value,
                    'title': alert.title,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat(),
                    'metric_name': alert.metric_name,
                    'metric_value': alert.metric_value,
                    'threshold': alert.threshold,
                    'duration_seconds': alert.duration_seconds,
                }
                for alert in self.get_active_alerts()
            ],
            'recent_history': [
                {
                    'type': alert.type.value,
                    'severity': alert.severity.value,
                    'title': alert.title,
                    'timestamp': alert.timestamp.isoformat(),
                }
                for alert in self.get_alert_history(10)
            ]
        }


class WebhookNotifier:
    """Send alerts via webhooks"""

    def __init__(self, webhook_url: str):
        """
        Initialize webhook notifier.
        
        Args:
            webhook_url: URL to POST alerts to
        """
        self.webhook_url = webhook_url

    def notify(self, alert: Alert):
        """Send alert via webhook"""
        import requests
        
        payload = {
            'type': alert.type.value,
            'severity': alert.severity.value,
            'title': alert.title,
            'message': alert.message,
            'timestamp': alert.timestamp.isoformat(),
            'metric': {
                'name': alert.metric_name,
                'value': alert.metric_value,
                'threshold': alert.threshold,
            }
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=5
            )
            logging.info(f"Webhook notifier: {response.status_code}")
        except Exception as e:
            logging.error(f"Failed to send webhook: {e}")


class EmailNotifier:
    """Send alerts via email"""

    def __init__(self, smtp_server: str, from_addr: str, to_addrs: List[str],
                 username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize email notifier.
        
        Args:
            smtp_server: SMTP server address
            from_addr: From email address
            to_addrs: List of recipient email addresses
            username: SMTP username
            password: SMTP password
        """
        self.smtp_server = smtp_server
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.username = username
        self.password = password

    def notify(self, alert: Alert):
        """Send alert via email"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        try:
            subject = f"[{alert.severity.value.upper()}] {alert.title}"
            
            body = f"""
System Monitor Alert

Title: {alert.title}
Severity: {alert.severity.value}
Message: {alert.message}

Metric Details:
- Name: {alert.metric_name}
- Current Value: {alert.metric_value:.2f}
- Threshold: {alert.threshold:.2f}
- Duration: {alert.duration_seconds:.1f}s

Timestamp: {alert.timestamp.isoformat()}
            """

            msg = MIMEMultipart()
            msg['From'] = self.from_addr
            msg['To'] = ', '.join(self.to_addrs)
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.smtp_server) as server:
                if self.username and self.password:
                    server.starttls()
                    server.login(self.username, self.password)
                
                server.send_message(msg)
                logging.info(f"Alert email sent to {self.to_addrs}")

        except Exception as e:
            logging.error(f"Failed to send email alert: {e}")
