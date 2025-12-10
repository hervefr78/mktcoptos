import React, { useState, useEffect, useRef } from 'react';
import CheckpointDialog from './CheckpointDialog';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Helper function to convert language code to full language name
const getLanguageName = (code) => {
  const languageMap = {
    'auto': 'English', // Default to English for auto-detect
    'en': 'English',
    'fr': 'French',
    'de': 'German',
    'es': 'Spanish',
    'it': 'Italian'
  };
  return languageMap[code] || 'English';
};

export default function StepGeneration({ data, updateData, agents, updateAgent, metrics, setMetrics, onNext, onBack }) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentAgentIndex, setCurrentAgentIndex] = useState(-1);
  const [error, setError] = useState(null);
  const [pipelineResult, setPipelineResult] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [agentMetrics, setAgentMetrics] = useState({});
  const eventSourceRef = useRef(null);

  // Checkpoint mode state - read from user preferences
  const [checkpointMode, setCheckpointMode] = useState(() => {
    const saved = localStorage.getItem('checkpointMode');
    return saved === 'true' ? 'checkpoint' : 'automatic';
  });
  const [currentCheckpoint, setCurrentCheckpoint] = useState(null);
  const [checkpointSessionId, setCheckpointSessionId] = useState(null);

  // New 7-agent pipeline matching backend
  const agentPipeline = [
    { id: 'trends_keywords', name: 'Trends & Keywords', icon: '🔍', description: 'Researching trends and keywords' },
    { id: 'tone_of_voice', name: 'Tone of Voice', icon: '🎨', description: 'Analyzing brand voice' },
    { id: 'structure_outline', name: 'Structure & Outline', icon: '📋', description: 'Creating content structure' },
    { id: 'writer', name: 'Writer', icon: '✍️', description: 'Writing content' },
    { id: 'seo_optimizer', name: 'SEO Optimizer', icon: '📈', description: 'Optimizing for SEO' },
    { id: 'originality_check', name: 'Originality Check', icon: '✅', description: 'Checking originality' },
    { id: 'final_review', name: 'Final Review', icon: '🎯', description: 'Final polish and review' },
  ];

  // Restore saved agent metrics when navigating back or when timeline data loads
  useEffect(() => {
    if (data.agentMetrics && Object.keys(data.agentMetrics).length > 0) {
      console.log('Restoring agent metrics from parent:', data.agentMetrics);
      setAgentMetrics(data.agentMetrics);
    }
  }, [data.agentMetrics]); // Re-run when parent's agentMetrics change

  // Sync agentMetrics to parent component when generation completes
  useEffect(() => {
    if (!isGenerating && Object.keys(agentMetrics).length > 0) {
      updateData({ agentMetrics });
    }
  }, [agentMetrics, isGenerating]);

  // Cleanup event source on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const handleCheckpointAction = async (actionData) => {
    if (!checkpointSessionId) {
      console.error('[CHECKPOINT] No checkpoint session ID');
      return;
    }

    console.log('[CHECKPOINT] Sending action:', actionData.action, 'for session:', checkpointSessionId);

    try {
      let endpoint = '';
      let body = {};

      if (actionData.action === 'save') {
        // Save for later
        endpoint = '/api/content-pipeline/checkpoint/save';
        body = { session_id: checkpointSessionId };
      } else {
        // All other actions
        endpoint = '/api/content-pipeline/checkpoint/action';
        body = {
          session_id: checkpointSessionId,
          action: actionData.action,
          edited_output: actionData.edited_output || null,
          next_agent_instructions: actionData.next_agent_instructions || null,
          restart_instructions: actionData.restart_instructions || null
        };
      }

      console.log('[CHECKPOINT] Request body:', body);

      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      console.log('[CHECKPOINT] Response status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('[CHECKPOINT] Error response:', errorText);
        throw new Error(`Checkpoint action failed: ${response.status}`);
      }

      const result = await response.json();
      console.log('[CHECKPOINT] Action result:', result);

      // Close checkpoint dialog
      setCurrentCheckpoint(null);

      // If cancelled or saved, stop generation
      if (actionData.action === 'cancel' || actionData.action === 'save') {
        setIsGenerating(false);
        updateData({ isGenerating: false });
      }

    } catch (err) {
      console.error('Checkpoint action error:', err);
      setError(err.message);
    }
  };

  const startGeneration = async () => {
    setIsGenerating(true);
    setError(null);
    setPipelineResult(null);
    setAgentMetrics({});
    updateData({ isGenerating: true });
    const startTime = Date.now();

    // Reset all agents to pending
    agentPipeline.forEach(agent => {
      updateAgent(agent.id, { status: 'pending', progress: 0, task: '', summary: null });
    });

    try {
      // Prepare request body
      const requestBody = {
        topic: data.topic || 'Marketing Content',
        content_type: data.contentType || 'blog post',
        audience: data.targetAudience || 'general audience',
        goal: 'awareness',
        brand_voice: data.tone || 'professional',
        language: getLanguageName(data.projectLanguage || 'auto'),
        length_constraints: '1000-1500 words',
        context_summary: data.additionalContext || '',
        user_id: 1,
        project_id: data.projectId || null,
        // Documents for tone/voice/style analysis
        style_document_ids: data.styleDocumentIds || [],
        // Documents for content/knowledge retrieval
        knowledge_document_ids: data.knowledgeDocumentIds || [],
        // Checkpoint mode (defaults to automatic)
        checkpoint_mode: checkpointMode
      };

      console.log('Starting generation with request:', {
        ...requestBody,
        style_docs: requestBody.style_document_ids.length,
        knowledge_docs: requestBody.knowledge_document_ids.length
      });

      // Use fetch with streaming for SSE
      const response = await fetch(`${API_BASE}/api/content-pipeline/run/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            console.log('Stream completed normally');
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const eventData = JSON.parse(line.slice(6));
                handlePipelineEvent(eventData, startTime);
              } catch (e) {
                console.error('Failed to parse event:', e);
                console.error('Problematic line:', line);
              }
            }
          }
        }
      } catch (readError) {
        console.error('Stream read error:', readError);
        console.error('Error name:', readError.name);
        console.error('Error message:', readError.message);
        // Re-throw to be caught by outer catch
        throw new Error(`Stream interrupted: ${readError.message}`);
      } finally {
        console.log('Cleaning up stream reader');
        reader.cancel().catch(() => {}); // Always cleanup reader
      }
    } catch (err) {
      console.error('Pipeline error:', err);
      setError(err.message);
      setIsGenerating(false);
      updateData({ isGenerating: false });
    }
  };

  const handlePipelineEvent = (event, startTime) => {
    switch (event.type) {
      case 'pipeline_start':
        console.log('Pipeline started:', event.pipeline_id, 'execution_id:', event.execution_id);
        // Save execution ID (database ID) for linking images to this pipeline run
        if (event.execution_id) {
          updateData({ pipelineExecutionId: event.execution_id });
        }
        // Save checkpoint session ID if in checkpoint mode
        if (event.checkpoint_session_id) {
          setCheckpointSessionId(event.checkpoint_session_id);
          setCheckpointMode(event.checkpoint_mode || 'automatic');
        }
        break;

      case 'checkpoint_reached':
        console.log('Checkpoint reached:', event.stage);
        // Show checkpoint dialog
        setCurrentCheckpoint({
          stage: event.stage,
          stage_output: event.stage_output,
          session_id: event.session_id,
          previous_results: event.previous_results || {}
        });
        break;

      case 'stage_start':
        const startIndex = agentPipeline.findIndex(a => a.id === event.stage);
        if (startIndex >= 0) {
          setCurrentAgentIndex(startIndex);
          updateAgent(event.stage, {
            status: 'working',
            progress: 10,
            task: event.message,
            startTime: Date.now()
          });
        }
        break;

      case 'stage_complete':
        const agent = agents.find(a => a.id === event.stage);
        const duration = event.duration_seconds || (agent?.startTime ? (Date.now() - agent.startTime) / 1000 : 0);

        // Extract tokens and cost from summary
        const inputTokens = event.summary?.input_tokens || 0;
        const outputTokens = event.summary?.output_tokens || 0;
        const totalTokens = inputTokens + outputTokens;

        // Estimate cost (Claude Sonnet rates: ~$0.003/1k input, ~$0.015/1k output)
        const estimatedCost = (inputTokens / 1000) * 0.003 + (outputTokens / 1000) * 0.015;

        // Create agent summary (Phase 1A: Real-time progress)
        // Use Array.from() to create independent copies to prevent data sharing between agents
        const summary = {
          duration: Math.round(duration),
          inputTokens,
          outputTokens,
          totalTokens,
          estimatedCost,
          actions: Array.from(event.actions || []),  // Independent copy of actions array
          badges: Array.from(event.badges || []).map(b => ({...b})),  // Deep copy of badges
          details: event.summary ? {...event.summary} : {},  // Copy details object
          timestamp: new Date().toISOString()
        };

        updateAgent(event.stage, {
          status: 'complete',
          progress: 100,
          task: 'Complete',
          summary,
          actions: Array.from(event.actions || []),  // Independent copy for display
          badges: Array.from(event.badges || []).map(b => ({...b}))  // Independent copy for display
        });

        // Update metrics
        setAgentMetrics(prev => ({
          ...prev,
          [event.stage]: summary
        }));

        // Debug log to verify data isolation
        console.log(`Agent ${event.stage} metrics:`, {
          actions: summary.actions,
          badges: summary.badges,
          details: summary.details
        });

        // Update overall metrics
        setMetrics(prev => ({
          ...prev,
          tokensUsed: prev.tokensUsed + totalTokens,
          estimatedCost: prev.estimatedCost + estimatedCost,
        }));
        break;

      case 'pipeline_complete':
        const totalTime = Math.floor((Date.now() - startTime) / 1000);
        setMetrics(prev => ({ ...prev, totalTime }));

        setPipelineResult(event.result);

        // Extract final content
        const finalText = event.result?.final_review?.final_text ||
                         event.result?.seo_version?.optimized_text ||
                         event.result?.draft?.full_text ||
                         '';

        // Update generation state first
        setIsGenerating(false);

        // Then update parent component data
        // Note: agentMetrics will be updated via separate useEffect
        updateData({
          isGenerating: false,
          generatedContent: finalText,
          pipelineResult: event.result,
          seoMetadata: event.result?.seo_version?.on_page_seo || {},
          suggestions: event.result?.final_review?.editor_notes_for_user || [],
          variants: event.result?.final_review?.suggested_variants || [],
        });
        break;

      case 'pipeline_error':
        setError(event.error);
        setIsGenerating(false);
        updateData({ isGenerating: false });
        break;

      case 'heartbeat':
        // Heartbeat to keep SSE connection alive during long-running agents
        // Silently ignore to prevent console spam
        break;

      default:
        console.log('Unknown event type:', event.type);
    }
  };

  const stopGeneration = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setIsGenerating(false);
    updateData({ isGenerating: false });
  };

  const getAgentStatus = (agentId) => {
    const agent = agents.find(a => a.id === agentId);
    return agent?.status || 'pending';
  };

  const getAgentProgress = (agentId) => {
    const agent = agents.find(a => a.id === agentId);
    return agent?.progress || 0;
  };

  const handleAgentClick = (agent) => {
    const agentData = agents.find(a => a.id === agent.id);
    if (agentData?.status === 'complete' && agentData?.summary) {
      setSelectedAgent({ ...agent, data: agentData });
    }
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '--';
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const canProceed = data.generatedContent && !isGenerating;

  // Calculate total metrics for all completed agents
  const totalMetrics = Object.values(agentMetrics).reduce((acc, m) => ({
    totalTokens: acc.totalTokens + (m.totalTokens || 0),
    estimatedCost: acc.estimatedCost + (m.estimatedCost || 0),
    totalTime: acc.totalTime + (m.duration || 0)
  }), { totalTokens: 0, estimatedCost: 0, totalTime: 0 });

  return (
    <div className="wizard-step step-generation">
      <div className="step-header">
        <span className="step-indicator">Step 3 of 5</span>
        <h2>Content Generation</h2>
        <p className="step-description">
          Watch as our AI agents create your content
        </p>
      </div>

      <div className="step-content generation-layout">
        {/* Agent Pipeline */}
        <div className="pipeline-section">
          <h3>Agent Pipeline</h3>

          {/* Overall Progress */}
          {isGenerating && (
            <div style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: '500' }}>Overall Progress</span>
                <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                  {Math.round((agentPipeline.filter(a => getAgentStatus(a.id) === 'complete').length / agentPipeline.length) * 100)}%
                </span>
              </div>
              <div style={{
                width: '100%',
                height: '8px',
                backgroundColor: '#e5e7eb',
                borderRadius: '4px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${(agentPipeline.filter(a => getAgentStatus(a.id) === 'complete').length / agentPipeline.length) * 100}%`,
                  height: '100%',
                  backgroundColor: '#8b5cf6',
                  borderRadius: '4px',
                  transition: 'width 0.5s ease'
                }} />
              </div>
              <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '4px' }}>
                {agentPipeline.filter(a => getAgentStatus(a.id) === 'complete').length} of {agentPipeline.length} steps completed
              </p>
            </div>
          )}

          <div className="agent-pipeline">
            {agentPipeline.map((agent, index) => {
              const status = getAgentStatus(agent.id);
              const progress = getAgentProgress(agent.id);
              const currentAgent = agents.find(a => a.id === agent.id);
              const isClickable = status === 'complete' && currentAgent?.summary;

              return (
                <div key={agent.id} className="pipeline-item" style={{ marginBottom: '16px' }}>
                  <div
                    className={`pipeline-agent ${status} ${isClickable ? 'clickable' : ''}`}
                    onClick={() => handleAgentClick(agent)}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      padding: '12px',
                      borderRadius: '8px',
                      backgroundColor: status === 'complete' ? '#f0fdf4' : status === 'working' ? '#eff6ff' : '#f9fafb',
                      border: `1px solid ${status === 'complete' ? '#86efac' : status === 'working' ? '#93c5fd' : '#e5e7eb'}`,
                      cursor: isClickable ? 'pointer' : 'default',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="agent-icon">{agent.icon}</span>
                        <span className="agent-name" style={{ fontWeight: '500' }}>{agent.name}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {status === 'complete' && (
                          <>
                            <span style={{ color: '#16a34a', fontWeight: '600' }}>✓ Complete</span>
                            {isClickable && (
                              <span style={{ color: '#6b7280', fontSize: '0.75rem' }}>▸</span>
                            )}
                          </>
                        )}
                        {status === 'working' && (
                          <span style={{ color: '#2563eb', fontSize: '0.875rem' }}>{progress}%</span>
                        )}
                        {status === 'pending' && (
                          <span style={{ color: '#6b7280', fontSize: '0.875rem' }}>Pending</span>
                        )}
                      </div>
                    </div>

                    {/* Progress bar */}
                    <div style={{
                      width: '100%',
                      height: '6px',
                      backgroundColor: '#e5e7eb',
                      borderRadius: '3px',
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        width: status === 'complete' ? '100%' : `${progress}%`,
                        height: '100%',
                        backgroundColor: status === 'complete' ? '#16a34a' : status === 'working' ? '#2563eb' : '#d1d5db',
                        borderRadius: '3px',
                        transition: 'width 0.3s ease'
                      }} />
                    </div>

                    {/* Show metrics for completed agents */}
                    {status === 'complete' && currentAgent?.summary && (
                      <div style={{
                        display: 'flex',
                        gap: '12px',
                        marginTop: '8px',
                        fontSize: '0.75rem',
                        color: '#6b7280'
                      }}>
                        <span>⏱ {formatDuration(currentAgent.summary.duration)}</span>
                        <span>🎯 {currentAgent.summary.totalTokens?.toLocaleString() || 0} tokens</span>
                        <span>💰 ${(currentAgent.summary.estimatedCost || 0).toFixed(4)}</span>
                      </div>
                    )}

                    {/* Current task description for working agents */}
                    {status === 'working' && currentAgent?.task && (
                      <p style={{
                        margin: '8px 0 0 0',
                        fontSize: '0.75rem',
                        color: '#4b5563',
                        fontStyle: 'italic'
                      }}>
                        {currentAgent.task}
                      </p>
                    )}
                  </div>

                  {index < agentPipeline.length - 1 && (
                    <div style={{
                      width: '2px',
                      height: '12px',
                      backgroundColor: status === 'complete' ? '#16a34a' : '#e5e7eb',
                      margin: '0 auto'
                    }} />
                  )}
                </div>
              );
            })}
          </div>

          {/* Error Display */}
          {error && (
            <div className="error-message">
              <p>⚠️ {error}</p>
              <button className="btn btn-outline" onClick={() => setError(null)}>
                Dismiss
              </button>
            </div>
          )}

          {/* Checkpoint Mode Indicator */}
          {!isGenerating && !data.generatedContent && (
            <div style={{
              padding: '12px 16px',
              marginBottom: '16px',
              backgroundColor: checkpointMode === 'checkpoint' ? '#eff6ff' : '#f9fafb',
              border: `1px solid ${checkpointMode === 'checkpoint' ? '#93c5fd' : '#e5e7eb'}`,
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <span style={{ fontSize: '1.25rem' }}>
                {checkpointMode === 'checkpoint' ? '🎯' : '⚡'}
              </span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: '600', fontSize: '0.875rem', color: '#111827' }}>
                  {checkpointMode === 'checkpoint' ? 'Checkpoint Mode Active' : 'Automatic Mode'}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '2px' }}>
                  {checkpointMode === 'checkpoint'
                    ? 'You will review and approve each stage before proceeding'
                    : 'Pipeline will run continuously without pausing'}
                </div>
              </div>
              <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                Change in Settings → Preferences
              </div>
            </div>
          )}

          {!isGenerating && !data.generatedContent && (
            <button className="btn btn-primary btn-large" onClick={startGeneration}>
              Start Content Generation
            </button>
          )}

          {data.generatedContent && !isGenerating && (
            <button className="btn btn-outline" onClick={startGeneration}>
              Regenerate Content
            </button>
          )}
        </div>

        {/* Agent Summary & Metrics Panel - Replaces Live Preview */}
        <div className="metrics-section">
          <h3>Generation Metrics</h3>

          {/* Total Metrics Summary */}
          <div style={{
            padding: '16px',
            backgroundColor: '#f9fafb',
            borderRadius: '8px',
            marginBottom: '20px',
            border: '1px solid #e5e7eb'
          }}>
            <h4 style={{ margin: '0 0 12px 0', fontSize: '0.875rem', fontWeight: '600', color: '#374151' }}>
              Total Usage
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '12px' }}>
              <div>
                <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '4px' }}>Time</div>
                <div style={{ fontSize: '1.25rem', fontWeight: '600', color: '#111827' }}>
                  {formatDuration(totalMetrics.totalTime)}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '4px' }}>Tokens</div>
                <div style={{ fontSize: '1.25rem', fontWeight: '600', color: '#111827' }}>
                  {totalMetrics.totalTokens.toLocaleString()}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '4px' }}>Cost</div>
                <div style={{ fontSize: '1.25rem', fontWeight: '600', color: '#111827' }}>
                  ${totalMetrics.estimatedCost.toFixed(4)}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '4px' }}>Brave Search</div>
                <div style={{ fontSize: '1.25rem', fontWeight: '600', color: '#111827' }}>
                  {pipelineResult?.brave_metrics?.requests_made || 0} req
                </div>
                <div style={{ fontSize: '0.625rem', color: '#6b7280', marginTop: '2px' }}>
                  {pipelineResult?.brave_metrics?.results_received || 0} results
                </div>
              </div>
            </div>
          </div>

          {/* Per-Agent Metrics */}
          {Object.keys(agentMetrics).length > 0 && (
            <div>
              <h4 style={{ margin: '0 0 12px 0', fontSize: '0.875rem', fontWeight: '600', color: '#374151' }}>
                Per-Agent Breakdown
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {agentPipeline.filter(a => agentMetrics[a.id]).map(agent => {
                  const metrics = agentMetrics[agent.id];
                  const agentData = agents.find(a => a.id === agent.id);
                  const hasActions = metrics.actions && metrics.actions.length > 0;

                  return (
                    <div
                      key={agent.id}
                      style={{
                        padding: '12px',
                        backgroundColor: '#fff',
                        borderRadius: '6px',
                        border: '1px solid #e5e7eb'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span>{agent.icon}</span>
                          <span style={{ fontSize: '0.875rem', fontWeight: '500' }}>{agent.name}</span>
                          <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>({metrics.duration}s)</span>
                        </div>
                        <div style={{ display: 'flex', gap: '16px', fontSize: '0.75rem', color: '#6b7280' }}>
                          <span>{metrics.totalTokens?.toLocaleString() || 0}</span>
                          <span>${(metrics.estimatedCost || 0).toFixed(4)}</span>
                        </div>
                      </div>

                      {/* Phase 1A: Action bullets (what this agent did) */}
                      {hasActions && (
                        <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #f3f4f6' }}>
                          <ul style={{
                            margin: 0,
                            paddingLeft: '20px',
                            fontSize: '0.75rem',
                            color: '#6b7280',
                            lineHeight: '1.6'
                          }}>
                            {metrics.actions.slice(0, 3).map((action, idx) => (
                              <li key={idx}>{action}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Phase 3: Change Log */}
                      {metrics.details?.change_log && metrics.details.change_log.length > 0 && (
                        <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #f3f4f6' }}>
                          <div style={{
                            fontSize: '0.65rem',
                            fontWeight: '600',
                            color: '#374151',
                            marginBottom: '4px'
                          }}>
                            What changed:
                          </div>
                          <div style={{
                            padding: '6px 8px',
                            backgroundColor: '#eff6ff',
                            borderLeft: '2px solid #3b82f6',
                            borderRadius: '3px'
                          }}>
                            <ul style={{
                              margin: 0,
                              paddingLeft: '16px',
                              fontSize: '0.7rem',
                              color: '#1e40af',
                              lineHeight: '1.5'
                            }}>
                              {metrics.details.change_log.slice(0, 3).map((change, idx) => (
                                <li key={idx}>{change}</li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      )}

                      {/* Phase 4: Context Provenance (Sources Used) */}
                      {metrics.details?.sources && metrics.details.sources.length > 0 && (
                        <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #f3f4f6' }}>
                          <div style={{
                            fontSize: '0.65rem',
                            fontWeight: '600',
                            color: '#374151',
                            marginBottom: '4px'
                          }}>
                            Sources used:
                          </div>
                          <div style={{
                            padding: '6px 8px',
                            backgroundColor: '#f0fdf4',
                            borderLeft: '2px solid #22c55e',
                            borderRadius: '3px',
                            display: 'flex',
                            flexWrap: 'wrap',
                            gap: '4px'
                          }}>
                            {metrics.details.sources.map((source, idx) => (
                              <div key={idx} style={{
                                fontSize: '0.65rem',
                                padding: '2px 6px',
                                backgroundColor: '#dcfce7',
                                border: '1px solid #86efac',
                                borderRadius: '8px',
                                color: '#166534',
                                fontWeight: '500',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '3px'
                              }}>
                                <span style={{ fontSize: '0.6rem' }}>📄</span>
                                <span>{source.name}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Phase 3A: Before/After Diff Snippets */}
                      {metrics.details?.diff_snippets && metrics.details.diff_snippets.length > 0 && (
                        <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #f3f4f6' }}>
                          <div style={{
                            fontSize: '0.75rem',
                            fontWeight: '600',
                            color: '#374151',
                            marginBottom: '8px'
                          }}>
                            Before → After:
                          </div>
                          {metrics.details.diff_snippets.map((diff, idx) => (
                            <div key={idx} style={{ marginTop: '12px' }}>
                              {diff.reason && (
                                <div style={{
                                  fontSize: '0.7rem',
                                  color: '#6b7280',
                                  marginBottom: '6px',
                                  fontStyle: 'italic',
                                  fontWeight: '500'
                                }}>
                                  {diff.reason}
                                </div>
                              )}
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                <div>
                                  <div style={{
                                    fontSize: '0.65rem',
                                    fontWeight: '600',
                                    color: '#92400e',
                                    marginBottom: '3px',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.5px'
                                  }}>
                                    Before:
                                  </div>
                                  <div style={{
                                    fontSize: '0.75rem',
                                    padding: '10px 12px',
                                    backgroundColor: '#fef3c7',
                                    border: '1px solid #f59e0b',
                                    borderRadius: '6px',
                                    color: '#92400e',
                                    lineHeight: '1.6',
                                    maxHeight: '150px',
                                    overflowY: 'auto',
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word'
                                  }}>
                                    {diff.before}
                                  </div>
                                </div>
                                <div style={{
                                  textAlign: 'center',
                                  color: '#9ca3af',
                                  fontSize: '0.8rem',
                                  fontWeight: '600'
                                }}>
                                  ↓
                                </div>
                                <div>
                                  <div style={{
                                    fontSize: '0.65rem',
                                    fontWeight: '600',
                                    color: '#166534',
                                    marginBottom: '3px',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.5px'
                                  }}>
                                    After:
                                  </div>
                                  <div style={{
                                    fontSize: '0.75rem',
                                    padding: '10px 12px',
                                    backgroundColor: '#dcfce7',
                                    border: '1px solid #22c55e',
                                    borderRadius: '6px',
                                    color: '#166534',
                                    lineHeight: '1.6',
                                    maxHeight: '150px',
                                    overflowY: 'auto',
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word'
                                  }}>
                                    {diff.after}
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Phase 2: Quality Badges */}
                      {metrics.badges && metrics.badges.length > 0 && (
                        <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #f3f4f6', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                          {metrics.badges.map((badge, idx) => {
                            const statusColors = {
                              good: { bg: '#dcfce7', border: '#16a34a', text: '#166534' },
                              warning: { bg: '#fef3c7', border: '#eab308', text: '#854d0e' },
                              error: { bg: '#fee2e2', border: '#dc2626', text: '#991b1b' }
                            };
                            const colors = statusColors[badge.status] || statusColors.warning;
                            return (
                              <div key={idx} style={{
                                fontSize: '0.7rem',
                                padding: '2px 8px',
                                borderRadius: '12px',
                                backgroundColor: colors.bg,
                                border: `1px solid ${colors.border}`,
                                color: colors.text,
                                fontWeight: '500',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px'
                              }}>
                                <span>{badge.label}</span>
                                <span style={{ fontWeight: '600' }}>{badge.value}</span>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Selected Agent Details Modal */}
          {selectedAgent && (
            <div style={{
              marginTop: '20px',
              padding: '16px',
              backgroundColor: '#eff6ff',
              borderRadius: '8px',
              border: '1px solid #93c5fd'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px' }}>
                <h4 style={{ margin: 0, fontSize: '0.875rem', fontWeight: '600', color: '#1e40af' }}>
                  {selectedAgent.icon} {selectedAgent.name} - Details
                </h4>
                <button
                  onClick={() => setSelectedAgent(null)}
                  style={{
                    background: 'none',
                    border: 'none',
                    fontSize: '1.25rem',
                    cursor: 'pointer',
                    color: '#6b7280',
                    padding: '0',
                    lineHeight: '1'
                  }}
                >
                  ×
                </button>
              </div>
              <div style={{ fontSize: '0.875rem', color: '#374151' }}>
                <div style={{ marginBottom: '8px' }}>
                  <strong>Duration:</strong> {formatDuration(selectedAgent.data.summary.duration)}
                </div>
                <div style={{ marginBottom: '8px' }}>
                  <strong>Input Tokens:</strong> {selectedAgent.data.summary.inputTokens?.toLocaleString() || 0}
                </div>
                <div style={{ marginBottom: '8px' }}>
                  <strong>Output Tokens:</strong> {selectedAgent.data.summary.outputTokens?.toLocaleString() || 0}
                </div>
                <div style={{ marginBottom: '8px' }}>
                  <strong>Estimated Cost:</strong> ${(selectedAgent.data.summary.estimatedCost || 0).toFixed(4)}
                </div>
                {selectedAgent.data.summary.details && (
                  <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid #93c5fd' }}>
                    <strong>Additional Info:</strong>
                    <pre style={{
                      marginTop: '8px',
                      fontSize: '0.75rem',
                      backgroundColor: '#fff',
                      padding: '8px',
                      borderRadius: '4px',
                      overflow: 'auto',
                      maxHeight: '200px'
                    }}>
                      {JSON.stringify(selectedAgent.data.summary.details, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* SEO Metadata Preview */}
          {pipelineResult?.seo_version?.on_page_seo && (
            <div style={{ marginTop: '20px' }}>
              <h4 style={{ margin: '0 0 12px 0', fontSize: '0.875rem', fontWeight: '600', color: '#374151' }}>
                SEO Metadata
              </h4>
              <div style={{
                padding: '12px',
                backgroundColor: '#fff',
                borderRadius: '6px',
                border: '1px solid #e5e7eb',
                fontSize: '0.875rem'
              }}>
                <div style={{ marginBottom: '8px' }}>
                  <strong>Title:</strong> {pipelineResult.seo_version.on_page_seo.title_tag}
                </div>
                <div style={{ marginBottom: '8px' }}>
                  <strong>Meta:</strong> {pipelineResult.seo_version.on_page_seo.meta_description}
                </div>
                <div>
                  <strong>Focus Keyword:</strong> {pipelineResult.seo_version.on_page_seo.focus_keyword}
                </div>
              </div>
            </div>
          )}

          {/* Placeholder when nothing is running */}
          {!isGenerating && Object.keys(agentMetrics).length === 0 && !data.generatedContent && (
            <div style={{
              padding: '40px',
              textAlign: 'center',
              color: '#6b7280',
              backgroundColor: '#f9fafb',
              borderRadius: '8px',
              border: '1px dashed #e5e7eb'
            }}>
              <p style={{ margin: 0 }}>Metrics will appear here as agents complete their work...</p>
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <div className="step-navigation">
        <button className="btn btn-secondary" onClick={onBack} disabled={isGenerating}>
          ← Back
        </button>
        <div className="nav-actions">
          {isGenerating && (
            <button className="btn btn-outline" onClick={stopGeneration}>
              Stop
            </button>
          )}
          <button
            className="btn btn-primary"
            onClick={onNext}
            disabled={!canProceed}
          >
            Review & Edit →
          </button>
        </div>
      </div>

      {/* Checkpoint Dialog */}
      {currentCheckpoint && (
        <CheckpointDialog
          checkpoint={currentCheckpoint}
          onAction={handleCheckpointAction}
          onClose={() => setCurrentCheckpoint(null)}
        />
      )}

      <style>{`
        .pipeline-agent.clickable:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
      `}</style>
    </div>
  );
}
