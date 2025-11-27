interface Toast {
  id: number;
  message: string;
  type: 'success' | 'error' | 'info';
}

interface ToastsProps {
  toasts: Toast[];
  onRemove: (id: number) => void;
}

export const Toasts = ({ toasts, onRemove }: ToastsProps) => {
  if (toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`toast toast-${toast.type}`}
          onClick={() => onRemove(toast.id)}
        >
          {toast.type === 'success' && '✓ '}
          {toast.type === 'error' && '✗ '}
          {toast.type === 'info' && 'ℹ '}
          {toast.message}
        </div>
      ))}
    </div>
  );
};
