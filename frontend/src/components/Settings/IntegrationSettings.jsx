import React, { useState, useEffect } from 'react';
import { settingsApi } from '../../services/settingsApi';
import './settings.css';

export default function IntegrationSettings() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState({ ollama: false, openai: false, sd: false, comfyui: false });
  const [ollamaModels, setOllamaModels] = useState([]);
  const [openaiModels, setOpenaiModels] = useState([]);
  const [loadingModels, setLoadingModels] = useState(false);

  // Get currently selected providers
  const selectedImageProvider = settings?.imageProvider || 'openai';
  const selectedImageModel = settings?.openaiImageModel || 'gpt-image-1';

  // Load settings on mount
  useEffect(() => {
    loadSettings();
    loadOpenAIModels();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const data = await settingsApi.getSettings();
      setSettings(data);

      // Load Ollama models if Ollama is selected
      if (data.llmProvider === 'ollama') {
        loadOllamaModels();
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
      alert('Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const loadOllamaModels = async (retryCount = 0) => {
    try {
      setLoadingModels(true);
      const data = await settingsApi.listOllamaModels();
      setOllamaModels(data.models || []);
    } catch (error) {
      console.error('Failed to load Ollama models:', error);

      // If Ollama is starting up, retry after a delay
      if (retryCount < 2 && error.message && error.message.includes('Cannot connect to Ollama')) {
        console.log(`Retrying Ollama connection in 3 seconds... (attempt ${retryCount + 1}/2)`);
        setTimeout(() => loadOllamaModels(retryCount + 1), 3000);
      } else {
        setOllamaModels([]);
      }
    } finally {
      if (retryCount === 0) {
        setLoadingModels(false);
      }
    }
  };

  const loadOpenAIModels = async () => {
    try {
      const models = await settingsApi.listOpenAIModels();
      setOpenaiModels(models || []);
    } catch (error) {
      console.error('Failed to load OpenAI models:', error);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      const updated = await settingsApi.updateSettings(settings);
      setSettings(updated);
      alert('Settings saved successfully');
    } catch (error) {
      console.error('Failed to save settings:', error);
      alert('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleTestOllama = async () => {
    try {
      setTesting({ ...testing, ollama: true });
      await settingsApi.testOllama(settings.ollamaBaseUrl);
      alert('Successfully connected to Ollama!');
      loadOllamaModels();
    } catch (error) {
      alert(`Ollama connection failed: ${error.message}`);
    } finally {
      setTesting({ ...testing, ollama: false });
    }
  };

  const handleTestOpenAI = async () => {
    try {
      setTesting({ ...testing, openai: true });
      await settingsApi.testOpenAI(settings.openaiApiKey);
      alert('Successfully connected to OpenAI!');
    } catch (error) {
      alert(`OpenAI connection failed: ${error.message}`);
    } finally {
      setTesting({ ...testing, openai: false });
    }
  };

  const handleTestSD = async () => {
    try {
      setTesting({ ...testing, sd: true });
      await settingsApi.testSD(settings.sdBaseUrl);
      alert('Successfully connected to Stable Diffusion!');
    } catch (error) {
      alert(`Stable Diffusion connection failed: ${error.message}`);
    } finally {
      setTesting({ ...testing, sd: false });
    }
  };

  if (loading) {
    return <div className="loading">Loading settings...</div>;
  }

  if (!settings) {
    return <div className="error">Failed to load settings</div>;
  }

  return (
    <form onSubmit={handleSave} className="integration-settings">
      {/* LLM Provider Section */}
      <div className="settings-card">
        <h3>🤖 LLM Provider</h3>
        <p className="description">Choose between local (Ollama) or cloud (OpenAI) LLM provider for text generation</p>

        <div className="provider-selection">
          <label className="radio-label">
            <input
              type="radio"
              name="llmProvider"
              value="ollama"
              checked={settings.llmProvider === 'ollama'}
              onChange={(e) => {
                setSettings({ ...settings, llmProvider: e.target.value });
                if (e.target.value === 'ollama') {
                  loadOllamaModels();
                }
              }}
            />
            <div>
              <span className="provider-name">Ollama (Local)</span>
              <span className="provider-desc">Free, private, runs on your machine</span>
            </div>
          </label>

          <label className="radio-label">
            <input
              type="radio"
              name="llmProvider"
              value="openai"
              checked={settings.llmProvider === 'openai'}
              onChange={(e) => setSettings({ ...settings, llmProvider: e.target.value })}
            />
            <div>
              <span className="provider-name">OpenAI (Cloud)</span>
              <span className="provider-desc">Fast, powerful, requires API key</span>
            </div>
          </label>
        </div>

        {/* OpenAI Configuration */}
        {settings.llmProvider === 'openai' && (
          <div className="provider-config">
            <div className="form-group">
              <label>OpenAI API Key</label>
              <input
                type="password"
                placeholder="sk-..."
                value={settings.openaiApiKey || ''}
                onChange={(e) => setSettings({ ...settings, openaiApiKey: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label>Organization ID (Optional)</label>
              <input
                type="text"
                placeholder="org-xxxxx"
                value={settings.openaiOrganizationId || ''}
                onChange={(e) => setSettings({ ...settings, openaiOrganizationId: e.target.value })}
              />
              <p className="helper-text">Required for verified organizations using gpt-image-1</p>
            </div>

            <button type="button" onClick={handleTestOpenAI} disabled={testing.openai} className="test-btn">
              {testing.openai ? 'Testing...' : 'Test Connection'}
            </button>

            <div className="form-group">
              <label>Model</label>
              <select
                value={settings.llmModel || ''}
                onChange={(e) => setSettings({ ...settings, llmModel: e.target.value })}
              >
                <option value="">Select a model</option>
                {openaiModels.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name} - ${model.inputPrice}/1M in, ${model.outputPrice}/1M out
                  </option>
                ))}
              </select>
              {settings.llmModel && (
                <div className="model-info">
                  {openaiModels.find(m => m.id === settings.llmModel)?.description}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Ollama Configuration */}
        {settings.llmProvider === 'ollama' && (
          <div className="provider-config">
            <div className="form-group">
              <label>Ollama Base URL</label>
              <input
                type="text"
                placeholder="http://localhost:11434"
                value={settings.ollamaBaseUrl || ''}
                onChange={(e) => setSettings({ ...settings, ollamaBaseUrl: e.target.value })}
              />
            </div>

            <button type="button" onClick={handleTestOllama} disabled={testing.ollama} className="test-btn">
              {testing.ollama ? 'Testing...' : 'Test Connection'}
            </button>

            <div className="form-group">
              <label>Model</label>
              {loadingModels ? (
                <div className="loading-small">Loading models...</div>
              ) : ollamaModels.length > 0 ? (
                <select
                  value={settings.llmModel || ''}
                  onChange={(e) => setSettings({ ...settings, llmModel: e.target.value })}
                >
                  <option value="">Select a model</option>
                  {ollamaModels.map((model) => (
                    <option key={model.name} value={model.name}>
                      {model.name} ({(model.size / 1024 / 1024 / 1024).toFixed(1)} GB)
                    </option>
                  ))}
                </select>
              ) : (
                <div>
                  <input
                    type="text"
                    placeholder="qwen2.5:7b"
                    value={settings.llmModel || ''}
                    onChange={(e) => setSettings({ ...settings, llmModel: e.target.value })}
                  />
                  <p className="warning">⚠️ No models found. Ollama might be starting up - please wait a moment and test the connection, or manually enter a model name.</p>
                  <button
                    type="button"
                    onClick={() => loadOllamaModels()}
                    className="test-btn"
                    style={{marginTop: '8px'}}
                  >
                    Retry Loading Models
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Image Generation Section */}
      <div className="settings-card">
        <h3>🎨 Image Generation</h3>
        <p className="description">Configure image generation provider for marketing visuals</p>

        <div className="provider-selection">
          <label className="radio-label">
            <input
              type="radio"
              name="imageProvider"
              value="openai"
              checked={settings.imageProvider === 'openai'}
              onChange={(e) => setSettings({ ...settings, imageProvider: e.target.value })}
            />
            <div>
              <span className="provider-name">OpenAI</span>
              <span className="provider-desc">Fast, cloud-based, starting at $0.005/image</span>
            </div>
          </label>

          <label className="radio-label">
            <input
              type="radio"
              name="imageProvider"
              value="comfyui"
              checked={settings.imageProvider === 'comfyui'}
              onChange={(e) => setSettings({ ...settings, imageProvider: e.target.value })}
            />
            <div>
              <span className="provider-name">ComfyUI (SDXL)</span>
              <span className="provider-desc">High quality, local, free, requires setup</span>
            </div>
          </label>

          <label className="radio-label">
            <input
              type="radio"
              name="imageProvider"
              value="stable-diffusion"
              checked={settings.imageProvider === 'stable-diffusion'}
              onChange={(e) => setSettings({ ...settings, imageProvider: e.target.value })}
            />
            <div>
              <span className="provider-name">Stable Diffusion (Automatic1111)</span>
              <span className="provider-desc">Legacy support</span>
            </div>
          </label>

          <label className="radio-label">
            <input
              type="radio"
              name="imageProvider"
              value="hybrid"
              checked={settings.imageProvider === 'hybrid'}
              onChange={(e) => setSettings({ ...settings, imageProvider: e.target.value })}
            />
            <div>
              <span className="provider-name">Hybrid (Recommended)</span>
              <span className="provider-desc">OpenAI for posts, ComfyUI for blogs</span>
            </div>
          </label>
        </div>

        {/* Hybrid Strategy Settings */}
        {selectedImageProvider === 'hybrid' && (
          <div className="hybrid-strategy">
            <h4>Hybrid Strategy</h4>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={settings.useGptImageForPosts || false}
                onChange={(e) => setSettings({ ...settings, useGptImageForPosts: e.target.checked })}
              />
              <div>
                <span className="strategy-name">Use OpenAI for LinkedIn Posts</span>
                <p className="strategy-desc">Fast generation (~5s), good quality, $0.015/image</p>
              </div>
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={settings.useComfyuiForBlogs || false}
                onChange={(e) => setSettings({ ...settings, useComfyuiForBlogs: e.target.checked })}
              />
              <div>
                <span className="strategy-name">Use ComfyUI for Blog Images</span>
                <p className="strategy-desc">Best quality, local generation, free (requires ComfyUI running)</p>
              </div>
            </label>
          </div>
        )}

        {/* OpenAI Image Settings */}
        {(selectedImageProvider === 'openai' || selectedImageProvider === 'hybrid') && (
          <div className="provider-config sub-section">
            <h4>OpenAI Image Settings</h4>

            <div className="form-group">
              <label>Model</label>
              <select
                value={settings.openaiImageModel || 'gpt-image-1'}
                onChange={(e) => setSettings({ ...settings, openaiImageModel: e.target.value })}
              >
                <option value="gpt-image-1">gpt-image-1 (Recommended - $0.015/image)</option>
                <option value="gpt-image-1-mini">gpt-image-1-mini (Faster & Cheaper - $0.005/image)</option>
                <option value="dall-e-3">DALL-E 3 (Legacy - $0.04/image)</option>
              </select>
            </div>

            <div className="form-group">
              <label>Image Size</label>
              <select
                value={settings.openaiImageSize || '1024x1024'}
                onChange={(e) => setSettings({ ...settings, openaiImageSize: e.target.value })}
              >
                <option value="1024x1024">1024x1024 (Square)</option>
                {selectedImageModel === 'dall-e-3' ? (
                  <>
                    <option value="1024x1792">1024x1792 (Portrait)</option>
                    <option value="1792x1024">1792x1024 (Landscape)</option>
                  </>
                ) : (
                  <>
                    <option value="1024x1536">1024x1536 (Portrait)</option>
                    <option value="1536x1024">1536x1024 (Landscape)</option>
                    <option value="auto">Auto (Let AI decide)</option>
                  </>
                )}
              </select>
              <p className="helper-text">
                {selectedImageModel === 'dall-e-3'
                  ? 'DALL-E 3 sizes: 1024x1024, 1024x1792, 1792x1024'
                  : 'gpt-image-1 sizes: 1024x1024, 1024x1536, 1536x1024, auto'}
              </p>
            </div>

            <div className="form-group">
              <label>Quality</label>
              <select
                value={settings.openaiImageQuality || 'standard'}
                onChange={(e) => setSettings({ ...settings, openaiImageQuality: e.target.value })}
              >
                <option value="standard">Standard (Faster, cheaper)</option>
                <option value="hd">HD (Higher detail)</option>
              </select>
            </div>

            <div className="form-group">
              <label>Style</label>
              <select
                value={settings.openaiImageStyle || 'natural'}
                onChange={(e) => setSettings({ ...settings, openaiImageStyle: e.target.value })}
              >
                <option value="natural">Natural (Subtle, realistic)</option>
                <option value="vivid">Vivid (Dramatic, hyper-real)</option>
              </select>
            </div>
          </div>
        )}

        {/* ComfyUI Settings */}
        {(selectedImageProvider === 'comfyui' || selectedImageProvider === 'hybrid') && (
          <div className="provider-config sub-section">
            <h4>ComfyUI Settings</h4>

            <div className="form-group">
              <label>ComfyUI Base URL</label>
              <input
                type="text"
                placeholder="http://localhost:8188"
                value={settings.comfyuiBaseUrl || ''}
                onChange={(e) => setSettings({ ...settings, comfyuiBaseUrl: e.target.value })}
              />
              <p className="helper-text">Make sure ComfyUI is running</p>
            </div>

            <div className="form-group">
              <label>SDXL Model</label>
              <input
                type="text"
                placeholder="sd_xl_turbo_1.0_fp16.safetensors"
                value={settings.sdxlModel || ''}
                onChange={(e) => setSettings({ ...settings, sdxlModel: e.target.value })}
              />
              <p className="helper-text">Model file in ComfyUI/models/checkpoints/</p>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Steps</label>
                <input
                  type="number"
                  placeholder="6"
                  value={settings.sdxlSteps || ''}
                  onChange={(e) => setSettings({ ...settings, sdxlSteps: parseInt(e.target.value) || 6 })}
                />
                <p className="helper-text">6 for Turbo, 20 for Base</p>
              </div>

              <div className="form-group">
                <label>CFG Scale</label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="1.0"
                  value={settings.sdxlCfgScale || ''}
                  onChange={(e) => setSettings({ ...settings, sdxlCfgScale: parseFloat(e.target.value) || 1.0 })}
                />
                <p className="helper-text">1.0 for Turbo, 7.0 for Base</p>
              </div>
            </div>

            <div className="form-group">
              <label>Sampler</label>
              <select
                value={settings.sdxlSampler || 'euler_ancestral'}
                onChange={(e) => setSettings({ ...settings, sdxlSampler: e.target.value })}
              >
                <option value="euler_ancestral">Euler Ancestral (Recommended for Turbo)</option>
                <option value="dpmpp_2m">DPM++ 2M (Good for Base)</option>
                <option value="euler">Euler</option>
                <option value="ddim">DDIM</option>
                <option value="dpmpp_sde">DPM++ SDE</option>
              </select>
            </div>
          </div>
        )}

        {/* Stable Diffusion (Legacy) */}
        {selectedImageProvider === 'stable-diffusion' && (
          <div className="provider-config sub-section">
            <h4>Stable Diffusion Settings</h4>

            <div className="form-group">
              <label>API URL</label>
              <input
                type="text"
                placeholder="http://localhost:7860"
                value={settings.sdBaseUrl || ''}
                onChange={(e) => setSettings({ ...settings, sdBaseUrl: e.target.value })}
              />
              <p className="helper-text">Automatic1111 WebUI URL</p>
            </div>

            <button type="button" onClick={handleTestSD} disabled={testing.sd} className="test-btn">
              {testing.sd ? 'Testing...' : 'Test Connection'}
            </button>
          </div>
        )}
      </div>

      {/* Web Search Section */}
      <div className="settings-card">
        <h3>🔍 Web Search Integration</h3>
        <p className="description">Configure web search API for real-time research and plagiarism detection</p>

        <div className="form-group">
          <label>Brave Search API Key</label>
          <input
            type="password"
            placeholder="BSA..."
            value={settings.braveSearchApiKey || ''}
            onChange={(e) => setSettings({ ...settings, braveSearchApiKey: e.target.value })}
          />
          <p className="helper-text">
            Used by Research agent (real-time trends) and Originality agent (plagiarism detection).
            Get your free API key at <a href="https://brave.com/search/api/" target="_blank" rel="noopener noreferrer">brave.com/search/api</a> (2,000 queries/month free)
          </p>
        </div>
      </div>

      <div className="form-actions">
        <button type="submit" disabled={saving} className="save-btn">
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </form>
  );
}
