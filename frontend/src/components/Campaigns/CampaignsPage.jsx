import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import CampaignModal from './CampaignModal';
import { API_ENDPOINTS } from '../../config/api';
import './CampaignsPage.css';

const CampaignsPage = () => {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadCampaigns();
  }, []);

  const loadCampaigns = async () => {
    setLoading(true);
    try {
      const res = await fetch(API_ENDPOINTS.CAMPAIGNS);
      if (!res.ok) {
        throw new Error('Unable to fetch campaigns');
      }
      const data = await res.json();
      setCampaigns(data);
      setError(null);
    } catch (err) {
      console.error('Failed to load campaigns', err);
      setError('Unable to load campaigns. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveCampaign = async (values) => {
    const isEdit = Boolean(editingCampaign?.id);
    const endpoint = isEdit ? API_ENDPOINTS.CAMPAIGN(editingCampaign.id) : API_ENDPOINTS.CAMPAIGNS;
    const method = isEdit ? 'PUT' : 'POST';

    try {
      const res = await fetch(endpoint, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      if (!res.ok) {
        throw new Error('Failed to save campaign');
      }
      await loadCampaigns();
      setModalOpen(false);
      setEditingCampaign(null);
    } catch (err) {
      console.error('Unable to save campaign', err);
      setError('Unable to save campaign. Please try again.');
    }
  };

  const openCreateModal = () => {
    navigate('/campaigns/new');
  };

  const openEditModal = (campaign) => {
    setEditingCampaign(campaign);
    setModalOpen(true);
  };

  const handleDeleteCampaign = async (campaignId, campaignName) => {
    if (!window.confirm(`Are you sure you want to delete "${campaignName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      const res = await fetch(API_ENDPOINTS.CAMPAIGN(campaignId), {
        method: 'DELETE',
        credentials: 'include',
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to delete campaign');
      }
      await loadCampaigns();
    } catch (err) {
      console.error('Unable to delete campaign', err);
      setError(err.message || 'Unable to delete campaign. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="campaigns-page">
        <div className="loading-container">
          <div className="loading-spinner" />
          <p>Loading campaigns...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="campaigns-page">
        <div className="error-container">
          <p>{error}</p>
          <button className="btn-primary" onClick={loadCampaigns}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="campaigns-page">
      <div className="page-header">
        <div>
          <h1>Campaigns</h1>
          <p className="page-subtitle">Group projects under campaigns and track their outputs</p>
        </div>
        <button className="btn-primary" onClick={openCreateModal}>
          + New Campaign
        </button>
      </div>

      {campaigns.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🚀</div>
          <h3>No campaigns yet</h3>
          <p>Create your first campaign to start grouping projects</p>
          <button className="btn-primary" onClick={openCreateModal}>
            Create Campaign
          </button>
        </div>
      ) : (
        <div className="campaigns-grid">
          {campaigns.map((campaign) => (
            <div key={campaign.id} className="campaign-card">
              <div className="campaign-card__header">
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h3>{campaign.name}</h3>
                    {campaign.campaign_type === 'integrated' && <span className="pill" style={{ background: '#dbeafe', color: '#1e40af' }}>🔗 Integrated</span>}
                    {campaign.campaign_type === 'standalone' && <span className="pill" style={{ background: '#f3f4f6', color: '#4b5563' }}>📄 Standalone</span>}
                  </div>
                  <p className="campaign-meta">
                    {campaign.category ? <span>Category: {campaign.category}</span> : <span>No category</span>}
                    {campaign.model && <span className="pill">Model: {campaign.model}</span>}
                  </p>
                </div>
                <div className="campaign-card__actions">
                  <button className="btn-icon" onClick={() => openEditModal(campaign)} title="Edit campaign">
                    ✏️
                  </button>
                  <button
                    className="btn-icon btn-icon-danger"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteCampaign(campaign.id, campaign.name);
                    }}
                    title="Delete campaign"
                  >
                    🗑️
                  </button>
                </div>
              </div>
              <p className="campaign-description">{campaign.description || 'No description provided.'}</p>

              {campaign.campaign_type === 'integrated' && campaign.projects && campaign.projects.length > 0 && (
                <div style={{ marginTop: '12px', padding: '12px', background: '#f9fafb', borderRadius: '8px', fontSize: '0.875rem' }}>
                  <div style={{ fontWeight: '600', marginBottom: '8px', color: '#374151' }}>
                    Campaign Structure:
                  </div>
                  {campaign.projects.filter(p => !p.parent_project_id).map(mainProject => (
                    <div key={mainProject.id} style={{ marginBottom: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {mainProject.is_main_project && <span>🎯</span>}
                        <span style={{ fontWeight: '500' }}>{mainProject.name}</span>
                        {mainProject.content_type && <span className="pill" style={{ fontSize: '0.75rem' }}>{mainProject.content_type}</span>}
                      </div>
                      {mainProject.sub_projects && mainProject.sub_projects.length > 0 && (
                        <div style={{ marginLeft: '24px', marginTop: '4px' }}>
                          {mainProject.sub_projects.map(sub => (
                            <div key={sub.id} style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#6b7280', marginTop: '4px' }}>
                              <span>└─►</span>
                              <span>{sub.name}</span>
                              {sub.content_type && <span className="pill" style={{ fontSize: '0.7rem' }}>{sub.content_type}</span>}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <div className="campaign-stats">
                <span className="pill">{campaign.project_count} projects</span>
                {campaign.campaign_type === 'integrated' && campaign.main_project_count > 0 && (
                  <span className="pill">{campaign.main_project_count} main</span>
                )}
                <span className="pill">Created {new Date(campaign.created_at).toLocaleDateString()}</span>
              </div>
              <div className="campaign-card__footer">
                <button className="btn-secondary" onClick={() => navigate(`/campaigns/${campaign.id}`)}>
                  View Details
                </button>
                <button
                  className="btn-primary"
                  onClick={() => navigate(`/projects?campaignId=${campaign.id}`)}
                >
                  Create Project
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {modalOpen && (
        <CampaignModal
          isOpen={modalOpen}
          onClose={() => {
            setModalOpen(false);
            setEditingCampaign(null);
          }}
          onSave={handleSaveCampaign}
          initialData={editingCampaign || {}}
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

export default CampaignsPage;
