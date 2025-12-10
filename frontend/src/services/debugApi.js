/**
 * API service for debug logs endpoints
 */

const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export const debugApi = {
  /**
   * Get recent pipeline executions
   * @param {number} limit - Number of records to return (1-200)
   * @param {string} status - Filter by status (optional)
   */
  async getPipelineExecutions(limit = 50, status = null) {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (status) {
      params.append('status', status);
    }

    const response = await fetch(
      `${API_BASE}/api/debug/pipeline-executions?${params.toString()}`
    );

    if (!response.ok) {
      throw new Error('Failed to fetch pipeline executions');
    }

    return response.json();
  },

  /**
   * Get recent agent activities
   * @param {number} limit - Number of records to return (1-200)
   * @param {string} status - Filter by status (optional)
   */
  async getAgentActivities(limit = 50, status = null) {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (status) {
      params.append('status', status);
    }

    const response = await fetch(
      `${API_BASE}/api/debug/agent-activities?${params.toString()}`
    );

    if (!response.ok) {
      throw new Error('Failed to fetch agent activities');
    }

    return response.json();
  },

  /**
   * Get full details for a specific execution
   * @param {number} executionId - The execution ID
   */
  async getExecutionDetails(executionId) {
    const response = await fetch(
      `${API_BASE}/api/debug/execution/${executionId}/full`
    );

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Execution not found');
      }
      throw new Error('Failed to fetch execution details');
    }

    return response.json();
  },

  /**
   * Get recent errors from the last N hours
   * @param {number} hours - Number of hours to look back (1-168)
   */
  async getRecentErrors(hours = 24) {
    const response = await fetch(
      `${API_BASE}/api/debug/errors/recent?hours=${hours}`
    );

    if (!response.ok) {
      throw new Error('Failed to fetch recent errors');
    }

    return response.json();
  }
};
