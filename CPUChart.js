import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

function CPUChart({ cpuHistory, currentCpu }) {
  // Prepare data for chart
  const data = cpuHistory.map((value, index) => ({
    time: index,
    cpu: Math.round(value * 10) / 10,
  }));

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          background: 'rgba(10, 14, 39, 0.95)',
          border: '1px solid var(--color-accent-cyan)',
          borderRadius: '4px',
          padding: '0.75rem',
          color: 'var(--color-accent-cyan)',
          fontSize: '0.85rem',
        }}>
          <p>{`CPU: ${payload[0].value.toFixed(1)}%`}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-container">
      <div className="chart-title">CPU Usage (Last 60s)</div>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 217, 255, 0.1)" />
          <XAxis 
            dataKey="time" 
            stroke="var(--color-text-secondary)"
            style={{ fontSize: '0.85rem' }}
            interval={Math.floor(cpuHistory.length / 6) || 0}
          />
          <YAxis 
            domain={[0, 100]} 
            stroke="var(--color-text-secondary)"
            style={{ fontSize: '0.85rem' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend 
            wrapperStyle={{ paddingTop: '1rem' }}
            contentStyle={{
              background: 'rgba(10, 14, 39, 0.95)',
              border: '1px solid var(--color-border)',
              borderRadius: '4px',
            }}
          />
          <Line
            type="monotone"
            dataKey="cpu"
            stroke="var(--color-accent-cyan)"
            dot={false}
            isAnimationActive={false}
            strokeWidth={2}
            name="CPU %"
          />
        </LineChart>
      </ResponsiveContainer>
      <div style={{
        marginTop: '1rem',
        padding: '0.75rem',
        background: 'rgba(0, 217, 255, 0.1)',
        borderRadius: '4px',
        textAlign: 'center',
        color: 'var(--color-accent-cyan)',
        fontWeight: 600,
      }}>
        Current: {currentCpu.toFixed(1)}%
      </div>
    </div>
  );
}

export default CPUChart;
