import React, { useState } from 'react';
import IntegrationSettings from './IntegrationSettings';
import UserPreferences from './UserPreferences';
import ServicesStatus from './ServicesStatus';
import InfrastructureDashboard from './InfrastructureDashboard';

const tabs = [
  { id: 'status', label: 'Services Status', component: <ServicesStatus /> },
  { id: 'integrations', label: 'Integrations', component: <IntegrationSettings /> },
  { id: 'preferences', label: 'Preferences', component: <UserPreferences /> },
  { id: 'infrastructure', label: 'Infrastructure', component: <InfrastructureDashboard /> },
];

export default function SettingsPage() {
  const [active, setActive] = useState('status');

  return (
    <div className="settings-page">
      <h2>Settings</h2>
      <div className="settings-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={active === tab.id ? 'active' : ''}
            onClick={() => setActive(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="settings-content">
        {tabs.find((t) => t.id === active)?.component}
      </div>
    </div>
  );
}

