import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import CampaignModal from '../Campaigns/CampaignModal';
import { API_ENDPOINTS } from '../../config/api';
import { CONTENT_TYPES } from '../../constants/contentOptions';
import './ProjectsPage.css';

const ProjectsPage = () => {
  const [projects, setProjects] = useState([]);
  const [contentHistory, setContentHistory] = useState({});
  const [contentLoading, setContentLoading] = useState({});
  const [contentErrors, setContentErrors] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    campaign: 'all',
    status: 'all',
    contentType: 'all',
    audience: 'all',
    category: 'all',
  });
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newProject, setNewProject] = useState({ name: '', description: '', language: 'auto', campaignId: '' });
  const [campaigns, setCampaigns] = useState([]);
  const [campaignsLoading, setCampaignsLoading] = useState(false);
  const [campaignError, setCampaignError] = useState(null);
  const [showCampaignModal, setShowCampaignModal] = useState(false);
  const [campaignDraft, setCampaignDraft] = useState(null);
  const [selectedProject, setSelectedProject] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    fetchProjects();
    fetchCampaigns();
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const campaignIdFromQuery = params.get('campaignId');
    if (campaignIdFromQuery) {
      setShowCreateModal(true);
      setNewProject((prev) => ({ ...prev, campaignId: campaignIdFromQuery }));
    }
  }, [location.search]);

  const fetchCampaigns = async () => {
    setCampaignsLoading(true);
    try {
      const res = await fetch(API_ENDPOINTS.CAMPAIGNS, {
        credentials: 'include',
      });
      if (!res.ok) {
        throw new Error('Failed to fetch campaigns');
      }
      const data = await res.json();
      setCampaigns(data);
      setCampaignError(null);
      if (!newProject.campaignId && data.length > 0) {
        setNewProject((prev) => ({ ...prev, campaignId: data[0].id }));
      }
    } catch (err) {
      console.error('Failed to load campaigns', err);
      setCampaignError('Unable to load campaigns. Create one to continue.');
    } finally {
      setCampaignsLoading(false);
    }
  };

  const fetchProjects = async () => {
    try {
      // Single efficient call with recent content included
      const res = await fetch(`${API_ENDPOINTS.PROJECTS}?include_recent_content=true&content_limit=1`, {
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Failed to fetch projects');
      const data = await res.json();
      setProjects(data);

      // Map recent content from project response to contentHistory state
      const historyMap = {};
      const loadingState = {};

      data.forEach(project => {
        historyMap[project.id] = project.recent_executions || [];
        loadingState[project.id] = false; // Already loaded
      });

      setContentHistory(historyMap);
      setContentLoading(loadingState);

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchProjectContent = async (projectId) => {
    try {
      const res = await fetch(`${API_ENDPOINTS.PIPELINE_HISTORY}?project_id=${projectId}&limit=1`, {
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        setContentHistory(prev => ({
          ...prev,
          [projectId]: data.executions || []
        }));
        setContentErrors(prev => ({ ...prev, [projectId]: null }));
      } else {
        setContentErrors(prev => ({
          ...prev,
          [projectId]: `Failed to load content (${res.status})`
        }));
      }
    } catch (err) {
      console.error(`Failed to fetch content for project ${projectId}:`, err);
      setContentErrors(prev => ({
        ...prev,
        [projectId]: 'Failed to load content'
      }));
    } finally {
      setContentLoading(prev => ({ ...prev, [projectId]: false }));
    }
  };

  const handleCreateProject = async (e) => {
    e.preventDefault();
    if (!newProject.campaignId) {
      setCampaignError('Select a campaign to continue.');
      return;
    }
    try {
      const res = await fetch(API_ENDPOINTS.PROJECTS, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          name: newProject.name,
          description: newProject.description,
          language: newProject.language,
          campaign_id: Number(newProject.campaignId),
        }),
      });
      if (res.ok) {
        setShowCreateModal(false);
        setNewProject({ name: '', description: '', language: 'auto', campaignId: '' });
        fetchProjects();
      } else {
        setCampaignError('Unable to create project. Please ensure a campaign is selected.');
      }
    } catch (err) {
      console.error('Failed to create project:', err);
      setCampaignError('Unable to create project.');
    }
  };

  const handleSaveCampaign = async (values) => {
    const isEdit = Boolean(campaignDraft?.id);
    const endpoint = isEdit ? API_ENDPOINTS.CAMPAIGN(campaignDraft.id) : API_ENDPOINTS.CAMPAIGNS;
    const method = isEdit ? 'PUT' : 'POST';
    try {
      const res = await fetch(endpoint, {
        method,
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(values),
      });
      if (!res.ok) {
        throw new Error('Failed to save campaign');
      }
      const data = await res.json();
      setShowCampaignModal(false);
      setCampaignDraft(null);
      await fetchCampaigns();
      if (data?.id) {
        setNewProject((prev) => ({ ...prev, campaignId: data.id }));
      }
    } catch (err) {
      console.error('Unable to save campaign', err);
      setCampaignError('Unable to save campaign. Please try again.');
    }
  };

  const handleCreateContent = (project) => {
    // Navigate to Content Wizard with project context
    navigate(`/content/new?projectId=${project.id}&projectName=${encodeURIComponent(project.name)}`);
  };

  const handleViewContent = (pipelineId) => {
    // Navigate to content view with debug logs
    navigate(`/content/view/${pipelineId}`);
  };

  const handleEditContent = (pipelineId) => {
    // Navigate to Review & Edit step (step 4) in the content wizard
    navigate(`/content/new?resume=${pipelineId}&step=4`);
  };

  const handleResumeContent = (execution) => {
    // Navigate to wizard with existing execution to resume
    navigate(`/content/new?projectId=${execution.project_id}&resume=${execution.pipeline_id}`);
  };

  const handleDeleteProject = async (projectId, projectName) => {
    if (!window.confirm(`Are you sure you want to delete "${projectName}"? This will also delete all associated content.`)) {
      return;
    }

    try {
      const res = await fetch(`${API_ENDPOINTS.PROJECTS}/${projectId}`, {
        method: 'DELETE',
        credentials: 'include',
      });

      if (res.ok) {
        // Remove project from state
        setProjects(prev => prev.filter(p => p.id !== projectId));
        // Clear content history for this project
        setContentHistory(prev => {
          const updated = { ...prev };
          delete updated[projectId];
          return updated;
        });
      } else {
        alert('Failed to delete project');
      }
    } catch (err) {
      console.error('Failed to delete project:', err);
      alert('Failed to delete project');
    }
  };

  // Helper to determine if project has completed content
  const hasCompletedContent = (projectId) => {
    const history = contentHistory[projectId] || [];
    return history.some(exec => exec.status === 'completed');
  };

  const getLatestExecution = (projectId) => {
    const history = contentHistory[projectId] || [];
    return history[0];
  };

  // Helper to get the most recent completed content
  const getMostRecentCompletedContent = (projectId) => {
    const history = contentHistory[projectId] || [];
    return history.find(exec => exec.status === 'completed');
  };

  const getProjectStatus = (projectId) => {
    const recent = getLatestExecution(projectId);
    return recent?.status || 'pending';
  };

  const getProjectContentType = (projectId) => {
    const completed = getMostRecentCompletedContent(projectId);
    const latest = getLatestExecution(projectId);
    return completed?.content_type || latest?.content_type || null;
  };

  const getProjectAudience = (project) => {
    const completed = getMostRecentCompletedContent(project.id);
    const latest = getLatestExecution(project.id);
    return completed?.audience || latest?.audience || project.default_target_audience || null;
  };

  const getStatusBadge = (status) => {
    const statusStyles = {
      completed: { background: '#dcfce7', color: '#166534' },
      running: { background: '#dbeafe', color: '#1e40af' },
      failed: { background: '#fee2e2', color: '#991b1b' },
      pending: { background: '#f3f4f6', color: '#4b5563' }
    };
    return statusStyles[status] || statusStyles.pending;
  };

  const uniqueValues = {
    campaigns: campaigns.map((c) => ({ label: c.name, value: String(c.id) })),
    statuses: Array.from(new Set(projects.map((p) => getProjectStatus(p.id)))).filter(Boolean),
    contentTypes: Array.from(new Set(projects.map((p) => getProjectContentType(p.id)).filter(Boolean))),
    audiences: Array.from(new Set(projects.map((p) => getProjectAudience(p)).filter(Boolean))),
    categories: Array.from(new Set(projects.map((p) => p.category_name).filter(Boolean))),
  };

  const filteredProjects = projects.filter((project) => {
    const campaignMatch = filters.campaign === 'all' || String(project.campaign_id) === filters.campaign;
    const statusMatch = filters.status === 'all' || getProjectStatus(project.id) === filters.status;
    const contentTypeMatch = filters.contentType === 'all' || getProjectContentType(project.id) === filters.contentType;
    const audienceMatch = filters.audience === 'all' || getProjectAudience(project) === filters.audience;
    const categoryMatch = filters.category === 'all' || project.category_name === filters.category;
    return campaignMatch && statusMatch && contentTypeMatch && audienceMatch && categoryMatch;
  });

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  if (loading) {
    return (
      <div className="projects-page">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading projects...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="projects-page">
        <div className="error-container">
          <p>Error: {error}</p>
          <button onClick={fetchProjects} className="btn-primary">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="projects-page">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1>Projects</h1>
          <p className="page-subtitle">Manage your projects and create content</p>
        </div>
        <button onClick={() => setShowCreateModal(true)} className="btn-primary">
          + New Project
        </button>
      </div>

      {/* Filters */}
      <div className="filters-card">
        <div className="filter-group">
          <label>Campaign</label>
          <select
            value={filters.campaign}
            onChange={(e) => handleFilterChange('campaign', e.target.value)}
          >
            <option value="all">All campaigns</option>
            {uniqueValues.campaigns.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>
        <div className="filter-group">
          <label>Status</label>
          <select
            value={filters.status}
            onChange={(e) => handleFilterChange('status', e.target.value)}
          >
            <option value="all">All statuses</option>
            {uniqueValues.statuses.map((status) => (
              <option key={status} value={status}>{status}</option>
            ))}
          </select>
        </div>
        <div className="filter-group">
          <label>Content Type</label>
          <select
            value={filters.contentType}
            onChange={(e) => handleFilterChange('contentType', e.target.value)}
          >
            <option value="all">All types</option>
            {uniqueValues.contentTypes.map((contentType) => (
              <option key={contentType} value={contentType}>{contentType}</option>
            ))}
          </select>
        </div>
        <div className="filter-group">
          <label>Audience</label>
          <select
            value={filters.audience}
            onChange={(e) => handleFilterChange('audience', e.target.value)}
          >
            <option value="all">All audiences</option>
            {uniqueValues.audiences.map((audience) => (
              <option key={audience} value={audience}>{audience}</option>
            ))}
          </select>
        </div>
        <div className="filter-group">
          <label>Category</label>
          <select
            value={filters.category}
            onChange={(e) => handleFilterChange('category', e.target.value)}
          >
            <option value="all">All categories</option>
            {uniqueValues.categories.map((category) => (
              <option key={category} value={category}>{category}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Projects Grid */}
      {projects.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📁</div>
          <h3>No projects yet</h3>
          <p>Create your first project to start generating content</p>
          <button onClick={() => setShowCreateModal(true)} className="btn-primary">
            Create Project
          </button>
        </div>
      ) : filteredProjects.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🔍</div>
          <h3>No projects match these filters</h3>
          <p>Adjust your filters or create a new project to get started.</p>
          <button onClick={() => setShowCreateModal(true)} className="btn-primary">
            Create Project
          </button>
        </div>
      ) : (
        <div className="projects-grid">
          {filteredProjects.map((project) => (
            <div key={project.id} className="project-card">
              <div className="project-card-header">
                <div className="project-card-title">
                  <h3>{project.name}</h3>
                  <span className="project-date">
                    {new Date(project.created_at).toLocaleDateString()}
                  </span>
                </div>
                <button
                  onClick={() => handleDeleteProject(project.id, project.name)}
                  className="btn-icon btn-danger"
                  title="Delete project"
                >
                  🗑️
                </button>
              </div>

              {/* Relationship Badges */}
              {(project.is_main_project || project.parent_project_id) && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                  {project.is_main_project && (
                    <span
                      className="badge"
                      style={{
                        background: '#dbeafe',
                        color: '#1e40af',
                        padding: '4px 10px',
                        borderRadius: '12px',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                    >
                      🎯 Main Project
                    </span>
                  )}
                  {project.parent_project_id && project.parent_project_name && (
                    <span
                      className="badge"
                      style={{
                        background: '#fef3c7',
                        color: '#92400e',
                        padding: '4px 10px',
                        borderRadius: '12px',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                      title={`Linked to ${project.parent_project_name}`}
                    >
                      🔗 Sub-Project
                      {project.inherit_tone && (
                        <span style={{ fontSize: '0.7rem', opacity: 0.8 }}>(Inherits tone)</span>
                      )}
                    </span>
                  )}
                  {project.content_type && (
                    <span
                      className="badge"
                      style={{
                        background: '#f3f4f6',
                        color: '#374151',
                        padding: '4px 10px',
                        borderRadius: '12px',
                        fontSize: '0.75rem',
                        fontWeight: '500'
                      }}
                    >
                      {CONTENT_TYPES.find(ct => ct.id === project.content_type)?.icon || '📄'} {CONTENT_TYPES.find(ct => ct.id === project.content_type)?.label || project.content_type}
                    </span>
                  )}
                </div>
              )}

              <div className="project-description-container">
                <p className="project-description line-clamp-3">
                  {project.description || 'No description provided'}
                </p>
              </div>

              {/* Project Settings - Always render for alignment */}
              <div className="project-meta">
                {project.campaign_name && (
                  <span className="meta-item">
                    <strong>Campaign:</strong> {project.campaign_name}
                  </span>
                )}
                {project.category_name && (
                  <span className="meta-item">
                    <strong>Category:</strong> {project.category_name}
                  </span>
                )}
                {getMostRecentCompletedContent(project.id)?.model_used && (
                  <span className="meta-item">
                    <strong>Model:</strong> {getMostRecentCompletedContent(project.id).model_used}
                  </span>
                )}
                {project.default_tone && (
                  <span className="meta-item">
                    <strong>Tone:</strong> {project.default_tone}
                  </span>
                )}
                {(getMostRecentCompletedContent(project.id)?.audience || project.default_target_audience) && (
                  <span className="meta-item">
                    <strong>Audience:</strong> {getMostRecentCompletedContent(project.id)?.audience || project.default_target_audience}
                  </span>
                )}
                {!getMostRecentCompletedContent(project.id)?.model_used && !project.default_tone && !getMostRecentCompletedContent(project.id)?.audience && !project.default_target_audience && (
                  <span className="meta-item" style={{ color: '#9ca3af', fontStyle: 'italic' }}>
                    No metadata available
                  </span>
                )}
              </div>

              {/* Content History */}
              <div className="content-history">
                <h4>Recent Content</h4>
                {contentLoading[project.id] ? (
                  <div className="content-loading">
                    <div className="loading-spinner-small"></div>
                    <span>Loading content...</span>
                  </div>
                ) : contentErrors[project.id] ? (
                  <div className="content-error">
                    <span>{contentErrors[project.id]}</span>
                    <button
                      onClick={() => fetchProjectContent(project.id)}
                      className="btn-small btn-secondary"
                    >
                      Retry
                    </button>
                  </div>
                ) : contentHistory[project.id]?.length > 0 ? (
                  <div className="content-list">
                    {contentHistory[project.id].map((execution) => (
                      <div key={execution.pipeline_id} className="content-item">
                        <div className="content-item-info">
                          <span className="content-topic">{execution.topic}</span>
                          <span
                            className="status-badge"
                            style={getStatusBadge(execution.status)}
                          >
                            {execution.status}
                          </span>
                        </div>
                        <div className="content-item-meta">
                          <span>{execution.content_type}</span>
                          {execution.word_count && (
                            <span>{execution.word_count} words</span>
                          )}
                          <span className="content-date">
                            {new Date(execution.created_at).toLocaleString()}
                          </span>
                        </div>
                        <div className="content-item-actions">
                          {execution.status === 'completed' ? (
                            <button
                              onClick={() => handleViewContent(execution.pipeline_id)}
                              className="btn-small"
                              title="View content and debug logs"
                            >
                              Show content and log
                            </button>
                          ) : execution.status === 'failed' ? (
                            <button
                              onClick={() => handleResumeContent(execution)}
                              className="btn-small btn-secondary"
                            >
                              Retry
                            </button>
                          ) : null}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="no-content">No content created yet</p>
                )}
              </div>

              {/* Linked Sub-Projects Info */}
              {project.is_main_project && (
                (() => {
                  const subProjects = projects.filter(p => p.parent_project_id === project.id);
                  return subProjects.length > 0 ? (
                    <div style={{
                      marginTop: '12px',
                      padding: '10px 12px',
                      background: '#f9fafb',
                      borderRadius: '8px',
                      borderLeft: '3px solid #3b82f6'
                    }}>
                      <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#374151', marginBottom: '6px' }}>
                        🔗 Linked Sub-Projects ({subProjects.length})
                      </div>
                      {subProjects.map(sub => (
                        <div key={sub.id} style={{
                          fontSize: '0.75rem',
                          color: '#6b7280',
                          marginTop: '4px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}>
                          <span>→</span>
                          <span>{sub.name}</span>
                          {sub.content_type && (
                            <span style={{
                              background: '#e5e7eb',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontSize: '0.7rem'
                            }}>
                              {CONTENT_TYPES.find(ct => ct.id === sub.content_type)?.label || sub.content_type}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : null;
                })()
              )}

              {/* Parent Project Link */}
              {project.parent_project_id && project.parent_project_name && (
                <div style={{
                  marginTop: '12px',
                  padding: '10px 12px',
                  background: '#fffbeb',
                  borderRadius: '8px',
                  borderLeft: '3px solid #f59e0b',
                  fontSize: '0.75rem'
                }}>
                  <div style={{ fontWeight: '600', color: '#92400e', marginBottom: '4px' }}>
                    ↖️ Part of Main Project
                  </div>
                  <div style={{ color: '#78350f' }}>
                    {project.parent_project_name}
                    {project.inherit_tone && <span style={{ marginLeft: '8px', opacity: 0.8 }}>(Inherits tone & content)</span>}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="project-actions">
                {hasCompletedContent(project.id) ? (
                  <button
                    onClick={() => {
                      const content = getMostRecentCompletedContent(project.id);
                      if (content) {
                        handleEditContent(content.pipeline_id);
                      }
                    }}
                    className="btn-primary btn-full"
                    title="Edit content in Review & Edit page"
                  >
                    View Content
                  </button>
                ) : (
                  <button
                    onClick={() => handleCreateContent(project)}
                    className="btn-primary btn-full"
                  >
                    Create Content
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2>Create New Project</h2>
            <form onSubmit={handleCreateProject}>
              <div className="form-group">
                <label htmlFor="projectName">Project Name</label>
                <input
                  id="projectName"
                  type="text"
                  value={newProject.name}
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  placeholder="Enter project name"
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="projectCampaign">Campaign</label>
                <div className="campaign-select-row">
                  <select
                    id="projectCampaign"
                    value={newProject.campaignId}
                    onChange={(e) => setNewProject({ ...newProject, campaignId: e.target.value })}
                    disabled={campaignsLoading || campaigns.length === 0}
                  >
                    {campaignsLoading && <option value="">Loading campaigns...</option>}
                    {!campaignsLoading && campaigns.length === 0 && (
                      <option value="">Create a campaign first</option>
                    )}
                    {campaigns.map((campaign) => (
                      <option key={campaign.id} value={campaign.id}>
                        {campaign.name} ({campaign.project_count} projects)
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => {
                      setCampaignDraft(null);
                      setShowCampaignModal(true);
                    }}
                  >
                    + New Campaign
                  </button>
                </div>
                {campaignError && <p className="form-helper error-text">{campaignError}</p>}
              </div>
              <div className="form-group">
                <label htmlFor="projectDesc">Description</label>
                <textarea
                  id="projectDesc"
                  value={newProject.description}
                  onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                  placeholder="Brief description of this project"
                  rows={3}
                />
              </div>
              <div className="form-group">
                <label htmlFor="projectLanguage">Language</label>
                <select
                  id="projectLanguage"
                  value={newProject.language}
                  onChange={(e) => setNewProject({ ...newProject, language: e.target.value })}
                >
                  <option value="auto">Automatically Detected (Default)</option>
                  <option value="en">English</option>
                  <option value="fr">French</option>
                  <option value="de">German</option>
                  <option value="es">Spanish</option>
                  <option value="it">Italian</option>
                </select>
              </div>
              <div className="modal-actions">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Create Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {showCampaignModal && (
        <CampaignModal
          isOpen={showCampaignModal}
          onClose={() => {
            setShowCampaignModal(false);
            setCampaignDraft(null);
          }}
          onSave={handleSaveCampaign}
          initialData={campaignDraft || {}}
          modelOptions={[
            { label: 'gpt-4', value: 'gpt-4' },
            { label: 'gpt-3.5-turbo', value: 'gpt-3.5-turbo' },
            { label: 'claude', value: 'claude' },
          ]}
        />
      )}
    </div>
  );
};

export default ProjectsPage;
