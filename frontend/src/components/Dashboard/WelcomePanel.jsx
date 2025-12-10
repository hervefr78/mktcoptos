import React from 'react';

const WelcomePanel = ({ headline, subtitle }) => {
  return (
    <div className="welcome-panel">
      <h1>{headline}</h1>
      {subtitle && <p>{subtitle}</p>}
    </div>
  );
};

export default WelcomePanel;
