import React from 'react';

export default function AgentActivityPanel({ agents, metrics, onClose }) {
  const activeAgents = agents.filter(a => a.status === 'working');
  const completedAgents = agents.filter(a => a.status === 'complete');
  const pendingAgents = agents.filter(a => a.status === 'pending');

  const getAgentIcon = (agentId) => {
    const icons = {
      trends_keywords: '🔍',
      tone_of_voice: '🎨',
      structure_outline: '📋',
      writer: '✍️',
      seo_optimizer: '📈',
      originality_check: '✅',
      final_review: '🎯',
    };
    return icons[agentId] || '🤖';
  };

  return (
    <div className="agent-activity-panel">
      <div className="panel-header">
        <h3>Agent Activity</h3>
        <button className="panel-close" onClick={onClose}>×</button>
      </div>

      <div className="panel-content">
        {/* Active Agents */}
        {activeAgents.length > 0 && (
          <div className="agent-section">
            <h4 className="section-title">
              <span className="pulse-dot" />
              Active Agents ({activeAgents.length})
            </h4>
            {activeAgents.map(agent => (
              <div key={agent.id} className="agent-card active">
                <div className="agent-card-header">
                  <span className="agent-icon">{getAgentIcon(agent.id)}</span>
                  <span className="agent-name">{agent.name}</span>
                </div>
                <p className="agent-task">{agent.task}</p>
                <div className="agent-progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${agent.progress}%` }}
                  />
                </div>
                <span className="progress-percent">{agent.progress}%</span>
              </div>
            ))}
          </div>
        )}

        {/* Completed Agents */}
        {completedAgents.length > 0 && (
          <div className="agent-section">
            <h4 className="section-title">
              ✓ Completed ({completedAgents.length})
            </h4>
            <ul className="completed-list">
              {completedAgents.map(agent => (
                <li key={agent.id}>
                  <span className="agent-icon small">{getAgentIcon(agent.id)}</span>
                  {agent.name}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Pending Agents */}
        {pendingAgents.length > 0 && (
          <div className="agent-section">
            <h4 className="section-title pending">
              Pending ({pendingAgents.length})
            </h4>
            <ul className="pending-list">
              {pendingAgents.map(agent => (
                <li key={agent.id}>
                  <span className="agent-icon small">{getAgentIcon(agent.id)}</span>
                  {agent.name}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Metrics Footer */}
      <div className="panel-footer">
        <div className="metric">
          <span className="metric-label">Total time</span>
          <span className="metric-value">
            {metrics.totalTime > 0 ? `${Math.floor(metrics.totalTime / 60)}m ${metrics.totalTime % 60}s` : '--'}
          </span>
        </div>
        <div className="metric">
          <span className="metric-label">Tokens used</span>
          <span className="metric-value">{metrics.tokensUsed.toLocaleString()}</span>
        </div>
        <div className="metric">
          <span className="metric-label">Est. cost</span>
          <span className="metric-value">${metrics.estimatedCost.toFixed(3)}</span>
        </div>
      </div>
    </div>
  );
}
