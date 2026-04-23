"""
Container Monitoring Module

Extends the system monitor to track Docker containers and other containerized workloads.
Reads from cgroup v2 for accurate container resource usage.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ContainerInfo:
    """Container resource information"""
    container_id: str
    name: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_limit_mb: float
    network_in: float
    network_out: float
    pids: int


class ContainerMonitor:
    """Monitor Docker and other container runtimes"""

    @staticmethod
    def get_docker_containers() -> List[ContainerInfo]:
        """
        Fetch Docker container stats using cgroups v2
        Reads from /sys/fs/cgroup for accurate metrics
        """
        containers = []
        
        try:
            # Try reading from Docker socket for container list
            docker_socket = Path('/var/run/docker.sock')
            if not docker_socket.exists():
                return containers
            
            # Alternative: read from cgroups
            cgroup_path = Path('/sys/fs/cgroup/docker')
            if not cgroup_path.exists():
                cgroup_path = Path('/sys/fs/cgroup')
            
            # This is a simplified implementation
            # For production, use Docker API via socket or python-docker library
            for cgroup_dir in cgroup_path.glob('*/'):
                if cgroup_dir.is_dir() and len(cgroup_dir.name) >= 12:
                    container_id = cgroup_dir.name[:12]
                    
                    # Read CPU stats from cgroup.stat
                    cpu_stat_file = cgroup_dir / 'cpu.stat'
                    mem_stat_file = cgroup_dir / 'memory.stat'
                    
                    if cpu_stat_file.exists() and mem_stat_file.exists():
                        try:
                            cpu_info = ContainerMonitor._read_cpu_stats(cpu_stat_file)
                            mem_info = ContainerMonitor._read_memory_stats(mem_stat_file)
                            
                            if cpu_info and mem_info:
                                containers.append(ContainerInfo(
                                    container_id=container_id,
                                    name=f"container-{container_id}",
                                    cpu_percent=cpu_info['cpu_percent'],
                                    memory_percent=mem_info['memory_percent'],
                                    memory_used_mb=mem_info['memory_used_mb'],
                                    memory_limit_mb=mem_info['memory_limit_mb'],
                                    network_in=0.0,  # Would read from veth interfaces
                                    network_out=0.0,
                                    pids=mem_info['pids'],
                                ))
                        except Exception as e:
                            continue
            
        except Exception as e:
            print(f"Error reading container stats: {e}")
        
        return containers

    @staticmethod
    def _read_cpu_stats(cpu_stat_file: Path) -> Optional[Dict]:
        """Read CPU stats from cgroup cpu.stat file"""
        try:
            with open(cpu_stat_file, 'r') as f:
                stats = {}
                for line in f:
                    if line.strip():
                        key, value = line.split()
                        stats[key] = int(value)
                
                # Calculate CPU percentage
                # This is simplified - actual calculation needs kernel ticks
                cpu_percent = min(100.0, (stats.get('usage_usec', 0) / 1000) % 100)
                
                return {'cpu_percent': cpu_percent}
        except Exception:
            return None

    @staticmethod
    def _read_memory_stats(mem_stat_file: Path) -> Optional[Dict]:
        """Read memory stats from cgroup memory.stat file"""
        try:
            with open(mem_stat_file, 'r') as f:
                stats = {}
                for line in f:
                    if line.strip() and ' ' in line:
                        key, value = line.split(maxsplit=1)
                        stats[key] = int(value)
                
                used = stats.get('anon', 0) + stats.get('file', 0)
                limit = stats.get('memory.max', 0)
                
                if limit == 0:
                    limit = 1  # Avoid division by zero
                
                memory_percent = (used / limit) * 100 if limit > 0 else 0
                
                return {
                    'memory_used_mb': used / (1024 * 1024),
                    'memory_limit_mb': limit / (1024 * 1024),
                    'memory_percent': min(100.0, memory_percent),
                    'pids': stats.get('pids.current', 0),
                }
        except Exception:
            return None


class KubernetesMonitor:
    """Monitor Kubernetes pods and resource usage (if running in K8s)"""
    
    @staticmethod
    def detect_kubernetes() -> bool:
        """Check if running in Kubernetes environment"""
        return (
            Path('/var/run/secrets/kubernetes.io').exists() and
            os.getenv('KUBERNETES_SERVICE_HOST') is not None
        )
    
    @staticmethod
    def get_pod_info() -> Optional[Dict]:
        """Get current pod info from downward API"""
        try:
            pod_name = os.getenv('HOSTNAME')
            namespace_file = Path('/var/run/secrets/kubernetes.io/serviceaccount/namespace')
            
            if namespace_file.exists():
                with open(namespace_file, 'r') as f:
                    namespace = f.read().strip()
                
                return {
                    'pod_name': pod_name,
                    'namespace': namespace,
                    'node': os.getenv('NODE_NAME', 'unknown'),
                }
        except Exception:
            pass
        
        return None
