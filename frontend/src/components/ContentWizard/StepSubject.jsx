import React from 'react';
import { CONTENT_TYPES } from '../../constants/contentOptions';

const tones = [
  { id: 'professional', label: 'Professional' },
  { id: 'thought-leadership', label: 'Thought Leadership' },
  { id: 'casual', label: 'Casual & Friendly' },
  { id: 'educational', label: 'Educational' },
  { id: 'persuasive', label: 'Persuasive' },
];

const audiences = [
  { id: 'cto', label: 'CTOs & Tech Leaders' },
  { id: 'marketing', label: 'Marketing Professionals' },
  { id: 'founders', label: 'Founders & Entrepreneurs' },
  { id: 'developers', label: 'Developers & Engineers' },
  { id: 'general', label: 'General Business Audience' },
];

export default function StepSubject({ data, updateData, onNext }) {
  const canProceed = data.topic.trim() && data.contentType;

  return (
    <div className="wizard-step step-subject">
      <div className="step-header">
        <span className="step-indicator">Step 1 of 5</span>
        <h2>Subject & Strategy</h2>
        <p className="step-description">
          Define what you want to create and who it's for
        </p>
      </div>

      <div className="step-content">
        {/* Sub-Project Banner */}
        {data.isSubProject && (
          <div className="sub-project-banner">
            <div className="banner-header">
              <span className="banner-icon">🔗</span>
              <div className="banner-content">
                <h3>Sub-Project: Linked to Main Project</h3>
                <p>
                  This project is linked to <strong>{data.parentProjectName}</strong>
                  {data.inheritTone && ' and inherits its tone and style'}
                </p>
              </div>
            </div>

            {data.parentContent && (
              <div className="parent-content-preview">
                <div className="preview-header">
                  <span className="preview-label">📄 Parent Content Available</span>
                  {data.parentContent.pipelineId && (
                    <a
                      href={`/content/view/${data.parentContent.pipelineId}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="preview-link"
                    >
                      View Full Content →
                    </a>
                  )}
                </div>
                <div className="preview-details">
                  {data.parentContent.topic && (
                    <div className="preview-field">
                      <strong>Topic:</strong> {data.parentContent.topic}
                    </div>
                  )}
                  {data.parentContent.tone && (
                    <div className="preview-field">
                      <strong>Tone:</strong> {data.parentContent.tone}
                      {data.inheritTone && <span className="inherited-badge">Inherited</span>}
                    </div>
                  )}
                  {data.parentContent.audience && (
                    <div className="preview-field">
                      <strong>Audience:</strong> {data.parentContent.audience}
                    </div>
                  )}
                </div>
                <div className="ai-suggestions">
                  <p className="suggestions-intro">💡 <strong>AI Suggestions</strong> based on parent content:</p>
                  <div className="suggestion-list">
                    <button
                      type="button"
                      className="suggestion-item"
                      onClick={() => {
                        if (data.projectContentType === 'social-media') {
                          updateData({
                            topic: `Social media promotion for: ${data.parentContent.topic}`,
                            targetAudience: data.parentContent.audience || data.targetAudience,
                          });
                        } else if (data.projectContentType === 'linkedin') {
                          updateData({
                            topic: `LinkedIn post highlighting: ${data.parentContent.topic}`,
                            targetAudience: data.parentContent.audience || data.targetAudience,
                          });
                        } else if (data.projectContentType === 'newsletter') {
                          updateData({
                            topic: `Newsletter featuring: ${data.parentContent.topic}`,
                            targetAudience: data.parentContent.audience || data.targetAudience,
                          });
                        } else {
                          updateData({
                            topic: `Adapted from: ${data.parentContent.topic}`,
                            targetAudience: data.parentContent.audience || data.targetAudience,
                          });
                        }
                      }}
                    >
                      Adapt parent topic for this content type
                    </button>
                    <button
                      type="button"
                      className="suggestion-item"
                      onClick={() => {
                        updateData({
                          topic: `Key insights from: ${data.parentContent.topic}`,
                          targetAudience: data.parentContent.audience || data.targetAudience,
                        });
                      }}
                    >
                      Extract key insights
                    </button>
                    {data.parentContent.keywords && (
                      <button
                        type="button"
                        className="suggestion-item"
                        onClick={() => {
                          updateData({
                            keywords: data.parentContent.keywords,
                          });
                        }}
                      >
                        Use parent keywords
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}

            {data.parentContentWarning && (
              <div className="parent-warning">
                <span className="warning-icon">⚠️</span>
                <p>{data.parentContentWarning}</p>
                <p className="warning-help">
                  Create content in the main project first, then return here to create linked sub-content.
                </p>
              </div>
            )}

            {data.parentContentError && (
              <div className="parent-error">
                <span className="error-icon">❌</span>
                <p>{data.parentContentError}</p>
              </div>
            )}
          </div>
        )}

        {/* Topic Input */}
        <div className="form-section">
          <label className="form-label">
            What topic would you like to create content about?
          </label>
          <textarea
            className="topic-input"
            placeholder="e.g., AI-powered customer service automation, benefits of cloud migration, sustainable business practices..."
            value={data.topic}
            onChange={(e) => updateData({ topic: e.target.value })}
            rows={3}
          />
          <div className="topic-suggestions">
            <span className="suggestion-label">Suggestions:</span>
            <button
              type="button"
              className="suggestion-chip"
              onClick={() => updateData({ topic: 'Industry trends and predictions for 2025' })}
            >
              Industry trends
            </button>
            <button
              type="button"
              className="suggestion-chip"
              onClick={() => updateData({ topic: 'How our product solves common challenges' })}
            >
              Product feature
            </button>
            <button
              type="button"
              className="suggestion-chip"
              onClick={() => updateData({ topic: 'Customer success story and results' })}
            >
              Case study
            </button>
          </div>
        </div>

        {/* Content Type Selection - Hidden for sub-projects (already selected when creating sub-project) */}
        {!data.isSubProject && (
          <div className="form-section">
            <label className="form-label">Content Type</label>
            <div className="content-type-grid">
              {CONTENT_TYPES.map((type) => (
                <div
                  key={type.id}
                  className={`content-type-card ${data.contentType === type.id ? 'selected' : ''}`}
                  onClick={() => updateData({ contentType: type.id })}
                >
                  <span className="type-icon">{type.icon}</span>
                  <span className="type-label">{type.label}</span>
                  <span className="type-description">{type.description}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Target Audience - Hidden for sub-projects with parent content */}
        {!(data.isSubProject && data.parentContent?.audience) && (
          <div className="form-section">
            <label className="form-label">Target Audience</label>
            <select
              className="form-select"
              value={data.targetAudience}
              onChange={(e) => updateData({ targetAudience: e.target.value })}
            >
              <option value="">Select an audience...</option>
              {audiences.map((audience) => (
                <option key={audience.id} value={audience.id}>
                  {audience.label}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Tone Selection - Hidden for sub-projects that inherit tone */}
        {!(data.isSubProject && data.inheritTone) && (
          <div className="form-section">
            <label className="form-label">Tone & Style</label>
            <div className="tone-options">
              {tones.map((tone) => (
                <label key={tone.id} className="tone-option">
                  <input
                    type="radio"
                    name="tone"
                    value={tone.id}
                    checked={data.tone === tone.id}
                    onChange={(e) => updateData({ tone: e.target.value })}
                  />
                  <span className="tone-label">{tone.label}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Keywords */}
        <div className="form-section">
          <label className="form-label">
            Keywords (optional)
            <span className="label-hint">Comma-separated terms to include</span>
          </label>
          <input
            type="text"
            className="form-input"
            placeholder="e.g., AI, automation, efficiency, ROI"
            value={data.keywords}
            onChange={(e) => updateData({ keywords: e.target.value })}
          />
        </div>
      </div>

      {/* Navigation */}
      <div className="step-navigation">
        <div className="nav-spacer" />
        <button
          className="btn btn-primary"
          onClick={onNext}
          disabled={!canProceed}
        >
          Next: Research & Context →
        </button>
      </div>
    </div>
  );
}
