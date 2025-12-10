import React, { useState, useEffect } from 'react';
import RAGInsightsPanel from './RAGInsightsPanel';
import AgentActivitiesTab from './AgentActivitiesTab';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function StepReview({ data, updateData, onNext, onBack }) {
  const [activeTab, setActiveTab] = useState('content');
  const [editedContent, setEditedContent] = useState(data.generatedContent || '');
  const [dismissedSuggestions, setDismissedSuggestions] = useState([]);
  const [categoryOptions, setCategoryOptions] = useState([
    'Technology',
    'Business',
    'Marketing',
    'Design',
    'Other',
  ]);
  const [categoriesLoading, setCategoriesLoading] = useState(false);
  const [categoryError, setCategoryError] = useState('');

  // SEO state - populated from pipeline results
  const [seoData, setSeoData] = useState({
    metaTitle: '',
    metaDescription: '',
    focusKeyword: '',
  });

  // Metadata state
  const [metadata, setMetadata] = useState({
    author: 'Marketing Team',
    category: data.metadata?.category || 'Technology',
    tags: '',
  });

  // Image generation state
  const [imageSubTab, setImageSubTab] = useState('generate');
  const [imagePrompt, setImagePrompt] = useState(data.imagePrompt || '');
  const [negativePrompt, setNegativePrompt] = useState('low quality, blurry, distorted');
  const [imageSize, setImageSize] = useState('square'); // Changed to semantic naming
  const [isGeneratingPrompt, setIsGeneratingPrompt] = useState(false);
  const [isGeneratingImage, setIsGeneratingImage] = useState(false);
  const [isSavingPrompt, setIsSavingPrompt] = useState(false);
  const [previewImageUrl, setPreviewImageUrl] = useState(null);
  const [contentImages, setContentImages] = useState(data.contentImages || []);
  const [uploadPreview, setUploadPreview] = useState(null);
  const [uploadFile, setUploadFile] = useState(null);
  const [imageDescription, setImageDescription] = useState('');
  const [databaseImages, setDatabaseImages] = useState([]);
  const [isLoadingDbImages, setIsLoadingDbImages] = useState(false);
  const [selectedDbImage, setSelectedDbImage] = useState(null);
  const [currentImageModel, setCurrentImageModel] = useState('gpt-image-1'); // Track current model

  // Timeline state (Phase 1B: Retrospective view)
  const [timeline, setTimeline] = useState(null);
  const [loadingTimeline, setLoadingTimeline] = useState(false);
  const [expandedStages, setExpandedStages] = useState(new Set());

  // Get actual size string based on selection and model
  const getImageSize = () => {
    const isDalle3 = currentImageModel === 'dall-e-3';

    if (imageSize === 'square') return '1024x1024';
    if (imageSize === 'landscape') return isDalle3 ? '1792x1024' : '1536x1024';
    if (imageSize === 'portrait') return isDalle3 ? '1024x1792' : '1024x1536';
    return '1024x1024';
  };

  // Get dimension labels for UI based on current model
  const getSizeLabel = (size) => {
    const isDalle3 = currentImageModel === 'dall-e-3';

    if (size === 'square') return '1024×1024';
    if (size === 'landscape') return isDalle3 ? '1792×1024' : '1536×1024';
    if (size === 'portrait') return isDalle3 ? '1024×1792' : '1024×1536';
    return '1024×1024';
  };

  // Image size options with semantic naming
  const imageSizeOptions = [
    { value: 'square', label: 'Square', icon: '⬜' },
    { value: 'landscape', label: 'Landscape', icon: '▭' },
    { value: 'portrait', label: 'Portrait', icon: '▯' },
  ];

  useEffect(() => {
    const controller = new AbortController();
    const loadCategories = async () => {
      setCategoriesLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/categories`, { signal: controller.signal });
        if (!res.ok) throw new Error('Failed to load categories');
        const data = await res.json();
        const fetched = Array.isArray(data?.categories) ? data.categories : [];
        const names = fetched
          .map((item) => (typeof item === 'string' ? item : item?.name))
          .filter(Boolean);
        if (names.length) {
          setCategoryOptions(names);
          setMetadata((prev) => ({ ...prev, category: prev.category || names[0] }));
        }
        setCategoryError('');
      } catch (err) {
        if (err.name === 'AbortError') return;
        console.error('Failed to load categories', err);
        setCategoryError('Unable to load categories right now.');
      } finally {
        setCategoriesLoading(false);
      }
    };

    loadCategories();

    return () => controller.abort();
  }, []);

  // Initialize from pipeline results
  useEffect(() => {
    if (data.generatedContent && !editedContent) {
      setEditedContent(data.generatedContent);
    }

    // Populate SEO data from pipeline results
    const seoVersion = data.pipelineResult?.seo_version?.on_page_seo;
    if (seoVersion) {
      setSeoData({
        metaTitle: seoVersion.title_tag || '',
        metaDescription: seoVersion.meta_description || '',
        focusKeyword: seoVersion.focus_keyword || '',
      });
    }
  }, [data.generatedContent, data.pipelineResult]);

  // Sync image prompt from data
  useEffect(() => {
    if (data.imagePrompt) {
      setImagePrompt(data.imagePrompt);
    }
  }, [data.imagePrompt]);

  // Get suggestions from pipeline results or use defaults
  const getSuggestions = () => {
    const editorNotes = data.pipelineResult?.final_review?.editor_notes_for_user || [];
    const suggestedVariants = data.pipelineResult?.final_review?.suggested_variants || [];

    if (editorNotes.length > 0) {
      return editorNotes.map((note, index) => ({
        id: index + 1,
        type: 'enhancement',
        text: note,
      }));
    }

    // Default suggestions if none from pipeline
    return [
      { id: 1, type: 'enhancement', text: 'Consider adding statistics to strengthen your argument' },
      { id: 2, type: 'action', text: 'Include a clear call-to-action at the end' },
      { id: 3, type: 'style', text: 'Review paragraph length for better readability' },
      { id: 4, type: 'seo', text: 'Ensure focus keyword appears in first paragraph' },
    ];
  };

  const suggestions = getSuggestions().filter(s => !dismissedSuggestions.includes(s.id));

  const handleContentChange = (e) => {
    setEditedContent(e.target.value);
    updateData({ editedContent: e.target.value });
  };

  const handleSeoChange = (field, value) => {
    setSeoData(prev => ({ ...prev, [field]: value }));
    updateData({
      seoData: { ...seoData, [field]: value }
    });
  };

  const handleMetadataChange = (field, value) => {
    setMetadata(prev => ({ ...prev, [field]: value }));
    updateData({
      metadata: { ...metadata, [field]: value }
    });
  };

  const applySuggestion = (suggestion) => {
    // Apply suggestion to content based on type
    let updatedContent = editedContent;

    if (suggestion.type === 'action' && suggestion.text.toLowerCase().includes('call-to-action')) {
      // Add CTA at end
      updatedContent += '\n\n**Ready to get started? Contact us today to learn more!**';
    } else if (suggestion.type === 'seo' && suggestion.text.toLowerCase().includes('meta description')) {
      // Generate meta description from content
      const firstParagraph = editedContent.split('\n')[0] || '';
      handleSeoChange('metaDescription', firstParagraph.slice(0, 160));
      alert('Meta description generated from first paragraph');
      return;
    } else {
      // For other suggestions, highlight the area to improve
      alert(`Suggestion applied: ${suggestion.text}\n\nPlease review and adjust your content accordingly.`);
      return;
    }

    setEditedContent(updatedContent);
    updateData({ editedContent: updatedContent });
    setDismissedSuggestions(prev => [...prev, suggestion.id]);
  };

  const dismissSuggestion = (suggestionId) => {
    setDismissedSuggestions(prev => [...prev, suggestionId]);
  };

  const regenerateSection = async () => {
    alert('Regenerating section... This would call the pipeline to regenerate the current content.');
    // TODO: Implement actual regeneration via API
  };

  const improveTone = async () => {
    alert('Improving tone... This would call the AI to adjust the writing style.');
    // TODO: Implement tone improvement via API
  };

  const adjustLength = async () => {
    const currentWords = editedContent.split(/\s+/).length;
    const action = prompt(`Current word count: ${currentWords}\n\nEnter target word count:`);
    if (action) {
      alert(`Adjusting content to approximately ${action} words...`);
      // TODO: Implement length adjustment via API
    }
  };

  // Save prompt to data
  const savePrompt = async () => {
    if (!imagePrompt.trim()) {
      alert('Prompt cannot be empty');
      return;
    }

    setIsSavingPrompt(true);
    try {
      // Save to wizard data
      updateData({ imagePrompt: imagePrompt });
      console.log('✅ Image prompt saved to content data');
      alert('Prompt saved successfully!');
    } catch (error) {
      console.error('❌ Failed to save prompt:', error);
      alert('Failed to save prompt');
    } finally {
      setIsSavingPrompt(false);
    }
  };

  // Generate prompt from content
  const generatePromptFromContent = async () => {
    if (!editedContent) {
      alert('No content available to generate prompt from');
      return;
    }

    setIsGeneratingPrompt(true);
    console.log('🎨 Generating image prompt from content...');
    try {
      const response = await fetch(`${API_BASE}/api/images/generate-prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: editedContent,
          content_type: data.contentType || 'blog',
          style_hints: data.tone || 'professional'
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        const errorMessage = errorData.detail || `HTTP ${response.status}`;
        console.error('Prompt generation error:', response.status, errorMessage);
        throw new Error(errorMessage);
      }

      const result = await response.json();
      console.log('✅ Prompt generated:', result.prompt);
      setImagePrompt(result.prompt);
      setNegativePrompt(result.negative_prompt);
      // Auto-save the generated prompt
      updateData({ imagePrompt: result.prompt });
    } catch (error) {
      console.error('Error generating prompt:', error);
      alert('Failed to generate prompt: ' + error.message);
    } finally {
      setIsGeneratingPrompt(false);
    }
  };

  // Generate image from prompt
  const generateImage = async () => {
    if (!imagePrompt) {
      alert('Please enter or generate an image prompt first');
      return;
    }

    const actualSize = getImageSize();
    setIsGeneratingImage(true);
    console.log('📸 Generating image with prompt:', imagePrompt, 'size:', actualSize);
    try {
      const response = await fetch(`${API_BASE}/api/images/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: imagePrompt,
          size: actualSize,
          quality: 'high',
          style: 'vivid',
          pipeline_execution_id: data.pipelineExecutionId || null,
          user_id: 1,  // TODO: Get from auth context
          project_id: data.projectId || null
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        const errorMessage = errorData.detail || `HTTP ${response.status}`;
        console.error('Image generation error:', response.status, errorMessage);
        throw new Error(errorMessage);
      }

      const result = await response.json();
      console.log('✅ Image generated and saved to database:', result);
      // The URL now points to our database image endpoint - prepend API_BASE if needed
      const fullUrl = result.url.startsWith('http') ? result.url : `${API_BASE}${result.url}`;
      setPreviewImageUrl(fullUrl);

      // Refresh database images list if we're on that tab
      if (imageSubTab === 'database') {
        await loadDatabaseImages();
      }
    } catch (error) {
      console.error('❌ Error generating image:', error);
      alert('Failed to generate image: ' + error.message);
    } finally {
      setIsGeneratingImage(false);
    }
  };

  // Handle file upload for preview
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setUploadFile(file);
      const reader = new FileReader();
      reader.onload = (e) => setUploadPreview(e.target.result);
      reader.readAsDataURL(file);
    }
  };

  // Use the preview image (add to content images)
  const usePreviewImage = async () => {
    if (previewImageUrl) {
      const newImage = {
        id: Date.now(),
        url: previewImageUrl,
        prompt: imagePrompt,
        type: 'generated',
        createdAt: new Date().toISOString()
      };
      const updatedImages = [...contentImages, newImage];
      setContentImages(updatedImages);
      updateData({ contentImages: updatedImages });
      setPreviewImageUrl(null);
      setImagePrompt('');

      // Refresh database images to show the newly saved image
      await loadDatabaseImages();
      alert('Image added to content and saved to gallery');
    }
  };

  // Use uploaded image
  const useUploadedImage = () => {
    if (uploadPreview) {
      const newImage = {
        id: Date.now(),
        url: uploadPreview,
        description: imageDescription,
        type: 'uploaded',
        filename: uploadFile?.name,
        createdAt: new Date().toISOString()
      };
      const updatedImages = [...contentImages, newImage];
      setContentImages(updatedImages);
      updateData({ contentImages: updatedImages });
      setUploadPreview(null);
      setUploadFile(null);
      setImageDescription('');
      alert('Image added to content');
    }
  };

  // Load images from database
  const loadDatabaseImages = async () => {
    setIsLoadingDbImages(true);
    try {
      // Build query params - if we have a projectId, filter by it
      const params = new URLSearchParams({ limit: '50', sortBy: 'newest' });

      // Filter by project ID if available
      if (data.projectId) {
        params.append('projectId', data.projectId);
      }

      const response = await fetch(`${API_BASE}/api/images/list?${params.toString()}`);
      if (response.ok) {
        const responseData = await response.json();
        // API returns { images: [...], pagination: {...} }
        setDatabaseImages(responseData.images || []);
        console.log(`Loaded ${responseData.images?.length || 0} images for project ${data.projectId || 'all'}`);
      } else {
        // Fallback to empty if endpoint doesn't exist yet
        setDatabaseImages([]);
      }
    } catch (error) {
      console.error('Error loading database images:', error);
      setDatabaseImages([]);
    } finally {
      setIsLoadingDbImages(false);
    }
  };

  // Select image from database
  const selectDatabaseImage = (image) => {
    setSelectedDbImage(image);
    const newImage = {
      id: Date.now(),
      url: `${API_BASE}/api/images/${image.id}`,
      description: image.description || image.prompt,
      type: 'database',
      originalId: image.id,
      createdAt: new Date().toISOString()
    };
    const updatedImages = [...contentImages, newImage];
    setContentImages(updatedImages);
    updateData({ contentImages: updatedImages });
    console.log('🔗 Image selected from database:', image.id);
    alert('Image added to content!');
  };

  // Load pipeline timeline (Phase 1B: Retrospective view)
  const loadTimeline = async () => {
    if (!data.pipelineId) return;

    setLoadingTimeline(true);
    try {
      const response = await fetch(`${API_BASE}/api/content-pipeline/history/${data.pipelineId}/timeline`);
      if (response.ok) {
        const timelineData = await response.json();
        console.log('Timeline data loaded:', timelineData);
        setTimeline(timelineData);
      } else {
        console.error('Failed to load timeline:', response.status);
      }
    } catch (error) {
      console.error('Error loading timeline:', error);
    } finally {
      setLoadingTimeline(false);
    }
  };

  // Toggle stage expansion in timeline
  const toggleStageExpansion = (stageName) => {
    setExpandedStages(prev => {
      const next = new Set(prev);
      if (next.has(stageName)) {
        next.delete(stageName);
      } else {
        next.add(stageName);
      }
      return next;
    });
  };

  // Format source label for display
  const formatSourceLabel = (source) => {
    if (source === 'manual-upload') return 'Uploaded by user';
    if (source === 'openai') return 'OpenAI';
    if (source === 'comfyui') return 'ComfyUI';
    if (source === 'stable-diffusion') return 'Stable Diffusion';
    return source;
  };

  // Remove image from content
  const removeContentImage = (imageId) => {
    const updatedImages = contentImages.filter(img => img.id !== imageId);
    setContentImages(updatedImages);
    updateData({ contentImages: updatedImages });
  };

  // Load database images when switching to that tab
  useEffect(() => {
    if (imageSubTab === 'database') {
      loadDatabaseImages();
    }
  }, [imageSubTab]);

  return (
    <div className="wizard-step step-review">
      <div className="step-header">
        <span className="step-indicator">Step 4 of 5</span>
        <h2>Review & Edit</h2>
        <p className="step-description">
          Refine your content before publishing
        </p>
      </div>

      <div className="step-content">
        {/* Tab Navigation */}
        <div className="review-tabs">
          <button
            className={`tab-btn ${activeTab === 'content' ? 'active' : ''}`}
            onClick={() => setActiveTab('content')}
          >
            Content
          </button>
          <button
            className={`tab-btn ${activeTab === 'images' ? 'active' : ''}`}
            onClick={() => setActiveTab('images')}
          >
            Images
          </button>
          <button
            className={`tab-btn ${activeTab === 'seo' ? 'active' : ''}`}
            onClick={() => setActiveTab('seo')}
          >
            SEO & GEO
          </button>
          <button
            className={`tab-btn ${activeTab === 'metadata' ? 'active' : ''}`}
            onClick={() => setActiveTab('metadata')}
          >
            Metadata
          </button>
          <button
            className={`tab-btn ${activeTab === 'rag' ? 'active' : ''}`}
            onClick={() => setActiveTab('rag')}
          >
            RAG Analysis
          </button>
          <button
            className={`tab-btn ${activeTab === 'timeline' ? 'active' : ''}`}
            onClick={() => {
              setActiveTab('timeline');
              if (!timeline) loadTimeline();
            }}
          >
            Timeline
          </button>
          <button
            className={`tab-btn ${activeTab === 'agents' ? 'active' : ''}`}
            onClick={() => setActiveTab('agents')}
          >
            AI Agents
          </button>
        </div>

        {/* Content Editor */}
        {activeTab === 'content' && (
          <div className="content-editor-section">
            <div className="editor-container">
              <textarea
                className="content-editor"
                value={editedContent}
                onChange={handleContentChange}
                rows={20}
              />
            </div>

            {/* AI Suggestions */}
            <div className="suggestions-panel">
              <h4>AI Suggestions</h4>
              {suggestions.length === 0 ? (
                <p className="no-suggestions">All suggestions addressed!</p>
              ) : (
                <div className="suggestions-list">
                  {suggestions.map((suggestion) => (
                    <div key={suggestion.id} className={`suggestion-item ${suggestion.type}`}>
                      <span className="suggestion-text">{suggestion.text}</span>
                      <div className="suggestion-actions">
                        <button
                          className="btn btn-small"
                          onClick={() => applySuggestion(suggestion)}
                        >
                          Apply
                        </button>
                        <button
                          className="btn btn-small btn-ghost"
                          onClick={() => dismissSuggestion(suggestion.id)}
                        >
                          Dismiss
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Images Tab */}
        {activeTab === 'images' && (
          <div className="images-section">
            {/* Image Sub-tabs */}
            <div className="image-subtabs" style={{ marginBottom: '20px', display: 'flex', gap: '8px' }}>
              <button
                className={`subtab-btn ${imageSubTab === 'generate' ? 'active' : ''}`}
                onClick={() => setImageSubTab('generate')}
                style={{
                  padding: '8px 16px',
                  border: imageSubTab === 'generate' ? '2px solid #3b82f6' : '1px solid #d1d5db',
                  borderRadius: '6px',
                  backgroundColor: imageSubTab === 'generate' ? '#dbeafe' : 'white',
                  color: imageSubTab === 'generate' ? '#1d4ed8' : '#374151',
                  fontWeight: imageSubTab === 'generate' ? '600' : '500',
                  cursor: 'pointer'
                }}
              >
                Generate Image
              </button>
              <button
                className={`subtab-btn ${imageSubTab === 'upload' ? 'active' : ''}`}
                onClick={() => setImageSubTab('upload')}
                style={{
                  padding: '8px 16px',
                  border: imageSubTab === 'upload' ? '2px solid #3b82f6' : '1px solid #d1d5db',
                  borderRadius: '6px',
                  backgroundColor: imageSubTab === 'upload' ? '#dbeafe' : 'white',
                  color: imageSubTab === 'upload' ? '#1d4ed8' : '#374151',
                  fontWeight: imageSubTab === 'upload' ? '600' : '500',
                  cursor: 'pointer'
                }}
              >
                Upload Image
              </button>
              <button
                className={`subtab-btn ${imageSubTab === 'database' ? 'active' : ''}`}
                onClick={() => setImageSubTab('database')}
                style={{
                  padding: '8px 16px',
                  border: imageSubTab === 'database' ? '2px solid #3b82f6' : '1px solid #d1d5db',
                  borderRadius: '6px',
                  backgroundColor: imageSubTab === 'database' ? '#dbeafe' : 'white',
                  color: imageSubTab === 'database' ? '#1d4ed8' : '#374151',
                  fontWeight: imageSubTab === 'database' ? '600' : '500',
                  cursor: 'pointer'
                }}
              >
                Select from Database
              </button>
            </div>

            {/* Generate Image Sub-tab */}
            {imageSubTab === 'generate' && (
              <div className="generate-image-section">
                {/* Image Prompt Section with improved UI */}
                <div className="form-group">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <label>Image Prompt (Editable)</label>
                    <button
                      className="btn btn-small btn-outline"
                      onClick={generatePromptFromContent}
                      disabled={isGeneratingPrompt || !editedContent}
                      style={{ fontSize: '0.75rem' }}
                    >
                      {isGeneratingPrompt ? 'Generating...' : imagePrompt ? 'Regenerate from Content' : 'Generate from Content'}
                    </button>
                  </div>

                  {imagePrompt ? (
                    <div style={{
                      marginBottom: '12px',
                      padding: '12px',
                      backgroundColor: '#f0f9ff',
                      borderRadius: '6px',
                      border: '1px solid #bae6fd'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '8px' }}>
                        <p style={{ fontSize: '0.75rem', fontWeight: '600', color: '#0369a1', margin: 0 }}>
                          ✅ Prompt (Editable):
                        </p>
                        <button
                          className="btn btn-small btn-outline"
                          onClick={savePrompt}
                          disabled={isSavingPrompt}
                          style={{ fontSize: '0.75rem' }}
                        >
                          {isSavingPrompt ? 'Saving...' : 'Save Prompt'}
                        </button>
                      </div>
                      <textarea
                        className="form-textarea"
                        value={imagePrompt}
                        onChange={(e) => setImagePrompt(e.target.value)}
                        rows={3}
                        placeholder="Edit the prompt for image generation..."
                        style={{
                          marginTop: '8px',
                          fontSize: '0.875rem',
                          fontFamily: 'monospace',
                          backgroundColor: 'white',
                          border: '1px solid #7dd3fc'
                        }}
                      />
                      <p style={{ fontSize: '0.75rem', color: '#0284c7', marginTop: '8px', marginBottom: 0 }}>
                        💡 Edit the prompt as needed, then click "Save Prompt" to update. Use "Regenerate from Content" to regenerate from post content.
                      </p>
                    </div>
                  ) : (
                    <p style={{ fontSize: '0.875rem', color: '#6b7280', fontStyle: 'italic', marginBottom: '12px' }}>
                      No prompt generated yet. Click "Generate from Content" to create an AI-optimized prompt.
                    </p>
                  )}
                </div>

                {/* Image Size Selector with model-aware labels */}
                <div className="form-group">
                  <label>Image Size</label>
                  <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                    {imageSizeOptions.map((option) => (
                      <button
                        key={option.value}
                        onClick={() => setImageSize(option.value)}
                        style={{
                          flex: 1,
                          padding: '12px 16px',
                          border: imageSize === option.value ? '2px solid #3b82f6' : '2px solid #e5e7eb',
                          borderRadius: '8px',
                          backgroundColor: imageSize === option.value ? '#dbeafe' : 'white',
                          color: imageSize === option.value ? '#1e40af' : '#374151',
                          cursor: 'pointer',
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          gap: '6px',
                          transition: 'all 0.2s'
                        }}
                      >
                        <span style={{ fontSize: '1.75rem' }}>{option.icon}</span>
                        <span style={{ fontSize: '0.875rem', fontWeight: imageSize === option.value ? '600' : '500' }}>
                          {option.label}
                        </span>
                        <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                          {getSizeLabel(option.value)}
                        </span>
                      </button>
                    ))}
                  </div>
                  <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '6px' }}>
                    Sizes are optimized for {currentImageModel === 'dall-e-3' ? 'DALL-E 3' : 'gpt-image-1'}
                  </p>
                </div>

                {/* Negative Prompt (Collapsible Advanced Section) */}
                <details style={{ marginTop: '16px', marginBottom: '16px' }}>
                  <summary style={{
                    cursor: 'pointer',
                    fontSize: '0.875rem',
                    fontWeight: '500',
                    color: '#374151',
                    padding: '8px 0',
                    listStyle: 'none'
                  }}>
                    ⚙️ Advanced: Negative Prompt (Optional)
                  </summary>
                  <div style={{ marginTop: '8px' }}>
                    <textarea
                      className="form-textarea"
                      value={negativePrompt}
                      onChange={(e) => setNegativePrompt(e.target.value)}
                      rows={2}
                      placeholder="What to avoid in the image (e.g., low quality, blurry, distorted)"
                      style={{ fontSize: '0.875rem' }}
                    />
                    <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '6px' }}>
                      Specify elements to exclude from the generated image
                    </p>
                  </div>
                </details>

                {/* Generate Button */}
                <div style={{ marginTop: '20px', marginBottom: '20px' }}>
                  <button
                    className="btn btn-primary"
                    onClick={generateImage}
                    disabled={isGeneratingImage || !imagePrompt.trim()}
                    style={{ width: '100%', padding: '12px' }}
                  >
                    {isGeneratingImage ? '⏳ Generating Image...' : '✨ Generate Image'}
                  </button>
                  <div style={{
                    marginTop: '12px',
                    padding: '12px',
                    backgroundColor: '#eff6ff',
                    borderRadius: '6px'
                  }}>
                    <p style={{ fontSize: '0.75rem', color: '#1e40af', fontWeight: '500', margin: 0, marginBottom: '4px' }}>
                      💡 Smart Generation Active
                    </p>
                    <p style={{ fontSize: '0.75rem', color: '#1d4ed8', margin: 0 }}>
                      Provider, model, quality, and other settings are configured in Settings → Image Generation
                    </p>
                  </div>
                </div>

                {/* Preview Generated Image */}
                {previewImageUrl && (
                  <div style={{
                    marginTop: '20px',
                    padding: '16px',
                    backgroundColor: '#f0fdf4',
                    borderRadius: '8px',
                    border: '2px solid #86efac'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <h4 style={{ margin: 0, fontSize: '0.875rem', fontWeight: '600', color: '#166534' }}>
                        ✨ New Image Ready
                      </h4>
                      <span style={{ fontSize: '0.75rem', color: '#16a34a' }}>
                        Not saved yet
                      </span>
                    </div>
                    <img
                      src={previewImageUrl}
                      alt="Generated preview"
                      style={{ width: '100%', height: 'auto', borderRadius: '8px', marginTop: '8px' }}
                    />
                    <div style={{ marginTop: '12px', display: 'flex', gap: '8px' }}>
                      <button className="btn btn-primary" onClick={usePreviewImage} style={{ flex: 1 }}>
                        ✓ Use This Image
                      </button>
                      <button className="btn btn-outline" onClick={() => setPreviewImageUrl(null)}>
                        Discard
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Upload Image Sub-tab */}
            {imageSubTab === 'upload' && (
              <div className="upload-image-section">
                <div className="form-group">
                  <label>Select Image File</label>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleFileSelect}
                    className="form-input"
                    style={{ padding: '8px' }}
                  />
                </div>

                {uploadPreview && (
                  <>
                    <div className="image-preview" style={{ marginTop: '16px' }}>
                      <img
                        src={uploadPreview}
                        alt="Upload preview"
                        style={{ maxWidth: '100%', maxHeight: '300px', borderRadius: '8px' }}
                      />
                    </div>

                    <div className="form-group" style={{ marginTop: '16px' }}>
                      <label>Image Description (optional)</label>
                      <input
                        type="text"
                        className="form-input"
                        value={imageDescription}
                        onChange={(e) => setImageDescription(e.target.value)}
                        placeholder="Describe this image..."
                      />
                    </div>

                    <div style={{ marginTop: '12px', display: 'flex', gap: '8px' }}>
                      <button className="btn btn-primary" onClick={useUploadedImage}>
                        Use This Image
                      </button>
                      <button className="btn btn-outline" onClick={() => {
                        setUploadPreview(null);
                        setUploadFile(null);
                      }}>
                        Cancel
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Select from Database Sub-tab */}
            {imageSubTab === 'database' && (
              <div className="database-images-section">
                {isLoadingDbImages ? (
                  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '60px' }}>
                    <p style={{ color: '#6b7280' }}>Loading images...</p>
                  </div>
                ) : databaseImages.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '60px', color: '#6b7280' }}>
                    <p style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '8px' }}>No images in database yet</p>
                    <p style={{ fontSize: '0.875rem' }}>Generate or upload images to build your library.</p>
                  </div>
                ) : (
                  <>
                    <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '12px' }}>
                      Click on an image to add it to your content
                    </div>
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
                      gap: '16px',
                      maxHeight: '500px',
                      overflowY: 'auto',
                      padding: '4px'
                    }}>
                      {databaseImages.map((image) => (
                        <div
                          key={image.id}
                          onClick={() => selectDatabaseImage(image)}
                          style={{
                            position: 'relative',
                            cursor: 'pointer',
                            border: selectedDbImage?.id === image.id ? '2px solid #3b82f6' : '2px solid #e5e7eb',
                            borderRadius: '8px',
                            overflow: 'hidden',
                            transition: 'all 0.2s',
                            backgroundColor: 'white'
                          }}
                          onMouseOver={(e) => {
                            if (selectedDbImage?.id !== image.id) {
                              e.currentTarget.style.borderColor = '#3b82f6';
                            }
                          }}
                          onMouseOut={(e) => {
                            if (selectedDbImage?.id !== image.id) {
                              e.currentTarget.style.borderColor = '#e5e7eb';
                            }
                          }}
                        >
                          <img
                            src={`${API_BASE}/api/images/${image.id}`}
                            alt={image.prompt || image.description || 'Database image'}
                            style={{ width: '100%', height: '140px', objectFit: 'cover' }}
                          />
                          <div style={{ padding: '8px', backgroundColor: 'white' }}>
                            <p style={{
                              margin: 0,
                              fontSize: '0.75rem',
                              color: '#374151',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              marginBottom: '4px'
                            }}>
                              {image.prompt || image.description || 'No description'}
                            </p>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span style={{ fontSize: '0.625rem', color: '#6b7280' }}>
                                {formatSourceLabel(image.source)}
                              </span>
                              {image.width && image.height && (
                                <span style={{ fontSize: '0.625rem', color: '#6b7280' }}>
                                  {image.width}×{image.height}
                                </span>
                              )}
                            </div>
                          </div>
                          {/* Selected checkmark */}
                          {selectedDbImage?.id === image.id && (
                            <div style={{
                              position: 'absolute',
                              top: '8px',
                              right: '8px',
                              backgroundColor: '#3b82f6',
                              color: 'white',
                              borderRadius: '50%',
                              padding: '4px',
                              width: '24px',
                              height: '24px',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center'
                            }}>
                              ✓
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Current Content Images */}
            {contentImages.length > 0 && (
              <div className="content-images" style={{ marginTop: '30px', borderTop: '1px solid #e5e7eb', paddingTop: '20px' }}>
                <h4>Images for This Content ({contentImages.length})</h4>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                  gap: '16px',
                  marginTop: '12px'
                }}>
                  {contentImages.map((image) => (
                    <div key={image.id} style={{
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px',
                      overflow: 'hidden'
                    }}>
                      <img
                        src={image.url}
                        alt={image.description || image.prompt || 'Content image'}
                        style={{ width: '100%', height: '150px', objectFit: 'cover' }}
                      />
                      <div style={{ padding: '8px' }}>
                        <span style={{
                          fontSize: '0.625rem',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          backgroundColor: image.type === 'generated' ? '#e0f2fe' : image.type === 'uploaded' ? '#f0fdf4' : '#fef3c7',
                          color: image.type === 'generated' ? '#0369a1' : image.type === 'uploaded' ? '#166534' : '#92400e'
                        }}>
                          {image.type}
                        </span>
                        <button
                          onClick={() => removeContentImage(image.id)}
                          style={{
                            float: 'right',
                            padding: '2px 8px',
                            fontSize: '0.75rem',
                            border: '1px solid #fca5a5',
                            borderRadius: '4px',
                            backgroundColor: 'white',
                            color: '#dc2626',
                            cursor: 'pointer'
                          }}
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* SEO Tab */}
        {activeTab === 'seo' && (
          <div className="seo-section">
            <div className="form-group">
              <label>Meta Title</label>
              <input
                type="text"
                className="form-input"
                placeholder="Enter meta title..."
                maxLength={60}
                value={seoData.metaTitle}
                onChange={(e) => handleSeoChange('metaTitle', e.target.value)}
              />
              <span className="char-count">{seoData.metaTitle.length}/60</span>
            </div>
            <div className="form-group">
              <label>Meta Description</label>
              <textarea
                className="form-textarea"
                placeholder="Enter meta description..."
                rows={3}
                maxLength={160}
                value={seoData.metaDescription}
                onChange={(e) => handleSeoChange('metaDescription', e.target.value)}
              />
              <span className="char-count">{seoData.metaDescription.length}/160</span>
            </div>
            <div className="form-group">
              <label>Focus Keyword</label>
              <input
                type="text"
                className="form-input"
                placeholder="Enter focus keyword"
                value={seoData.focusKeyword}
                onChange={(e) => handleSeoChange('focusKeyword', e.target.value)}
              />
            </div>
            <div className="seo-score">
              <span className="score-label">SEO & GEO Score</span>
              <span className="score-value">
                {seoData.metaTitle && seoData.metaDescription && seoData.focusKeyword
                  ? '92/100'
                  : seoData.metaTitle || seoData.metaDescription
                  ? '65/100'
                  : '30/100'}
              </span>
            </div>
          </div>
        )}

        {/* Metadata Tab */}
        {activeTab === 'metadata' && (
          <div className="metadata-section">
            <div className="form-group">
              <label>Author</label>
              <input
                type="text"
                className="form-input"
                value={metadata.author}
                onChange={(e) => handleMetadataChange('author', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Category</label>
              <select
                className="form-select"
                value={metadata.category}
                onChange={(e) => handleMetadataChange('category', e.target.value)}
                disabled={categoriesLoading && categoryOptions.length === 0}
              >
                {categoriesLoading && categoryOptions.length === 0 && (
                  <option value="">Loading categories…</option>
                )}
                {categoryOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              {categoryError && <p className="form-helper error-text">{categoryError}</p>}
            </div>
            <div className="form-group">
              <label>Tags</label>
              <input
                type="text"
                className="form-input"
                placeholder="Add tags separated by commas..."
                value={metadata.tags}
                onChange={(e) => handleMetadataChange('tags', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Publish Date</label>
              <input
                type="date"
                className="form-input"
                defaultValue={new Date().toISOString().split('T')[0]}
              />
            </div>
          </div>
        )}

        {/* RAG Analysis Tab */}
        {activeTab === 'rag' && (
          <div className="rag-analysis-section">
            {data.pipelineResult?.rag_insights ? (
              <RAGInsightsPanel insights={data.pipelineResult.rag_insights} />
            ) : (
              <div style={{
                padding: '2rem',
                textAlign: 'center',
                color: '#666',
                backgroundColor: '#f5f5f5',
                borderRadius: '8px',
                margin: '1rem 0'
              }}>
                <p style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>No RAG Analysis Available</p>
                <p style={{ fontSize: '0.9rem' }}>
                  RAG analysis appears here when knowledge base documents are used during content generation.
                </p>
              </div>
            )}
          </div>
        )}

        {/* AI Agents Tab */}
        {activeTab === 'agents' && (
          <div className="agents-section">
            {data.pipelineExecutionId ? (
              <AgentActivitiesTab
                executionId={data.pipelineExecutionId}
                pipelineId={data.pipelineId}
              />
            ) : (
              <div style={{
                padding: '3rem',
                textAlign: 'center',
                color: '#666',
                backgroundColor: '#f9fafb',
                borderRadius: '8px',
                border: '1px solid #e5e7eb'
              }}>
                <p style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>No Agent Activity Data</p>
                <p style={{ fontSize: '0.9rem' }}>
                  Agent activity tracking is available after running the content pipeline.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Timeline Tab (Phase 1B: Retrospective view) */}
        {activeTab === 'timeline' && (
          <div className="timeline-section" style={{ padding: '1rem 0' }}>
            {loadingTimeline ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
                Loading timeline...
              </div>
            ) : timeline ? (
              <div>
                {/* Timeline Header */}
                <div style={{
                  padding: '1rem',
                  backgroundColor: '#f9fafb',
                  borderRadius: '8px',
                  marginBottom: '1.5rem',
                  border: '1px solid #e5e7eb'
                }}>
                  <h3 style={{ margin: '0 0 0.75rem 0', fontSize: '1rem', fontWeight: '600' }}>
                    Pipeline Execution Summary
                  </h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', fontSize: '0.875rem' }}>
                    <div>
                      <div style={{ color: '#6b7280', marginBottom: '0.25rem' }}>Status</div>
                      <div style={{ fontWeight: '600', color: timeline.status === 'completed' ? '#16a34a' : '#f59e0b' }}>
                        {timeline.status.toUpperCase()}
                      </div>
                    </div>
                    <div>
                      <div style={{ color: '#6b7280', marginBottom: '0.25rem' }}>Total Duration</div>
                      <div style={{ fontWeight: '600' }}>{timeline.total_duration || 0}s</div>
                    </div>
                    <div>
                      <div style={{ color: '#6b7280', marginBottom: '0.25rem' }}>Word Count</div>
                      <div style={{ fontWeight: '600' }}>{timeline.metadata?.word_count?.toLocaleString() || 'N/A'}</div>
                    </div>
                    <div>
                      <div style={{ color: '#6b7280', marginBottom: '0.25rem' }}>Originality</div>
                      <div style={{ fontWeight: '600' }}>{timeline.metadata?.originality_score || 'N/A'}</div>
                    </div>
                    {timeline.metadata?.brave_metrics && (
                      <div>
                        <div style={{ color: '#6b7280', marginBottom: '0.25rem' }}>Brave Search</div>
                        <div style={{ fontWeight: '600' }}>{timeline.metadata.brave_metrics.requests_made || 0} req</div>
                        <div style={{ fontSize: '0.625rem', color: '#6b7280' }}>{timeline.metadata.brave_metrics.results_received || 0} results</div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Stage Timeline */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {Object.entries(timeline.stages || {}).map(([stageName, stageData], index) => {
                    const isExpanded = expandedStages.has(stageName);
                    const stageLabels = {
                      'trends_keywords': { icon: '🔍', name: 'Research & Keywords' },
                      'tone_of_voice': { icon: '🎨', name: 'Tone of Voice' },
                      'structure_outline': { icon: '📋', name: 'Structure & Outline' },
                      'writer': { icon: '✍️', name: 'Content Writer' },
                      'seo_optimizer': { icon: '🎯', name: 'SEO & GEO Optimizer' },
                      'originality_check': { icon: '✅', name: 'Originality Check' },
                      'final_review': { icon: '🔎', name: 'Final Review' }
                    };
                    const label = stageLabels[stageName] || { icon: '📌', name: stageName };

                    return (
                      <div
                        key={stageName}
                        style={{
                          border: '1px solid #e5e7eb',
                          borderRadius: '8px',
                          backgroundColor: '#fff',
                          overflow: 'hidden'
                        }}
                      >
                        {/* Stage Header (Collapsible) */}
                        <div
                          onClick={() => toggleStageExpansion(stageName)}
                          style={{
                            padding: '1rem',
                            cursor: 'pointer',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            backgroundColor: isExpanded ? '#f9fafb' : '#fff',
                            transition: 'background-color 0.2s'
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <span style={{ fontSize: '1.5rem' }}>{label.icon}</span>
                            <div>
                              <div style={{ fontWeight: '600', fontSize: '0.95rem' }}>{label.name}</div>
                              <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem' }}>
                                {stageData.duration_seconds}s • {stageData.actions?.length || 0} actions
                              </div>
                            </div>
                          </div>
                          <span style={{ fontSize: '1.25rem', color: '#6b7280' }}>
                            {isExpanded ? '▼' : '▶'}
                          </span>
                        </div>

                        {/* Stage Details (Expandable) */}
                        {isExpanded && (
                          <div style={{ padding: '0 1rem 1rem 1rem', borderTop: '1px solid #f3f4f6' }}>
                            {/* Quality Badges */}
                            {stageData.badges && stageData.badges.length > 0 && (
                              <div style={{ marginTop: '0.75rem', marginBottom: '1rem' }}>
                                <div style={{ fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>
                                  Quality Metrics:
                                </div>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                  {stageData.badges.map((badge, idx) => {
                                    const badgeColors = {
                                      'good': { bg: '#dcfce7', border: '#22c55e', text: '#166534' },
                                      'warning': { bg: '#fef3c7', border: '#f59e0b', text: '#92400e' },
                                      'error': { bg: '#fee2e2', border: '#ef4444', text: '#991b1b' }
                                    };
                                    const colors = badgeColors[badge.status] || badgeColors['good'];

                                    return (
                                      <div key={idx} style={{
                                        fontSize: '0.75rem',
                                        padding: '6px 12px',
                                        backgroundColor: colors.bg,
                                        border: `1px solid ${colors.border}`,
                                        borderRadius: '6px',
                                        color: colors.text,
                                        fontWeight: '500',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '6px'
                                      }}>
                                        <span style={{ fontWeight: '600' }}>{badge.label}</span>
                                        {badge.value && <span>{badge.value}</span>}
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}

                            {/* Action Bullets */}
                            {stageData.actions && stageData.actions.length > 0 && (
                              <div style={{ marginTop: '0.75rem' }}>
                                <div style={{ fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>
                                  What happened:
                                </div>
                                <ul style={{ margin: 0, paddingLeft: '1.5rem', fontSize: '0.875rem', color: '#6b7280', lineHeight: '1.8' }}>
                                  {stageData.actions.map((action, idx) => (
                                    <li key={idx}>{action}</li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Phase 3: Change Log */}
                            {stageData.summary?.change_log && stageData.summary.change_log.length > 0 && (
                              <div style={{ marginTop: '1rem' }}>
                                <div style={{ fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>
                                  What changed:
                                </div>
                                <div style={{
                                  padding: '0.75rem',
                                  backgroundColor: '#eff6ff',
                                  borderLeft: '3px solid #3b82f6',
                                  borderRadius: '4px'
                                }}>
                                  <ul style={{ margin: 0, paddingLeft: '1.5rem', fontSize: '0.875rem', color: '#1e40af', lineHeight: '1.8' }}>
                                    {stageData.summary.change_log.map((change, idx) => (
                                      <li key={idx}>{change}</li>
                                    ))}
                                  </ul>
                                </div>
                              </div>
                            )}

                            {/* Phase 4: Context Provenance (Sources Used) */}
                            {stageData.summary?.sources && stageData.summary.sources.length > 0 && (
                              <div style={{ marginTop: '1rem' }}>
                                <div style={{ fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>
                                  Sources used:
                                </div>
                                <div style={{
                                  padding: '0.75rem',
                                  backgroundColor: '#f0fdf4',
                                  borderLeft: '3px solid #22c55e',
                                  borderRadius: '4px'
                                }}>
                                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                    {stageData.summary.sources.map((source, idx) => (
                                      <div key={idx} style={{
                                        fontSize: '0.75rem',
                                        padding: '4px 10px',
                                        backgroundColor: '#dcfce7',
                                        border: '1px solid #86efac',
                                        borderRadius: '12px',
                                        color: '#166534',
                                        fontWeight: '500',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '4px'
                                      }}>
                                        <span>📄</span>
                                        <span>{source.name}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              </div>
                            )}

                            {/* Phase 3A: Before/After Diff Snippets */}
                            {stageData.summary?.diff_snippets && stageData.summary.diff_snippets.length > 0 && (
                              <div style={{ marginTop: '1rem' }}>
                                <div style={{ fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>
                                  Before → After:
                                </div>
                                {stageData.summary.diff_snippets.map((diff, idx) => (
                                  <div key={idx} style={{ marginTop: '0.75rem' }}>
                                    {diff.reason && (
                                      <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.5rem', fontStyle: 'italic' }}>
                                        {diff.reason}
                                      </div>
                                    )}
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '8px', alignItems: 'start' }}>
                                      <div>
                                        <div style={{ fontSize: '0.7rem', fontWeight: '600', color: '#92400e', marginBottom: '4px' }}>
                                          Before:
                                        </div>
                                        <div style={{
                                          fontSize: '0.8rem',
                                          padding: '8px 10px',
                                          backgroundColor: '#fef3c7',
                                          border: '1px solid #f59e0b',
                                          borderRadius: '6px',
                                          color: '#92400e',
                                          lineHeight: '1.6'
                                        }}>
                                          {diff.before}
                                        </div>
                                      </div>
                                      <div style={{ paddingTop: '24px', fontSize: '1rem', color: '#9ca3af' }}>→</div>
                                      <div>
                                        <div style={{ fontSize: '0.7rem', fontWeight: '600', color: '#166534', marginBottom: '4px' }}>
                                          After:
                                        </div>
                                        <div style={{
                                          fontSize: '0.8rem',
                                          padding: '8px 10px',
                                          backgroundColor: '#dcfce7',
                                          border: '1px solid #22c55e',
                                          borderRadius: '6px',
                                          color: '#166534',
                                          lineHeight: '1.6'
                                        }}>
                                          {diff.after}
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Phase 2: Quality Badges */}
                            {stageData.badges && stageData.badges.length > 0 && (
                              <div style={{ marginTop: '1rem' }}>
                                <div style={{ fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>
                                  Quality Indicators:
                                </div>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                  {stageData.badges.map((badge, idx) => {
                                    const statusColors = {
                                      good: { bg: '#dcfce7', border: '#16a34a', text: '#166534' },
                                      warning: { bg: '#fef3c7', border: '#eab308', text: '#854d0e' },
                                      error: { bg: '#fee2e2', border: '#dc2626', text: '#991b1b' }
                                    };
                                    const colors = statusColors[badge.status] || statusColors.warning;
                                    return (
                                      <div key={idx} style={{
                                        fontSize: '0.8rem',
                                        padding: '6px 12px',
                                        borderRadius: '16px',
                                        backgroundColor: colors.bg,
                                        border: `1px solid ${colors.border}`,
                                        color: colors.text,
                                        fontWeight: '500',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '6px'
                                      }}>
                                        <span>{badge.label}</span>
                                        <span style={{ fontWeight: '600' }}>{badge.value}</span>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}

                            {/* Summary Details */}
                            {stageData.summary && Object.keys(stageData.summary).length > 0 && (
                              <div style={{ marginTop: '1rem', padding: '0.75rem', backgroundColor: '#f9fafb', borderRadius: '6px' }}>
                                <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                                  {Object.entries(stageData.summary).map(([key, value]) => {
                                    if (key === 'input_tokens' || key === 'output_tokens') return null;
                                    return (
                                      <div key={key} style={{ marginBottom: '0.25rem' }}>
                                        <strong style={{ textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}:</strong>{' '}
                                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div style={{
                padding: '2rem',
                textAlign: 'center',
                color: '#666',
                backgroundColor: '#f5f5f5',
                borderRadius: '8px'
              }}>
                <p style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>No Timeline Available</p>
                <p style={{ fontSize: '0.9rem' }}>
                  Timeline data will appear here after content generation.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Quick Actions */}
        <div className="quick-actions">
          <button className="btn btn-outline" onClick={regenerateSection}>
            Regenerate Section
          </button>
          <button className="btn btn-outline" onClick={improveTone}>
            Improve Tone
          </button>
          <button className="btn btn-outline" onClick={adjustLength}>
            Adjust Length
          </button>
        </div>
      </div>

      {/* Navigation */}
      <div className="step-navigation">
        <button className="btn btn-secondary" onClick={onBack}>
          Back
        </button>
        <button className="btn btn-primary" onClick={onNext}>
          Preview & Publish
        </button>
      </div>
    </div>
  );
}
