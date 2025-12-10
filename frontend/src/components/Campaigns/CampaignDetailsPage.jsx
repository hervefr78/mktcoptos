import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import CampaignModal from './CampaignModal';
import { API_ENDPOINTS } from '../../config/api';
import { CONTENT_TYPES } from '../../constants/contentOptions';
import './CampaignsPage.css';

const CampaignDetailsPage = () => {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const [campaign, setCampaign] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCampaignModal, setShowCampaignModal] = useState(false);
  const [newProject, setNewProject] = useState({
    name: '',
    description: '',
    language: 'auto',
    is_main_project: false,
    parent_project_id: null,
    content_type: '',
    inherit_tone: true
  });
  const [projectError, setProjectError] = useState(null);

  const loadCampaign = async () => {
    setLoading(true);
    try {
      const res = await fetch(API_ENDPOINTS.CAMPAIGN(campaignId), {
        credentials: 'include',
      });
      if (!res.ok) {
        throw new Error('Unable to load campaign');
      }
      const data = await res.json();
      setCampaign(data);
      setError(null);
    } catch (err) {
      console.error('Failed to load campaign', err);
      setError('Unable to load campaign');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCampaign();
  }, [campaignId]);

  const handleSaveCampaign = async (values) => {
    try {
      const res = await fetch(API_ENDPOINTS.CAMPAIGN(campaignId), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(values),
      });
      if (!res.ok) {
        throw new Error('Failed to update campaign');
      }
      await loadCampaign();
      setShowCampaignModal(false);
    } catch (err) {
      console.error('Unable to update campaign', err);
      setError('Unable to update campaign');
    }
  };

  const handleCreateProject = async (e) => {
    e.preventDefault();
    setProjectError(null);
    try {
      const payload = {
        name: newProject.name,
        description: newProject.description,
        language: newProject.language,
        campaign_id: Number(campaignId),
      };

      // Add integrated campaign fields
      if (campaign.campaign_type === 'integrated') {
        payload.is_main_project = newProject.is_main_project;
        if (newProject.content_type) {
          payload.content_type = newProject.content_type;
        }
        if (!newProject.is_main_project && newProject.parent_project_id) {
          payload.parent_project_id = Number(newProject.parent_project_id);
          payload.inherit_tone = newProject.inherit_tone;
        }
      }

      const res = await fetch(API_ENDPOINTS.PROJECTS, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        throw new Error('Failed to create project');
      }
      setNewProject({
        name: '',
        description: '',
        language: 'auto',
        is_main_project: false,
        parent_project_id: null,
        content_type: '',
        inherit_tone: true
      });
      await loadCampaign();
    } catch (err) {
      console.error('Unable to create project', err);
      setProjectError('Unable to create project. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="campaigns-page">
        <div className="loading-container">
          <div className="loading-spinner" />
          <p>Loading campaign...</p>
        </div>
      </div>
    );
  }

  if (error || !campaign) {
    return (
      <div className="campaigns-page">
        <div className="error-container">
          <p>{error || 'Campaign not found'}</p>
          <button className="btn-secondary" onClick={() => navigate('/campaigns')}>
            Back to campaigns
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="campaigns-page">
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
            <h1>{campaign.name}</h1>
            {campaign.campaign_type === 'integrated' && (
              <span className="pill" style={{ background: '#dbeafe', color: '#1e40af', fontSize: '0.875rem' }}>
                🔗 Integrated Campaign
              </span>
            )}
            {campaign.campaign_type === 'standalone' && (
              <span className="pill" style={{ background: '#f3f4f6', color: '#4b5563', fontSize: '0.875rem' }}>
                📄 Standalone
              </span>
            )}
          </div>
          <p className="page-subtitle">{campaign.description || 'No description provided.'}</p>
          <div className="campaign-meta" style={{ marginTop: 8 }}>
            {campaign.category && <span className="pill">Category: {campaign.category}</span>}
            {campaign.model && <span className="pill">Model: {campaign.model}</span>}
            <span className="pill">{campaign.project_count} projects</span>
            {campaign.campaign_type === 'integrated' && campaign.main_project_count > 0 && (
              <span className="pill">{campaign.main_project_count} main</span>
            )}
          </div>
        </div>
        <div className="campaign-card__actions">
          <button className="btn-secondary" onClick={() => setShowCampaignModal(true)}>
            Edit Campaign
          </button>
          <button className="btn-primary" onClick={() => navigate('/campaigns')}>
            All Campaigns
          </button>
        </div>
      </div>

      <div className="campaign-details-grid">
        <div className="campaign-panel">
          <h3>Campaign Structure</h3>
          {campaign.projects.length === 0 ? (
            <p className="muted">No projects yet. Create one below.</p>
          ) : campaign.campaign_type === 'integrated' ? (
            /* Integrated Campaign - Show Hierarchy */
            <div className="projects-hierarchy">
              {/* Main Projects Section */}
              {campaign.projects.filter(p => !p.parent_project_id && p.is_main_project).length > 0 && (
                <div style={{ marginBottom: '24px' }}>
                  <h4 style={{ fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '12px' }}>
                    🎯 Main Projects
                  </h4>
                  {campaign.projects.filter(p => !p.parent_project_id && p.is_main_project).map((mainProject) => (
                    <div key={mainProject.id} style={{ marginBottom: '16px', padding: '12px', background: '#f9fafb', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                            <p className="project-title" style={{ marginBottom: 0 }}>{mainProject.name}</p>
                            {mainProject.content_type && (
                              <span style={{ background: '#e5e7eb', padding: '2px 8px', borderRadius: '12px', fontSize: '0.7rem', color: '#374151' }}>
                                {CONTENT_TYPES.find(ct => ct.id === mainProject.content_type)?.icon || '📄'} {CONTENT_TYPES.find(ct => ct.id === mainProject.content_type)?.label || mainProject.content_type}
                              </span>
                            )}
                          </div>
                          <p className="project-meta">Created {new Date(mainProject.created_at).toLocaleDateString()}</p>
                        </div>
                        <button
                          className="btn-small btn-secondary"
                          onClick={() => navigate(`/content/new?projectId=${mainProject.id}&projectName=${encodeURIComponent(mainProject.name)}`)}
                        >
                          Create Content
                        </button>
                      </div>

                      {/* Sub-Projects */}
                      {mainProject.sub_projects && mainProject.sub_projects.length > 0 && (
                        <div style={{ marginTop: '12px', marginLeft: '16px', paddingLeft: '12px', borderLeft: '2px solid #d1d5db' }}>
                          <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#6b7280', marginBottom: '8px' }}>
                            Linked Sub-Projects ({mainProject.sub_projects.length})
                          </div>
                          {mainProject.sub_projects.map((sub) => (
                            <div key={sub.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px', background: '#ffffff', borderRadius: '6px', marginBottom: '6px' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span style={{ color: '#9ca3af' }}>└─►</span>
                                <span style={{ fontSize: '0.875rem' }}>{sub.name}</span>
                                {sub.content_type && (
                                  <span style={{ background: '#f3f4f6', padding: '2px 6px', borderRadius: '8px', fontSize: '0.7rem', color: '#6b7280' }}>
                                    {CONTENT_TYPES.find(ct => ct.id === sub.content_type)?.label || sub.content_type}
                                  </span>
                                )}
                                {sub.inherit_tone && (
                                  <span style={{ fontSize: '0.7rem', color: '#9ca3af' }}>(Inherits tone)</span>
                                )}
                              </div>
                              <button
                                className="btn-small btn-secondary"
                                onClick={() => navigate(`/content/new?projectId=${sub.id}&projectName=${encodeURIComponent(sub.name)}`)}
                                style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                              >
                                Create Content
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Standalone Projects in Campaign */}
              {campaign.projects.filter(p => !p.parent_project_id && !p.is_main_project).length > 0 && (
                <div>
                  <h4 style={{ fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '12px' }}>
                    📄 Standalone Projects
                  </h4>
                  {campaign.projects.filter(p => !p.parent_project_id && !p.is_main_project).map((project) => (
                    <div key={project.id} style={{ marginBottom: '12px', padding: '12px', background: '#ffffff', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <p className="project-title" style={{ marginBottom: '4px' }}>{project.name}</p>
                          <p className="project-meta">Created {new Date(project.created_at).toLocaleDateString()}</p>
                        </div>
                        <button
                          className="btn-small btn-secondary"
                          onClick={() => navigate(`/content/new?projectId=${project.id}&projectName=${encodeURIComponent(project.name)}`)}
                        >
                          Create Content
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            /* Standalone Campaign - Simple List */
            <div className="projects-list">
              {campaign.projects.map((project) => (
                <div key={project.id} className="project-row">
                  <div>
                    <p className="project-title">{project.name}</p>
                    <p className="project-meta">Created {new Date(project.created_at).toLocaleString()}</p>
                    {project.language && <p className="project-meta">Language: {project.language}</p>}
                  </div>
                  <div className="project-row__actions">
                    <button
                      className="btn-secondary"
                      onClick={() => navigate(`/content/new?projectId=${project.id}&projectName=${encodeURIComponent(project.name)}`)}
                    >
                      Create Content
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="campaign-panel">
          <h3>Add Project to Campaign</h3>
          <form className="stacked-form" onSubmit={handleCreateProject}>
            {/* Project Type Selection */}
            {campaign.campaign_type === 'integrated' && (
              <div style={{ marginBottom: '24px' }}>
                <label className="modal__label" style={{ marginBottom: '12px' }}>Project Type</label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div
                    onClick={() => setNewProject((prev) => ({ ...prev, is_main_project: true, parent_project_id: null }))}
                    style={{
                      padding: '16px',
                      border: `2px solid ${newProject.is_main_project ? '#3b82f6' : '#e5e7eb'}`,
                      borderRadius: '8px',
                      cursor: 'pointer',
                      background: newProject.is_main_project ? '#eff6ff' : '#ffffff',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    <div style={{ fontSize: '2rem', marginBottom: '8px' }}>🎯</div>
                    <div style={{ fontWeight: '600', color: '#111827', marginBottom: '4px' }}>Main Project</div>
                    <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>Source content for sub-projects</div>
                  </div>
                  <div
                    onClick={() => setNewProject((prev) => ({ ...prev, is_main_project: false }))}
                    style={{
                      padding: '16px',
                      border: `2px solid ${!newProject.is_main_project ? '#3b82f6' : '#e5e7eb'}`,
                      borderRadius: '8px',
                      cursor: 'pointer',
                      background: !newProject.is_main_project ? '#eff6ff' : '#ffffff',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    <div style={{ fontSize: '2rem', marginBottom: '8px' }}>🔗</div>
                    <div style={{ fontWeight: '600', color: '#111827', marginBottom: '4px' }}>Sub-Project</div>
                    <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>Linked to a main project</div>
                  </div>
                </div>
              </div>
            )}

            {/* Content Type Selection - Visual Cards */}
            {campaign.campaign_type === 'integrated' && (
              <div style={{ marginBottom: '24px' }}>
                <label className="modal__label" style={{ marginBottom: '12px' }}>
                  Content Type {!newProject.is_main_project && <span style={{ color: '#6b7280', fontWeight: '400' }}>(optional)</span>}
                </label>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
                  gap: '12px'
                }}>
                  {CONTENT_TYPES.map((type) => (
                    <div
                      key={type.id}
                      onClick={() => setNewProject((prev) => ({ ...prev, content_type: type.id }))}
                      style={{
                        padding: '16px 12px',
                        border: `2px solid ${newProject.content_type === type.id ? '#3b82f6' : '#e5e7eb'}`,
                        borderRadius: '8px',
                        cursor: 'pointer',
                        background: newProject.content_type === type.id ? '#eff6ff' : '#ffffff',
                        transition: 'all 0.2s ease',
                        textAlign: 'center',
                        position: 'relative'
                      }}
                      onMouseEnter={(e) => {
                        if (newProject.content_type !== type.id) {
                          e.currentTarget.style.borderColor = '#d1d5db';
                          e.currentTarget.style.background = '#f9fafb';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (newProject.content_type !== type.id) {
                          e.currentTarget.style.borderColor = '#e5e7eb';
                          e.currentTarget.style.background = '#ffffff';
                        }
                      }}
                    >
                      <div style={{ fontSize: '2rem', marginBottom: '8px' }}>{type.icon}</div>
                      <div style={{ fontSize: '0.8rem', fontWeight: '500', color: '#374151', lineHeight: '1.2' }}>
                        {type.label}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Link to Main Project */}
            {campaign.campaign_type === 'integrated' && !newProject.is_main_project && (
              <label className="modal__label">
                Link to Main Project (Optional)
                <select
                  value={newProject.parent_project_id || ''}
                  onChange={(e) => setNewProject((prev) => ({ ...prev, parent_project_id: e.target.value || null }))}
                >
                  <option value="">Standalone (no parent)</option>
                  {campaign.projects.filter(p => p.is_main_project && !p.parent_project_id).map((mainProj) => (
                    <option key={mainProj.id} value={mainProj.id}>
                      {mainProj.name}
                    </option>
                  ))}
                </select>
                {newProject.parent_project_id && (
                  <>
                    <p className="modal__helper" style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '8px' }}>
                      ✓ This project will use the main project's content as source material
                    </p>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '12px', fontSize: '0.875rem' }}>
                      <input
                        type="checkbox"
                        checked={newProject.inherit_tone}
                        onChange={(e) => setNewProject((prev) => ({ ...prev, inherit_tone: e.target.checked }))}
                      />
                      <span>Inherit tone from main project</span>
                    </label>
                  </>
                )}
              </label>
            )}

            <label className="modal__label">
              Name
              <input
                type="text"
                value={newProject.name}
                onChange={(e) => setNewProject((prev) => ({ ...prev, name: e.target.value }))}
                placeholder="My project name"
                required
              />
            </label>

            <label className="modal__label">
              Description
              <textarea
                rows={3}
                value={newProject.description}
                onChange={(e) => setNewProject((prev) => ({ ...prev, description: e.target.value }))}
                placeholder="Brief description of this project..."
              />
            </label>

            <label className="modal__label">
              Language
              <select
                value={newProject.language}
                onChange={(e) => setNewProject((prev) => ({ ...prev, language: e.target.value }))}
              >
                <option value="auto">Auto-detect</option>
                <option value="en">English</option>
                <option value="fr">French</option>
                <option value="de">German</option>
                <option value="es">Spanish</option>
                <option value="it">Italian</option>
              </select>
            </label>

            {projectError && <p className="error-text">{projectError}</p>}

            <div className="modal__footer">
              <button
                type="button"
                className="modal__secondary"
                onClick={() => setNewProject({
                  name: '',
                  description: '',
                  language: 'auto',
                  is_main_project: false,
                  parent_project_id: null,
                  content_type: '',
                  inherit_tone: true
                })}
              >
                Clear Form
              </button>
              <button type="submit" className="modal__primary">
                Create Project
              </button>
            </div>
          </form>
        </div>
      </div>

      {showCampaignModal && (
        <CampaignModal
          isOpen={showCampaignModal}
          onClose={() => setShowCampaignModal(false)}
          onSave={handleSaveCampaign}
          initialData={campaign}
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

export default CampaignDetailsPage;
