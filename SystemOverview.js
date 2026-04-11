import React from 'react';

function SystemOverview({ metrics }) {
  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const formatRate = (bytesPerSec) => {
    const k = 1024;
    const sizes = ['B/s', 'KB/s', 'MB/s'];
    if (bytesPerSec === 0) return '0 B/s';
    const i = Math.floor(Math.log(bytesPerSec) / Math.log(k));
    return Math.round((bytesPerSec / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="system-overview">
      {/* CPU */}
      <div className="metric-card">
        <div className="metric-label">CPU Usage</div>
        <div>
          <span className="metric-value">{metrics.cpu_percent.toFixed(1)}</span>
          <span className="metric-unit">%</span>
        </div>
        <div className="metric-bar">
          <div className="metric-bar-fill" style={{ width: `${metrics.cpu_percent}%` }}></div>
        </div>
      </div>

      {/* Memory */}
      <div className="metric-card">
        <div className="metric-label">Memory Usage</div>
        <div>
          <span className="metric-value">{metrics.memory_percent.toFixed(1)}</span>
          <span className="metric-unit">%</span>
        </div>
        <div className="metric-bar">
          <div className="metric-bar-fill" style={{ width: `${metrics.memory_percent}%` }}></div>
        </div>
      </div>

      {/* Memory Details */}
      <div className="metric-card">
        <div className="metric-label">Memory</div>
        <div>
          <span className="metric-value">{formatBytes(metrics.memory_used_mb * 1024 * 1024)}</span>
        </div>
        <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
          of {formatBytes(metrics.memory_total_mb * 1024 * 1024)}
        </div>
      </div>

      {/* Disk I/O */}
      <div className="metric-card">
        <div className="metric-label">Disk Read</div>
        <div>
          <span className="metric-value" style={{ fontSize: '1.8rem' }}>
            {formatRate(metrics.disk_read_rate)}
          </span>
        </div>
      </div>

      {/* Disk Write */}
      <div className="metric-card">
        <div className="metric-label">Disk Write</div>
        <div>
          <span className="metric-value" style={{ fontSize: '1.8rem' }}>
            {formatRate(metrics.disk_write_rate)}
          </span>
        </div>
      </div>

      {/* Network Sent */}
      <div className="metric-card">
        <div className="metric-label">Network Sent</div>
        <div>
          <span className="metric-value" style={{ fontSize: '1.8rem' }}>
            {formatRate(metrics.net_sent_rate)}
          </span>
        </div>
      </div>

      {/* Network Received */}
      <div className="metric-card">
        <div className="metric-label">Network Received</div>
        <div>
          <span className="metric-value" style={{ fontSize: '1.8rem' }}>
            {formatRate(metrics.net_recv_rate)}
          </span>
        </div>
      </div>

      {/* Process Count */}
      <div className="metric-card">
        <div className="metric-label">Processes</div>
        <div>
          <span className="metric-value">{metrics.processes.length}</span>
        </div>
      </div>
    </div>
  );
}

export default SystemOverview;
