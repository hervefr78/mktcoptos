import React, { useState } from 'react';

const activityTypes = [
  { id: 'blog', label: 'Blog' },
  { id: 'linkedin', label: 'LinkedIn' },
  { id: 'x', label: 'X' },
  { id: 'web', label: 'Web Page' },
];

export default function ActivityWizard({ onGenerate }) {
  const [step, setStep] = useState(1);
  const [project, setProject] = useState('');
  const [campaign, setCampaign] = useState('');
  const [activityType, setActivityType] = useState('');
  const [topic, setTopic] = useState('');
  const [keywords, setKeywords] = useState('');
  const [tone, setTone] = useState('');
  const [length, setLength] = useState('');
  const [toneRef, setToneRef] = useState(null);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState('');

  const next = () => setStep((s) => s + 1);
  const back = () => setStep((s) => s - 1);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setFeedback('');
    try {
      const prompt = `Create a ${activityType} about "${topic}" using keywords "${keywords}". Tone: "${tone}". Length: "${length}".`;

      const res = await fetch('/llm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      });

      const data = await res.json().catch(() => null);
      if (!res.ok) {
        throw new Error(data?.detail || 'Failed to start content generation');
      }

      if (onGenerate) {
        try {
          onGenerate(data);
        } catch (e) {
          console.error('onGenerate callback failed', e);
        }
      }

      setFeedback(
        data?.task_id
          ? `Generation started (task ${data.task_id}).`
          : 'Content generation started.'
      );
    } catch (err) {
      setFeedback(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="activity-wizard">
      {step === 1 && (
        <div className="step step-project">
          <h2>Select Project or Campaign</h2>
          <div>
            <label>Project</label>
            <input value={project} onChange={(e) => setProject(e.target.value)} />
          </div>
          <div>
            <label>Campaign</label>
            <input value={campaign} onChange={(e) => setCampaign(e.target.value)} />
          </div>
          <button disabled={!project && !campaign} onClick={next}>
            Next
          </button>
        </div>
      )}

      {step === 2 && (
        <div className="step step-activity-type">
          <h2>Choose Activity Type</h2>
          <div className="activity-types">
            {activityTypes.map((type) => (
              <div
                key={type.id}
                className={`activity-card ${
                  activityType === type.id ? 'selected' : ''
                }`}
                onClick={() => setActivityType(type.id)}
              >
                {type.label}
              </div>
            ))}
          </div>
          <div className="navigation">
            <button onClick={back}>Back</button>
            <button onClick={next} disabled={!activityType}>
              Next
            </button>
          </div>
        </div>
      )}

      {step === 3 && (
        <form className="step step-form" onSubmit={handleSubmit}>
          <h2>Activity Details</h2>
          <div>
            <label>Topic</label>
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              required
            />
          </div>
          <div>
            <label>Keywords</label>
            <input value={keywords} onChange={(e) => setKeywords(e.target.value)} />
          </div>
          <div>
            <label>Tone</label>
            <input value={tone} onChange={(e) => setTone(e.target.value)} />
          </div>
          <div>
            <label>Length / Format</label>
            <input value={length} onChange={(e) => setLength(e.target.value)} />
          </div>
          <div>
            <label>Tone Reference (optional)</label>
            <input
              type="file"
              onChange={(e) => setToneRef(e.target.files?.[0] || null)}
            />
          </div>
          <div className="navigation">
            <button type="button" onClick={back}>
              Back
            </button>
            <button type="submit" disabled={loading}>
              Generate Content Now
            </button>
          </div>
        </form>
      )}

      {loading && (
        <div className="loading-indicator">
          <div className="spinner" />
          <p>Generating content...</p>
        </div>
      )}
      {feedback && !loading && <div className="feedback">{feedback}</div>}
    </div>
  );
}

