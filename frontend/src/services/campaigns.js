import { API_BASE } from '../config/api';
import { fetchWithRetry, fetchJsonWithRetry } from '../utils/fetchWithRetry';

const CAMPAIGNS_ENDPOINT = `${API_BASE}/api/campaigns`;

const toQueryString = (params = {}) => {
  const query = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '' || value === 'All') {
      return;
    }
    if (Array.isArray(value)) {
      value.forEach((entry) => query.append(key, entry));
    } else {
      query.append(key, value);
    }
  });

  const queryString = query.toString();
  return queryString ? `?${queryString}` : '';
};

export async function fetchCampaigns(params = {}) {
  const response = await fetchJsonWithRetry(`${CAMPAIGNS_ENDPOINT}${toQueryString(params)}`, {
    credentials: 'include',
  });
  return Array.isArray(response) ? response : response?.campaigns || [];
}

export async function createCampaign(payload) {
  const response = await fetchWithRetry(CAMPAIGNS_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error('Failed to create campaign');
  }

  return response.json();
}

export async function updateCampaign(id, payload) {
  const response = await fetchWithRetry(`${CAMPAIGNS_ENDPOINT}/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error('Failed to update campaign');
  }

  return response.json();
}

export async function deleteCampaign(id) {
  const response = await fetchWithRetry(`${CAMPAIGNS_ENDPOINT}/${id}`, {
    method: 'DELETE',
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error('Failed to delete campaign');
  }
}
