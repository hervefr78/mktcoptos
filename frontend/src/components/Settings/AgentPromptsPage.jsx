import React, { useEffect, useMemo, useState } from 'react';
import { agentPromptsApi } from '../../services/agentPromptsApi';
import './agent-prompts.css';

const initialGenerator = {
  goal: '',
  audience: '',
  brandVoice: '',
  outputFormat: '',
  constraints: '',
  variables: '',
};

export default function AgentPromptsPage() {
  const [prompts, setPrompts] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [current, setCurrent] = useState(null);
  const [bestPractices, setBestPractices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generatorInput, setGeneratorInput] = useState(initialGenerator);
  const [generatorStatus, setGeneratorStatus] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const [promptList, practices] = await Promise.all([
          agentPromptsApi.list(),
          agentPromptsApi.bestPractices(),
        ]);
        setPrompts(promptList);
        setBestPractices(practices);
        if (promptList.length > 0) {
          setSelectedId(promptList[0].agentId);
          setCurrent(promptList[0]);
        }
      } catch (error) {
        console.error('Failed to load agent prompts', error);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const selectedPrompt = useMemo(() => {
    return prompts.find((p) => p.agentId === selectedId) || null;
  }, [prompts, selectedId]);

  useEffect(() => {
    if (selectedPrompt) {
      setCurrent(selectedPrompt);
      setGeneratorInput(initialGenerator);
      setGeneratorStatus('');
    }
  }, [selectedPrompt]);

  const handleSelect = (agentId) => {
    setSelectedId(agentId);
  };

  const handleSave = async () => {
    if (!current) return;
    try {
      setSaving(true);
      const updated = await agentPromptsApi.update(current.agentId, {
        systemPrompt: current.systemPrompt,
        userPromptTemplate: current.userPromptTemplate,
      });
      setPrompts((prev) => prev.map((p) => (p.agentId === updated.agentId ? updated : p)));
      setCurrent(updated);
      setGeneratorStatus('Saved changes successfully');
    } catch (error) {
      console.error('Failed to save agent prompt', error);
      setGeneratorStatus('Save failed - please retry');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    if (!current || !selectedPrompt) return;
    setCurrent({
      ...current,
      systemPrompt: selectedPrompt.defaultSystemPrompt,
      userPromptTemplate: selectedPrompt.defaultUserPromptTemplate,
      source: 'default',
    });
  };

  const parseVariables = (value) => {
    const lines = value.split('\n').map((line) => line.trim()).filter(Boolean);
    const entries = lines.map((line) => line.split(':'));
    const result = {};
    entries.forEach(([key, ...rest]) => {
      if (key) {
        result[key.trim()] = rest.join(':').trim();
      }
    });
    return Object.keys(result).length ? result : undefined;
  };

  const handleGenerate = async () => {
    if (!current) return;
    try {
      setGeneratorStatus('Generating prompt suggestions...');
      const suggestion = await agentPromptsApi.generate({
        agentId: current.agentId,
        goal: generatorInput.goal || undefined,
        audience: generatorInput.audience || undefined,
        brandVoice: generatorInput.brandVoice || undefined,
        outputFormat: generatorInput.outputFormat || undefined,
        constraints: generatorInput.constraints || undefined,
        variables: parseVariables(generatorInput.variables || ''),
      });
      setCurrent((prev) => ({
        ...prev,
        systemPrompt: suggestion.systemPrompt || prev.systemPrompt,
        userPromptTemplate: suggestion.userPromptTemplate || prev.userPromptTemplate,
      }));
      setGeneratorStatus('Applied generated prompt. Review and adjust if needed.');
    } catch (error) {
      console.error('Failed to generate prompt suggestion', error);
      setGeneratorStatus('Generation failed - please refine inputs.');
    }
  };

  const renderPreview = (template = '') => {
    if (!template) return '';
    return template.replace(/\{(.*?)\}/g, '{$1}');
  };

  if (loading) {
    return <div className="loading">Loading agent prompts...</div>;
  }

  if (!current) {
    return <div className="error">No agent prompts available</div>;
  }

  return (
    <div className="agent-prompts-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Agent Prompt Manager</p>
          <h1>Fine-tune each agent&apos;s prompt</h1>
          <p className="page-description">
            Read, edit, and generate role-specific prompts for the multi-agent pipeline. Every agent has its own
            system prompt and user template with variable support.
          </p>
        </div>
        <div className="header-actions">
          <button className="ghost" onClick={handleReset} disabled={saving}>Reset to default</button>
          <button className="primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save changes'}
          </button>
        </div>
      </header>

      <div className="agent-prompts-grid">
        <section className="panel agents-list">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Agents</p>
              <h3>Pipeline roles</h3>
            </div>
          </div>
          <div className="agent-items">
            {prompts.map((prompt) => (
              <button
                key={prompt.agentId}
                className={`agent-pill ${selectedId === prompt.agentId ? 'active' : ''}`}
                onClick={() => handleSelect(prompt.agentId)}
              >
                <div className="agent-pill-heading">
                  <span className="agent-name">{prompt.name}</span>
                  <span className={`badge ${prompt.source === 'custom' ? 'badge-custom' : 'badge-default'}`}>
                    {prompt.source === 'custom' ? 'Custom' : 'Default'}
                  </span>
                </div>
                <p className="agent-desc">{prompt.description}</p>
              </button>
            ))}
          </div>
        </section>

        <section className="panel editor">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Prompt editor</p>
              <h3>{current.name}</h3>
              <p className="muted">Variables: {current.variables.join(', ') || 'None'}</p>
            </div>
          </div>

          <div className="editor-fields">
            <label className="field-label">System prompt</label>
            <textarea
              value={current.systemPrompt || ''}
              onChange={(e) => setCurrent({ ...current, systemPrompt: e.target.value })}
              rows={12}
              className="prompt-area"
              placeholder="Define the agent role, responsibilities, constraints, and output contract."
            />

            <label className="field-label">User prompt template</label>
            <textarea
              value={current.userPromptTemplate || ''}
              onChange={(e) => setCurrent({ ...current, userPromptTemplate: e.target.value })}
              rows={10}
              className="prompt-area"
              placeholder="Add the user-facing instructions and variable placeholders."
            />
          </div>

          <div className="preview">
            <div className="preview-header">
              <span className="eyebrow">Preview</span>
              <span className="muted">Placeholders rendered as {'{variable}'}</span>
            </div>
            <pre className="preview-box">{renderPreview(current.userPromptTemplate)}</pre>
          </div>
        </section>

        <section className="panel assistant">
          <div className="panel-header">
            <div>
              <p className="eyebrow">AI Assistant</p>
              <h3>Generate a tailored prompt</h3>
              <p className="muted">Describe the goal and constraints. We&apos;ll extend the default prompt for this agent.</p>
            </div>
          </div>

          <div className="generator-form">
            <label>Goal</label>
            <input
              type="text"
              value={generatorInput.goal}
              onChange={(e) => setGeneratorInput({ ...generatorInput, goal: e.target.value })}
              placeholder="Align tone agent to match playful launch copy"
            />

            <label>Audience</label>
            <input
              type="text"
              value={generatorInput.audience}
              onChange={(e) => setGeneratorInput({ ...generatorInput, audience: e.target.value })}
              placeholder="B2B marketers in SaaS"
            />

            <label>Brand voice / style</label>
            <input
              type="text"
              value={generatorInput.brandVoice}
              onChange={(e) => setGeneratorInput({ ...generatorInput, brandVoice: e.target.value })}
              placeholder="Casual, clear, emoji-friendly"
            />

            <label>Output format</label>
            <input
              type="text"
              value={generatorInput.outputFormat}
              onChange={(e) => setGeneratorInput({ ...generatorInput, outputFormat: e.target.value })}
              placeholder="JSON keys, bullet list, Markdown section"
            />

            <label>Constraints</label>
            <input
              type="text"
              value={generatorInput.constraints}
              onChange={(e) => setGeneratorInput({ ...generatorInput, constraints: e.target.value })}
              placeholder="Avoid claims without sources, keep under 500 words"
            />

            <label>Variable examples (key: value per line)</label>
            <textarea
              rows={4}
              value={generatorInput.variables}
              onChange={(e) => setGeneratorInput({ ...generatorInput, variables: e.target.value })}
              placeholder={'topic: onboarding automation\naudience: HR teams'}
            />

            <button className="primary full" onClick={handleGenerate} disabled={saving}>
              Generate suggestion
            </button>
            {generatorStatus && <p className="status-message">{generatorStatus}</p>}
          </div>

          <div className="best-practices">
            <div className="panel-header compact">
              <p className="eyebrow">Best practices</p>
              <h4>Prompt guardrails</h4>
            </div>
            <ul>
              {bestPractices.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        </section>
      </div>
    </div>
  );
}
