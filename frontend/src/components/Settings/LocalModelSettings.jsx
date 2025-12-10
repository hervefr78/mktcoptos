import React, { useEffect, useState } from 'react';

const availableModels = ['llama2', 'mistral', 'vicuna'];

export default function LocalModelSettings() {
  const [model, setModel] = useState('');
  const [status, setStatus] = useState('disconnected');

  useEffect(() => {
    if (!model) {
      setStatus('disconnected');
      return;
    }
    setStatus('checking');
    const id = setTimeout(() => setStatus('ready'), 500);
    return () => clearTimeout(id);
  }, [model]);

  return (
    <div className="local-model-settings">
      <h3>Local Model Selection</h3>
      <select value={model} onChange={(e) => setModel(e.target.value)}>
        <option value="">Select a model</option>
        {availableModels.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
      {model && <p className={`status status-${status}`}>Status: {status}</p>}
    </div>
  );
}

