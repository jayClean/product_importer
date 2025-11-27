import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchWebhooks, testWebhook } from '../../api/webhooks';
import { WebhookList } from '../../components/WebhookList';
import { WebhookForm } from '../../components/WebhookForm';
import { Toasts } from '../../components/Toasts';

export const WebhooksTab = () => {
  const [showForm, setShowForm] = useState(false);
  const [editingWebhook, setEditingWebhook] = useState<any>(null);
  const [toasts, setToasts] = useState<Array<{ id: number; message: string; type: 'success' | 'error' | 'info' }>>([]);
  const queryClient = useQueryClient();

  const { data: webhooks, isLoading, error } = useQuery({
    queryKey: ['webhooks'],
    queryFn: fetchWebhooks,
  });

  const testMutation = useMutation({
    mutationFn: (id: number) => testWebhook(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
      setToasts([{ id: Date.now(), message: 'Webhook test initiated', type: 'info' }]);
    },
    onError: (error: Error) => {
      setToasts([{ id: Date.now(), message: `Test failed: ${error.message}`, type: 'error' }]);
    },
  });

  const handleCreate = () => {
    setEditingWebhook(null);
    setShowForm(true);
  };

  const handleEdit = (webhook: any) => {
    setEditingWebhook(webhook);
    setShowForm(true);
  };

  const handleFormClose = () => {
    setShowForm(false);
    setEditingWebhook(null);
  };

  const handleTest = (id: number) => {
    testMutation.mutate(id);
  };

  return (
    <div className="webhooks-tab">
      <div className="webhooks-header">
        <h2>Webhooks</h2>
        <button onClick={handleCreate} className="btn-primary">
          Add Webhook
        </button>
      </div>

      {isLoading && <p>Loading webhooks...</p>}
      {error && <p className="error">Error loading webhooks: {(error as Error).message}</p>}

      {webhooks && webhooks.length > 0 && (
        <WebhookList
          webhooks={webhooks}
          onEdit={handleEdit}
          onDelete={() => {
            queryClient.invalidateQueries({ queryKey: ['webhooks'] });
            setToasts([{ id: Date.now(), message: 'Webhook deleted', type: 'success' }]);
          }}
          onTest={handleTest}
          isTesting={testMutation.isPending}
        />
      )}

      {webhooks && webhooks.length === 0 && (
        <p className="empty-state">No webhooks found</p>
      )}

      {showForm && (
        <WebhookForm
          webhook={editingWebhook}
          onClose={handleFormClose}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['webhooks'] });
            handleFormClose();
            setToasts([{ id: Date.now(), message: editingWebhook ? 'Webhook updated' : 'Webhook created', type: 'success' }]);
          }}
        />
      )}

      <Toasts toasts={toasts} onRemove={(id) => setToasts(toasts.filter(t => t.id !== id))} />
    </div>
  );
};
