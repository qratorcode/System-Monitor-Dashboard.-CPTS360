const express = require('express');
const WebSocket = require('ws');
const http = require('http');
const path = require('path');
const cors = require('cors');
const bodyParser = require('body-parser');

const app = express();
const server = http.createServer(app);

// Middleware
app.use(cors());
app.use(bodyParser.json());

// Serve React frontend static files (after build)
// In development, the React dev server will handle this
app.use(express.static(path.join(__dirname, '.')));

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: Date.now() });
});

// WebSocket server for metrics streaming
const wss = new WebSocket.Server({ server });

// Store all connected clients
const clients = new Set();
let latestMetrics = null;

wss.on('connection', (ws) => {
  console.log('[WS] New client connected. Total clients:', clients.size + 1);
  clients.add(ws);

  // Send latest metrics if available
  if (latestMetrics) {
    ws.send(JSON.stringify(latestMetrics));
  }

  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);

      // Store the latest metrics
      latestMetrics = {
        timestamp: Date.now(),
        ...data,
      };

      // Broadcast to all connected frontend clients
      clients.forEach((client) => {
        if (client.readyState === WebSocket.OPEN) {
          client.send(JSON.stringify(latestMetrics));
        }
      });

      console.log(`[METRICS] Received and broadcast: CPU=${data.cpu_percent.toFixed(1)}%, Memory=${data.memory_percent.toFixed(1)}%, Processes=${data.processes.length}`);
    } catch (error) {
      console.error('[WS] Error parsing message:', error);
    }
  });

  ws.on('close', () => {
    clients.delete(ws);
    console.log('[WS] Client disconnected. Total clients:', clients.size);
  });

  ws.on('error', (error) => {
    console.error('[WS] WebSocket error:', error);
    clients.delete(ws);
  });
});

// Fallback for React Router - serve index.html for all non-API routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

// Server configuration
const PORT = process.env.PORT || 3000;
const METRICS_WS_PORT = 8080; // Separate port for Python daemon metrics

// Create a separate WebSocket server on port 8080 for the Python daemon
const metricsServer = http.createServer();
const metricsWss = new WebSocket.Server({ server: metricsServer });

// This WebSocket server receives metrics from the Python daemon
metricsWss.on('connection', (ws) => {
  console.log('[METRICS-WS] Python daemon connected');

  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);

      // Store and broadcast metrics
      latestMetrics = {
        timestamp: Date.now(),
        ...data,
      };

      // Send to all frontend clients
      clients.forEach((client) => {
        if (client.readyState === WebSocket.OPEN) {
          client.send(JSON.stringify(latestMetrics));
        }
      });

      console.log(`[METRICS] CPU=${data.cpu_percent.toFixed(1)}%, Memory=${data.memory_percent.toFixed(1)}%, Processes=${data.processes.length}`);
    } catch (error) {
      console.error('[METRICS-WS] Error processing metrics:', error);
    }
  });

  ws.on('close', () => {
    console.log('[METRICS-WS] Python daemon disconnected');
  });

  ws.on('error', (error) => {
    console.error('[METRICS-WS] Error:', error);
  });
});

// Start servers
server.listen(PORT, () => {
  console.log(`✓ Frontend/API server running on http://localhost:${PORT}`);
  console.log(`✓ Open http://localhost:${PORT} in your browser`);
});

metricsServer.listen(METRICS_WS_PORT, () => {
  console.log(`✓ Metrics WebSocket server listening on ws://localhost:${METRICS_WS_PORT}`);
  console.log(`✓ Python daemon should connect to ws://localhost:${METRICS_WS_PORT}`);
});

// Handle graceful shutdown
process.on('SIGTERM', () => {
  console.log('\n[SERVER] Shutting down gracefully...');
  server.close(() => {
    console.log('[SERVER] Frontend server closed');
  });
  metricsServer.close(() => {
    console.log('[SERVER] Metrics server closed');
  });
  process.exit(0);
});
