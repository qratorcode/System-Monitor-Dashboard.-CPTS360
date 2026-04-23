"""
Historical Data Persistence Module

Stores system metrics in a database for long-term analysis,
trending, and historical reporting.

Supports SQLite (default) and PostgreSQL.
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class MetricsDatabase:
    """
    Stores and retrieves historical system metrics.
    
    Tables:
    - metrics: System-wide metrics (CPU, memory, disk, network)
    - processes: Per-process metrics snapshots
    - alerts: Historical alert records
    """

    def __init__(self, db_path: str = './metrics.db'):
        """
        Initialize metrics database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_db()

    def _init_db(self):
        """Initialize database schema if needed"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Metrics table - stores system-wide metrics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL UNIQUE,
                    cpu_percent REAL,
                    memory_percent REAL,
                    memory_used_mb REAL,
                    memory_total_mb REAL,
                    disk_read_rate REAL,
                    disk_write_rate REAL,
                    net_sent_rate REAL,
                    net_recv_rate REAL,
                    process_count INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Process metrics table - snapshots of process data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS process_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    pid INTEGER,
                    name TEXT,
                    cpu_percent REAL,
                    memory_percent REAL,
                    memory_mb REAL,
                    num_threads INTEGER,
                    state TEXT,
                    ppid INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(timestamp, pid)
                )
            ''')

            # Alerts table - historical alerts
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    alert_type TEXT,
                    severity TEXT,
                    title TEXT,
                    message TEXT,
                    metric_name TEXT,
                    metric_value REAL,
                    threshold REAL,
                    duration_seconds REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create indices for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_process_timestamp ON process_metrics(timestamp DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_process_pid ON process_metrics(pid)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity)')

            conn.commit()
            conn.close()
            self.logger.info(f"Database initialized: {self.db_path}")

        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")

    def store_metrics(self, metrics: Dict):
        """
        Store system metrics snapshot.
        
        Args:
            metrics: Dictionary of system metrics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            timestamp = datetime.fromtimestamp(metrics['timestamp'])

            cursor.execute('''
                INSERT INTO metrics (
                    timestamp, cpu_percent, memory_percent,
                    memory_used_mb, memory_total_mb, disk_read_rate,
                    disk_write_rate, net_sent_rate, net_recv_rate,
                    process_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp,
                metrics.get('cpu_percent', 0),
                metrics.get('memory_percent', 0),
                metrics.get('memory_used_mb', 0),
                metrics.get('memory_total_mb', 0),
                metrics.get('disk_read_rate', 0),
                metrics.get('disk_write_rate', 0),
                metrics.get('net_sent_rate', 0),
                metrics.get('net_recv_rate', 0),
                len(metrics.get('processes', []))
            ))

            # Store process metrics
            if 'processes' in metrics:
                for proc in metrics['processes']:
                    try:
                        cursor.execute('''
                            INSERT INTO process_metrics (
                                timestamp, pid, name, cpu_percent,
                                memory_percent, num_threads, state, ppid
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            timestamp,
                            proc.get('pid'),
                            proc.get('name'),
                            proc.get('cpu_percent', 0),
                            proc.get('memory_percent', 0),
                            proc.get('num_threads', 0),
                            proc.get('state'),
                            proc.get('ppid')
                        ))
                    except sqlite3.IntegrityError:
                        # Duplicate entry - ignore
                        pass

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.error(f"Failed to store metrics: {e}")

    def store_alert(self, alert: Dict):
        """
        Store alert record.
        
        Args:
            alert: Alert information dictionary
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            timestamp = datetime.fromisoformat(alert['timestamp']) if isinstance(alert['timestamp'], str) else datetime.now()

            cursor.execute('''
                INSERT INTO alerts (
                    timestamp, alert_type, severity, title, message,
                    metric_name, metric_value, threshold, duration_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp,
                alert.get('type'),
                alert.get('severity'),
                alert.get('title'),
                alert.get('message'),
                alert.get('metric_name'),
                alert.get('metric_value'),
                alert.get('threshold'),
                alert.get('duration_seconds', 0)
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.error(f"Failed to store alert: {e}")

    def get_metrics_range(self, hours: int = 24) -> List[Dict]:
        """
        Get metrics from the last N hours.
        
        Args:
            hours: Number of hours to retrieve
            
        Returns:
            List of metric records
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cutoff_time = datetime.now() - timedelta(hours=hours)

            cursor.execute('''
                SELECT * FROM metrics
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            ''', (cutoff_time,))

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(f"Failed to retrieve metrics: {e}")
            return []

    def get_process_history(self, pid: int, hours: int = 24) -> List[Dict]:
        """
        Get CPU/memory history for a specific process.
        
        Args:
            pid: Process ID
            hours: Number of hours to retrieve
            
        Returns:
            List of process metric records
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cutoff_time = datetime.now() - timedelta(hours=hours)

            cursor.execute('''
                SELECT * FROM process_metrics
                WHERE pid = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            ''', (pid, cutoff_time))

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(f"Failed to retrieve process history: {e}")
            return []

    def get_alerts_range(self, hours: int = 24, severity: Optional[str] = None) -> List[Dict]:
        """
        Get alerts from the last N hours.
        
        Args:
            hours: Number of hours to retrieve
            severity: Optional filter by severity (critical, warning, info)
            
        Returns:
            List of alert records
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cutoff_time = datetime.now() - timedelta(hours=hours)

            if severity:
                cursor.execute('''
                    SELECT * FROM alerts
                    WHERE timestamp >= ? AND severity = ?
                    ORDER BY timestamp DESC
                ''', (cutoff_time, severity))
            else:
                cursor.execute('''
                    SELECT * FROM alerts
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                ''', (cutoff_time,))

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(f"Failed to retrieve alerts: {e}")
            return []

    def get_statistics(self, hours: int = 24) -> Dict:
        """
        Get aggregate statistics for a time period.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dictionary with min/max/avg statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_time = datetime.now() - timedelta(hours=hours)

            cursor.execute('''
                SELECT 
                    MIN(cpu_percent) as cpu_min,
                    MAX(cpu_percent) as cpu_max,
                    AVG(cpu_percent) as cpu_avg,
                    MIN(memory_percent) as mem_min,
                    MAX(memory_percent) as mem_max,
                    AVG(memory_percent) as mem_avg,
                    COUNT(*) as sample_count
                FROM metrics
                WHERE timestamp >= ?
            ''', (cutoff_time,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    'cpu': {
                        'min': row[0],
                        'max': row[1],
                        'avg': row[2],
                    },
                    'memory': {
                        'min': row[3],
                        'max': row[4],
                        'avg': row[5],
                    },
                    'sample_count': row[6],
                    'hours': hours,
                }
            return {}

        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {}

    def cleanup_old_data(self, days: int = 30):
        """
        Delete metrics older than N days to manage database size.
        
        Args:
            days: Delete data older than this many days
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_time = datetime.now() - timedelta(days=days)

            # Delete old metrics
            cursor.execute('DELETE FROM metrics WHERE timestamp < ?', (cutoff_time,))
            deleted_metrics = cursor.rowcount

            # Delete old process metrics
            cursor.execute('DELETE FROM process_metrics WHERE timestamp < ?', (cutoff_time,))
            deleted_processes = cursor.rowcount

            # Delete old alerts
            cursor.execute('DELETE FROM alerts WHERE timestamp < ?', (cutoff_time,))
            deleted_alerts = cursor.rowcount

            conn.commit()
            conn.close()

            self.logger.info(f"Cleaned up old data: {deleted_metrics} metrics, "
                           f"{deleted_processes} process records, {deleted_alerts} alerts")

        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")

    def get_database_size(self) -> int:
        """Get database file size in bytes"""
        try:
            return Path(self.db_path).stat().st_size
        except Exception:
            return 0

    def export_to_json(self, output_file: str, hours: int = 24):
        """
        Export metrics to JSON file for analysis.
        
        Args:
            output_file: Path to output JSON file
            hours: Hours of data to export
        """
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'metrics': self.get_metrics_range(hours),
                'statistics': self.get_statistics(hours),
                'alerts': self.get_alerts_range(hours),
            }

            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            self.logger.info(f"Exported metrics to {output_file}")

        except Exception as e:
            self.logger.error(f"Failed to export metrics: {e}")
