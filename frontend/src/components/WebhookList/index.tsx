import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deleteWebhook } from '../../api/webhooks';

interface Webhook {
  id: number;
  url: string;
  event: string;
  enabled: boolean;
  last_test_status?: number | null;
  last_test_response_ms?: number | null;
  created_at: string;
}

interface WebhookListProps {
  webhooks: Webhook[];
  onEdit: (webhook: Webhook) => void;
  onDelete: (id: number) => void;
  onTest: (id: number) => void;
  isTesting: boolean;
}

export const WebhookList = ({ webhooks, onEdit, onDelete, onTest, isTesting }: WebhookListProps) => {
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteWebhook(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
      onDelete(id);
    },
  });

  const handleDelete = (id: number) => {
    if (window.confirm('Are you sure you want to delete this webhook?')) {
      deleteMutation.mutate(id);
    }
  };

  if (webhooks.length === 0) {
    return <p className="empty-state">No webhooks configured</p>;
  }

  return (
    <div className="webhook-list">
      {webhooks.map((webhook) => (
        <div key={webhook.id} className="webhook-card">
          <div className="webhook-header">
            <h4>{webhook.url}</h4>
            <span className={`status-badge ${webhook.enabled ? 'enabled' : 'disabled'}`}>
              {webhook.enabled ? 'Enabled' : 'Disabled'}
            </span>
          </div>
          <div className="webhook-details">
            <p><strong>Event:</strong> {webhook.event}</p>
            {webhook.last_test_status && (
              <p>
                <strong>Last Test:</strong>{' '}
                <span className={webhook.last_test_status === 200 ? 'success' : 'error'}>
                  {webhook.last_test_status} ({webhook.last_test_response_ms}ms)
                </span>
              </p>
            )}
          </div>
          <div className="webhook-actions">
            <button onClick={() => onTest(webhook.id)} disabled={isTesting} className="btn-test">
              Test
            </button>
            <button onClick={() => onEdit(webhook)} className="btn-edit">
              Edit
            </button>
            <button
              onClick={() => handleDelete(webhook.id)}
              className="btn-delete"
              disabled={deleteMutation.isPending}
            >
              Delete
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};
