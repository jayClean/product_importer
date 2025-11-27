import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchProducts, deleteAllProducts } from '../../api/products';
import { ProductTable } from '../../components/ProductTable';
import { ProductForm } from '../../components/ProductForm';
import { BulkDeleteDialog } from '../../components/BulkDeleteDialog';
import { Toasts } from '../../components/Toasts';

export const ProductsTab = () => {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [filters, setFilters] = useState({
    sku: '',
    name: '',
    description: '',
    active: undefined as boolean | undefined,
  });
  const [showForm, setShowForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState<any>(null);
  const [showBulkDelete, setShowBulkDelete] = useState(false);
  const [toasts, setToasts] = useState<Array<{ id: number; message: string; type: 'success' | 'error' | 'info' }>>([]);
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['products', page, pageSize, filters],
    queryFn: () => fetchProducts({ page, page_size: pageSize, ...filters }),
  });

  const bulkDeleteMutation = useMutation({
    mutationFn: deleteAllProducts,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      setShowBulkDelete(false);
      setToasts([{ id: Date.now(), message: 'All products deleted successfully', type: 'success' }]);
    },
    onError: (error: Error) => {
      setToasts([{ id: Date.now(), message: `Delete failed: ${error.message}`, type: 'error' }]);
    },
  });

  const handleEdit = (product: any) => {
    setEditingProduct(product);
    setShowForm(true);
  };

  const handleCreate = () => {
    setEditingProduct(null);
    setShowForm(true);
  };

  const handleFormClose = () => {
    setShowForm(false);
    setEditingProduct(null);
  };

  return (
    <div className="products-tab">
      <div className="products-header">
        <h2>Products</h2>
        <div className="products-actions">
          <button onClick={handleCreate} className="btn-primary">
            Add Product
          </button>
          <button onClick={() => setShowBulkDelete(true)} className="btn-danger">
            Delete All
          </button>
        </div>
      </div>

      <div className="products-filters">
        <input
          type="text"
          placeholder="Filter by SKU"
          value={filters.sku}
          onChange={(e) => setFilters({ ...filters, sku: e.target.value })}
        />
        <input
          type="text"
          placeholder="Filter by Name"
          value={filters.name}
          onChange={(e) => setFilters({ ...filters, name: e.target.value })}
        />
        <input
          type="text"
          placeholder="Filter by Description"
          value={filters.description}
          onChange={(e) => setFilters({ ...filters, description: e.target.value })}
        />
        <select
          value={filters.active === undefined ? '' : filters.active.toString()}
          onChange={(e) => {
            const value = e.target.value;
            setFilters({
              ...filters,
              active: value === '' ? undefined : value === 'true',
            });
          }}
        >
          <option value="">All Status</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
      </div>

      {isLoading && <p>Loading products...</p>}
      {error && <p className="error">Error loading products: {(error as Error).message}</p>}

      {data && (
        <>
          <ProductTable
            products={data.items || []}
            onEdit={handleEdit}
            onDelete={(id) => {
              queryClient.invalidateQueries({ queryKey: ['products'] });
              setToasts([{ id: Date.now(), message: 'Product deleted', type: 'success' }]);
            }}
          />

          <div className="pagination">
              <div className="pagination-info">
                <span>
                  Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, data.total)} of {data.total} products
                </span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setPage(1); // Reset to first page when changing page size
                  }}
                  className="page-size-select"
                >
                  <option value={25}>25 per page</option>
                  <option value={50}>50 per page</option>
                  <option value={100}>100 per page</option>
                  <option value={200}>200 per page</option>
                </select>
              </div>
              <div className="pagination-controls">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="btn-pagination"
                >
                  Previous
                </button>
                <span>
                  Page {data.page} of {Math.ceil(data.total / data.page_size) || 1}
                </span>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={page >= Math.ceil(data.total / data.page_size)}
                  className="btn-pagination"
                >
                  Next
                </button>
              </div>
            </div>
        </>
      )}

      {showForm && (
        <ProductForm
          product={editingProduct}
          onClose={handleFormClose}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['products'] });
            handleFormClose();
            setToasts([{ id: Date.now(), message: editingProduct ? 'Product updated' : 'Product created', type: 'success' }]);
          }}
        />
      )}

      {showBulkDelete && (
        <BulkDeleteDialog
          onConfirm={() => bulkDeleteMutation.mutate()}
          onCancel={() => setShowBulkDelete(false)}
          isDeleting={bulkDeleteMutation.isPending}
        />
      )}

      <Toasts toasts={toasts} onRemove={(id) => setToasts(toasts.filter(t => t.id !== id))} />
    </div>
  );
};
