import React, { useState, useEffect } from 'react';
import './settings.css';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function ServicesStatus() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [healthData, setHealthData] = useState(null);
  const [lastChecked, setLastChecked] = useState(null);

  const fetchHealth = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${API_BASE}/api/settings/health/services`);
      if (!response.ok) {
        throw new Error(`Failed to fetch health status: ${response.status}`);
      }
      const data = await response.json();
      setHealthData(data);
      setLastChecked(new Date());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    // Refresh every 30 seconds
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIndicator = (status) => {
    switch (status) {
      case 'connected':
        return <span className="status-indicator status-green" title="Connected">●</span>;
      case 'disconnected':
        return <span className="status-indicator status-red" title="Disconnected">●</span>;
      case 'error':
        return <span className="status-indicator status-yellow" title="Error">●</span>;
      case 'not_configured':
        return <span className="status-indicator status-gray" title="Not Configured">●</span>;
      default:
        return <span className="status-indicator status-gray" title="Unknown">●</span>;
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'connected':
        return 'Connected';
      case 'disconnected':
        return 'Disconnected';
      case 'error':
        return 'Error';
      case 'not_configured':
        return 'Not Configured';
      default:
        return 'Unknown';
    }
  };

  if (loading && !healthData) {
    return (
      <div className="services-status">
        <h3>Services Status</h3>
        <div className="status-loading">Checking services...</div>
      </div>
    );
  }

  if (error && !healthData) {
    return (
      <div className="services-status">
        <h3>Services Status</h3>
        <div className="status-error">
          <p>Failed to check services: {error}</p>
          <button onClick={fetchHealth} className="refresh-btn">Retry</button>
        </div>
      </div>
    );
  }

  const { services, llmProvider, imageProvider } = healthData || {};

  return (
    <div className="services-status">
      <div className="status-header">
        <h3>Services Status</h3>
        <button onClick={fetchHealth} className="refresh-btn" disabled={loading}>
          {loading ? 'Checking...' : 'Refresh'}
        </button>
      </div>

      {lastChecked && (
        <p className="last-checked">
          Last checked: {lastChecked.toLocaleTimeString()}
        </p>
      )}

      {/* Current Selection Summary */}
      <div className="current-selection">
        <h4>Current Configuration</h4>
        <div className="selection-grid">
          <div className="selection-item">
            <span className="selection-label">LLM Provider:</span>
            <span className="selection-value">{llmProvider === 'openai' ? 'OpenAI' : 'Ollama'}</span>
          </div>
          <div className="selection-item">
            <span className="selection-label">Image Provider:</span>
            <span className="selection-value">
              {imageProvider === 'openai' ? 'OpenAI (DALL-E)' :
               imageProvider === 'comfyui' ? 'ComfyUI (SDXL)' :
               imageProvider === 'stable-diffusion' ? 'Stable Diffusion' :
               imageProvider === 'hybrid' ? 'Hybrid' : imageProvider}
            </span>
          </div>
        </div>
      </div>

      {/* Services Grid */}
      <div className="services-grid">
        {/* Ollama */}
        <div className={`service-card ${llmProvider === 'ollama' ? 'active-service' : ''}`}>
          <div className="service-header">
            {getStatusIndicator(services?.ollama?.status)}
            <h4>Ollama</h4>
            {llmProvider === 'ollama' && <span className="active-badge">Active LLM</span>}
          </div>
          <div className="service-details">
            <p><strong>Status:</strong> {getStatusText(services?.ollama?.status)}</p>
            <p><strong>URL:</strong> {services?.ollama?.url}</p>
            {services?.ollama?.modelsCount !== undefined && (
              <p><strong>Models:</strong> {services?.ollama?.modelsCount} installed</p>
            )}
            {services?.ollama?.selectedModel && (
              <p><strong>Selected:</strong> {services?.ollama?.selectedModel}</p>
            )}
            {services?.ollama?.models && services.ollama.models.length > 0 && (
              <div className="models-list">
                <strong>Available:</strong>
                <ul>
                  {services.ollama.models.map((model, idx) => (
                    <li key={idx}>{model}</li>
                  ))}
                </ul>
              </div>
            )}
            {services?.ollama?.error && (
              <p className="service-error"><strong>Error:</strong> {services.ollama.error}</p>
            )}
          </div>
        </div>

        {/* OpenAI */}
        <div className={`service-card ${llmProvider === 'openai' || imageProvider === 'openai' ? 'active-service' : ''}`}>
          <div className="service-header">
            {getStatusIndicator(services?.openai?.status)}
            <h4>OpenAI</h4>
            {llmProvider === 'openai' && <span className="active-badge">Active LLM</span>}
            {imageProvider === 'openai' && <span className="active-badge">Active Image</span>}
          </div>
          <div className="service-details">
            <p><strong>Status:</strong> {getStatusText(services?.openai?.status)}</p>
            <p><strong>API Key:</strong> {services?.openai?.configured ? 'Configured' : 'Not Set'}</p>
            {services?.openai?.selectedModel && (
              <p><strong>LLM Model:</strong> {services?.openai?.selectedModel}</p>
            )}
            {services?.openai?.imageModel && (
              <p><strong>Image Model:</strong> {services?.openai?.imageModel}</p>
            )}
            {services?.openai?.error && (
              <p className="service-error"><strong>Error:</strong> {services.openai.error}</p>
            )}
          </div>
        </div>

        {/* ComfyUI */}
        <div className={`service-card ${imageProvider === 'comfyui' || imageProvider === 'hybrid' ? 'active-service' : ''}`}>
          <div className="service-header">
            {getStatusIndicator(services?.comfyui?.status)}
            <h4>ComfyUI</h4>
            {(imageProvider === 'comfyui' || imageProvider === 'hybrid') && (
              <span className="active-badge">Active Image</span>
            )}
          </div>
          <div className="service-details">
            <p><strong>Status:</strong> {getStatusText(services?.comfyui?.status)}</p>
            <p><strong>URL:</strong> {services?.comfyui?.url}</p>
            {services?.comfyui?.selectedModel && (
              <p><strong>Model:</strong> {services?.comfyui?.selectedModel}</p>
            )}
            {services?.comfyui?.error && (
              <p className="service-error"><strong>Error:</strong> {services.comfyui.error}</p>
            )}
          </div>
        </div>
      </div>

      {/* Help Text */}
      <div className="status-help">
        <h4>Status Legend</h4>
        <ul>
          <li><span className="status-indicator status-green">●</span> Connected - Service is running and accessible</li>
          <li><span className="status-indicator status-yellow">●</span> Error - Service has configuration issues</li>
          <li><span className="status-indicator status-red">●</span> Disconnected - Cannot connect to service</li>
          <li><span className="status-indicator status-gray">●</span> Not Configured - Service not set up</li>
        </ul>
      </div>
    </div>
  );
}
