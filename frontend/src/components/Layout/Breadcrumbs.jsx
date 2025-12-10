import React from 'react';
import { useLocation } from 'react-router-dom';

const Breadcrumbs = () => {
  const location = useLocation();
  const pathnames = location.pathname.split('/').filter(Boolean);

  return (
    <nav aria-label="Breadcrumb" className="breadcrumbs" style={{ display: 'flex', flexWrap: 'wrap' }}>
      <ol style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexWrap: 'wrap' }}>
        <li style={{ marginRight: '8px' }}>
          <a href="/">Home</a>
        </li>
        {pathnames.map((name, index) => {
          const routeTo = '/' + pathnames.slice(0, index + 1).join('/');
          const isLast = index === pathnames.length - 1;
          return (
            <li key={routeTo} style={{ marginRight: '8px' }} aria-current={isLast ? 'page' : undefined}>
              {isLast ? (
                <span>{decodeURIComponent(name)}</span>
              ) : (
                <a href={routeTo}>{decodeURIComponent(name)}</a>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};

export default Breadcrumbs;
