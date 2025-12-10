import React from 'react';
import PropTypes from 'prop-types';

const statusLabels = {
  draft: 'Draft',
  active: 'Active',
  paused: 'Paused',
  completed: 'Completed',
};

const statusTone = {
  draft: 'muted',
  active: 'positive',
  paused: 'warning',
  completed: 'success',
};

const formatDate = (dateString) => {
  if (!dateString) return '—';
  const date = new Date(dateString);
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
};

const CampaignRow = ({ campaign, onEdit, onDelete }) => {
  const statusKey = campaign.status?.toLowerCase();
  const statusClass = statusTone[statusKey] || 'muted';

  return (
    <div className="campaign-row-item">
      <div>
        <p className="item-title">{campaign.title}</p>
        <div className="chip-row">
          <span className="chip pill">{campaign.category || 'Uncategorized'}</span>
          <span className={`chip pill status ${statusClass}`}>
            {statusLabels[statusKey] || campaign.status || 'Unknown'}
          </span>
          <span className="chip pill subtle">{campaign.model_used || 'Unspecified model'}</span>
        </div>
      </div>
      <div className="campaign-row-meta">
        <div>
          <p className="meta-label">Created</p>
          <p className="muted">{formatDate(campaign.created_at)}</p>
        </div>
        <div>
          <p className="meta-label">Updated</p>
          <p className="muted">{formatDate(campaign.updated_at)}</p>
        </div>
        <div className="campaign-actions">
          <button type="button" className="ghost" onClick={() => onEdit(campaign)}>Edit</button>
          <button
            type="button"
            className="danger"
            onClick={() => onDelete(campaign)}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
};

CampaignRow.propTypes = {
  campaign: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    title: PropTypes.string,
    category: PropTypes.string,
    status: PropTypes.string,
    model_used: PropTypes.string,
    created_at: PropTypes.string,
    updated_at: PropTypes.string,
  }).isRequired,
  onEdit: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
};

export default CampaignRow;
