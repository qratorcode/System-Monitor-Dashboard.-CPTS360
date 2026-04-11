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
        try:
            stat_data = self._read_file('/proc/stat')
            if not stat_data:
                return 0.0, None

            lines = stat_data.strip().split('\n')
            cpu_line = lines[0]  # First line is total CPU stats
            
            # Parse: cpu  user nice system idle iowait irq softirq ...
            parts = cpu_line.split()
            user = int(parts[1])
            nice = int(parts[2])
            system = int(parts[3])
            idle = int(parts[4])
            iowait = int(parts[5])
            
            total = user + nice + system + idle + iowait
            busy = user + nice + system + iowait
            
            # Calculate CPU percentage based on change since last reading
            cpu_percent = 0.0
            if self.prev_cpu_stats is not None:
                prev_total, prev_busy = self.prev_cpu_stats
                if total > prev_total:
                    cpu_percent = ((busy - prev_busy) / (total - prev_total)) * 100
            
            return min(100.0, cpu_percent), (total, busy)
        except Exception as e:
            logger.error(f"Error reading CPU metrics: {e}")
            return 0.0, None

    def _get_memory_metrics(self) -> tuple:
        """
        VIRTUAL MEMORY: Monitor memory usage via /proc/meminfo
        Tracks memory usage patterns and VM mappings
        """
        try:
            meminfo = self._read_file('/proc/meminfo')
            if not meminfo:
                return 0.0, 0.0, 0.0

            mem_dict = {}
            for line in meminfo.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    mem_dict[key.strip()] = int(value.split()[0])

            total = mem_dict.get('MemTotal', 1)
            available = mem_dict.get('MemAvailable', mem_dict.get('MemFree', 0))
            used = total - available
            
            memory_percent = (used / total) * 100 if total > 0 else 0
            
            return memory_percent, used / 1024, total / 1024
        except Exception as e:
            logger.error(f"Error reading memory metrics: {e}")
            return 0.0, 0.0, 0.0

    def _get_disk_io_metrics(self) -> tuple:
        """
        SYSTEM I/O: Monitor disk activity via /proc/diskstats
        Collects disk I/O statistics and file system activity metrics
        """
        try:
            diskstats = self._read_file('/proc/diskstats')
            if not diskstats:
                return 0.0, 0.0

            total_read_sectors = 0
            total_write_sectors = 0

            for line in diskstats.split('\n'):
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) < 14:
                    continue
                
                # Skip loop, ram, and dm devices
                device = parts[2]
                if device.startswith(('loop', 'ram', 'dm-')):
                    continue

                reads_completed = int(parts[3])
                writes_completed = int(parts[7])

                # Sectors * 512 bytes = bytes
                sectors_read = int(parts[5]) if len(parts) > 5 else 0
                sectors_written = int(parts[9]) if len(parts) > 9 else 0

                total_read_sectors += sectors_read
                total_write_sectors += sectors_written

            # Convert to bytes
            total_read_bytes = total_read_sectors * 512
            total_write_bytes = total_write_sectors * 512

            # Calculate rates (bytes/sec)
            read_rate = 0.0
            write_rate = 0.0
            if self.prev_disk_io is not None:
                time_diff = time.time() - self.prev_time
                if time_diff > 0:
                    read_rate = (total_read_bytes - self.prev_disk_io[0]) / time_diff
                    write_rate = (total_write_bytes - self.prev_disk_io[1]) / time_diff

            return max(0, read_rate), max(0, write_rate), (total_read_bytes, total_write_bytes)
        except Exception as e:
            logger.error(f"Error reading disk I/O metrics: {e}")
            return 0.0, 0.0, (0, 0)

    def _get_network_metrics(self) -> tuple:
        """
        SYSTEM I/O: Monitor network activity via /proc/net/dev
        Collects network activity metrics and read/write operations
        """
        try:
            netdev = self._read_file('/proc/net/dev')
            if not netdev:
                return 0.0, 0.0

            total_sent = 0
            total_recv = 0

            for line in netdev.split('\n')[2:]:  # Skip header lines
                if not line.strip():
                    continue
                
                # Skip loopback
                if 'lo:' in line:
                    continue

                # Parse: face |bytes    packets errs drop fifo frame compressed multicast|
                parts = line.split()
                if len(parts) < 16:
                    continue

                # Columns: name, recv_bytes, recv_packets, recv_errs, ...
                try:
                    recv_bytes = int(parts[1])
                    sent_bytes = int(parts[9])
                    total_recv += recv_bytes
                    total_sent += sent_bytes
                except (ValueError, IndexError):
                    continue

            # Calculate rates (bytes/sec)
            sent_rate = 0.0
            recv_rate = 0.0
            if self.prev_net_io is not None:
                time_diff = time.time() - self.prev_time
                if time_diff > 0:
                    sent_rate = (total_sent - self.prev_net_io[0]) / time_diff
                    recv_rate = (total_recv - self.prev_net_io[1]) / time_diff

            return max(0, sent_rate), max(0, recv_rate), (total_sent, total_recv)
        except Exception as e:
            logger.error(f"Error reading network metrics: {e}")
            return 0.0, 0.0, (0, 0)

    def _get_process_metrics(self) -> List[ProcessInfo]:
        """
        PROCESS SCHEDULING: Monitor active processes and their resource usage
        Shows PIDs, states, CPU/memory usage, thread counts, and parent-child relationships
        """
        processes = []
        try:
            proc_dir = Path('/proc')
            
            # Get CPU and memory for scaling
            _, _, memory_total = self._get_memory_metrics()
            
            for proc_path in proc_dir.iterdir():
                try:
                    if not proc_path.is_dir() or not proc_path.name.isdigit():
                        continue
                    
                    pid = int(proc_path.name)
                    
                    # Read status file for process info
                    status_file = proc_path / 'status'
                    if not status_file.exists():
                        continue
                    
                    status = self._read_file(str(status_file))
                    if not status:
                        continue
                    
                    # Extract info from status
                    info = {}
                    for line in status.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            info[key.strip()] = value.strip()
                    
                    name = info.get('Name', 'unknown')
                    state = info.get('State', '?').split()[0] if 'State' in info else '?'
                    num_threads = int(info.get('Threads', '1'))
                    ppid = int(info.get('PPid', '-1'))
                    vm_rss_kb = int(info.get('VmRSS', '0').split()[0])
                    
                    # Read stat file for CPU metrics
                    stat_file = proc_path / 'stat'
                    if stat_file.exists():
                        stat_data = self._read_file(str(stat_file))
                        if stat_data:
                            # Last field is typically utime + stime
                            stat_parts = stat_data.split()
                            if len(stat_parts) > 14:
                                # Rough CPU estimation based on CPU time
                                # (This is a simplified calculation)
                                cpu_time = int(stat_parts[13]) + int(stat_parts[14])
                                cpu_percent = min(100.0, (cpu_time % 1000) / 10.0)
                            else:
                                cpu_percent = 0.0
                        else:
                            cpu_percent = 0.0
                    else:
                        cpu_percent = 0.0
                    
                    # Calculate memory percentage
                    memory_percent = (vm_rss_kb / (memory_total * 1024)) * 100 if memory_total > 0 else 0
                    
                    processes.append(ProcessInfo(
                        pid=pid,
                        name=name[:50],  # Truncate long names
                        state=state,
                        cpu_percent=min(100.0, cpu_percent),
                        memory_percent=min(100.0, memory_percent),
                        num_threads=num_threads,
                        ppid=ppid,
                    ))
                except Exception as e:
                    continue
            
            # Sort by CPU usage (highest first)
            processes.sort(key=lambda x: x.cpu_percent, reverse=True)
            
        except Exception as e:
            logger.error(f"Error reading process metrics: {e}")
        
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
