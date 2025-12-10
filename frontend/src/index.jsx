import React from 'react';
import ReactDOM from 'react-dom/client';
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom';
import { ConversationProvider } from './state/ConversationContext';
import ErrorBoundary from './components/ErrorBoundary';
import Layout from './components/Layout';
import RequireAuth from './components/RequireAuth';
import DashboardPage from './components/Dashboard/DashboardPage';
import CampaignsPageComponent from './components/Campaigns/CampaignsPage';
import CampaignCreation from './components/Campaigns/CampaignCreation';
import CampaignDetailsPage from './components/Campaigns/CampaignDetailsPage';
import ProjectsPage from './components/Projects/ProjectsPage';
import NewActivityPage from './components/Activities/NewActivityPage';
import ContentWizard from './components/ContentWizard/ContentWizard';
import ViewContent from './components/ContentWizard/ViewContent';
import ImagesPage from './components/Images/ImagesPage';
import CategoriesPage from './components/Categories/CategoriesPage';
import AdminPage from './components/AdminPage';
import RequireRole from './components/RequireRole';
import SettingsPage from './components/Settings/SettingsPage';
import PromptContextsPage from './components/Settings/PromptContextsPage';
import AgentPromptsPage from './components/Settings/AgentPromptsPage';
import RagPage from './components/Rag/RagPage';
import DebugLogs from './pages/DebugLogs';
import NotFoundPage from './components/NotFoundPage';
import CampaignsPage from './components/Campaigns/CampaignsPage';
import theme, { applyTheme } from './theme';
import './styles.css';
import './utils/auth';

applyTheme(theme);

const router = createBrowserRouter(
  [
    { path: '/', element: <Navigate to="/dashboard" replace /> },
    {
      element: (
        <RequireAuth>
          <Layout />
        </RequireAuth>
      ),
      children: [
        { path: '/dashboard', element: <DashboardPage /> },
        { path: '/campaigns', element: <CampaignsPageComponent /> },
        { path: '/campaigns/new', element: <CampaignCreation /> },
        { path: '/campaigns/:campaignId', element: <CampaignDetailsPage /> },
        { path: '/projects', element: <ProjectsPage /> },
        { path: '/activities/new', element: <NewActivityPage /> },
        { path: '/content/new', element: <ContentWizard /> },
        { path: '/content/view/:pipelineId', element: <ViewContent /> },
        { path: '/images', element: <ImagesPage /> },
        { path: '/categories', element: <CategoriesPage /> },
        {
          path: '/admin/users',
          element: (
            <RequireRole role="Admin">
              <AdminPage />
            </RequireRole>
          ),
        },
        { path: '/settings', element: <SettingsPage /> },
        { path: '/settings/prompt-contexts', element: <PromptContextsPage /> },
        { path: '/settings/agent-prompts', element: <AgentPromptsPage /> },
        { path: '/rag', element: <RagPage /> },
        { path: '/campaigns', element: <CampaignsPage /> },
        { path: '/debug', element: <DebugLogs /> },
      ],
    },
    { path: '*', element: <NotFoundPage /> },
  ],
  { future: { v7_relativeSplatPath: true } }
);

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <ErrorBoundary>
    <ConversationProvider>
      <RouterProvider router={router} />
    </ConversationProvider>
  </ErrorBoundary>
);
