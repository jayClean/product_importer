// Product API wrappers to keep React hooks declarative.
import { apiClient } from './client';

export const fetchProducts = async (params: Record<string, unknown>) => {
  // Fetch paginated list for the dashboard grid with applied filters.
  return apiClient.get('/api/products', params);
};

export const createProduct = async (payload: unknown) => {
  // Create product via modal or inline row add.
  return apiClient.post('/api/products', payload);
};

export const updateProduct = async (id: number, payload: unknown) => {
  // Persist edits from inline editing experience.
  return apiClient.put(`/api/products/${id}`, payload);
};

export const deleteProduct = async (id: number) => {
  // Single-row delete with confirmation toast.
  return apiClient.delete(`/api/products/${id}`);
};

export const deleteAllProducts = async () => {
  // Bulk delete action triggered from danger zone UI.
  return apiClient.delete('/api/products');
};
