/**
 * Centralized API configuration
 */

export const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const API_ENDPOINTS = {
  // Projects
  PROJECTS: `${API_BASE}/api/projects`,
  PROJECT: (id) => `${API_BASE}/api/projects/${id}`,
  PROJECT_ARCHIVE: (id) => `${API_BASE}/api/projects/${id}/archive`,
  PROJECT_UNARCHIVE: (id) => `${API_BASE}/api/projects/${id}/unarchive`,

  // Content Pipeline
  PIPELINE_RUN: `${API_BASE}/api/content-pipeline/run`,
  PIPELINE_RUN_STREAM: `${API_BASE}/api/content-pipeline/run/stream`,
  PIPELINE_HISTORY: `${API_BASE}/api/content-pipeline/history`,
  PIPELINE_EXECUTION: (id) => `${API_BASE}/api/content-pipeline/executions/${id}`,

  // Campaigns (aliases of projects with campaign metadata)
  CAMPAIGNS: `${API_BASE}/api/campaigns`,
  CAMPAIGN: (id) => `${API_BASE}/api/campaigns/${id}`,

  // Categories
  CATEGORIES: `${API_BASE}/api/categories`,
  CATEGORY: (id) => `${API_BASE}/api/categories/${id}`,

  // Settings
  SETTINGS: `${API_BASE}/api/settings`,
  SETTINGS_HISTORY: `${API_BASE}/api/settings/history`,

  // RAG
  RAG_DOCUMENTS: `${API_BASE}/api/rag/documents`,
  RAG_QUERY: `${API_BASE}/api/rag/query`,
  RAG_COLLECTIONS: `${API_BASE}/api/rag/collections`,

  // Auth
  LOGIN: `${API_BASE}/api/auth/login`,
  LOGOUT: `${API_BASE}/api/auth/logout`,
  ME: `${API_BASE}/api/auth/me`,

  // Admin
  USERS: `${API_BASE}/api/admin/users`,
  USER: (id) => `${API_BASE}/api/admin/users/${id}`,

  // Health
  HEALTH: `${API_BASE}/health`,
};

/**
 * Default fetch options with common headers
 */
export const defaultFetchOptions = {
  headers: {
    'Content-Type': 'application/json',
  },
};

/**
 * Helper function for API requests
 */
export async function apiRequest(url, options = {}) {
  const response = await fetch(url, {
    ...defaultFetchOptions,
    ...options,
    headers: {
      ...defaultFetchOptions.headers,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = new Error(`API Error: ${response.status}`);
    error.status = response.status;
    try {
      error.data = await response.json();
    } catch {
      error.data = null;
    }
    throw error;
  }

  return response.json();
}
