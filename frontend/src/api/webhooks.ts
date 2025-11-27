// Webhook management API wrappers for UI tab.
import { apiClient } from './client';

export const fetchWebhooks = async () => apiClient.get('/api/webhooks');

export const createWebhook = async (payload: unknown) =>
  apiClient.post('/api/webhooks', payload);

export const updateWebhook = async (id: number, payload: unknown) =>
  apiClient.put(`/api/webhooks/${id}`, payload);

export const deleteWebhook = async (id: number) =>
  apiClient.delete(`/api/webhooks/${id}`);

export const testWebhook = async (id: number) =>
  apiClient.post(`/api/webhooks/${id}/test`);
