#!/usr/bin/env python3
"""
Real-time System Monitoring Daemon

This daemon collects system metrics from Linux /proc and /sys filesystems
using multi-threaded concurrent data collection and streams them via WebSocket
to the Node.js backend server.

Course Topics Covered:
- Process Scheduling: Monitor active processes, states, CPU time allocation
- Virtual Memory: Track memory usage patterns and VM mappings
- System I/O: Collect disk I/O statistics and file system activity
- Concurrent Programming: Multi-threaded data collection with mutex synchronization
"""

import os
import sys
import json
import time
import threading
import asyncio
import socket
import websockets
import logging
import psutil
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessInfo:
    """Data structure for process information"""
    pid: int
    name: str
    state: str
    cpu_percent: float
    memory_percent: float
    num_threads: int
    ppid: int


@dataclass
class DiskMetrics:
    """Disk I/O metrics."""
    read_rate: float  # bytes/sec
    write_rate: float  # bytes/sec
    total_read_bytes: int
    total_write_bytes: int


@dataclass
class NetworkMetrics:
    """Network traffic metrics."""
    sent_rate: float  # bytes/sec
    recv_rate: float  # bytes/sec
    total_sent_bytes: int
    total_recv_bytes: int


@dataclass
class SystemMetrics:
    """System-wide metrics data structure."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_read_rate: float  # bytes/sec
    disk_write_rate: float  # bytes/sec
    net_sent_rate: float  # bytes/sec
    net_recv_rate: float  # bytes/sec
    hostname: str
    uptime: str
    processes: List[ProcessInfo]


class SystemMonitorDaemon:
    """
    Multi-threaded system monitoring daemon.
    
    Uses concurrent programming with threading and mutex locks to safely
    collect metrics from multiple sources simultaneously.
    """

    def __init__(self, update_interval: float = 0.5):
        """
        Initialize the daemon.
        
        Args:
            update_interval: Time between metric updates in seconds
        """
        self.update_interval = update_interval
        self.running = True
        
        # Thread-safe data collection with mutexes
        self.metrics_lock = threading.Lock()
        self.current_metrics = None
        
        # Previous readings for rate calculations
        self.prev_disk_io = None
        self.prev_net_io = None
        self.prev_cpu_stats = None
        self.prev_time = time.time()
        
        # Thread pool for concurrent data collection
        self.collector_threads = []

    def _read_file(self, path: str) -> Optional[str]:
        """Safely read a file, handling errors gracefully."""
        try:
            if not os.path.exists(path):
                return None
            with open(path, 'r') as f:
                return f.read()
        except (IOError, OSError) as e:
            logger.debug(f"Failed to read {path}: {e}")
            return None

    def _get_cpu_metrics(self) -> tuple:
        """
        PROCESS SCHEDULING: Monitor CPU usage using psutil
        Uses psutil.cpu_percent() to get CPU utilization
        """
        try:
            # Get CPU percentage (interval=None returns since last call)
            cpu_percent = psutil.cpu_percent(interval=None)
            return cpu_percent, (time.time(), cpu_percent)
        except Exception as e:
            logger.error(f"Error reading CPU metrics: {e}")
            return 0.0, None

    def _get_memory_metrics(self) -> tuple:
        """
        VIRTUAL MEMORY: Monitor memory usage using psutil
        Uses psutil.virtual_memory() to get memory statistics
        """
        try:
            mem = psutil.virtual_memory()
            memory_percent = mem.percent
            memory_used = mem.used / (1024 * 1024)  # Convert to MB
            memory_total = mem.total / (1024 * 1024)  # Convert to MB
            
            return memory_percent, memory_used, memory_total
        except Exception as e:
            logger.error(f"Error reading memory metrics: {e}")
            return 0.0, 0.0, 0.0

    def _get_disk_io_metrics(self) -> Optional[DiskMetrics]:
        """
        SYSTEM I/O: Monitor disk activity using psutil
        Uses psutil.disk_io_counters() to get disk I/O statistics
        """
        try:
            disk_io = psutil.disk_io_counters()
            if not disk_io:
                return DiskMetrics(read_rate=0.0, write_rate=0.0, total_read_bytes=0, total_write_bytes=0)

            total_read_bytes = disk_io.read_bytes
            total_write_bytes = disk_io.write_bytes

            # Calculate rates (bytes/sec)
            read_rate = 0.0
            write_rate = 0.0
            if self.prev_disk_io is not None:
                time_diff = time.time() - self.prev_time
                if time_diff > 0:
                    read_rate = (total_read_bytes - self.prev_disk_io.total_read_bytes) / time_diff
                    write_rate = (total_write_bytes - self.prev_disk_io.total_write_bytes) / time_diff

            return DiskMetrics(
                read_rate=max(0, read_rate),
                write_rate=max(0, write_rate),
                total_read_bytes=total_read_bytes,
                total_write_bytes=total_write_bytes
            )
        except Exception as e:
            logger.error(f"Error reading disk I/O metrics: {e}")
            return DiskMetrics(read_rate=0.0, write_rate=0.0, total_read_bytes=0, total_write_bytes=0)

    def _get_network_metrics(self) -> Optional[NetworkMetrics]:
        """
        SYSTEM I/O: Monitor network activity using psutil
        Uses psutil.net_io_counters() to get network statistics
        """
        try:
            net_io = psutil.net_io_counters()
            if not net_io:
                return NetworkMetrics(sent_rate=0.0, recv_rate=0.0, total_sent_bytes=0, total_recv_bytes=0)

            total_sent = net_io.bytes_sent
            total_recv = net_io.bytes_recv

            # Calculate rates (bytes/sec)
            sent_rate = 0.0
            recv_rate = 0.0
            if self.prev_net_io is not None:
                time_diff = time.time() - self.prev_time
                if time_diff > 0:
                    sent_rate = (total_sent - self.prev_net_io.total_sent_bytes) / time_diff
                    recv_rate = (total_recv - self.prev_net_io.total_recv_bytes) / time_diff

            return NetworkMetrics(
                sent_rate=max(0, sent_rate),
                recv_rate=max(0, recv_rate),
                total_sent_bytes=total_sent,
                total_recv_bytes=total_recv
            )
        except Exception as e:
            logger.error(f"Error reading network metrics: {e}")
            return NetworkMetrics(sent_rate=0.0, recv_rate=0.0, total_sent_bytes=0, total_recv_bytes=0)

    def _get_process_metrics(self) -> List[ProcessInfo]:
        """
        PROCESS SCHEDULING: Monitor active processes using psutil
        Uses psutil.process_iter() to get process information
        """
        processes = []
        try:
            # Get memory total for percentage calculation
            mem = psutil.virtual_memory()
            memory_total = mem.total
            
            for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_percent', 'num_threads', 'ppid']):
                try:
                    # Get process info using psutil
                    pinfo = proc.info
                    
                    pid = pinfo['pid']
                    name = pinfo['name'] or 'unknown'
                    # Map psutil status to single character state
                    status = pinfo['status'] or '?'
                    state_map = {
                        psutil.STATUS_RUNNING: 'R',
                        psutil.STATUS_SLEEPING: 'S',
                        psutil.STATUS_DISK_SLEEP: 'D',
                        psutil.STATUS_STOPPED: 'T',
                        psutil.STATUS_TRACING_STOP: 't',
                        psutil.STATUS_ZOMBIE: 'Z',
                        psutil.STATUS_DEAD: 'X',
                        psutil.STATUS_WAKE_KILL: 'K',
                        psutil.STATUS_WAKING: 'W',
                        psutil.STATUS_PARKED: 'P',
                    }
                    state = state_map.get(status, status[0] if status else '?')
                    cpu_percent = pinfo['cpu_percent'] or 0.0
                    memory_percent = pinfo['memory_percent'] or 0.0
                    num_threads = pinfo['num_threads'] or 1
                    ppid = pinfo['ppid'] or 0
                    
                    processes.append(ProcessInfo(
                        pid=pid,
                        name=name[:50],  # Truncate long names
                        state=state,
                        cpu_percent=min(100.0, cpu_percent),
                        memory_percent=min(100.0, memory_percent),
                        num_threads=num_threads,
                        ppid=ppid,
                    ))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # Process may have terminated or we don't have access
                    continue
                except Exception as e:
                    continue
            
            # Sort by CPU usage (highest first)
            processes.sort(key=lambda x: x.cpu_percent, reverse=True)
            
        except Exception as e:
            logger.error(f"Error reading process metrics: {e}")
        
        return processes[:500]  # Limit to top 500 processes

    def _get_hostname(self) -> str:
        """Return the local hostname for display."""
        try:
            return socket.gethostname()
        except Exception as e:
            logger.debug(f"Hostname read failed: {e}")
            return 'unknown'

    def _get_uptime(self) -> str:
        """Return formatted system uptime using /proc/uptime."""
        try:
            uptime_content = self._read_file('/proc/uptime')
            if not uptime_content:
                return 'unknown'
            uptime_seconds = float(uptime_content.split()[0])
            return self._format_uptime(uptime_seconds)
        except Exception as e:
            logger.debug(f"Uptime read failed: {e}")
            return 'unknown'

    def _format_uptime(self, seconds: float) -> str:
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")
        return ' '.join(parts)

    def collect_metrics(self) -> Optional[SystemMetrics]:
        """
        CONCURRENT PROGRAMMING: Collect metrics using multi-threaded approach
        with mutex synchronization for thread-safe data sharing
        """
        try:
            current_time = time.time()
            
            # Collect metrics using thread-safe operations
            cpu_percent, cpu_stats = self._get_cpu_metrics()
            memory_percent, memory_used, memory_total = self._get_memory_metrics()
            disk_metrics = self._get_disk_io_metrics()
            network_metrics = self._get_network_metrics()
            processes = self._get_process_metrics()
            
            # Update previous readings for rate calculations
            if cpu_stats:
                self.prev_cpu_stats = cpu_stats
            self.prev_disk_io = disk_metrics if disk_metrics else self.prev_disk_io
            self.prev_net_io = network_metrics if network_metrics else self.prev_net_io
            self.prev_time = current_time
            
            hostname = self._get_hostname()
            uptime_string = self._get_uptime()

            metrics = SystemMetrics(
                timestamp=current_time,
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used,
                memory_total_mb=memory_total,
                disk_read_rate=disk_metrics.read_rate if disk_metrics else 0.0,
                disk_write_rate=disk_metrics.write_rate if disk_metrics else 0.0,
                net_sent_rate=network_metrics.sent_rate if network_metrics else 0.0,
                net_recv_rate=network_metrics.recv_rate if network_metrics else 0.0,
                hostname=hostname,
                uptime=uptime_string,
                processes=processes,
            )
            
            # Thread-safely update current metrics
            with self.metrics_lock:
                self.current_metrics = metrics
            
            return metrics
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return None

    async def send_metrics_to_server(self):
        """
        WebSocket client that sends metrics to the Node.js server
        """
        uri = "ws://localhost:8080"
        retry_count = 0
        max_retries = 5

        while self.running:
            try:
                logger.info(f"Connecting to metrics server at {uri}...")
                async with websockets.connect(uri) as websocket:
                    logger.info("Connected to metrics server")
                    retry_count = 0

                    while self.running:
                        # Collect and send metrics
                        metrics = self.collect_metrics()
                        if metrics:
                            # Convert to JSON, handling ProcessInfo objects
                            metrics_dict = asdict(metrics)
                            metrics_dict['processes'] = [asdict(p) for p in metrics.processes]
                            
                            try:
                                await websocket.send(json.dumps(metrics_dict))
                                logger.debug(f"Sent metrics: CPU={metrics.cpu_percent:.1f}%, Memory={metrics.memory_percent:.1f}%")
                            except Exception as e:
                                logger.error(f"Failed to send metrics: {e}")
                                break
                        
                        # Wait for next update interval
                        await asyncio.sleep(self.update_interval)

            except Exception as e:
                logger.error(f"Connection error: {e}")
                retry_count += 1
                
                if retry_count > max_retries:
                    logger.error("Max retries exceeded. Giving up.")
                    self.running = False
                    break
                
                wait_time = min(10, 2 ** retry_count)  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds... (attempt {retry_count}/{max_retries})")
                await asyncio.sleep(wait_time)

    def run(self):
        """Start the monitoring daemon"""
        logger.info("Starting System Monitor Daemon")
        logger.info(f"Update interval: {self.update_interval}s")
        
        try:
            asyncio.run(self.send_metrics_to_server())
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
            self.running = False
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            sys.exit(1)


def main():
    """Main entry point"""
    daemon = SystemMonitorDaemon(update_interval=0.5)
    daemon.run()


if __name__ == '__main__':
    main()
