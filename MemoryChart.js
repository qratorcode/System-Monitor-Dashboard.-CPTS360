import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

function MemoryChart({ memoryHistory, currentMemory }) {
  // Prepare data for chart
  const data = memoryHistory.map((value, index) => ({
    time: index,
    memory: Math.round(value * 10) / 10,
  }));

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          background: 'rgba(10, 14, 39, 0.95)',
          border: '1px solid var(--color-accent-green)',
          borderRadius: '4px',
          padding: '0.75rem',
          color: 'var(--color-accent-green)',
          fontSize: '0.85rem',
        }}>
          <p>{`Memory: ${payload[0].value.toFixed(1)}%`}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-container">
      <div className="chart-title">Memory Usage (Last 60s)</div>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(57, 255, 20, 0.1)" />
          <XAxis 
            dataKey="time" 
            stroke="var(--color-text-secondary)"
            style={{ fontSize: '0.85rem' }}
            interval={Math.floor(memoryHistory.length / 6) || 0}
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
            dataKey="memory"
            stroke="var(--color-accent-green)"
            dot={false}
            isAnimationActive={false}
            strokeWidth={2}
            name="Memory %"
          />
        </LineChart>
      </ResponsiveContainer>
      <div style={{
        marginTop: '1rem',
        padding: '0.75rem',
        background: 'rgba(57, 255, 20, 0.1)',
        borderRadius: '4px',
        textAlign: 'center',
        color: 'var(--color-accent-green)',
        fontWeight: 600,
      }}>
        Current: {currentMemory.toFixed(1)}%
      </div>
    </div>
  );
}

export default MemoryChart;
