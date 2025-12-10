import React, { useState, useEffect } from 'react';
import { debugApi } from '../services/debugApi';
import './DebugLogs.css';

export default function DebugLogs() {
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('errors'); // errors, executions, activities
  const [recentErrors, setRecentErrors] = useState(null);
  const [executions, setExecutions] = useState([]);
  const [activities, setActivities] = useState([]);
  const [selectedExecution, setSelectedExecution] = useState(null);
  const [executionDetails, setExecutionDetails] = useState(null);
  const [errorHours, setErrorHours] = useState(24);
  const [executionLimit, setExecutionLimit] = useState(50);
  const [executionStatus, setExecutionStatus] = useState('');
  const [activityLimit, setActivityLimit] = useState(50);
  const [activityStatus, setActivityStatus] = useState('');
  const [activityError, setActivityError] = useState('');

  useEffect(() => {
    loadRecentErrors();
  }, [errorHours]);

  useEffect(() => {
    if (activeTab === 'executions') {
      loadExecutions();
    }
  }, [activeTab, executionLimit, executionStatus]);

  useEffect(() => {
    if (activeTab === 'activities') {
      loadActivities();
    }
  }, [activeTab, activityLimit, activityStatus]);

  const loadRecentErrors = async () => {
    try {
      const data = await debugApi.getRecentErrors(errorHours);
      setRecentErrors(data);
    } catch (error) {
      console.error('Failed to load recent errors:', error);
    }
  };

  const loadExecutions = async () => {
    setLoading(true);
    try {
      const data = await debugApi.getPipelineExecutions(
        executionLimit,
        executionStatus || null
      );
      setExecutions(data.executions);
    } catch (error) {
      console.error('Failed to load executions:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadActivities = async () => {
    setLoading(true);
    setActivityError('');
    try {
      const data = await debugApi.getAgentActivities(
        activityLimit,
        activityStatus || null
      );
      setActivities(data.activities || []);
    } catch (error) {
      console.error('Failed to load activities:', error);
      setActivityError('Failed to load agent activities. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const loadExecutionDetails = async (executionId) => {
    try {
      const data = await debugApi.getExecutionDetails(executionId);
      setExecutionDetails(data);
      setSelectedExecution(executionId);
    } catch (error) {
      console.error('Failed to load execution details:', error);
      alert('Failed to load execution details');
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  const getStatusBadge = (status) => {
    const colors = {
      completed: '#10b981',
      running: '#3b82f6',
      failed: '#ef4444',
      pending: '#f59e0b',
    };
    return (
      <span
        style={{
          backgroundColor: colors[status] || '#6b7280',
          color: 'white',
          padding: '2px 8px',
          borderRadius: '4px',
          fontSize: '12px',
          fontWeight: 'bold',
        }}
      >
        {status}
      </span>
    );
  };

  return (
    <div className="debug-logs-container">
      <div className="debug-logs-header">
        <h1>🐛 Debug Logs</h1>
        <p>View pipeline executions, agent activities, and errors</p>
      </div>

      {/* Tabs */}
      <div className="debug-tabs">
        <button
          className={`debug-tab ${activeTab === 'errors' ? 'active' : ''}`}
          onClick={() => setActiveTab('errors')}
        >
          Recent Errors
        </button>
        <button
          className={`debug-tab ${activeTab === 'executions' ? 'active' : ''}`}
          onClick={() => setActiveTab('executions')}
        >
          Pipeline Executions
        </button>
        <button
          className={`debug-tab ${activeTab === 'activities' ? 'active' : ''}`}
          onClick={() => setActiveTab('activities')}
        >
          Agent Activities
        </button>
      </div>

      {/* Recent Errors Tab */}
      {activeTab === 'errors' && (
        <div className="debug-content">
          <div className="debug-filters">
            <label>
              Time Range:
              <select
                value={errorHours}
                onChange={(e) => setErrorHours(Number(e.target.value))}
              >
                <option value={1}>Last 1 hour</option>
                <option value={6}>Last 6 hours</option>
                <option value={24}>Last 24 hours</option>
                <option value={72}>Last 3 days</option>
                <option value={168}>Last 7 days</option>
              </select>
            </label>
            <button onClick={loadRecentErrors} className="refresh-btn">
              🔄 Refresh
            </button>
          </div>

          {recentErrors && (
            <div className="errors-section">
              <div className="error-summary">
                <div className="error-stat">
                  <h3>{recentErrors.summary.failed_executions}</h3>
                  <p>Failed Executions</p>
                </div>
                <div className="error-stat">
                  <h3>{recentErrors.summary.failed_activities}</h3>
                  <p>Failed Agent Activities</p>
                </div>
                <div className="error-stat">
                  <h3>{recentErrors.summary.executions_with_warnings}</h3>
                  <p>Executions with Warnings</p>
                </div>
              </div>

              {/* Failed Executions */}
              <div className="error-group">
                <h3>❌ Failed Executions</h3>
                {recentErrors.failed_executions.length === 0 ? (
                  <p className="no-data">No failed executions</p>
                ) : (
                  <div className="error-list">
                    {recentErrors.failed_executions.map((ex) => (
                      <div key={ex.id} className="error-card">
                        <div className="error-header">
                          <strong>#{ex.id}</strong> - {ex.pipeline_id}
                          <span className="error-date">
                            {formatDate(ex.created_at)}
                          </span>
                        </div>
                        <div className="error-topic">{ex.topic}</div>
                        <div className="error-stage">
                          Failed at: <strong>{ex.error_stage}</strong>
                        </div>
                        <div className="error-message">{ex.error_message}</div>
                        <button
                          onClick={() => loadExecutionDetails(ex.id)}
                          className="view-details-btn"
                        >
                          View Full Details
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Failed Activities */}
              <div className="error-group">
                <h3>⚠️ Failed Agent Activities</h3>
                {recentErrors.failed_activities.length === 0 ? (
                  <p className="no-data">No failed activities</p>
                ) : (
                  <div className="error-list">
                    {recentErrors.failed_activities.map((a) => (
                      <div key={a.id} className="error-card">
                        <div className="error-header">
                          <strong>{a.agent_name}</strong>
                          <span className="error-date">
                            {formatDate(a.started_at)}
                          </span>
                        </div>
                        <div className="error-stage">
                          Pipeline #{a.pipeline_execution_id} - Stage:{' '}
                          {a.stage}
                        </div>
                        <div className="error-message">{a.error_message}</div>
                        {a.warnings && a.warnings.length > 0 && (
                          <div className="warnings">
                            Warnings: {JSON.stringify(a.warnings)}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Warnings */}
              {recentErrors.executions_with_warnings.length > 0 && (
                <div className="error-group">
                  <h3>⚡ Executions with Warnings</h3>
                  <div className="error-list">
                    {recentErrors.executions_with_warnings.map((ex) => (
                      <div key={ex.id} className="error-card warning">
                        <div className="error-header">
                          <strong>#{ex.id}</strong> - {ex.pipeline_id}
                          <span className="error-date">
                            {formatDate(ex.created_at)}
                          </span>
                        </div>
                        <div className="error-topic">{ex.topic}</div>
                        <div className="error-stage">
                          Status: {getStatusBadge(ex.status)} - Stage:{' '}
                          {ex.current_stage}
                        </div>
                        <div className="error-message">{ex.error_message}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Pipeline Executions Tab */}
      {activeTab === 'executions' && (
        <div className="debug-content">
          <div className="debug-filters">
            <label>
              Limit:
              <select
                value={executionLimit}
                onChange={(e) => setExecutionLimit(Number(e.target.value))}
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </label>
            <label>
              Status:
              <select
                value={executionStatus}
                onChange={(e) => setExecutionStatus(e.target.value)}
              >
                <option value="">All</option>
                <option value="pending">Pending</option>
                <option value="running">Running</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>
            </label>
            <button onClick={loadExecutions} className="refresh-btn">
              🔄 Refresh
            </button>
          </div>

          {loading ? (
            <p>Loading...</p>
          ) : (
            <div className="executions-list">
              {executions.map((ex) => (
                <div key={ex.id} className="execution-card">
                  <div className="execution-header">
                    <div>
                      <strong>#{ex.id}</strong> - {ex.pipeline_id}
                    </div>
                    <div>{getStatusBadge(ex.status)}</div>
                  </div>
                  <div className="execution-body">
                    <div className="execution-field">
                      <strong>Topic:</strong> {ex.topic}
                    </div>
                    <div className="execution-field">
                      <strong>Type:</strong> {ex.content_type}
                    </div>
                    <div className="execution-field">
                      <strong>Started:</strong> {formatDate(ex.started_at)}
                    </div>
                    {ex.completed_at && (
                      <div className="execution-field">
                        <strong>Completed:</strong>{' '}
                        {formatDate(ex.completed_at)}
                      </div>
                    )}
                    {ex.current_stage && (
                      <div className="execution-field">
                        <strong>Current Stage:</strong> {ex.current_stage}
                      </div>
                    )}
                    {ex.total_duration_seconds && (
                      <div className="execution-field">
                        <strong>Duration:</strong> {ex.total_duration_seconds}s
                      </div>
                    )}
                    {ex.total_tokens_used && (
                      <div className="execution-field">
                        <strong>Tokens:</strong>{' '}
                        {ex.total_tokens_used.toLocaleString()}
                      </div>
                    )}
                    {ex.error_message && (
                      <div className="execution-error">
                        <strong>Error ({ex.error_stage}):</strong>{' '}
                        {ex.error_message}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => loadExecutionDetails(ex.id)}
                    className="view-details-btn"
                  >
                    View Full Details
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Agent Activities Tab */}
      {activeTab === 'activities' && (
        <div className="debug-content">
          <div className="debug-filters">
            <label>
              Limit:
              <select
                value={activityLimit}
                onChange={(e) => setActivityLimit(Number(e.target.value))}
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </label>
            <label>
              Status:
              <select
                value={activityStatus}
                onChange={(e) => setActivityStatus(e.target.value)}
              >
                <option value="">All</option>
                <option value="running">Running</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>
            </label>
            <button onClick={loadActivities} className="refresh-btn">
              🔄 Refresh
            </button>
          </div>

          {loading ? (
            <p>Loading...</p>
          ) : (
            <div className="activities-list">
              {activityError && (
                <p className="error-message">{activityError}</p>
              )}

              {!activityError && activities.length === 0 && (
                <p className="no-data">No agent activities found.</p>
              )}

              {activities.map((a) => (
                <div key={a.id} className="activity-card">
                  <div className="activity-header">
                    <div>
                      <strong>{a.agent_name}</strong>
                    </div>
                    <div>{getStatusBadge(a.status)}</div>
                  </div>
                  <div className="activity-body">
                    <div className="activity-field">
                      <strong>Pipeline:</strong> #{a.pipeline_execution_id}
                    </div>
                    <div className="activity-field">
                      <strong>Stage:</strong> {a.stage}
                    </div>
                    <div className="activity-field">
                      <strong>Started:</strong> {formatDate(a.started_at)}
                    </div>
                    {a.duration_seconds && (
                      <div className="activity-field">
                        <strong>Duration:</strong> {a.duration_seconds}s
                      </div>
                    )}
                    {a.decisions && a.decisions.length > 0 && (
                      <div className="activity-field">
                        <strong>Decisions:</strong>
                        <ul className="decision-list">
                          {a.decisions.map((d, i) => (
                            <li key={i}>{d.description}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {a.error_message && (
                      <div className="activity-error">
                        <strong>Error:</strong> {a.error_message}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Execution Details Modal */}
      {executionDetails && (
        <div className="modal-overlay" onClick={() => setExecutionDetails(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Execution #{selectedExecution} Details</h2>
              <button
                onClick={() => setExecutionDetails(null)}
                className="close-btn"
              >
                ✕
              </button>
            </div>
            <div className="modal-body">
              <div className="detail-section">
                <h3>Execution Info</h3>
                <div className="detail-grid">
                  <div>
                    <strong>Pipeline ID:</strong>{' '}
                    {executionDetails.execution.pipeline_id}
                  </div>
                  <div>
                    <strong>Status:</strong>{' '}
                    {getStatusBadge(executionDetails.execution.status)}
                  </div>
                  <div>
                    <strong>Topic:</strong> {executionDetails.execution.topic}
                  </div>
                  <div>
                    <strong>Type:</strong>{' '}
                    {executionDetails.execution.content_type}
                  </div>
                  <div>
                    <strong>Duration:</strong>{' '}
                    {executionDetails.execution.total_duration_seconds}s
                  </div>
                  <div>
                    <strong>Tokens:</strong>{' '}
                    {executionDetails.execution.total_tokens_used?.toLocaleString()}
                  </div>
                </div>
                {executionDetails.execution.error_message && (
                  <div className="error-box">
                    <strong>Error:</strong>{' '}
                    {executionDetails.execution.error_message}
                  </div>
                )}
              </div>

              <div className="detail-section">
                <h3>Agent Activities ({executionDetails.activities.length})</h3>
                {executionDetails.activities.map((a, i) => (
                  <div key={i} className="detail-card">
                    <div className="detail-card-header">
                      <strong>{a.agent_name}</strong>
                      {getStatusBadge(a.status)}
                    </div>
                    <div className="detail-card-body">
                      <div>Duration: {a.duration_seconds}s</div>
                      {a.decisions && a.decisions.length > 0 && (
                        <div>
                          <strong>Decisions:</strong>
                          <ul>
                            {a.decisions.map((d, j) => (
                              <li key={j}>{d.description}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {a.error_message && (
                        <div className="error-text">
                          Error: {a.error_message}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <div className="detail-section">
                <h3>Step Results ({executionDetails.steps.length})</h3>
                {executionDetails.steps.map((s, i) => (
                  <div key={i} className="detail-card">
                    <div className="detail-card-header">
                      <strong>
                        {s.stage_order}. {s.stage}
                      </strong>
                      {getStatusBadge(s.status)}
                    </div>
                    {s.error_message && (
                      <div className="error-text">Error: {s.error_message}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
