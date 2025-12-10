import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_ENDPOINTS } from '../../config/api';
import { CONTENT_TYPES } from '../../constants/contentOptions';
import './CampaignCreation.css';

const CampaignCreation = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [availableCategories, setAvailableCategories] = useState([]);
  const [categoriesLoading, setCategoriesLoading] = useState(false);
  const [categoryError, setCategoryError] = useState(null);
  const [newCategory, setNewCategory] = useState('');
  const [addingCategory, setAddingCategory] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Campaign form state
  const [campaign, setCampaign] = useState({
    name: '',
    description: '',
    categoryId: '',
    campaign_type: 'standalone',
    default_language: 'auto',
  });

  // Projects form state (for integrated campaigns)
  const [projects, setProjects] = useState([]);
  const [currentProject, setCurrentProject] = useState({
    name: '',
    description: '',
    language: 'auto',
    is_main_project: false,
    parent_project_id: null,
    content_type: '',
    inherit_tone: true,
  });


  const effectiveCategories = useMemo(() => {
    return availableCategories
      .map((option, index) => {
        if (typeof option === 'string') {
          return { id: option, name: option };
        }
        if (option && typeof option === 'object') {
          const id = option.id ?? option.value ?? index;
          const name = option.name ?? option.label ?? option.value ?? `Category ${index + 1}`;
          return { id, name };
        }
        return null;
      })
      .filter(Boolean);
  }, [availableCategories]);

  useEffect(() => {
    const loadCategories = async () => {
      setCategoriesLoading(true);
      try {
        const response = await fetch(API_ENDPOINTS.CATEGORIES, {
          credentials: 'include', // Include cookies for authentication
        });
        if (!response.ok) {
          throw new Error(`Failed to load categories: ${response.status}`);
        }
        const data = await response.json();
        console.log('Categories API response:', data); // Debug logging
        const fetched = Array.isArray(data?.categories) ? data.categories : [];
        console.log('Parsed categories:', fetched); // Debug logging
        setAvailableCategories(fetched);
        if (fetched.length > 0 && !campaign.categoryId) {
          setCampaign(prev => ({ ...prev, categoryId: fetched[0].id }));
        }
        setCategoryError(null);
      } catch (err) {
        console.error('Failed to load categories', err);
        setCategoryError('Unable to load categories. You can add one below.');
      } finally {
        setCategoriesLoading(false);
      }
    };

    loadCategories();
  }, []);

  const handleCampaignChange = (e) => {
    const { name, value } = e.target;
    setCampaign((prev) => ({ ...prev, [name]: value }));
  };

  const handleAddCategory = async (e) => {
    e.preventDefault();
    const trimmed = newCategory.trim();
    if (!trimmed) return;

    setAddingCategory(true);
    try {
      const response = await fetch(API_ENDPOINTS.CATEGORIES, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: trimmed }),
      });
      if (!response.ok) {
        throw new Error('Failed to create category');
      }

      const data = await response.json();
      const updatedCategories = Array.isArray(data?.categories) ? data.categories : [];
      setAvailableCategories(updatedCategories);
      const matched = updatedCategories.find(
        (cat) => (cat.name || cat.label || cat.value || '').toLowerCase() === trimmed.toLowerCase()
      );
      setCampaign((prev) => ({ ...prev, categoryId: matched?.id ?? prev.categoryId }));
      setNewCategory('');
      setCategoryError(null);
    } catch (err) {
      console.error('Unable to create category', err);
      setCategoryError('Unable to add category. Please try again.');
    } finally {
      setAddingCategory(false);
    }
  };

  const handleProjectChange = (e) => {
    const { name, value, type, checked } = e.target;
    setCurrentProject((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
      // Reset parent when marking as main project
      ...(name === 'is_main_project' && checked ? { parent_project_id: null } : {}),
    }));
  };

  const handleAddProject = (e) => {
    e.preventDefault();
    if (!currentProject.name.trim()) return;

    const newProject = {
      ...currentProject,
      id: Date.now(), // Temporary ID for UI
    };
    setProjects([...projects, newProject]);
    setCurrentProject({
      name: '',
      description: '',
      language: 'auto',
      is_main_project: false,
      parent_project_id: null,
      content_type: '',
      inherit_tone: true,
    });
  };

  const handleRemoveProject = (projectId) => {
    setProjects(projects.filter((p) => p.id !== projectId));
  };

  const canProceedFromStep1 = () => {
    return campaign.name.trim().length > 0 && campaign.categoryId && effectiveCategories.length > 0;
  };

  const canProceedFromStep2 = () => {
    if (campaign.campaign_type === 'standalone') {
      return true; // Can create campaign without projects
    }
    // For integrated, at least suggest having projects but allow skipping
    return true;
  };

  const handleNext = () => {
    if (currentStep === 1 && canProceedFromStep1()) {
      setCurrentStep(2);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      // Step 1: Create campaign
      const selectedCategory = effectiveCategories.find(
        (cat) => String(cat.id) === String(campaign.categoryId)
      );
      const categoryIdValue = selectedCategory?.id;

      const campaignPayload = {
        name: campaign.name,
        description: campaign.description,
        category_id: typeof categoryIdValue === 'number' ? categoryIdValue : Number(categoryIdValue) || categoryIdValue,
        category: selectedCategory?.name,
        campaign_type: campaign.campaign_type,
        default_language: campaign.default_language,
      };

      const campaignRes = await fetch(API_ENDPOINTS.CAMPAIGNS, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(campaignPayload),
      });

      if (!campaignRes.ok) {
        throw new Error('Failed to create campaign');
      }

      const campaignData = await campaignRes.json();
      const campaignId = campaignData.id;

      // Step 2: Create projects if any
      if (projects.length > 0) {
        // Map temporary IDs to create parent relationships
        const idMapping = {};

        for (const project of projects) {
          const projectPayload = {
            name: project.name,
            description: project.description,
            language: project.language,
            campaign_id: campaignId,
          };

          if (campaign.campaign_type === 'integrated') {
            projectPayload.is_main_project = project.is_main_project;
            if (project.content_type) {
              projectPayload.content_type = project.content_type;
            }
            // Map parent_project_id if it was set
            if (!project.is_main_project && project.parent_project_id) {
              const realParentId = idMapping[project.parent_project_id];
              if (realParentId) {
                projectPayload.parent_project_id = realParentId;
                projectPayload.inherit_tone = project.inherit_tone;
              }
            }
          }

          const projectRes = await fetch(API_ENDPOINTS.PROJECTS, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(projectPayload),
          });

          if (!projectRes.ok) {
            console.error(`Failed to create project: ${project.name}`);
            continue; // Continue with other projects
          }

          const projectData = await projectRes.json();
          idMapping[project.id] = projectData.id; // Map temp ID to real ID
        }
      }

      // Navigate to the campaign details page
      navigate(`/campaigns/${campaignId}`);
    } catch (err) {
      console.error('Failed to create campaign', err);
      setError('Failed to create campaign. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const mainProjects = projects.filter((p) => p.is_main_project);

  return (
    <div className="campaign-creation-page">
      <div className="campaign-creation-container">
        {/* Header */}
        <div className="creation-header">
          <div>
            <h1>Create New Campaign</h1>
            <p className="creation-subtitle">
              {campaign.campaign_type === 'integrated'
                ? 'Set up a multi-project integrated campaign'
                : 'Create a standalone campaign'}
            </p>
          </div>
          <button className="btn-secondary" onClick={() => navigate('/campaigns')}>
            Cancel
          </button>
        </div>

        {/* Progress Steps */}
        <div className="creation-steps">
          <div className={`step ${currentStep === 1 ? 'active' : currentStep > 1 ? 'completed' : ''}`}>
            <div className="step-number">{currentStep > 1 ? '✓' : '1'}</div>
            <div className="step-label">Campaign Details</div>
          </div>
          <div className="step-divider"></div>
          <div className={`step ${currentStep === 2 ? 'active' : currentStep > 2 ? 'completed' : ''}`}>
            <div className="step-number">{currentStep > 2 ? '✓' : '2'}</div>
            <div className="step-label">
              {campaign.campaign_type === 'integrated' ? 'Add Projects (Optional)' : 'Review & Create'}
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Step 1: Campaign Details */}
          {currentStep === 1 && (
            <div className="creation-step-content">
              <div className="form-section">
                <h3>Basic Information</h3>
                <label className="form-label">
                  Campaign Name *
                  <input
                    name="name"
                    value={campaign.name}
                    onChange={handleCampaignChange}
                    placeholder="Spring Product Launch 2024"
                    required
                  />
                </label>
                <label className="form-label">
                  Description
                  <textarea
                    name="description"
                    value={campaign.description}
                    onChange={handleCampaignChange}
                    placeholder="Goals, target audience, and content focus"
                    rows={3}
                  />
                </label>
              </div>

              <div className="form-section">
                <h3>Campaign Type</h3>
                <div className="campaign-type-selector">
                  <label
                    className={`type-card ${campaign.campaign_type === 'standalone' ? 'selected' : ''}`}
                    onClick={() => setCampaign((prev) => ({ ...prev, campaign_type: 'standalone' }))}
                  >
                    <input
                      type="radio"
                      name="campaign_type"
                      value="standalone"
                      checked={campaign.campaign_type === 'standalone'}
                      onChange={handleCampaignChange}
                    />
                    <div className="type-content">
                      <div className="type-icon">📄</div>
                      <div className="type-title">Standalone</div>
                      <div className="type-description">
                        Single independent project with its own content and settings
                      </div>
                    </div>
                  </label>
                  <label
                    className={`type-card ${campaign.campaign_type === 'integrated' ? 'selected' : ''}`}
                    onClick={() => setCampaign((prev) => ({ ...prev, campaign_type: 'integrated' }))}
                  >
                    <input
                      type="radio"
                      name="campaign_type"
                      value="integrated"
                      checked={campaign.campaign_type === 'integrated'}
                      onChange={handleCampaignChange}
                    />
                    <div className="type-content">
                      <div className="type-icon">🔗</div>
                      <div className="type-title">Integrated Campaign</div>
                      <div className="type-description">
                        Multiple linked projects sharing tone and source content
                      </div>
                    </div>
                  </label>
                </div>
              </div>

              <div className="form-section">
                <h3>Settings</h3>
                <label className="form-label">
                  Category *
                  <select
                    name="categoryId"
                    value={campaign.categoryId}
                    onChange={handleCampaignChange}
                    disabled={categoriesLoading || effectiveCategories.length === 0}
                    required
                  >
                    {categoriesLoading && <option value="">Loading categories...</option>}
                    {!categoriesLoading && effectiveCategories.length === 0 && (
                      <option value="">Add a category to continue</option>
                    )}
                    {effectiveCategories.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.name}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="inline-form">
                  <div className="inline-input-group">
                    <input
                      type="text"
                      placeholder="Add a new category"
                      value={newCategory}
                      onChange={(e) => setNewCategory(e.target.value)}
                    />
                    <button
                      type="button"
                      className="btn-tertiary"
                      onClick={handleAddCategory}
                      disabled={addingCategory}
                    >
                      {addingCategory ? 'Adding...' : 'Add Category'}
                    </button>
                  </div>
                  {categoryError && <p className="error-text">{categoryError}</p>}
                </div>

                <label className="form-label">
                  Default Language
                  <select name="default_language" value={campaign.default_language} onChange={handleCampaignChange}>
                    <option value="auto">Automatically detected</option>
                    <option value="en">English</option>
                    <option value="fr">French</option>
                    <option value="de">German</option>
                    <option value="es">Spanish</option>
                    <option value="it">Italian</option>
                  </select>
                </label>
              </div>

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => navigate('/campaigns')}>
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleNext}
                  disabled={!canProceedFromStep1()}
                >
                  Next: {campaign.campaign_type === 'integrated' ? 'Add Projects' : 'Review'}
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Projects (for integrated) or Review (for standalone) */}
          {currentStep === 2 && (
            <div className="creation-step-content">
              {campaign.campaign_type === 'integrated' ? (
                <>
                  <div className="form-section">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <h3>Add Projects to Campaign</h3>
                        <p className="helper-text">
                          Create main projects and sub-projects. You can also add projects later.
                        </p>
                      </div>
                    </div>

                    {/* Current Projects List */}
                    {projects.length > 0 && (
                      <div className="projects-preview">
                        <h4>Projects ({projects.length})</h4>
                        {projects.map((project) => (
                          <div key={project.id} className="project-preview-card">
                            <div className="project-preview-content">
                              <div className="project-preview-header">
                                <span className="project-preview-name">{project.name}</span>
                                <div className="project-preview-badges">
                                  {project.is_main_project && (
                                    <span className="badge badge-main">🎯 Main</span>
                                  )}
                                  {project.parent_project_id && (
                                    <span className="badge badge-sub">🔗 Sub</span>
                                  )}
                                  {project.content_type && (
                                    <span className="badge badge-content">
                                      {CONTENT_TYPES.find((ct) => ct.id === project.content_type)?.icon} {CONTENT_TYPES.find((ct) => ct.id === project.content_type)?.label}
                                    </span>
                                  )}
                                </div>
                              </div>
                              {project.description && (
                                <p className="project-preview-description">{project.description}</p>
                              )}
                              {project.parent_project_id && (
                                <p className="project-preview-meta">
                                  → Linked to: {mainProjects.find((p) => p.id === project.parent_project_id)?.name}
                                  {project.inherit_tone && ' (Inherits tone)'}
                                </p>
                              )}
                            </div>
                            <button
                              type="button"
                              className="btn-remove"
                              onClick={() => handleRemoveProject(project.id)}
                            >
                              ×
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Add Project Form */}
                    <div className="add-project-form">
                      <h4>Add a Project</h4>
                      <div className="form-grid">
                        <label className="form-label">
                          Project Name
                          <input
                            name="name"
                            value={currentProject.name}
                            onChange={handleProjectChange}
                            placeholder="Blog series, social media posts, etc."
                          />
                        </label>
                        <label className="form-label">
                          Description
                          <textarea
                            name="description"
                            value={currentProject.description}
                            onChange={handleProjectChange}
                            placeholder="Purpose and goals of this project"
                            rows={2}
                          />
                        </label>
                        <label className="form-label checkbox-label">
                          <input
                            type="checkbox"
                            name="is_main_project"
                            checked={currentProject.is_main_project}
                            onChange={handleProjectChange}
                          />
                          <span>🎯 This is a main project (source for sub-content)</span>
                        </label>
                        {!currentProject.is_main_project && mainProjects.length > 0 && (
                          <label className="form-label">
                            Link to Main Project (Optional)
                            <select
                              name="parent_project_id"
                              value={currentProject.parent_project_id || ''}
                              onChange={handleProjectChange}
                            >
                              <option value="">Standalone (no parent)</option>
                              {mainProjects.map((mainProj) => (
                                <option key={mainProj.id} value={mainProj.id}>
                                  {mainProj.name}
                                </option>
                              ))}
                            </select>
                          </label>
                        )}
                        {currentProject.parent_project_id && (
                          <label className="form-label checkbox-label">
                            <input
                              type="checkbox"
                              name="inherit_tone"
                              checked={currentProject.inherit_tone}
                              onChange={handleProjectChange}
                            />
                            <span>Inherit tone from main project</span>
                          </label>
                        )}
                        <label className="form-label">
                          Content Type
                          <select
                            name="content_type"
                            value={currentProject.content_type}
                            onChange={handleProjectChange}
                          >
                            <option value="">Select content type...</option>
                            {CONTENT_TYPES.map((type) => (
                              <option key={type.id} value={type.id}>
                                {type.icon} {type.label}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="form-label">
                          Language
                          <select
                            name="language"
                            value={currentProject.language}
                            onChange={handleProjectChange}
                          >
                            <option value="auto">Automatically detected</option>
                            <option value="en">English</option>
                            <option value="fr">French</option>
                            <option value="de">German</option>
                            <option value="es">Spanish</option>
                            <option value="it">Italian</option>
                          </select>
                        </label>
                      </div>
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={handleAddProject}
                        disabled={!currentProject.name.trim()}
                      >
                        Add Project
                      </button>
                    </div>
                  </div>
                </>
              ) : (
                <div className="form-section">
                  <h3>Review Campaign</h3>
                  <div className="review-details">
                    <div className="review-row">
                      <span className="review-label">Name:</span>
                      <span className="review-value">{campaign.name}</span>
                    </div>
                    {campaign.description && (
                      <div className="review-row">
                        <span className="review-label">Description:</span>
                        <span className="review-value">{campaign.description}</span>
                      </div>
                    )}
                    <div className="review-row">
                      <span className="review-label">Type:</span>
                      <span className="review-value">Standalone</span>
                    </div>
                    <div className="review-row">
                      <span className="review-label">Category:</span>
                      <span className="review-value">
                        {effectiveCategories.find((c) => String(c.id) === String(campaign.categoryId))?.name}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {error && <p className="error-text">{error}</p>}

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={handleBack}>
                  Back
                </button>
                <button type="submit" className="btn-primary" disabled={saving}>
                  {saving ? 'Creating...' : 'Create Campaign'}
                </button>
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  );
};

export default CampaignCreation;
