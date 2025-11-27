interface BulkDeleteDialogProps {
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting: boolean;
}

export const BulkDeleteDialog = ({ onConfirm, onCancel, isDeleting }: BulkDeleteDialogProps) => {
  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-content danger" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Delete All Products</h3>
          <button onClick={onCancel} className="modal-close">×</button>
        </div>
        <div className="modal-body">
          <p>⚠️ Are you sure you want to delete <strong>all products</strong>?</p>
          <p>This action cannot be undone.</p>
        </div>
        <div className="modal-actions">
          <button onClick={onCancel} disabled={isDeleting}>
            Cancel
          </button>
          <button onClick={onConfirm} disabled={isDeleting} className="btn-danger">
            {isDeleting ? 'Deleting...' : 'Delete All'}
          </button>
        </div>
      </div>
    </div>
  );
};
