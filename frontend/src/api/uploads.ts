// Upload-specific API helpers for CSV import flow.
import { apiClient } from './client';
import type { UploadResponse, UploadStatus } from '../types/api';

export const uploadCsv = async (file: File): Promise<UploadResponse> => {
  // POST multipart form to kick off Celery import job.
  return apiClient.upload<UploadResponse>('/api/uploads/', file);
};

export const fetchUploadStatus = async (jobId: string): Promise<UploadStatus> => {
  // Poll backend for progress fallback when SSE/WebSockets unavailable.
  return apiClient.get<UploadStatus>(`/api/uploads/${jobId}/status`);
};
