import React, { useState, useEffect } from 'react';
import { agentActivitiesApi } from '../../services/agentActivitiesApi';

export default function AgentActivitiesTab({ executionId, pipelineId }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [detailTab, setDetailTab] = useState('overview');
  const [downloadingReport, setDownloadingReport] = useState(false);

  useEffect(() => {
    if (executionId) {
      loadActivities();
    }
  }, [executionId]);

  const loadActivities = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await agentActivitiesApi.getSummary(executionId);
      setSummary(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadReport = async () => {
    try {
      setDownloadingReport(true);
      await agentActivitiesApi.downloadReport(executionId, pipelineId);
    } catch (err) {
      alert('Failed to download report: ' + err.message);
    } finally {
      setDownloadingReport(false);
    }
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0s';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(0);
    return `${minutes}m ${secs}s`;
  };

  const formatCost = (cost) => {
    if (!cost || cost === 0) return '$0.00';
    return `$${cost.toFixed(4)}`;
  };

  const getStatusColor = (status) => {
    switch(status) {
      case 'completed': return '#10b981';
      case 'failed': return '#ef4444';
      case 'running': return '#3b82f6';
      default: return '#6b7280';
    }
  };

  const getStatusIcon = (status) => {
    switch(status) {
      case 'completed': return '✓';
      case 'failed': return '✗';
      case 'running': return '⟳';
      default: return '○';
    }
  };

  if (loading) {
    return (
      <div style={{
        padding: '3rem',
        textAlign: 'center',
        color: '#666'
      }}>
        Loading agent activities...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        padding: '2rem',
        background: '#fee2e2',
        borderRadius: '8px',
        color: '#991b1b'
      }}>
        <strong>Error:</strong> {error}
      </div>
    );
  }

  if (!summary || summary.total_agents === 0) {
    return (
      <div style={{
        padding: '3rem',
        textAlign: 'center',
        color: '#666'
      }}>
        No agent activity data available for this execution.
      </div>
    );
  }

  return (
    <div className="agent-activities-container">
      {/* Summary Header */}
      <div style={{
        background: '#f9fafb',
        padding: '1.5rem',
        borderRadius: '8px',
        marginBottom: '1.5rem',
        border: '1px solid #e5e7eb'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1rem'
        }}>
          <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#111827' }}>
            Agent Execution Summary
          </h3>
          <button
            onClick={handleDownloadReport}
            disabled={downloadingReport}
            style={{
              padding: '0.5rem 1rem',
              background: downloadingReport ? '#9ca3af' : '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: downloadingReport ? 'not-allowed' : 'pointer',
              fontSize: '0.875rem',
              fontWeight: '500'
            }}
          >
            {downloadingReport ? 'Generating...' : '📄 Download PDF Report'}
          </button>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
          gap: '1rem'
        }}>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>
              TOTAL AGENTS
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#111827' }}>
              {summary.total_agents}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>
              TOTAL DURATION
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#111827' }}>
              {formatDuration(summary.total_duration)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>
              TOTAL TOKENS
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#111827' }}>
              {summary.total_tokens.toLocaleString()}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>
              TOTAL COST
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#111827' }}>
              {formatCost(summary.total_cost)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>
              DECISIONS MADE
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#111827' }}>
              {summary.total_decisions}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>
              RAG DOCS USED
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#111827' }}>
              {summary.total_rag_docs}
            </div>
          </div>
        </div>
      </div>

      {/* Agent List */}
      <div style={{
        display: 'grid',
        gap: '1rem'
      }}>
        {summary.agents.map((agent, index) => (
          <div
            key={agent.id}
            style={{
              background: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              overflow: 'hidden',
              transition: 'all 0.2s',
              cursor: 'pointer'
            }}
            onClick={() => setSelectedAgent(selectedAgent?.id === agent.id ? null : agent)}
          >
            {/* Agent Header */}
            <div style={{
              padding: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '1rem',
              background: selectedAgent?.id === agent.id ? '#f3f4f6' : 'white'
            }}>
              {/* Status Icon */}
              <div style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                background: getStatusColor(agent.status) + '20',
                color: getStatusColor(agent.status),
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.25rem',
                fontWeight: '600'
              }}>
                {index + 1}
              </div>

              {/* Agent Info */}
              <div style={{ flex: 1 }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  marginBottom: '0.25rem'
                }}>
                  <h4 style={{ margin: 0, fontSize: '1rem', color: '#111827' }}>
                    {agent.agent_name}
                  </h4>
                  <span style={{
                    padding: '0.125rem 0.5rem',
                    background: getStatusColor(agent.status) + '20',
                    color: getStatusColor(agent.status),
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    fontWeight: '500'
                  }}>
                    {agent.status.toUpperCase()}
                  </span>
                  {agent.badges && agent.badges.length > 0 && (
                    <span style={{
                      padding: '0.125rem 0.5rem',
                      background: '#fef3c7',
                      color: '#92400e',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                      fontWeight: '500'
                    }}>
                      {agent.badges[0].name}
                    </span>
                  )}
                </div>
                <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                  {formatDuration(agent.duration_seconds)} • {(agent.input_tokens + agent.output_tokens).toLocaleString()} tokens • {formatCost(agent.estimated_cost)}
                </div>
              </div>

              {/* Expand Icon */}
              <div style={{
                color: '#9ca3af',
                fontSize: '1.25rem'
              }}>
                {selectedAgent?.id === agent.id ? '▼' : '▶'}
              </div>
            </div>

            {/* Agent Details (Expanded) */}
            {selectedAgent?.id === agent.id && (
              <div style={{
                borderTop: '1px solid #e5e7eb',
                padding: '1rem',
                background: '#f9fafb'
              }}>
                {/* Detail Tabs */}
                <div style={{
                  display: 'flex',
                  gap: '0.5rem',
                  marginBottom: '1rem',
                  borderBottom: '1px solid #e5e7eb',
                  paddingBottom: '0.5rem'
                }}>
                  {['overview', 'decisions', 'rag', 'changes'].map(tab => (
                    <button
                      key={tab}
                      onClick={(e) => {
                        e.stopPropagation();
                        setDetailTab(tab);
                      }}
                      style={{
                        padding: '0.5rem 1rem',
                        background: detailTab === tab ? 'white' : 'transparent',
                        border: detailTab === tab ? '1px solid #e5e7eb' : 'none',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontSize: '0.875rem',
                        fontWeight: detailTab === tab ? '500' : '400',
                        color: detailTab === tab ? '#111827' : '#6b7280'
                      }}
                    >
                      {tab.charAt(0).toUpperCase() + tab.slice(1)}
                    </button>
                  ))}
                </div>

                {/* Overview Tab */}
                {detailTab === 'overview' && (
                  <div>
                    {agent.output_summary && Object.keys(agent.output_summary).length > 0 && (
                      <div style={{ marginBottom: '1rem' }}>
                        <div style={{ fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem', color: '#374151' }}>
                          Output Summary
                        </div>
                        <div style={{
                          background: 'white',
                          padding: '0.75rem',
                          borderRadius: '6px',
                          fontSize: '0.875rem',
                          border: '1px solid #e5e7eb'
                        }}>
                          {Object.entries(agent.output_summary).map(([key, value]) => (
                            <div key={key} style={{ marginBottom: '0.25rem' }}>
                              <strong>{key.replace(/_/g, ' ')}:</strong> {JSON.stringify(value)}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {agent.quality_metrics && Object.keys(agent.quality_metrics).length > 0 && (
                      <div>
                        <div style={{ fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem', color: '#374151' }}>
                          Quality Metrics
                        </div>
                        <div style={{
                          background: 'white',
                          padding: '0.75rem',
                          borderRadius: '6px',
                          fontSize: '0.875rem',
                          border: '1px solid #e5e7eb'
                        }}>
                          {Object.entries(agent.quality_metrics).map(([key, value]) => (
                            <div key={key} style={{ marginBottom: '0.25rem' }}>
                              <strong>{key.replace(/_/g, ' ')}:</strong> {JSON.stringify(value)}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Decisions Tab */}
                {detailTab === 'decisions' && (
                  <div>
                    {agent.decisions && agent.decisions.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {agent.decisions.map((decision, idx) => (
                          <div key={idx} style={{
                            background: 'white',
                            padding: '0.75rem',
                            borderRadius: '6px',
                            border: '1px solid #e5e7eb'
                          }}>
                            <div style={{ fontSize: '0.875rem', color: '#111827' }}>
                              {decision.description}
                            </div>
                            {decision.timestamp && (
                              <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '0.25rem' }}>
                                {new Date(decision.timestamp).toLocaleTimeString()}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ textAlign: 'center', padding: '2rem', color: '#9ca3af' }}>
                        No decisions recorded
                      </div>
                    )}
                  </div>
                )}

                {/* RAG Tab */}
                {detailTab === 'rag' && (
                  <div>
                    {agent.rag_documents && agent.rag_documents.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {agent.rag_documents.map((doc, idx) => (
                          <div key={idx} style={{
                            background: 'white',
                            padding: '0.75rem',
                            borderRadius: '6px',
                            border: '1px solid #e5e7eb'
                          }}>
                            <div style={{ fontSize: '0.875rem', color: '#111827', fontWeight: '500' }}>
                              {doc.doc_name}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem' }}>
                              {doc.chunks_used} chunks • {doc.purpose || 'Supporting content'}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ textAlign: 'center', padding: '2rem', color: '#9ca3af' }}>
                        No RAG documents used
                      </div>
                    )}
                  </div>
                )}

                {/* Changes Tab */}
                {detailTab === 'changes' && (
                  <div>
                    {agent.changes_made && agent.changes_made.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {agent.changes_made.map((change, idx) => (
                          <div key={idx} style={{
                            background: 'white',
                            padding: '0.75rem',
                            borderRadius: '6px',
                            border: '1px solid #e5e7eb'
                          }}>
                            <div style={{ fontSize: '0.875rem', color: '#111827', fontWeight: '500' }}>
                              {change.type?.replace(/_/g, ' ') || 'Change'}
                            </div>
                            {change.reason && (
                              <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem' }}>
                                {change.reason}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ textAlign: 'center', padding: '2rem', color: '#9ca3af' }}>
                        No content changes recorded
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
