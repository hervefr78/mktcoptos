import React, { useEffect, useState } from 'react';
import { API_BASE } from '../../config/api';
import { fetchWithRetry } from '../../utils/fetchWithRetry';

const RecentActivity = () => {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchActivity = async () => {
      try {
        setLoading(true);
        // Fetch recent pipeline executions as activity
        const res = await fetchWithRetry(`${API_BASE}/api/content-pipeline/history?limit=10`);
        if (!res.ok) {
          throw new Error('Failed to fetch activity');
        }
        const data = await res.json();

        // Transform pipeline executions into activity items
        const activityItems = (data.executions || []).map(exec => ({
          id: exec.id,
          message: `${exec.status === 'completed' ? '✓' : exec.status === 'failed' ? '✗' : '⋯'} ${exec.content_type}: "${exec.topic}"`,
          timestamp: exec.created_at,
          status: exec.status,
          type: 'content'
        }));

        setActivities(activityItems);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch activity:', err);
        setError('Unable to load recent activity. Please check your connection.');
        setActivities([]);
      } finally {
        setLoading(false);
      }
    };

    fetchActivity();
  }, []);

  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="recent-activity">
      <h2>Recent Activity</h2>
      {loading ? (
        <p className="loading-text">Loading activity...</p>
      ) : error ? (
        <p className="error-text">{error}</p>
      ) : activities.length === 0 ? (
        <p className="empty-text">No recent activity. Create your first content to get started!</p>
      ) : (
        <ul>
          {activities.map((item) => (
            <li key={item.id} className={`activity-item ${item.status}`}>
              <span className="activity-message">{item.message}</span>
              <span className="activity-time">{formatDate(item.timestamp)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default RecentActivity;
