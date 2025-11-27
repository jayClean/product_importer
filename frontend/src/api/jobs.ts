// Job API wrappers for import job tracking
import { apiClient } from './client';
import type { Job } from '../types/api';

export const fetchJobs = async (params?: { limit?: number; status?: string }): Promise<Job[]> => {
  return apiClient.get<Job[]>('/api/jobs', params);
};

export const fetchJob = async (jobId: string): Promise<Job> => {
  return apiClient.get<Job>(`/api/jobs/${jobId}`);
};
