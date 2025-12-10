const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const agentPromptsApi = {
  async list() {
    const response = await fetch(`${API_BASE}/api/agent-prompts`);
    if (!response.ok) throw new Error('Failed to load agent prompts');
    return response.json();
  },

  async get(agentId) {
    const response = await fetch(`${API_BASE}/api/agent-prompts/${agentId}`);
    if (!response.ok) throw new Error('Failed to load agent prompt');
    return response.json();
  },

  async update(agentId, payload) {
    const response = await fetch(`${API_BASE}/api/agent-prompts/${agentId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error('Failed to update agent prompt');
    return response.json();
  },

  async bestPractices() {
    const response = await fetch(`${API_BASE}/api/agent-prompts/best-practices`);
    if (!response.ok) throw new Error('Failed to load best practices');
    return response.json();
  },

  async generate(payload) {
    const response = await fetch(`${API_BASE}/api/agent-prompts/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error('Failed to generate prompt suggestion');
    return response.json();
  },
};
