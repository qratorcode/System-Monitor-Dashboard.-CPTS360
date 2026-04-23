"""
Configuration Management for System Monitor Daemon

Loads and validates configuration from JSON file.
Provides sensible defaults for all settings.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """Load and manage daemon configuration"""

    # Default configuration values
    DEFAULT_CONFIG = {
        "daemon": {
            "update_interval": 0.5,
            "websocket_url": "ws://localhost:8080",
            "reconnect_retries": 5,
            "reconnect_backoff_max": 10,
            "process_limit": 500,
            "process_refresh_interval": 1.0,
        },
        "collection": {
            "enable_cpu": True,
            "enable_memory": True,
            "enable_disk_io": True,
            "enable_network": True,
            "enable_processes": True,
            "enable_containers": False,
            "enable_services": False,
        },
        "database": {
            "enabled": True,
            "path": "./metrics.db",
            "cleanup_days": 30,
            "cleanup_interval": 3600,
        },
        "alerts": {
            "enabled": True,
            "thresholds": {
                "cpu_percent_warning": 80,
                "cpu_percent_critical": 95,
                "memory_percent_warning": 85,
                "memory_percent_critical": 95,
                "disk_read_rate_warning": 500000000,
                "disk_write_rate_warning": 500000000,
                "network_rate_warning": 1000000000,
            },
            "duration_seconds": {
                "warning": 60,
                "critical": 30,
            },
        },
        "logging": {
            "level": "INFO",
            "format": "[%(levelname)s] %(message)s",
            "file": None,
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader.
        
        Args:
            config_path: Path to config.json file (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.config = self.DEFAULT_CONFIG.copy()

        if config_path:
            self.load_config_file(config_path)
        else:
            # Try to find config.json in common locations
            for path in [Path('./daemon/config.json'), Path('./config.json'), Path('config.json')]:
                if path.exists():
                    self.load_config_file(str(path))
                    break

    def load_config_file(self, config_path: str):
        """
        Load configuration from JSON file.
        
        Args:
            config_path: Path to config.json
        """
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                self.logger.warning(f"Config file not found: {config_path}, using defaults")
                return

            with open(config_file, 'r') as f:
                loaded_config = json.load(f)

            # Merge loaded config with defaults (loaded config takes precedence)
            self._deep_merge(self.config, loaded_config)
            self.logger.info(f"Configuration loaded from {config_path}")

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file: {e}")
        except Exception as e:
            self.logger.error(f"Error loading config file: {e}")

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively merge override config into base config.
        
        Args:
            base: Base configuration dictionary
            override: Override configuration dictionary
            
        Returns:
            Merged configuration
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                ConfigLoader._deep_merge(base[key], value)
            else:
                base[key] = value
        return base

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Get a configuration value by key path.
        
        Usage:
            config.get('daemon', 'update_interval')  # Returns 0.5
            config.get('alerts', 'enabled')           # Returns True
            
        Args:
            *keys: Nested keys to access
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        current = self.config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def get_daemon_config(self) -> Dict[str, Any]:
        """Get daemon configuration section"""
        return self.config.get('daemon', {})

    def get_collection_config(self) -> Dict[str, Any]:
        """Get collection configuration section"""
        return self.config.get('collection', {})

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration section"""
        return self.config.get('database', {})

    def get_alerts_config(self) -> Dict[str, Any]:
        """Get alerts configuration section"""
        return self.config.get('alerts', {})

    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration section"""
        return self.config.get('logging', {})

    def update_threshold(self, metric: str, value: float):
        """
        Update an alert threshold at runtime.
        
        Args:
            metric: Metric name (e.g., 'cpu_percent_warning')
            value: New threshold value
        """
        if 'alerts' in self.config and 'thresholds' in self.config['alerts']:
            self.config['alerts']['thresholds'][metric] = value
            self.logger.info(f"Updated threshold: {metric} = {value}")

    def save_to_file(self, config_path: str):
        """
        Save current configuration to file.
        
        Args:
            config_path: Path to save config.json
        """
        try:
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.logger.info(f"Configuration saved to {config_path}")
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")

    def validate(self) -> bool:
        """
        Validate configuration values.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        errors = []

        # Validate daemon settings
        update_interval = self.get('daemon', 'update_interval')
        if not isinstance(update_interval, (int, float)) or update_interval <= 0:
            errors.append("daemon.update_interval must be positive number")

        # Validate database settings
        if self.get('database', 'cleanup_days', default=30) <= 0:
            errors.append("database.cleanup_days must be positive")

        # Validate alert thresholds
        thresholds = self.get('alerts', 'thresholds', default={})
        for threshold_name, threshold_value in thresholds.items():
            if not isinstance(threshold_value, (int, float)) or threshold_value < 0:
                errors.append(f"Invalid threshold {threshold_name}: {threshold_value}")

        if errors:
            for error in errors:
                self.logger.error(f"Configuration validation error: {error}")
            return False

        self.logger.info("Configuration validation passed")
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Get full configuration as dictionary"""
        return self.config.copy()

    def print_summary(self):
        """Print configuration summary to console"""
        print("\n" + "=" * 60)
        print("SYSTEM MONITOR DAEMON CONFIGURATION")
        print("=" * 60)

        daemon_config = self.get_daemon_config()
        print(f"\nDaemon Settings:")
        print(f"  Update Interval: {daemon_config.get('update_interval')}s")
        print(f"  WebSocket URL: {daemon_config.get('websocket_url')}")
        print(f"  Process Limit: {daemon_config.get('process_limit')}")

        collection_config = self.get_collection_config()
        print(f"\nData Collection:")
        for key, enabled in collection_config.items():
            status = "✓ Enabled" if enabled else "✗ Disabled"
            print(f"  {key}: {status}")

        database_config = self.get_database_config()
        if database_config.get('enabled'):
            print(f"\nDatabase:")
            print(f"  Path: {database_config.get('path')}")
            print(f"  Cleanup Days: {database_config.get('cleanup_days')}")

        alerts_config = self.get_alerts_config()
        if alerts_config.get('enabled'):
            print(f"\nAlerts:")
            thresholds = alerts_config.get('thresholds', {})
            print(f"  CPU Warning: {thresholds.get('cpu_percent_warning')}%")
            print(f"  CPU Critical: {thresholds.get('cpu_percent_critical')}%")
            print(f"  Memory Warning: {thresholds.get('memory_percent_warning')}%")
            print(f"  Memory Critical: {thresholds.get('memory_percent_critical')}%")

        print("\n" + "=" * 60 + "\n")
