import React, { useState } from 'react';
import './wizard.css';

export default function RAGInsightsPanel({ insights }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedChunk, setSelectedChunk] = useState(null);
  const [expandedDocuments, setExpandedDocuments] = useState(new Set());
  const [showAttributionModal, setShowAttributionModal] = useState(false);

  if (!insights || !insights.enabled) {
    return (
      <div className="rag-insights-panel disabled">
        <div className="insights-header">
          <span className="insights-icon">ℹ️</span>
          <span className="insights-title">RAG Analysis</span>
        </div>
        <p className="insights-message">
          {insights?.message || "No RAG documents were configured for this content"}
        </p>
      </div>
    );
  }

  const toggleDocument = (docId) => {
    setExpandedDocuments((prev) => {
      const next = new Set(prev);
      if (next.has(docId)) {
        next.delete(docId);
      } else {
        next.add(docId);
      }
      return next;
    });
  };

  const getScoreColor = (score) => {
    if (score >= 0.8) return '#10b981'; // Green
    if (score >= 0.6) return '#f59e0b'; // Orange
    return '#ef4444'; // Red
  };

  const getScoreLabel = (score) => {
    if (score >= 0.8) return 'Excellent match';
    if (score >= 0.6) return 'Good match';
    return 'Fair match';
  };

  const exportToCSV = () => {
    const rows = [
      ['Document Name', 'Chunks Used', 'Avg Relevance', 'Influence %', 'Style Similarity']
    ];

    insights.documents.forEach(doc => {
      const styleSim = insights.style_similarity?.document_similarities?.find(
        d => d.document_id === doc.id
      );
      rows.push([
        doc.name,
        doc.chunks_used,
        `${Math.round(doc.avg_relevance * 100)}%`,
        `${Math.round(doc.influence_percentage)}%`,
        styleSim ? `${Math.round(styleSim.avg_similarity * 100)}%` : 'N/A'
      ]);
    });

    const csvContent = rows.map(row => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rag-insights-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportToJSON = () => {
    const data = JSON.stringify(insights, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rag-insights-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="rag-insights-panel">
      {/* Header with expand/collapse */}
      <div
        className="insights-header clickable"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="header-left">
          <span className="insights-icon">✨</span>
          <span className="insights-title">RAG Analysis</span>
          <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
        </div>
        <div className="header-stats">
          <span className="stat">{insights.total_documents_used} docs</span>
          <span className="stat-separator">•</span>
          <span className="stat">{insights.total_chunks_retrieved} chunks</span>
          <span className="stat-separator">•</span>
          <span className="stat" style={{ color: getScoreColor(insights.average_relevance_score) }}>
            {Math.round(insights.average_relevance_score * 100)}% match
          </span>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="insights-content">
          {/* Export Buttons */}
          <div className="export-section">
            <button onClick={exportToCSV} className="btn-export">
              📊 Export CSV
            </button>
            <button onClick={exportToJSON} className="btn-export">
              📄 Export JSON
            </button>
          </div>

          {/* Overall Stats */}
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{insights.total_documents_used}</div>
              <div className="stat-label">Documents Used</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{insights.total_chunks_retrieved}</div>
              <div className="stat-label">Chunks Retrieved</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{Math.round(insights.average_relevance_score * 100)}%</div>
              <div className="stat-label">Avg. Relevance</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">
                {Object.keys(insights.chunks_by_stage || {}).length}
              </div>
              <div className="stat-label">Stages Used</div>
            </div>
          </div>

          {/* Documents Breakdown */}
          <div className="documents-section">
            <h4 className="section-title">Document Influence</h4>
            {insights.documents && insights.documents.map((doc) => {
              const isDocExpanded = expandedDocuments.has(doc.id);
              const docChunks = (insights.detailed_chunks || []).filter(
                c => c.document_id === doc.id
              );

              return (
                <div key={doc.id} className="document-card">
                  <div
                    className="document-header"
                    onClick={() => toggleDocument(doc.id)}
                  >
                    <div className="document-info">
                      <span className="document-icon">📄</span>
                      <div className="document-details">
                        <div className="document-name">{doc.name}</div>
                        <div className="document-meta">
                          {doc.chunks_used} chunks • {Math.round(doc.avg_relevance * 100)}% relevance
                        </div>
                      </div>
                    </div>
                    <div className="document-stats">
                      <div className="influence-bar">
                        <div
                          className="influence-fill"
                          style={{
                            width: `${doc.influence_percentage}%`,
                            backgroundColor: getScoreColor(doc.avg_relevance)
                          }}
                        />
                      </div>
                      <span className="influence-percentage">
                        {Math.round(doc.influence_percentage)}%
                      </span>
                      <span className="expand-icon-small">{isDocExpanded ? '▼' : '▶'}</span>
                    </div>
                  </div>

                  {/* Document Chunks (when expanded) */}
                  {isDocExpanded && (
                    <div className="document-chunks">
                      {docChunks.map((chunk, idx) => (
                        <div key={chunk.chunk_id || idx} className="chunk-preview">
                          <div className="chunk-header">
                            <span className="chunk-label">Chunk {idx + 1}</span>
                            <span
                              className="chunk-score"
                              style={{ color: getScoreColor(chunk.score) }}
                            >
                              {Math.round(chunk.score * 100)}% • {getScoreLabel(chunk.score)}
                            </span>
                          </div>
                          <p className="chunk-text">{chunk.text}</p>
                          <button
                            className="btn-link-small"
                            onClick={() => setSelectedChunk(chunk)}
                          >
                            View full chunk
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Usage by Stage */}
          {insights.chunks_by_stage && Object.keys(insights.chunks_by_stage).length > 0 && (
            <div className="stages-section">
              <h4 className="section-title">Usage by Pipeline Stage</h4>
              <div className="stages-grid">
                {Object.entries(insights.chunks_by_stage).map(([stage, count]) => (
                  <div key={stage} className="stage-stat">
                    <span className="stage-name">{stage.replace(/_/g, ' ')}</span>
                    <span className="stage-count">{count} chunks</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Style Similarity Analysis */}
          {insights.style_similarity && (
            <div className="similarity-section">
              <h4 className="section-title">Style Similarity Analysis</h4>
              <div className="similarity-overall">
                <div className="similarity-score-large">
                  <div className="score-circle" style={{
                    background: `conic-gradient(${getScoreColor(insights.style_similarity.overall_similarity)} ${insights.style_similarity.overall_similarity * 360}deg, #e5e7eb 0deg)`
                  }}>
                    <div className="score-inner">
                      {Math.round(insights.style_similarity.overall_similarity * 100)}%
                    </div>
                  </div>
                  <div className="score-label-large">Overall Style Match</div>
                </div>
              </div>
              <div className="similarity-by-document">
                {insights.style_similarity.document_similarities?.map((doc) => (
                  <div key={doc.document_id} className="similarity-doc-card">
                    <div className="similarity-doc-name">{doc.document_name}</div>
                    <div className="similarity-bars">
                      <div className="similarity-bar-row">
                        <span className="bar-label">Avg Match</span>
                        <div className="similarity-bar">
                          <div
                            className="similarity-bar-fill"
                            style={{
                              width: `${doc.avg_similarity * 100}%`,
                              backgroundColor: getScoreColor(doc.avg_similarity)
                            }}
                          />
                        </div>
                        <span className="bar-value">{Math.round(doc.avg_similarity * 100)}%</span>
                      </div>
                      <div className="similarity-bar-row">
                        <span className="bar-label">Max Match</span>
                        <div className="similarity-bar">
                          <div
                            className="similarity-bar-fill"
                            style={{
                              width: `${doc.max_similarity * 100}%`,
                              backgroundColor: getScoreColor(doc.max_similarity)
                            }}
                          />
                        </div>
                        <span className="bar-value">{Math.round(doc.max_similarity * 100)}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <p className="similarity-note">
                ℹ️ Style similarity is calculated using embedding-based cosine similarity between
                your generated content and the RAG documents.
              </p>
            </div>
          )}

          {/* Sentence Attribution */}
          {insights.sentence_attribution && (
            <div className="attribution-section">
              <h4 className="section-title">Sentence Attribution</h4>
              <div className="attribution-summary">
                <div className="attribution-stat">
                  <span className="stat-number">{insights.sentence_attribution.attributed_sentences}</span>
                  <span className="stat-desc">of {insights.sentence_attribution.total_sentences} sentences attributed to RAG</span>
                </div>
                <div className="attribution-percentage">
                  {insights.sentence_attribution.attribution_percentage}% attribution rate
                </div>
              </div>
              <button
                onClick={() => setShowAttributionModal(true)}
                className="btn btn-secondary"
                style={{ marginTop: '12px' }}
              >
                View Sentence-by-Sentence Attribution
              </button>
            </div>
          )}
        </div>
      )}

      {/* Sentence Attribution Modal */}
      {showAttributionModal && insights.sentence_attribution && (
        <div className="modal-overlay" onClick={() => setShowAttributionModal(false)}>
          <div className="modal-content attribution-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Sentence-Level Attribution</h3>
              <button className="modal-close" onClick={() => setShowAttributionModal(false)}>
                ✕
              </button>
            </div>
            <div className="modal-body">
              <p className="modal-description">
                Each sentence shows whether it was influenced by RAG documents based on embedding similarity.
                Highlighted sentences have ≥60% similarity to specific RAG chunks.
              </p>
              <div className="attribution-list">
                {insights.sentence_attribution.details?.map((attr, idx) => (
                  <div
                    key={idx}
                    className={`attribution-item ${attr.attributed ? 'attributed' : 'not-attributed'}`}
                  >
                    <div className="attribution-sentence">
                      <span className="sentence-number">{idx + 1}.</span>
                      <span className="sentence-text">{attr.sentence}</span>
                    </div>
                    {attr.attributed ? (
                      <div className="attribution-details">
                        <span className="attribution-badge" style={{ backgroundColor: getScoreColor(attr.similarity) }}>
                          {Math.round(attr.similarity * 100)}% match
                        </span>
                        <span className="attribution-source">
                          From: {attr.document_name}
                        </span>
                      </div>
                    ) : (
                      <div className="attribution-details">
                        <span className="attribution-badge-none">
                          Original ({Math.round(attr.similarity * 100)}% max)
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowAttributionModal(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Chunk Viewer Modal */}
      {selectedChunk && (
        <div className="modal-overlay" onClick={() => setSelectedChunk(null)}>
          <div className="modal-content chunk-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Full Chunk Content</h3>
              <button className="modal-close" onClick={() => setSelectedChunk(null)}>
                ✕
              </button>
            </div>
            <div className="modal-body">
              <div className="chunk-metadata">
                <div className="meta-item">
                  <strong>Document:</strong> {selectedChunk.document_name}
                </div>
                <div className="meta-item">
                  <strong>Relevance Score:</strong>{' '}
                  <span style={{ color: getScoreColor(selectedChunk.score) }}>
                    {Math.round(selectedChunk.score * 100)}% ({getScoreLabel(selectedChunk.score)})
                  </span>
                </div>
                <div className="meta-item">
                  <strong>Used in Stage:</strong> {selectedChunk.used_in_stage?.replace(/_/g, ' ')}
                </div>
                {selectedChunk.chunk_position > 0 && (
                  <div className="meta-item">
                    <strong>Position in Document:</strong> Chunk #{selectedChunk.chunk_position}
                  </div>
                )}
              </div>
              <div className="chunk-full-text">
                <h4>Chunk Text:</h4>
                <p>{selectedChunk.full_text || selectedChunk.text}</p>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setSelectedChunk(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
