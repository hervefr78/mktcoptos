import React, { useState, useEffect } from 'react';
import { API_BASE } from '../../config/api';

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

export default function StepResearch({ data, updateData, agents, updateAgent, onNext, onBack }) {
  const [isResearching, setIsResearching] = useState(false);
  const [researchProgress, setResearchProgress] = useState(0);
  const [error, setError] = useState(null);
  const [showStyleDocs, setShowStyleDocs] = useState(false);
  const [showKnowledgeDocs, setShowKnowledgeDocs] = useState(false);
  const [availableDocuments, setAvailableDocuments] = useState([]);
  const [loadingDocuments, setLoadingDocuments] = useState(false);

  // Fetch available RAG documents
  const fetchDocuments = async () => {
    setLoadingDocuments(true);
    try {
      const response = await fetch(`${API_BASE}/api/rag/documents`);
      if (response.ok) {
        const docs = await response.json();
        // Only show completed documents
        setAvailableDocuments(docs.filter(d => d.status === 'completed'));
      }
    } catch (err) {
      console.error('Failed to fetch documents:', err);
    } finally {
      setLoadingDocuments(false);
    }
  };

  // Load documents when either modal opens
  useEffect(() => {
    if (showStyleDocs || showKnowledgeDocs) {
      fetchDocuments();
    }
  }, [showStyleDocs, showKnowledgeDocs]);

  // Toggle style document selection (for tone/voice)
  const toggleStyleDocument = (doc) => {
    const currentIds = data.styleDocumentIds || [];
    const currentDocs = data.styleDocuments || [];

    if (currentIds.includes(doc.id)) {
      updateData({
        styleDocumentIds: currentIds.filter(id => id !== doc.id),
        styleDocuments: currentDocs.filter(d => d.id !== doc.id)
      });
    } else {
      updateData({
        styleDocumentIds: [...currentIds, doc.id],
        styleDocuments: [...currentDocs, { id: doc.id, name: doc.original_filename }]
      });
    }
  };

  // Toggle knowledge document selection (for content/information)
  const toggleKnowledgeDocument = (doc) => {
    const currentIds = data.knowledgeDocumentIds || [];
    const currentDocs = data.knowledgeDocuments || [];

    if (currentIds.includes(doc.id)) {
      updateData({
        knowledgeDocumentIds: currentIds.filter(id => id !== doc.id),
        knowledgeDocuments: currentDocs.filter(d => d.id !== doc.id)
      });
    } else {
      updateData({
        knowledgeDocumentIds: [...currentIds, doc.id],
        knowledgeDocuments: [...currentDocs, { id: doc.id, name: doc.original_filename }]
      });
    }
  };

  const startResearch = async () => {
    setIsResearching(true);
    setError(null);
    updateAgent('research', { status: 'working', progress: 0, task: 'Starting research...' });

    try {
      // Progress update helper
      const updateProgress = (progress, task) => {
        setResearchProgress(progress);
        updateAgent('research', { progress, task });
      };

      updateProgress(10, 'Analyzing topic and context...');

      // Call the backend to run trends/keywords analysis
      const requestBody = {
        topic: data.topic || 'general topic',
        content_type: data.contentType || 'blog post',
        audience: data.targetAudience || 'general',
        goal: data.goal || 'awareness',
        brand_voice: data.brandVoice || data.tone || 'professional',
        language: getLanguageName(data.projectLanguage || 'auto'),
        length_constraints: data.wordCount || '1000-1500 words',
        context_summary: data.additionalContext || '',
        user_id: 1,
      };
      console.log('Research request:', requestBody);

      const response = await fetch(`${API_BASE}/api/content-pipeline/run/single-agent/trends_keywords`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      updateProgress(50, 'Processing research data...');

      if (!response.ok) {
        // Try to get detailed error message
        let errorDetail = 'Failed to fetch research data';
        try {
          const errorText = await response.text();
          console.error('Raw error response:', errorText);
          const errorData = JSON.parse(errorText);
          console.error('Parsed error data:', errorData);
          if (errorData.detail) {
            // Pydantic validation error
            if (Array.isArray(errorData.detail)) {
              errorDetail = errorData.detail.map(e => `${e.loc?.join('.')}: ${e.msg}`).join(', ');
            } else {
              errorDetail = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
            }
          }
        } catch (e) {
          console.error('Error parsing response:', e);
        }
        console.error('Research API error:', response.status, errorDetail);
        throw new Error(errorDetail);
      }

      const result = await response.json();
      const researchData = result.result || {};

      updateProgress(80, 'Generating research brief...');

      // Helper to sanitize keywords/phrases - strip URLs and limit length
      const sanitizeKeyword = (keyword) => {
        if (!keyword || typeof keyword !== 'string') return null;
        // Remove URLs
        let clean = keyword.replace(/https?:\/\/[^\s]+/g, '').trim();
        // Remove special separators
        clean = clean.replace(/[⸻—–]/g, ' ').trim();
        // Limit length (keywords should be short phrases)
        if (clean.length > 100) {
          clean = clean.substring(0, 100).trim() + '...';
        }
        return clean.length > 2 ? clean : null;
      };

      // Helper to sanitize array of keywords
      const sanitizeKeywords = (arr, fallback) => {
        if (!Array.isArray(arr)) return fallback;
        const sanitized = arr
          .map(sanitizeKeyword)
          .filter(k => k !== null);
        return sanitized.length > 0 ? sanitized : fallback;
      };

      // Transform the trends/keywords result into a research brief
      const researchBrief = {
        keyThemes: sanitizeKeywords(
          researchData.primary_keywords?.slice(0, 5),
          ['Topic analysis', 'Key concepts', 'Main themes']
        ),
        competitorInsights: sanitizeKeywords(
          researchData.trending_topics?.slice(0, 3),
          ['Current trends', 'Industry insights']
        ),
        suggestedAngles: sanitizeKeywords(
          researchData.angle_ideas?.slice(0, 3),
          ['Unique perspective', 'Data-driven approach']
        ),
        recommendedLength: data.wordCount ||
                         (data.contentType === 'blog' ? '1500-2000 words' : '200-300 words'),
        secondaryKeywords: sanitizeKeywords(
          researchData.secondary_keywords?.slice(0, 5),
          []
        ),
        contentHooks: sanitizeKeywords(
          researchData.content_hooks?.slice(0, 3),
          []
        ),
      };

      updateProgress(100, 'Research complete');

      // Complete research
      updateAgent('research', { status: 'complete', progress: 100, task: 'Research complete' });

      updateData({
        researchComplete: true,
        researchBrief: researchBrief,
        trendsKeywordsResult: researchData, // Store full result for later use
      });

    } catch (err) {
      console.error('Research failed:', err);
      setError('Research failed. Using default suggestions.');

      // Fallback to generated defaults based on topic
      const fallbackBrief = generateFallbackBrief(data);

      updateAgent('research', { status: 'complete', progress: 100, task: 'Research complete (with defaults)' });

      updateData({
        researchComplete: true,
        researchBrief: fallbackBrief,
      });
    } finally {
      setIsResearching(false);
    }
  };

  // Generate contextual fallback based on user input
  const generateFallbackBrief = (data) => {
    const topic = data.topic || 'your topic';
    const contentType = data.contentType || 'content';
    const audience = data.targetAudience || 'audience';

    return {
      keyThemes: [
        `${topic} fundamentals`,
        `${topic} best practices`,
        `${topic} trends`,
      ],
      competitorInsights: [
        `Address ${audience} pain points`,
        `Highlight unique value propositions`,
      ],
      suggestedAngles: [
        'Problem-solution narrative',
        'Expert insights and data',
        `Practical tips for ${audience}`,
      ],
      recommendedLength: data.wordCount ||
                        (contentType === 'blog' ? '1500-2000 words' : '200-300 words'),
      secondaryKeywords: [],
      contentHooks: [],
    };
  };

  const canProceed = data.researchComplete;

  return (
    <div className="wizard-step step-research">
      <div className="step-header">
        <span className="step-indicator">Step 2 of 5</span>
        <h2>Research & Context</h2>
        <p className="step-description">
          Gather relevant information and set the context for your content
        </p>
      </div>

      <div className="step-content">
        {/* Research Agent Status */}
        <div className="agent-status-card">
          <div className="agent-header">
            <span className="agent-icon">Research</span>
            <span className="agent-name">Research Agent</span>
            <span className={`agent-badge ${agents.find(a => a.id === 'research')?.status}`}>
              {agents.find(a => a.id === 'research')?.status === 'complete' ? 'Complete' :
               agents.find(a => a.id === 'research')?.status === 'working' ? 'Working' : 'Ready'}
            </span>
          </div>

          {isResearching && (
            <div className="agent-progress">
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${researchProgress}%` }}
                />
              </div>
              <span className="progress-task">
                {agents.find(a => a.id === 'research')?.task}
              </span>
            </div>
          )}

          {error && (
            <p className="error-text" style={{ color: '#ef4444', fontSize: '0.875rem', marginTop: '8px' }}>
              {error}
            </p>
          )}

          {!data.researchComplete && !isResearching && (
            <button className="btn btn-secondary" onClick={startResearch}>
              Start Research
            </button>
          )}

          {data.researchComplete && !isResearching && (
            <button
              className="btn btn-outline"
              onClick={() => {
                updateData({ researchComplete: false, researchBrief: null });
                updateAgent('research', { status: 'idle', progress: 0, task: '' });
              }}
              style={{ marginTop: '8px' }}
            >
              Re-run Research
            </button>
          )}
        </div>

        {/* Additional Context */}
        <div className="form-section">
          <label className="form-label">
            Additional Context
            <span className="label-hint">Any specific points or data to include</span>
          </label>
          <textarea
            className="form-textarea"
            placeholder="Include recent product updates, specific statistics, customer quotes..."
            value={data.additionalContext || ''}
            onChange={(e) => updateData({ additionalContext: e.target.value })}
            rows={4}
          />
        </div>

        {/* Style & Tone Documents */}
        <div className="form-section">
          <label className="form-label">
            Style & Tone Reference
            <span className="label-hint">Documents to mimic writing style and voice</span>
          </label>
          <button
            type="button"
            className="btn btn-outline"
            onClick={() => setShowStyleDocs(!showStyleDocs)}
          >
            + Add Style Documents
          </button>

          {showStyleDocs && (
            <div className="knowledge-base-selector" style={{
              marginTop: '12px',
              padding: '12px',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              backgroundColor: '#f9fafb'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <h4 style={{ margin: 0, fontSize: '0.875rem', fontWeight: '600' }}>Select Style Documents</h4>
                <button
                  type="button"
                  onClick={() => setShowStyleDocs(false)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.25rem', color: '#6b7280' }}
                >
                  ×
                </button>
              </div>

              {loadingDocuments ? (
                <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>Loading documents...</p>
              ) : availableDocuments.length === 0 ? (
                <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                  No processed documents available.
                </p>
              ) : availableDocuments.filter(doc => doc.collection === 'brand_voice').length === 0 ? (
                <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                  No style documents available. Upload documents with collection type "brand_voice".
                </p>
              ) : (
                <div style={{ maxHeight: '150px', overflowY: 'auto' }}>
                  {availableDocuments
                    .filter(doc => doc.collection === 'brand_voice')  // Only show brand_voice documents
                    .map(doc => (
                    <label
                      key={doc.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '8px',
                        cursor: 'pointer',
                        borderRadius: '4px',
                        backgroundColor: (data.styleDocumentIds || []).includes(doc.id) ? '#fef3c7' : 'transparent'
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={(data.styleDocumentIds || []).includes(doc.id)}
                        onChange={() => toggleStyleDocument(doc)}
                        style={{ marginRight: '8px' }}
                      />
                      <span style={{ fontSize: '0.875rem' }}>{doc.original_filename}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}

          {data.styleDocuments && data.styleDocuments.length > 0 && (
            <div className="reference-list" style={{ marginTop: '12px' }}>
              {data.styleDocuments.map((doc) => (
                <div key={doc.id} className="reference-item">
                  <span className="reference-icon" style={{ backgroundColor: '#fef3c7' }}>S</span>
                  <span className="reference-name">{doc.name}</span>
                  <button
                    type="button"
                    className="reference-remove"
                    onClick={() => {
                      updateData({
                        styleDocumentIds: (data.styleDocumentIds || []).filter(id => id !== doc.id),
                        styleDocuments: (data.styleDocuments || []).filter(d => d.id !== doc.id)
                      });
                    }}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Knowledge & Content Documents */}
        <div className="form-section">
          <label className="form-label">
            Knowledge & Content
            <span className="label-hint">Documents to extract information from</span>
          </label>
          <button
            type="button"
            className="btn btn-outline"
            onClick={() => setShowKnowledgeDocs(!showKnowledgeDocs)}
          >
            + Add Knowledge Documents
          </button>

          {showKnowledgeDocs && (
            <div className="knowledge-base-selector" style={{
              marginTop: '12px',
              padding: '12px',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              backgroundColor: '#f9fafb'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <h4 style={{ margin: 0, fontSize: '0.875rem', fontWeight: '600' }}>Select Knowledge Documents</h4>
                <button
                  type="button"
                  onClick={() => setShowKnowledgeDocs(false)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.25rem', color: '#6b7280' }}
                >
                  ×
                </button>
              </div>

              {loadingDocuments ? (
                <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>Loading documents...</p>
              ) : availableDocuments.length === 0 ? (
                <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                  No processed documents available.
                </p>
              ) : availableDocuments.filter(doc => doc.collection === 'knowledge_base').length === 0 ? (
                <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                  No knowledge documents available. Upload documents with collection type "knowledge_base".
                </p>
              ) : (
                <div style={{ maxHeight: '150px', overflowY: 'auto' }}>
                  {availableDocuments
                    .filter(doc => doc.collection === 'knowledge_base')  // Only show knowledge_base documents
                    .map(doc => (
                    <label
                      key={doc.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '8px',
                        cursor: 'pointer',
                        borderRadius: '4px',
                        backgroundColor: (data.knowledgeDocumentIds || []).includes(doc.id) ? '#e0e7ff' : 'transparent'
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={(data.knowledgeDocumentIds || []).includes(doc.id)}
                        onChange={() => toggleKnowledgeDocument(doc)}
                        style={{ marginRight: '8px' }}
                      />
                      <span style={{ fontSize: '0.875rem' }}>{doc.original_filename}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}

          {data.knowledgeDocuments && data.knowledgeDocuments.length > 0 && (
            <div className="reference-list" style={{ marginTop: '12px' }}>
              {data.knowledgeDocuments.map((doc) => (
                <div key={doc.id} className="reference-item">
                  <span className="reference-icon" style={{ backgroundColor: '#e0e7ff' }}>K</span>
                  <span className="reference-name">{doc.name}</span>
                  <button
                    type="button"
                    className="reference-remove"
                    onClick={() => {
                      updateData({
                        knowledgeDocumentIds: (data.knowledgeDocumentIds || []).filter(id => id !== doc.id),
                        knowledgeDocuments: (data.knowledgeDocuments || []).filter(d => d.id !== doc.id)
                      });
                    }}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Uploaded Files */}
          {data.referenceFiles && data.referenceFiles.length > 0 && (
            <div className="reference-list">
              {data.referenceFiles.map((file, idx) => (
                <div key={idx} className="reference-item">
                  <span className="reference-icon">File</span>
                  <span className="reference-name">{file.name}</span>
                  <button
                    type="button"
                    className="reference-remove"
                    onClick={() => {
                      const newFiles = data.referenceFiles.filter((_, i) => i !== idx);
                      updateData({ referenceFiles: newFiles });
                    }}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Research Brief Results */}
        {data.researchComplete && data.researchBrief && (
          <div className="research-brief">
            <h3>Research Brief</h3>

            <div className="brief-section">
              <h4>Key Themes & Keywords</h4>
              <div className="brief-tags">
                {data.researchBrief.keyThemes.map((theme, idx) => (
                  <span key={idx} className="brief-tag">{theme}</span>
                ))}
              </div>
            </div>

            {data.researchBrief.secondaryKeywords && data.researchBrief.secondaryKeywords.length > 0 && (
              <div className="brief-section">
                <h4>Secondary Keywords</h4>
                <div className="brief-tags">
                  {data.researchBrief.secondaryKeywords.map((keyword, idx) => (
                    <span key={idx} className="brief-tag secondary">{keyword}</span>
                  ))}
                </div>
              </div>
            )}

            <div className="brief-section">
              <h4>Trending Topics & Insights</h4>
              <ul className="brief-list">
                {data.researchBrief.competitorInsights.map((insight, idx) => (
                  <li key={idx}>{insight}</li>
                ))}
              </ul>
            </div>

            <div className="brief-section">
              <h4>Suggested Content Angles</h4>
              <ul className="brief-list">
                {data.researchBrief.suggestedAngles.map((angle, idx) => (
                  <li key={idx}>{angle}</li>
                ))}
              </ul>
            </div>

            {data.researchBrief.contentHooks && data.researchBrief.contentHooks.length > 0 && (
              <div className="brief-section">
                <h4>Content Hooks</h4>
                <ul className="brief-list">
                  {data.researchBrief.contentHooks.map((hook, idx) => (
                    <li key={idx}>{hook}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="brief-section">
              <h4>Recommended Length</h4>
              <p>{data.researchBrief.recommendedLength}</p>
            </div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="step-navigation">
        <button className="btn btn-secondary" onClick={onBack}>
          Back
        </button>
        <button
          className="btn btn-primary"
          onClick={onNext}
          disabled={!canProceed}
        >
          Generate Content
        </button>
      </div>
    </div>
  );
}
