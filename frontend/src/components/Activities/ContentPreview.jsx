import React, { useState } from 'react';

function Gauge({ label, value }) {
  const clamped = Math.min(100, Math.max(0, value));
  const color = clamped > 80 ? '#4caf50' : clamped > 50 ? '#ff9800' : '#f44336';

  return (
    <div className="gauge">
      <div className="gauge-label">
        {label}: {clamped}%
      </div>
      <div className="gauge-bar">
        <div className="gauge-fill" style={{ width: `${clamped}%`, background: color }} />
      </div>
    </div>
  );
}

export default function ContentPreview({ sections = [], scores = {}, onChange, onRegenerate }) {
  const [activeTab, setActiveTab] = useState('rich');
  const [content, setContent] = useState(() =>
    sections.reduce((acc, s) => ({ ...acc, [s.id]: s.html }), {})
  );

  const handleEdit = (id, html) => {
    setContent((c) => ({ ...c, [id]: html }));
    if (onChange) onChange(id, html);
  };

  return (
    <div className="content-preview">
      <div className="content-tabs">
        <button
          className={activeTab === 'rich' ? 'active' : ''}
          onClick={() => setActiveTab('rich')}
        >
          Rich Text
        </button>
        <button
          className={activeTab === 'raw' ? 'active' : ''}
          onClick={() => setActiveTab('raw')}
        >
          Raw HTML
        </button>
      </div>

      <div className="scores">
        <Gauge label="Originality" value={scores.originality || 0} />
        <Gauge label="SEO" value={scores.seo || 0} />
        <Gauge label="Tone Match" value={scores.tone || 0} />
      </div>

      <div className="sections">
        {sections.map((section) => (
          <div key={section.id} className="section">
            <div className="section-header">
              <h3>{section.title}</h3>
              <button onClick={() => onRegenerate && onRegenerate(section.id)}>
                Regenerate
              </button>
            </div>
            {activeTab === 'rich' ? (
              <div
                className="section-content"
                contentEditable
                suppressContentEditableWarning
                onBlur={(e) => handleEdit(section.id, e.currentTarget.innerHTML)}
                dangerouslySetInnerHTML={{ __html: content[section.id] || '' }}
              />
            ) : (
              <textarea
                value={content[section.id] || ''}
                onChange={(e) => handleEdit(section.id, e.target.value)}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

