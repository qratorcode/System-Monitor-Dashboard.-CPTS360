import React, { useState } from 'react';
import CPUChart from './CPUChart';
import MemoryChart from './MemoryChart';
import SystemOverview from './SystemOverview';
import ProcessTable from './ProcessTable';

function Dashboard({ metrics }) {
  const [sortColumn, setSortColumn] = useState('cpu_percent');
  const [sortOrder, setSortOrder] = useState('desc');
  const [filterText, setFilterText] = useState('');

  const handleSort = (column) => {
    if (sortColumn === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortOrder('desc');
    }
  };

  const filteredProcesses = metrics.processes.filter((process) =>
    process.name.toLowerCase().includes(filterText.toLowerCase()) ||
    process.pid.toString().includes(filterText)
  );

  const sortedProcesses = [...filteredProcesses].sort((a, b) => {
    let aVal = a[sortColumn];
    let bVal = b[sortColumn];

    if (typeof aVal === 'string') {
      aVal = aVal.toLowerCase();
      bVal = bVal.toLowerCase();
    }

    if (sortOrder === 'asc') {
      return aVal > bVal ? 1 : -1;
    } else {
      return aVal < bVal ? 1 : -1;
    }
  });

  return (
    <div className="dashboard">
      {/* System Overview */}
      <SystemOverview metrics={metrics} />

      {/* Charts Grid */}
      <div className="charts-grid">
        <CPUChart cpuHistory={metrics.cpu_history} currentCpu={metrics.cpu_percent} />
        <MemoryChart memoryHistory={metrics.memory_history} currentMemory={metrics.memory_percent} />
      </div>

      {/* Process Table */}
      <ProcessTable
        processes={sortedProcesses}
        filterText={filterText}
        onFilterChange={setFilterText}
        sortColumn={sortColumn}
        sortOrder={sortOrder}
        onSort={handleSort}
      />
    </div>
  );
}

export default Dashboard;
