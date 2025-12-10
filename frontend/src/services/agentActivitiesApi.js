/**
 * Agent Activities API client
 *
 * Provides access to agent activity tracking and reporting endpoints
 */

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const agentActivitiesApi = {
  /**
   * Get all agent activities for a pipeline execution
   * @param {number} executionId - Pipeline execution ID
   * @returns {Promise<Array>} List of agent activities
   */
  async getActivities(executionId) {
    const response = await fetch(
      `${API_BASE}/api/content-pipeline/execution/${executionId}/activities`
    );
    if (!response.ok) {
      throw new Error('Failed to load agent activities');
    }

    const data = await response.json();
    const activities = Array.isArray(data)
      ? data
      : Array.isArray(data?.activities)
        ? data.activities
        : [];

    return activities;
  },

  /**
   * Get a single agent activity by ID
   * @param {number} activityId - Agent activity ID
   * @returns {Promise<Object>} Agent activity details
   */
  async getActivity(activityId) {
    const response = await fetch(
      `${API_BASE}/api/content-pipeline/activity/${activityId}`
    );
    if (!response.ok) {
      throw new Error('Failed to load agent activity');
    }
    return response.json();
  },

  /**
   * Download PDF report for pipeline execution
   * @param {number} executionId - Pipeline execution ID
   * @param {string} pipelineId - Pipeline ID for filename
   * @returns {Promise<void>} Triggers download
   */
  async downloadReport(executionId, pipelineId) {
    const response = await fetch(
      `${API_BASE}/api/content-pipeline/execution/${executionId}/report`
    );
    if (!response.ok) {
      throw new Error('Failed to generate report');
    }

    // Create blob and trigger download
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pipeline_${pipelineId}_report.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },

  /**
   * Get agent activity summary for execution
   * @param {number} executionId - Pipeline execution ID
   * @returns {Promise<Object>} Summary with total agents, costs, etc.
   */
  async getSummary(executionId) {
    const activities = await this.getActivities(executionId);
    const safeActivities = Array.isArray(activities) ? activities : [];

    const summary = {
      total_agents: safeActivities.length,
      completed: safeActivities.filter(a => a.status === 'completed').length,
      failed: safeActivities.filter(a => a.status === 'failed').length,
      total_duration: safeActivities.reduce((sum, a) => sum + (a.duration_seconds || 0), 0),
      total_tokens: safeActivities.reduce((sum, a) =>
        sum + (a.input_tokens || 0) + (a.output_tokens || 0), 0
      ),
      total_cost: safeActivities.reduce((sum, a) => sum + parseFloat(a.estimated_cost || 0), 0),
      total_decisions: safeActivities.reduce((sum, a) => sum + (a.decisions?.length || 0), 0),
      total_rag_docs: safeActivities.reduce((sum, a) => sum + (a.rag_documents?.length || 0), 0),
      agents: safeActivities
    };

    return summary;
  }
};
