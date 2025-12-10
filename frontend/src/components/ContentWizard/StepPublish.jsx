import React, { useState } from 'react';

export default function StepPublish({ data, updateData, onBack }) {
  const [previewMode, setPreviewMode] = useState('desktop');
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishSuccess, setPublishSuccess] = useState(false);

  const handlePublish = async () => {
    setIsPublishing(true);

    // Simulate publishing
    await new Promise(resolve => setTimeout(resolve, 2000));

    setIsPublishing(false);
    setPublishSuccess(true);
  };

  const handleExport = (format) => {
    // In real implementation, this would export the content
    console.log('Exporting as:', format);
    const content = data.editedContent || data.generatedContent;

    // Simple download simulation
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `content.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const wordCount = (data.editedContent || data.generatedContent || '').split(/\s+/).filter(Boolean).length;
  const readingTime = Math.ceil(wordCount / 200);

  if (publishSuccess) {
    return (
      <div className="wizard-step step-publish">
        <div className="publish-success">
          <div className="success-icon">✓</div>
          <h2>Content Published Successfully!</h2>
          <p>Your content is now live and ready to engage your audience.</p>

          <div className="success-actions">
            <button className="btn btn-primary" onClick={() => window.location.href = '/dashboard'}>
              Go to Dashboard
            </button>
            <button className="btn btn-secondary" onClick={() => setPublishSuccess(false)}>
              Create Another
            </button>
          </div>

          <div className="published-links">
            <h4>Quick Links</h4>
            <a href="#" className="published-link">View Published Content →</a>
            <a href="#" className="published-link">Share on LinkedIn →</a>
            <a href="#" className="published-link">Download PDF →</a>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="wizard-step step-publish">
      <div className="step-header">
        <span className="step-indicator">Step 5 of 5</span>
        <h2>Preview & Publish</h2>
        <p className="step-description">
          Review your content and publish to your channels
        </p>
      </div>

      <div className="step-content">
        {/* Preview Mode Selector */}
        <div className="preview-controls">
          <span className="preview-label">Preview:</span>
          <div className="preview-modes">
            <button
              className={`mode-btn ${previewMode === 'desktop' ? 'active' : ''}`}
              onClick={() => setPreviewMode('desktop')}
            >
              Desktop
            </button>
            <button
              className={`mode-btn ${previewMode === 'mobile' ? 'active' : ''}`}
              onClick={() => setPreviewMode('mobile')}
            >
              Mobile
            </button>
            <button
              className={`mode-btn ${previewMode === 'email' ? 'active' : ''}`}
              onClick={() => setPreviewMode('email')}
            >
              Email
            </button>
          </div>
        </div>

        {/* Preview Container */}
        <div className={`preview-container ${previewMode}`}>
          <div className="preview-frame">
            <div className="preview-content-rendered">
              <pre>{data.editedContent || data.generatedContent || 'No content to preview'}</pre>
            </div>
          </div>
        </div>

        {/* Publishing Options */}
        <div className="publish-options">
          <div className="option-group">
            <h4>📅 Schedule</h4>
            <input
              type="datetime-local"
              className="form-input"
              onChange={(e) => updateData({ scheduledDate: e.target.value })}
            />
          </div>

          <div className="option-group">
            <h4>📤 Export</h4>
            <div className="export-buttons">
              <button className="btn btn-small" onClick={() => handleExport('md')}>
                MD
              </button>
              <button className="btn btn-small" onClick={() => handleExport('html')}>
                HTML
              </button>
              <button className="btn btn-small" onClick={() => handleExport('pdf')}>
                PDF
              </button>
            </div>
          </div>
        </div>

        {/* Delivery Channels */}
        <div className="delivery-channels">
          <h4>Delivery Channels</h4>
          <div className="channel-options">
            <label className="channel-option">
              <input type="checkbox" defaultChecked />
              <span>Blog (WordPress)</span>
            </label>
            <label className="channel-option">
              <input type="checkbox" />
              <span>LinkedIn</span>
            </label>
            <label className="channel-option">
              <input type="checkbox" />
              <span>Newsletter</span>
            </label>
            <label className="channel-option">
              <input type="checkbox" defaultChecked />
              <span>Download</span>
            </label>
          </div>
        </div>

        {/* Content Summary */}
        <div className="content-summary">
          <h4>Content Summary</h4>
          <div className="summary-grid">
            <div className="summary-item">
              <span className="summary-label">Word count</span>
              <span className="summary-value">{wordCount.toLocaleString()}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Reading time</span>
              <span className="summary-value">{readingTime} min</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Images</span>
              <span className="summary-value">{data.generatedImages?.length || 0}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">SEO score</span>
              <span className="summary-value">92/100</span>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="step-navigation">
        <button className="btn btn-secondary" onClick={onBack}>
          ← Back
        </button>
        <div className="publish-actions">
          <button className="btn btn-outline">
            Save Draft
          </button>
          <button
            className="btn btn-primary btn-publish"
            onClick={handlePublish}
            disabled={isPublishing}
          >
            {isPublishing ? 'Publishing...' : 'Publish →'}
          </button>
        </div>
      </div>
    </div>
  );
}
