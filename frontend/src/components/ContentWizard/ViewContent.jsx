import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { API_BASE } from '../../config/api';
import { fetchWithRetry } from '../../utils/fetchWithRetry';
import './wizard.css';

export default function ViewContent() {
  const { pipelineId } = useParams();
  const navigate = useNavigate();
  const [execution, setExecution] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [logsLoading, setLogsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('content');
  const [expandedStages, setExpandedStages] = useState({});

  useEffect(() => {
    fetchExecution();
  }, [pipelineId]);

  const fetchExecution = async () => {
    try {
      const res = await fetchWithRetry(`${API_BASE}/api/content-pipeline/history/${pipelineId}?include_full_result=true`, {
        credentials: 'include',
      });
      if (!res.ok) {
        throw new Error(`Failed to fetch content: ${res.status}`);
      }
      const data = await res.json();
      setExecution(data);
    } catch (err) {
      console.error('Failed to fetch execution:', err);
      setError(err.message || 'Unable to load content. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  const fetchLogs = async () => {
    setLogsLoading(true);
    try {
      const res = await fetchWithRetry(`${API_BASE}/api/content-pipeline/history/${pipelineId}/logs`, {
        credentials: 'include',
      });
      if (!res.ok) {
        throw new Error(`Failed to fetch logs: ${res.status}`);
      }
      const data = await res.json();
      setLogs(data.logs || []);
    } catch (err) {
      console.error('Failed to fetch logs:', err);
      alert('Unable to load logs. Please check your connection.');
    } finally {
      setLogsLoading(false);
    }
  };

  const handleDeleteLogs = async () => {
    if (!confirm('Are you sure you want to delete all logs for this pipeline? This cannot be undone.')) {
      return;
    }
    try {
      const res = await fetchWithRetry(`${API_BASE}/api/content-pipeline/history/${pipelineId}/logs`, {
        method: 'DELETE',
        credentials: 'include',
      });
      if (res.ok) {
        setLogs([]);
        alert('Logs deleted successfully');
      } else {
        alert('Failed to delete logs');
      }
    } catch (err) {
      console.error('Failed to delete logs:', err);
      alert('Unable to delete logs. Please check your connection.');
    }
  };

  const handleExportLogs = () => {
    const dataStr = JSON.stringify(logs, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pipeline-logs-${pipelineId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const toggleStage = (stageId) => {
    setExpandedStages(prev => ({
      ...prev,
      [stageId]: !prev[stageId]
    }));
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    if (tab === 'debug' && logs.length === 0) {
      fetchLogs();
    }
  };

  const handleBack = () => {
    navigate('/projects');
  };

  const handleCopyContent = () => {
    const content = execution?.final_content ||
                   execution?.final_result?.final_review?.final_text ||
                   execution?.final_result?.seo_version?.optimized_text ||
                   execution?.final_result?.draft?.full_text || '';
    navigator.clipboard.writeText(content);
    alert('Content copied to clipboard!');
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    alert('Copied to clipboard!');
  };

  if (loading) {
    return (
      <div className="content-wizard">
        <div className="wizard-loading">
          <div className="loading-spinner"></div>
          <p>Loading content...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="content-wizard">
        <div className="view-content-container">
          <div className="view-content-header">
            <button className="back-button" onClick={handleBack}>
              ← Back to Projects
            </button>
          </div>
          <div className="error-container">
            <p>Error: {error}</p>
            <button onClick={fetchExecution} className="btn-primary">
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const finalContent = execution?.final_content ||
                      execution?.final_result?.final_review?.final_text ||
                      execution?.final_result?.seo_version?.optimized_text ||
                      execution?.final_result?.draft?.full_text || '';

  const seoData = execution?.final_result?.seo_version?.on_page_seo;
  const suggestions = execution?.final_result?.final_review?.editor_notes_for_user || [];

  const stageNames = {
    trends_keywords: 'Trends & Keywords',
    tone_of_voice: 'Tone of Voice',
    structure_outline: 'Structure & Outline',
    writer: 'Writer',
    seo_optimizer: 'SEO & GEO Optimizer',
    originality_check: 'Originality Check',
    final_review: 'Final Review'
  };

  return (
    <div className="content-wizard">
      <div className="view-content-container">
        {/* Header */}
        <div className="view-content-header">
          <button className="back-button" onClick={handleBack}>
            ← Back to Projects
          </button>
          <h1>View Content</h1>
        </div>

        {/* Tabs */}
        <div className="view-content-tabs">
          <button
            className={`tab-btn ${activeTab === 'content' ? 'active' : ''}`}
            onClick={() => handleTabChange('content')}
          >
            Content
          </button>
          <button
            className={`tab-btn ${activeTab === 'debug' ? 'active' : ''}`}
            onClick={() => handleTabChange('debug')}
          >
            Debug Logs
          </button>
        </div>

        {activeTab === 'content' ? (
          <>
            {/* Content Info */}
            <div className="view-content-info">
              <div className="info-item">
                <strong>Topic:</strong> {execution?.topic}
              </div>
              <div className="info-item">
                <strong>Type:</strong> {execution?.content_type}
              </div>
              <div className="info-item">
                <strong>Status:</strong>
                <span className={`status-badge ${execution?.status}`}>
                  {execution?.status}
                </span>
              </div>
              {execution?.word_count && (
                <div className="info-item">
                  <strong>Word Count:</strong> {execution.word_count}
                </div>
              )}
              {execution?.seo_score && (
                <div className="info-item">
                  <strong>SEO & GEO Score:</strong> {execution.seo_score}
                </div>
              )}
              {execution?.final_result?.brave_metrics && (
                <div className="info-item">
                  <strong>Brave Search:</strong> {execution.final_result.brave_metrics.requests_made} requests, {execution.final_result.brave_metrics.results_received} results
                </div>
              )}
              <div className="info-item">
                <strong>Created:</strong> {new Date(execution?.created_at).toLocaleString()}
              </div>
            </div>

            {/* SEO & GEO Metadata */}
            {seoData && (
              <div className="view-content-seo">
                <h3>SEO & GEO Metadata</h3>
                <div className="seo-fields">
                  {seoData.title_tag && (
                    <div className="seo-field">
                      <label>Title Tag:</label>
                      <span>{seoData.title_tag}</span>
                    </div>
                  )}
                  {seoData.meta_description && (
                    <div className="seo-field">
                      <label>Meta Description:</label>
                      <span>{seoData.meta_description}</span>
                    </div>
                  )}
                  {seoData.focus_keyword && (
                    <div className="seo-field">
                      <label>Focus Keyword:</label>
                      <span>{seoData.focus_keyword}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Main Content */}
            <div className="view-content-main">
              <div className="content-header">
                <h3>Generated Content</h3>
                <button className="btn-secondary" onClick={handleCopyContent}>
                  Copy to Clipboard
                </button>
              </div>
              <div className="content-body">
                <pre>{finalContent}</pre>
              </div>
            </div>

            {/* Editor Suggestions */}
            {suggestions.length > 0 && (
              <div className="view-content-suggestions">
                <h3>Editor Notes</h3>
                <ul>
                  {suggestions.map((note, index) => (
                    <li key={index}>{note}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Actions */}
            <div className="view-content-actions">
              <button className="btn-secondary" onClick={handleBack}>
                Back to Projects
              </button>
              <button className="btn-primary" onClick={handleCopyContent}>
                Copy Content
              </button>
            </div>
          </>
        ) : (
          /* Debug Logs Tab */
          <div className="debug-logs-container">
            <div className="debug-logs-header">
              <h3>Agent Communication Logs</h3>
              <div className="debug-logs-actions">
                <button className="btn-small btn-secondary" onClick={fetchLogs}>
                  Refresh
                </button>
                <button className="btn-small btn-secondary" onClick={handleExportLogs} disabled={logs.length === 0}>
                  Export JSON
                </button>
                <button className="btn-small btn-danger" onClick={handleDeleteLogs} disabled={logs.length === 0}>
                  Delete Logs
                </button>
              </div>
            </div>

            {logsLoading ? (
              <div className="logs-loading">
                <div className="loading-spinner-small"></div>
                <span>Loading logs...</span>
              </div>
            ) : logs.length === 0 ? (
              <div className="no-logs">
                <p>No agent logs available for this pipeline.</p>
                <p className="no-logs-hint">Logs are captured when running the pipeline with logging enabled.</p>
              </div>
            ) : (
              <div className="logs-list">
                {logs.map((log, index) => (
                  <div key={log.id || index} className={`log-item ${log.status}`}>
                    <div
                      className="log-header"
                      onClick={() => toggleStage(log.stage)}
                    >
                      <div className="log-title">
                        <span className="log-order">{log.stage_order}</span>
                        <span className="log-stage">{stageNames[log.stage] || log.stage}</span>
                        <span className={`log-status-badge ${log.status}`}>{log.status}</span>
                      </div>
                      <div className="log-meta">
                        {log.duration_seconds && <span>{log.duration_seconds}s</span>}
                        {log.tokens_used && <span>{log.tokens_used} tokens</span>}
                        {log.model_used && <span>{log.model_used}</span>}
                        <span className="expand-icon">{expandedStages[log.stage] ? '▼' : '▶'}</span>
                      </div>
                    </div>

                    {expandedStages[log.stage] && (
                      <div className="log-details">
                        {/* Input Context */}
                        {log.input_context && (
                          <div className="log-section">
                            <div className="log-section-header">
                              <h4>Input Context</h4>
                              <button
                                className="btn-tiny"
                                onClick={() => copyToClipboard(JSON.stringify(log.input_context, null, 2))}
                              >
                                Copy
                              </button>
                            </div>
                            <pre className="log-content">{JSON.stringify(log.input_context, null, 2)}</pre>
                          </div>
                        )}

                        {/* System Prompt */}
                        {log.prompt_system && (
                          <div className="log-section">
                            <div className="log-section-header">
                              <h4>System Prompt</h4>
                              <button
                                className="btn-tiny"
                                onClick={() => copyToClipboard(log.prompt_system)}
                              >
                                Copy
                              </button>
                            </div>
                            <pre className="log-content">{log.prompt_system}</pre>
                          </div>
                        )}

                        {/* User Prompt */}
                        {log.prompt_user && (
                          <div className="log-section">
                            <div className="log-section-header">
                              <h4>User Prompt</h4>
                              <button
                                className="btn-tiny"
                                onClick={() => copyToClipboard(log.prompt_user)}
                              >
                                Copy
                              </button>
                            </div>
                            <pre className="log-content">{log.prompt_user}</pre>
                          </div>
                        )}

                        {/* Raw Response */}
                        {log.raw_response && (
                          <div className="log-section">
                            <div className="log-section-header">
                              <h4>Raw Response</h4>
                              <button
                                className="btn-tiny"
                                onClick={() => copyToClipboard(log.raw_response)}
                              >
                                Copy
                              </button>
                            </div>
                            <pre className="log-content">{log.raw_response}</pre>
                          </div>
                        )}

                        {/* Parsed Result */}
                        {log.result && (
                          <div className="log-section">
                            <div className="log-section-header">
                              <h4>Parsed Result</h4>
                              <button
                                className="btn-tiny"
                                onClick={() => copyToClipboard(JSON.stringify(log.result, null, 2))}
                              >
                                Copy
                              </button>
                            </div>
                            <pre className="log-content">{JSON.stringify(log.result, null, 2)}</pre>
                          </div>
                        )}

                        {/* Error */}
                        {log.error_message && (
                          <div className="log-section error">
                            <h4>Error</h4>
                            <pre className="log-content error">{log.error_message}</pre>
                          </div>
                        )}

                        {/* Metrics */}
                        <div className="log-metrics">
                          <span>Input: {log.input_tokens || 0} tokens</span>
                          <span>Output: {log.output_tokens || 0} tokens</span>
                          {log.temperature && <span>Temp: {log.temperature}</span>}
                          {log.retry_count > 0 && <span>Retries: {log.retry_count}</span>}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
