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

export const register = (data) => api.post('/auth/register', data);
export const login = (data) => api.post('/auth/login', data);

export const getProfile = () => api.get('/users/me');
export const updateProfile = (data) => api.put('/users/me', data);

export const createGroup = (data, token) => {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  return api.post('/groups', data, { headers });
};
export const getGroup = (groupId) => api.get(`/groups/${groupId}`);
export const getMyGroups = () => api.get('/groups/my'); 
export const restartGroup = (groupId) => api.post(`/groups/${groupId}/restart`); 
export const joinGroup = (inviteCode, token) => {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  return api.post(`/groups/join/${inviteCode}`, {}, { headers });
};
export const getGroupMembers = (groupId) => api.get(`/groups/${groupId}/members`);

export const submitPreferences = (data) => api.post('/preferences', data);

export const generateRecommendation = (data) => api.post('/recommendations', data);
export const getRecommendation = (recId) => api.get(`/recommendations/${recId}`);
export const replanRecommendation = (data) => api.post('/recommendations/replan', data);

export const submitFeedback = (data) => api.post('/feedback', data);