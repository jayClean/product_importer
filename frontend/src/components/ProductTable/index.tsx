import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deleteProduct } from '../../api/products';

interface Product {
  id: number;
  sku: string;
  name: string;
  description: string | null;
  active: boolean;
  created_at?: string;
  updated_at?: string;
}

interface ProductTableProps {
  products: Product[];
  onEdit: (product: Product) => void;
  onDelete: (id: number) => void;
}

export const ProductTable = ({ products, onEdit, onDelete }: ProductTableProps) => {
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteProduct(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      onDelete(id);
    },
  });

  const handleDelete = (id: number) => {
    if (window.confirm('Are you sure you want to delete this product?')) {
      deleteMutation.mutate(id);
    }
  };

  if (products.length === 0) {
    return <p className="empty-state">No products found</p>;
  }

  return (
    <div className="product-table-container">
      <table className="product-table">
        <thead>
          <tr>
            <th>SKU</th>
            <th>Name</th>
            <th>Description</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => (
            <tr key={product.id}>
              <td>{product.sku}</td>
              <td>{product.name}</td>
              <td>{product.description || '-'}</td>
              <td>
                <span className={`status-badge ${product.active ? 'active' : 'inactive'}`}>
                  {product.active ? 'Active' : 'Inactive'}
                </span>
              </td>
              <td>
                <div className="action-buttons">
                  <button onClick={() => onEdit(product)} className="btn-edit">
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(product.id)}
                    className="btn-delete"
                    disabled={deleteMutation.isPending}
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
