// Type definitions for API responses

export interface Job {
  id: string;
  type: string;
  status: 'pending' | 'running' | 'failed' | 'completed';
  progress: number | null;
  message: string | null;
  total_rows: number | null;
  processed_rows: number | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  meta: Record<string, unknown> | null;
}

export interface Product {
  id: number;
  sku: string;
  name: string;
  description: string | null;
  active: boolean;
  is_deleted: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ProductListResponse {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
}

export interface Webhook {
  id: number;
  url: string;
  event: string;
  enabled: boolean;
  secret?: string | null;
  last_test_status?: string | null;
  last_test_response_ms?: number | null;
  created_at?: string | null;
}

export interface UploadResponse {
  id: string;
}

export interface UploadStatus {
  progress: number | null;
  status: 'pending' | 'running' | 'failed' | 'completed';
  message: string | null;
}

