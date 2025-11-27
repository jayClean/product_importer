// Upload-specific API helpers for CSV import flow.
import { apiClient } from './client';

export const uploadCsv = async (file: File) => {
  // POST multipart form to kick off Celery import job.
  return apiClient.upload('/api/uploads/', file);
};

export const fetchUploadStatus = async (jobId: string) => {
  // Poll backend for progress fallback when SSE/WebSockets unavailable.
  return apiClient.get(`/api/uploads/${jobId}/status`);
};
