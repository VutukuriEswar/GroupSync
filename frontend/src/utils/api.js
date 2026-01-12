import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
});

export const setAuthToken = (token) => {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
};

// Auth
export const register = (data) => api.post('/auth/register', data);
export const login = (data) => api.post('/auth/login', data);

// Groups
export const createGroup = (data, token) => {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  return api.post('/groups', data, { headers });
};
export const getGroup = (groupId) => api.get(`/groups/${groupId}`);
export const joinGroup = (inviteCode, token) => {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  return api.post(`/groups/join/${inviteCode}`, {}, { headers });
};
export const getGroupMembers = (groupId) => api.get(`/groups/${groupId}/members`);

// Preferences
export const submitPreferences = (data) => api.post('/preferences', data);

// Recommendations
export const generateRecommendation = (data) => api.post('/recommendations', data);
export const getRecommendation = (recId) => api.get(`/recommendations/${recId}`);
export const replanRecommendation = (data) => api.post('/recommendations/replan', data);

// Feedback
export const submitFeedback = (data) => api.post('/feedback', data);