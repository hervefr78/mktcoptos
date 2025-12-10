import React, { useState, useEffect } from 'react';
import './settings.css';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function InfrastructureDashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [infraData, setInfraData] = useState(null);
  const [lastChecked, setLastChecked] = useState(null);

  const fetchInfraHealth = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${API_BASE}/api/settings/health/infrastructure`);
      if (!response.ok) {
        throw new Error(`Failed to fetch infrastructure status: ${response.status}`);
      }
      const data = await response.json();
      setInfraData(data);
      setLastChecked(new Date());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInfraHealth();
    // Refresh every 30 seconds
    const interval = setInterval(fetchInfraHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIndicator = (status) => {
    switch (status) {
      case 'healthy':
      case 'running':
        return <span className="status-indicator status-green" title="Healthy">●</span>;
      case 'unhealthy':
      case 'timeout':
        return <span className="status-indicator status-yellow" title="Unhealthy">●</span>;
      case 'unreachable':
      case 'exited':
      case 'not_found':
      case 'error':
        return <span className="status-indicator status-red" title="Stopped">●</span>;
      default:
        return <span className="status-indicator status-gray" title="Unknown">●</span>;
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'healthy':
        return 'Healthy';
      case 'running':
        return 'Running';
      case 'unhealthy':
        return 'Unhealthy';
      case 'unreachable':
        return 'Unreachable';
      case 'timeout':
        return 'Timeout';
      case 'exited':
        return 'Stopped';
      case 'not_found':
        return 'Not Found';
      case 'error':
        return 'Error';
      default:
        return status || 'Unknown';
    }
  };

  const getServiceIcon = (type) => {
    switch (type) {
      case 'database':
        return '🗄️';
      case 'cache':
        return '⚡';
      case 'api':
        return '🔌';
      case 'web':
        return '🌐';
      case 'llm':
        return '🤖';
      case 'vectordb':
        return '📊';
      default:
        return '📦';
    }
  };

  const getServiceDescription = (name) => {
    const descriptions = {
      postgres: 'PostgreSQL database for persistent storage',
      redis: 'Redis cache for session and queue management',
      backend: 'FastAPI backend server',
      frontend: 'React frontend application',
      ollama: 'Local LLM inference server',
      chromadb: 'Vector database for RAG/embeddings',
    };
    return descriptions[name] || '';
  };

  if (loading && !infraData) {
    return (
      <div className="infrastructure-dashboard">
        <h3>Infrastructure Dashboard</h3>
        <div className="status-loading">Checking infrastructure...</div>
      </div>
    );
  }

  if (error && !infraData) {
    return (
      <div className="infrastructure-dashboard">
        <h3>Infrastructure Dashboard</h3>
        <div className="status-error">
          <p>Failed to check infrastructure: {error}</p>
          <button onClick={fetchInfraHealth} className="refresh-btn">Retry</button>
        </div>
      </div>
    );
  }

  const { services } = infraData || { services: [] };

  // Count healthy vs total
  const healthyCount = services.filter(s => s.status === 'healthy' || s.status === 'running').length;
  const totalCount = services.length;

  return (
    <div className="infrastructure-dashboard">
      <div className="status-header">
        <h3>Infrastructure Dashboard</h3>
        <button onClick={fetchInfraHealth} className="refresh-btn" disabled={loading}>
          {loading ? 'Checking...' : 'Refresh'}
        </button>
      </div>

      {lastChecked && (
        <p className="last-checked">
          Last checked: {lastChecked.toLocaleTimeString()}
        </p>
      )}

      {/* Summary */}
      <div className="infra-summary">
        <div className={`summary-card ${healthyCount === totalCount ? 'all-healthy' : 'some-issues'}`}>
          <span className="summary-count">{healthyCount}/{totalCount}</span>
          <span className="summary-label">Services Running</span>
        </div>
      </div>

      {/* Services Grid */}
      <div className="infra-services-grid">
        {services.map((service) => (
          <div key={service.name} className={`infra-service-card ${service.status === 'healthy' || service.status === 'running' ? 'service-healthy' : 'service-issue'}`}>
            <div className="infra-service-header">
              <span className="service-icon">{getServiceIcon(service.type)}</span>
              {getStatusIndicator(service.status)}
              <h4>{service.name}</h4>
            </div>
            <div className="infra-service-details">
              <p className="service-description">{getServiceDescription(service.name)}</p>
              <div className="service-meta">
                <span><strong>Status:</strong> {getStatusText(service.status)}</span>
                <span><strong>Host:</strong> {service.host}:{service.port}</span>
              </div>
              {service.error && (
                <p className="service-error">{service.error}</p>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="infra-actions">
        <h4>Quick Actions</h4>
        <p className="actions-help">Use these commands in your terminal to manage services:</p>
        <div className="action-commands">
          <div className="command-item">
            <code>./restart.sh</code>
            <span>Restart all services</span>
          </div>
          <div className="command-item">
            <code>./logs.sh backend</code>
            <span>View backend logs</span>
          </div>
          <div className="command-item">
            <code>docker compose ps</code>
            <span>Check all container status</span>
          </div>
          <div className="command-item">
            <code>docker compose restart &lt;service&gt;</code>
            <span>Restart specific service</span>
          </div>
        </div>
      </div>

      {/* System Info */}
      <div className="system-info">
        <h4>System Information</h4>
        <div className="info-grid">
          <div className="info-item">
            <span className="info-label">API Endpoint</span>
            <span className="info-value">{API_BASE}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Frontend URL</span>
            <span className="info-value">http://localhost:3000</span>
          </div>
          <div className="info-item">
            <span className="info-label">Database Port</span>
            <span className="info-value">5433</span>
          </div>
        </div>
      </div>
    </div>
  );
}
