// Webhook management API wrappers for UI tab.
import { apiClient } from './client';
import type { Webhook } from '../types/api';

export const fetchWebhooks = async (): Promise<Webhook[]> => 
  apiClient.get<Webhook[]>('/api/webhooks');

export const createWebhook = async (payload: unknown): Promise<Webhook> =>
  apiClient.post<Webhook>('/api/webhooks', payload);

export const updateWebhook = async (id: number, payload: unknown): Promise<Webhook> =>
  apiClient.put<Webhook>(`/api/webhooks/${id}`, payload);

export const deleteWebhook = async (id: number): Promise<void> =>
  apiClient.delete<void>(`/api/webhooks/${id}`);

export const testWebhook = async (id: number): Promise<void> =>
  apiClient.post<void>(`/api/webhooks/${id}/test`);
