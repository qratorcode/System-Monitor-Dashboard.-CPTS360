import React from 'react';

function ProcessTable({ processes, filterText, onFilterChange, sortColumn, sortOrder, onSort }) {
  const formatCpuMemory = (value) => {
    return Math.round(value * 10) / 10;
  };

  const getSortIndicator = (column) => {
    if (sortColumn !== column) return ' ↕';
    return sortOrder === 'asc' ? ' ↑' : ' ↓';
  };

  const StateTag = ({ state }) => {
    let className = 'process-state';
    if (state === 'S') className += ' sleeping';
    if (state === 'T') className += ' stopped';
    
    const stateNames = {
      'R': 'Running',
      'S': 'Sleeping',
      'D': 'Disk',
      'Z': 'Zombie',
      'T': 'Stopped',
      'X': 'Dead',
    };

    return <span className={className}>{stateNames[state] || state}</span>;
  };

  return (
    <div className="process-table-container">
      <div className="process-table-header">Running Processes</div>
      
      <div className="process-filters">
        <input
          type="text"
          placeholder="Filter by process name or PID..."
          value={filterText}
          onChange={(e) => onFilterChange(e.target.value)}
        />
        <span style={{
          alignSelf: 'center',
          color: 'var(--color-text-secondary)',
          fontSize: '0.9rem',
        }}>
          {processes.length} processes
        </span>
      </div>

      {processes.length === 0 ? (
        <div className="empty-state">
          {filterText ? 'No processes match your filter' : 'No processes found'}
        </div>
      ) : (
        <table className="process-table">
          <thead>
            <tr>
              <th onClick={() => onSort('pid')} title="Click to sort">
                PID{getSortIndicator('pid')}
              </th>
              <th onClick={() => onSort('name')} title="Click to sort">
                Process Name{getSortIndicator('name')}
              </th>
              <th onClick={() => onSort('state')} title="Click to sort">
                State{getSortIndicator('state')}
              </th>
              <th onClick={() => onSort('cpu_percent')} title="Click to sort">
                CPU %{getSortIndicator('cpu_percent')}
              </th>
              <th onClick={() => onSort('memory_percent')} title="Click to sort">
                Memory %{getSortIndicator('memory_percent')}
              </th>
              <th onClick={() => onSort('num_threads')} title="Click to sort">
                Threads{getSortIndicator('num_threads')}
              </th>
              <th onClick={() => onSort('ppid')} title="Click to sort">
                Parent PID{getSortIndicator('ppid')}
              </th>
            </tr>
          </thead>
          <tbody>
            {processes.map((process) => (
              <tr key={process.pid}>
                <td>{process.pid}</td>
                <td className="process-name">{process.name}</td>
                <td>
                  <StateTag state={process.state} />
                </td>
                <td style={{
                  color: process.cpu_percent > 50 ? 'var(--color-accent-red)' :
                          process.cpu_percent > 20 ? 'var(--color-accent-orange)' :
                          'var(--color-accent-green)',
                  fontWeight: 500,
                }}>
                  {formatCpuMemory(process.cpu_percent)}%
                </td>
                <td style={{
                  color: process.memory_percent > 50 ? 'var(--color-accent-red)' :
                          process.memory_percent > 20 ? 'var(--color-accent-orange)' :
                          'var(--color-accent-green)',
                  fontWeight: 500,
                }}>
                  {formatCpuMemory(process.memory_percent)}%
                </td>
                <td>{process.num_threads}</td>
                <td>{process.ppid}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default ProcessTable;
