// Job API wrappers for import job tracking
import { apiClient } from './client';

export const fetchJobs = async (params?: { limit?: number; status?: string }) => {
  return apiClient.get('/api/jobs', params);
};

export const fetchJob = async (jobId: string) => {
  return apiClient.get(`/api/jobs/${jobId}`);
};
