import React, { useState } from 'react';
import ShareDialog from './ShareDialog';

/**
 * HierarchyTree displays a nested tree of Projects -> Campaigns -> Activities.
 * Each node can be expanded/collapsed and includes a checkbox for batch
 * selection.  A "Share" action exposes a dialog for granting permissions.
 */
const HierarchyTree = ({ data = [], onShare }) => {
  const [expanded, setExpanded] = useState({});
  const [selected, setSelected] = useState({});
  const [shareTarget, setShareTarget] = useState(null);

  const toggleExpand = (id) => {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const markTree = (node, value, map) => {
    map[node.id] = value;
    if (node.campaigns) {
      node.campaigns.forEach((c) => markTree(c, value, map));
    }
    if (node.activities) {
      node.activities.forEach((a) => markTree(a, value, map));
    }
  };

  const toggleSelect = (node) => {
    setSelected((prev) => {
      const next = { ...prev };
      const newValue = !next[node.id];
      markTree(node, newValue, next);
      return next;
    });
  };

  const handleShare = (permissions) => {
    if (onShare) {
      onShare(shareTarget, permissions);
    }
    setShareTarget(null);
  };

  const renderActivities = (activities) =>
    activities.map((act) => (
      <div key={act.id} className="tree-node activity">
        <input
          type="checkbox"
          checked={!!selected[act.id]}
          onChange={() => toggleSelect(act)}
        />
        <span>{act.name}</span>
        <button type="button" onClick={() => setShareTarget(act)}>
          Share
        </button>
      </div>
    ));

  const renderCampaigns = (campaigns) =>
    campaigns.map((camp) => (
      <div key={camp.id} className="tree-node campaign">
        <div className="tree-node-header">
          {camp.activities && camp.activities.length > 0 && (
            <button
              type="button"
              className="toggle"
              onClick={() => toggleExpand(camp.id)}
            >
              {expanded[camp.id] ? '-' : '+'}
            </button>
          )}
          <input
            type="checkbox"
            checked={!!selected[camp.id]}
            onChange={() => toggleSelect(camp)}
          />
          <span>{camp.name}</span>
          <button type="button" onClick={() => setShareTarget(camp)}>
            Share
          </button>
        </div>
        {expanded[camp.id] && camp.activities && (
          <div className="tree-children">
            {renderActivities(camp.activities)}
          </div>
        )}
      </div>
    ));

  const renderProjects = () =>
    data.map((proj) => (
      <div key={proj.id} className="tree-node project">
        <div className="tree-node-header">
          {proj.campaigns && proj.campaigns.length > 0 && (
            <button
              type="button"
              className="toggle"
              onClick={() => toggleExpand(proj.id)}
            >
              {expanded[proj.id] ? '-' : '+'}
            </button>
          )}
          <input
            type="checkbox"
            checked={!!selected[proj.id]}
            onChange={() => toggleSelect(proj)}
          />
          <span>{proj.name}</span>
          <button type="button" onClick={() => setShareTarget(proj)}>
            Share
          </button>
        </div>
        {expanded[proj.id] && proj.campaigns && (
          <div className="tree-children">
            {renderCampaigns(proj.campaigns)}
          </div>
        )}
      </div>
    ));

  return (
    <div className="hierarchy-tree">
      {renderProjects()}
      {shareTarget && (
        <ShareDialog
          isOpen={!!shareTarget}
          targetName={shareTarget.name}
          onClose={() => setShareTarget(null)}
          onShare={handleShare}
        />
      )}
    </div>
  );
};

export default HierarchyTree;
