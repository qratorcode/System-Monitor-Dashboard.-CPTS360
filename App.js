import React, { useState, useEffect } from 'react';
import './App.css';
import Dashboard from './components/Dashboard';

function App() {
  const [metrics, setMetrics] = useState({
    timestamp: Date.now(),
    cpu_percent: 0,
    memory_percent: 0,
    memory_used_mb: 0,
    memory_total_mb: 0,
    disk_read_rate: 0,
    disk_write_rate: 0,
    net_sent_rate: 0,
    net_recv_rate: 0,
    processes: [],
    cpu_history: [],
    memory_history: [],
  });

  const [connectionStatus, setConnectionStatus] = useState('connecting');

  useEffect(() => {
    let ws = null;
    let reconnectTimeout = null;

    const connectWebSocket = () => {
      try {
        ws = new WebSocket('ws://localhost:8080');

        ws.onopen = () => {
          setConnectionStatus('connected');
          console.log('Connected to monitoring server');
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setMetrics((prevMetrics) => {
              const newCpuHistory = [...prevMetrics.cpu_history, data.cpu_percent].slice(-60);
              const newMemHistory = [...prevMetrics.memory_history, data.memory_percent].slice(-60);

              return {
                ...data,
                cpu_history: newCpuHistory,
                memory_history: newMemHistory,
              };
            });
          } catch (error) {
            console.error('Failed to parse metrics:', error);
          }
        };

        ws.onerror = (error) => {
          setConnectionStatus('error');
          console.error('WebSocket error:', error);
        };

        ws.onclose = () => {
          setConnectionStatus('disconnected');
          console.log('Disconnected from monitoring server, attempting to reconnect...');
          reconnectTimeout = setTimeout(connectWebSocket, 3000);
        };
      } catch (error) {
        console.error('WebSocket connection error:', error);
        setConnectionStatus('error');
        reconnectTimeout = setTimeout(connectWebSocket, 3000);
      }
    };

    connectWebSocket();

    return () => {
      if (ws) {
        ws.close();
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
    };
  }, []);

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-content">
          <h1>System Monitor</h1>
          <div className="status-indicator">
            <span className={`status-dot ${connectionStatus}`}></span>
            <span className="status-text">
              {connectionStatus === 'connected' && 'Live'}
              {connectionStatus === 'disconnected' && 'Reconnecting...'}
              {connectionStatus === 'connecting' && 'Connecting...'}
              {connectionStatus === 'error' && 'Connection Error'}
            </span>
          </div>
        </div>
      </header>

      <main className="app-main">
        <Dashboard metrics={metrics} />
      </main>

      <footer className="app-footer">
        <p>Real-time system monitoring • Updates every ~500ms</p>
      </footer>
    </div>
  );
}

export default App;
