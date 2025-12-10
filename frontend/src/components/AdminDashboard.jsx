import React, { useEffect, useState } from 'react';
import UserTable from './Admin/UserTable';

const AdminDashboard = () => {
  const [logs, setLogs] = useState('');

  const fetchLogs = async () => {
    try {
      const res = await fetch('/logs');
      const text = await res.text();
      setLogs(text);
    } catch (err) {
      setLogs('Unable to fetch logs');
    }
  };

  useEffect(() => {
    fetchLogs();
    const id = setInterval(fetchLogs, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <div>
      <h2>Recent Logs</h2>
      <pre style={{ maxHeight: '300px', overflowY: 'scroll', background: '#eee', padding: '10px' }}>
        {logs}
      </pre>
      <UserTable />
    </div>
  );
};

export default AdminDashboard;
