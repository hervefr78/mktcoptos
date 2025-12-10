import React from 'react';

const QuickActions = ({ onNewProject, onNewCampaign, onNewActivity }) => {
  return (
    <div className="quick-actions">
      <button onClick={onNewProject}>New Project</button>
      <button onClick={onNewCampaign}>New Marketing Campaign</button>
      <button onClick={onNewActivity}>New Marketing Activity</button>
    </div>
  );
};

export default QuickActions;
