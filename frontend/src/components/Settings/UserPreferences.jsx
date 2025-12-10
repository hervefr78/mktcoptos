import React, { useState, useEffect } from 'react';

export default function UserPreferences() {
  const [length, setLength] = useState('medium');
  const [tone, setTone] = useState('neutral');
  const [seo, setSeo] = useState(true);
  const [checkpointMode, setCheckpointMode] = useState(() => {
    const saved = localStorage.getItem('checkpointMode');
    return saved === 'true';
  });

  // Save checkpoint mode to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('checkpointMode', checkpointMode.toString());
  }, [checkpointMode]);

  return (
    <div className="user-preferences">
      <h3>Default Preferences</h3>
      <div>
        <label>Content Length</label>
        <select value={length} onChange={(e) => setLength(e.target.value)}>
          <option value="short">Short</option>
          <option value="medium">Medium</option>
          <option value="long">Long</option>
        </select>
      </div>
      <div>
        <label>Tone</label>
        <select value={tone} onChange={(e) => setTone(e.target.value)}>
          <option value="neutral">Neutral</option>
          <option value="friendly">Friendly</option>
          <option value="professional">Professional</option>
        </select>
      </div>
      <div>
        <label>
          <input
            type="checkbox"
            checked={seo}
            onChange={(e) => setSeo(e.target.checked)}
          />
          Enable SEO Optimization
        </label>
      </div>
      <div>
        <label>
          <input
            type="checkbox"
            checked={checkpointMode}
            onChange={(e) => setCheckpointMode(e.target.checked)}
          />
          Enable Checkpoint Mode (Manual approval at each pipeline stage)
        </label>
      </div>
    </div>
  );
}

