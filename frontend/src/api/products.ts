// Product API wrappers to keep React hooks declarative.
import { apiClient } from './client';
import type { Product, ProductListResponse } from '../types/api';

export const fetchProducts = async (params: Record<string, unknown>): Promise<ProductListResponse> => {
  // Fetch paginated list for the dashboard grid with applied filters.
  return apiClient.get<ProductListResponse>('/api/products', params);
};

export const createProduct = async (payload: unknown): Promise<Product> => {
  // Create product via modal or inline row add.
  return apiClient.post<Product>('/api/products', payload);
};

export const updateProduct = async (id: number, payload: unknown): Promise<Product> => {
  // Persist edits from inline editing experience.
  return apiClient.put<Product>(`/api/products/${id}`, payload);
};

export const deleteProduct = async (id: number): Promise<void> => {
  // Single-row delete with confirmation toast.
  return apiClient.delete<void>(`/api/products/${id}`);
};

export const deleteAllProducts = async (): Promise<void> => {
  // Bulk delete action triggered from danger zone UI.
  return apiClient.delete<void>('/api/products');
};
