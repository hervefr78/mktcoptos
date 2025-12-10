import React, { useState, useEffect, useRef } from 'react';
import { NavLink } from 'react-router-dom';
import './Sidebar.css';

const SIDEBAR_WIDTH_KEY = 'sidebar-width';
const DEFAULT_WIDTH = 240;
const MIN_WIDTH = 200;
const MAX_WIDTH = 400;

const Sidebar = () => {
  const [sidebarWidth, setSidebarWidth] = useState(DEFAULT_WIDTH);
  const [isResizing, setIsResizing] = useState(false);
  const [user, setUser] = useState(null);
  const sidebarRef = useRef(null);

  // Navigation items with icons
  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: '📊' },
    { path: '/campaigns', label: 'Campaigns', icon: '🚀' },
    { path: '/projects', label: 'Projects', icon: '📁' },
    { path: '/categories', label: 'Categories', icon: '🏷️' },
    { path: '/images', label: 'Images Gallery', icon: '🖼️' },
    { path: '/rag', label: 'Knowledge Base', icon: '📚' },
    { path: '/debug', label: 'Debug Logs', icon: '🐛' },
    { path: '/settings', label: 'Settings', icon: '⚙️' },
    { path: '/settings/agent-prompts', label: 'Agent Prompts', icon: '🤖' },
    { path: '/settings/prompt-contexts', label: 'Prompt Contexts', icon: '💬' },
    { path: '/admin/users', label: 'User Management', icon: '👥' },
  ];

  // Load user info from localStorage
  useEffect(() => {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        setUser(JSON.parse(userStr));
      } catch (e) {
        console.error('Failed to parse user data:', e);
      }
    }
  }, []);

  // Load sidebar width from localStorage on mount
  useEffect(() => {
    const savedWidth = localStorage.getItem(SIDEBAR_WIDTH_KEY);
    if (savedWidth) {
      const width = parseInt(savedWidth, 10);
      if (width >= MIN_WIDTH && width <= MAX_WIDTH) {
        setSidebarWidth(width);
      }
    }
  }, []);

  // Save sidebar width to localStorage when it changes
  useEffect(() => {
    localStorage.setItem(SIDEBAR_WIDTH_KEY, sidebarWidth.toString());
  }, [sidebarWidth]);

  // Handle resize mouse down
  const handleMouseDown = (e) => {
    e.preventDefault();
    setIsResizing(true);
  };

  // Handle resize mouse move and mouse up
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;

      const newWidth = e.clientX;
      if (newWidth >= MIN_WIDTH && newWidth <= MAX_WIDTH) {
        setSidebarWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing]);

  const handleLogout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    window.location.href = '/login';
  };

  return (
    <aside
      ref={sidebarRef}
      style={{ width: `${sidebarWidth}px` }}
      className="enhanced-sidebar"
    >
      {/* Logo/Brand */}
      <div className="sidebar-header">
        <div className="sidebar-brand-text">
          <h1 className="brand-name">
            <span className="brand-exo">EXO</span>
            <span className="brand-marketing">marketing</span>
          </h1>
          <p className="brand-tagline">Smart Content Generator</p>
        </div>
        <div className="sidebar-app-logo">
          <img
            src="/marketingAssistant_app_logo.png"
            alt="Marketing Assistant"
            className="sidebar-app-logo-img"
          />
        </div>
        <p className="sidebar-powered-by">Powered by Fast Growth Advisors</p>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/settings'}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'active' : ''}`
            }
          >
            <span className="sidebar-link-icon">{item.icon}</span>
            <span className="sidebar-link-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User section */}
      <div className="sidebar-user">
        <div className="user-info">
          <div className="user-avatar">
            {user?.name?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div className="user-details">
            <p className="user-name">{user?.name || 'User'}</p>
            <p className="user-email">{user?.email || 'user@example.com'}</p>
          </div>
        </div>
        <button onClick={handleLogout} className="logout-btn">
          Sign Out
        </button>
      </div>

      {/* Resize handle */}
      <div
        onMouseDown={handleMouseDown}
        className={`resize-handle ${isResizing ? 'resizing' : ''}`}
      >
        <div className="resize-handle-hitbox" />
      </div>
    </aside>
  );
};

export default Sidebar;
