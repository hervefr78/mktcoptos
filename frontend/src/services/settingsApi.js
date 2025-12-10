/**
 * Settings API client
 */

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const settingsApi = {
  /**
   * Get current settings
   */
  async getSettings() {
    const response = await fetch(`${API_BASE}/api/settings`);
    if (!response.ok) throw new Error('Failed to load settings');
    return response.json();
  },

  /**
   * Update settings
   */
  async updateSettings(settings) {
    const response = await fetch(`${API_BASE}/api/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
    if (!response.ok) throw new Error('Failed to update settings');
    return response.json();
  },

  /**
   * List available Ollama models
   */
  async listOllamaModels() {
    const response = await fetch(`${API_BASE}/api/settings/ollama/models`);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Cannot connect to Ollama');
    }
    return response.json();
  },

  /**
   * Test Ollama connection
   */
  async testOllama(baseUrl) {
    const url = baseUrl ? `${API_BASE}/api/settings/ollama/test?base_url=${baseUrl}` : `${API_BASE}/api/settings/ollama/test`;
    const response = await fetch(url, { method: 'POST' });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Cannot connect to Ollama');
    }
    return response.json();
  },

  /**
   * Test OpenAI connection
   */
  async testOpenAI(apiKey) {
    const url = apiKey ? `${API_BASE}/api/settings/openai/test?api_key=${apiKey}` : `${API_BASE}/api/settings/openai/test`;
    const response = await fetch(url, { method: 'POST' });
    if (!response.ok) throw new Error('Cannot connect to OpenAI');
    return response.json();
  },

  /**
   * List OpenAI models with pricing
   */
  async listOpenAIModels() {
    const response = await fetch(`${API_BASE}/api/settings/openai/models`);
    if (!response.ok) throw new Error('Failed to load OpenAI models');
    return response.json();
  },

  /**
   * Test Stable Diffusion connection
   */
  async testSD(baseUrl) {
    const url = baseUrl ? `${API_BASE}/api/settings/sd/test?base_url=${baseUrl}` : `${API_BASE}/api/settings/sd/test`;
    const response = await fetch(url, { method: 'POST' });
    if (!response.ok) throw new Error('Cannot connect to Stable Diffusion');
    return response.json();
  },
};
