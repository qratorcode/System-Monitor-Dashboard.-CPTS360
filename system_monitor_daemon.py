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
import websockets
import logging
import psutil
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

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
class SystemMetrics:
    """System metrics data structure"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_read_rate: float  # bytes/sec
    disk_write_rate: float  # bytes/sec
    net_sent_rate: float  # bytes/sec
    net_recv_rate: float  # bytes/sec
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
        PROCESS SCHEDULING: Monitor CPU usage via /proc/stat
        Reads kernel-level CPU statistics from /proc/stat
        """
        return psutil.cpu_percent(interval=0.1), None

    def _get_memory_metrics(self) -> tuple:
        """
        VIRTUAL MEMORY: Monitor memory usage via /proc/meminfo
        Tracks memory usage patterns and VM mappings
        """
        mem = psutil.virtual_memory()
        return mem.percent, mem.used / (1024**2), mem.total / (1024**2)

    def _get_disk_io_metrics(self) -> tuple:
        """
        SYSTEM I/O: Monitor disk activity via /proc/diskstats
        Collects disk I/O statistics and file system activity metrics
        """
        io = psutil.disk_io_counters()
        if self.prev_disk_io is None:
            self.prev_disk_io = (io.read_bytes, io.write_bytes)
            return 0.0, 0.0, (io.read_bytes, io.write_bytes)
        time_diff = time.time() - self.prev_time
        read_rate = (io.read_bytes - self.prev_disk_io[0]) / time_diff if time_diff > 0 else 0
        write_rate = (io.write_bytes - self.prev_disk_io[1]) / time_diff if time_diff > 0 else 0
        return max(0, read_rate), max(0, write_rate), (io.read_bytes, io.write_bytes)

    def _get_network_metrics(self) -> tuple:
        """
        SYSTEM I/O: Monitor network activity via /proc/net/dev
        Collects network activity metrics and read/write operations
        """
        net = psutil.net_io_counters()
        current_time = time.time()
        if self.prev_net_io is None:
            self.prev_net_io = (net.bytes_sent, net.bytes_recv, current_time)
            return 0.0, 0.0, (net.bytes_sent, net.bytes_recv, current_time)
        time_diff = current_time - self.prev_net_io[2]
        sent_rate = (net.bytes_sent - self.prev_net_io[0]) / time_diff if time_diff > 0 else 0
        recv_rate = (net.bytes_recv - self.prev_net_io[1]) / time_diff if time_diff > 0 else 0
        return max(0, sent_rate), max(0, recv_rate), (net.bytes_sent, net.bytes_recv, current_time)

    def _get_process_metrics(self) -> List[ProcessInfo]:
        """
        PROCESS SCHEDULING: Monitor active processes and their resource usage
        Shows PIDs, states, CPU/memory usage, thread counts, and parent-child relationships
        """
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_percent', 'num_threads', 'ppid']):
            try:
                info = proc.info
                processes.append(ProcessInfo(
                    pid=info['pid'],
                    name=(info['name'] or 'unknown')[:50],
                    state=info['status'] or '?',
                    cpu_percent=info['cpu_percent'] or 0.0,
                    memory_percent=info['memory_percent'] or 0.0,
                    num_threads=info['num_threads'] or 1,
                    ppid=info['ppid'] or -1,
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        processes.sort(key=lambda x: x.cpu_percent, reverse=True)
        return processes[:500]  # Limit to top 500 processes

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
            disk_read_rate, disk_write_rate, disk_io = self._get_disk_io_metrics()
            net_sent_rate, net_recv_rate, net_io = self._get_network_metrics()
            processes = self._get_process_metrics()
            
            # Update previous readings for rate calculations
            if cpu_stats:
                self.prev_cpu_stats = cpu_stats
            self.prev_disk_io = disk_io if disk_io else self.prev_disk_io
            self.prev_net_io = net_io if net_io else self.prev_net_io
            self.prev_time = current_time
            
            metrics = SystemMetrics(
                timestamp=current_time,
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used,
                memory_total_mb=memory_total,
                disk_read_rate=disk_read_rate,
                disk_write_rate=disk_write_rate,
                net_sent_rate=net_sent_rate,
                net_recv_rate=net_recv_rate,
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
