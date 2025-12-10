import React, { useState, useEffect } from 'react';
import { settingsApi } from '../../services/settingsApi';
import './settings.css';

export default function PromptContextsPage() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const data = await settingsApi.getSettings();
      setSettings(data);
    } catch (error) {
      console.error('Failed to load settings:', error);
      alert('Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      await settingsApi.updateSettings(settings);
      alert('Prompt contexts saved successfully!');
    } catch (error) {
      console.error('Failed to save settings:', error);
      alert('Failed to save prompt contexts');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading prompt contexts...</div>;
  }

  if (!settings) {
    return <div className="error">Failed to load prompt contexts</div>;
  }

  return (
    <div className="prompt-contexts-page">
      <div className="page-header">
        <h1>💬 Prompt Contexts</h1>
        <p className="page-description">
          Customize the behavior and tone of the AI by providing custom context for each generation type.
          These contexts will guide the AI in generating content that matches your brand voice and requirements.
        </p>
      </div>

      <form onSubmit={handleSave} className="prompt-contexts-form">
        {/* Marketing Content Context */}
        <div className="settings-card">
          <h3>📢 Marketing Content Context</h3>
          <p className="description">
            This context will be used when generating marketing materials, campaigns, and promotional content.
            Define your brand voice, target audience, and key messaging guidelines.
          </p>
          <textarea
            value={settings.marketingPromptContext || ''}
            onChange={(e) => setSettings({ ...settings, marketingPromptContext: e.target.value })}
            rows={6}
            className="context-textarea"
            placeholder="Example: You are creating content for a B2B SaaS company targeting enterprise customers. Focus on ROI, efficiency gains, and professional credibility. Use data-driven insights and concrete examples. Maintain an authoritative yet approachable tone."
          />
          <p className="hint">This will be prepended to marketing content generation prompts</p>
        </div>

        {/* Blog Context */}
        <div className="settings-card">
          <h3>📝 Blog Content Context</h3>
          <p className="description">
            This context will be used when generating blog posts and articles.
            Specify your writing style, SEO considerations, and content depth preferences.
          </p>
          <textarea
            value={settings.blogPromptContext || ''}
            onChange={(e) => setSettings({ ...settings, blogPromptContext: e.target.value })}
            rows={6}
            className="context-textarea"
            placeholder="Example: Write in-depth, educational blog posts that demonstrate thought leadership. Use clear headings, bullet points, and practical examples. Include data and research to support claims. Optimize for SEO while maintaining readability. Target intermediate to advanced readers."
          />
          <p className="hint">This will be prepended to blog generation prompts</p>
        </div>

        {/* Social Media Context */}
        <div className="settings-card">
          <h3>📱 Social Media Context</h3>
          <p className="description">
            This context will be used when generating social media posts and engagement content.
            Define your social media strategy, tone, and engagement approach.
          </p>
          <textarea
            value={settings.socialMediaPromptContext || ''}
            onChange={(e) => setSettings({ ...settings, socialMediaPromptContext: e.target.value })}
            rows={6}
            className="context-textarea"
            placeholder="Example: Create engaging, conversational social media content that encourages interaction. Use questions to spark discussion. Keep posts concise and actionable. Include relevant hashtags. Maintain a friendly, approachable tone while staying professional."
          />
          <p className="hint">This will be prepended to social media generation prompts</p>
        </div>

        {/* Image Prompt Context */}
        <div className="settings-card">
          <h3>🎨 Image Generation Context</h3>
          <p className="description">
            This context will be used when generating prompts for AI image generation.
            Define your visual brand style, color preferences, and aesthetic guidelines.
          </p>
          <textarea
            value={settings.imagePromptContext || ''}
            onChange={(e) => setSettings({ ...settings, imagePromptContext: e.target.value })}
            rows={6}
            className="context-textarea"
            placeholder="Example: Generate images with a modern, professional aesthetic. Use a color palette of blues, grays, and whites. Prefer clean, minimalist compositions. Images should convey innovation, trust, and expertise. Avoid cluttered or overly complex visuals."
          />
          <p className="hint">This will be prepended to image prompt generation</p>
        </div>

        <div className="form-actions">
          <button type="submit" disabled={saving} className="save-btn">
            {saving ? 'Saving...' : 'Save Prompt Contexts'}
          </button>
          <button
            type="button"
            onClick={loadSettings}
            className="test-btn"
            disabled={saving}
          >
            Reset to Saved
          </button>
        </div>
      </form>

      <div className="info-panel">
        <h4>💡 Tips for Effective Prompt Contexts</h4>
        <ul>
          <li><strong>Be Specific:</strong> Provide clear, detailed guidelines rather than vague instructions</li>
          <li><strong>Include Examples:</strong> Reference specific examples of tone or style you want</li>
          <li><strong>Define Audience:</strong> Clearly state who the content is for</li>
          <li><strong>Set Boundaries:</strong> Mention what to avoid as well as what to include</li>
          <li><strong>Test and Iterate:</strong> Refine your contexts based on the generated output</li>
        </ul>
      </div>
    </div>
  );
}
