import React, { useState } from 'react';
import ActivityWizard from './ActivityWizard';
import ContentPreview from './ContentPreview';
import ActionPanel from './ActionPanel';

export default function NewActivityPage() {
  const [sections, setSections] = useState([]);
  const [scores, setScores] = useState({});
  const [content, setContent] = useState('');

  const handleGenerate = (data) => {
    const newSections = data?.sections || [];
    const newScores = data?.scores || data?.metrics || {};
    setSections(newSections);
    setScores(newScores);
    setContent(newSections.map((s) => s.html).join('\n'));
  };

  const handleChange = (id, html) => {
    const updated = sections.map((s) => (s.id === id ? { ...s, html } : s));
    setSections(updated);
    setContent(updated.map((s) => s.html).join('\n'));
  };

  const handleRegenerate = async (id) => {
    // Placeholder for section regeneration logic
    console.warn(`Regenerate section ${id} not implemented`);
  };

  return (
    <div className="new-activity-page">
      <ActivityWizard onGenerate={handleGenerate} />
      {sections.length > 0 && (
        <>
          <ContentPreview
            sections={sections}
            scores={scores}
            onChange={handleChange}
            onRegenerate={handleRegenerate}
          />
          <ActionPanel content={content} />
        </>
      )}
    </div>
  );
}
