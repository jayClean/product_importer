import { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { createWebhook, updateWebhook } from '../../api/webhooks';

interface Webhook {
  id?: number;
  url: string;
  event: string;
  enabled: boolean;
  secret?: string;
}

interface WebhookFormProps {
  webhook?: Webhook | null;
  onClose: () => void;
  onSuccess: () => void;
}

const EVENT_TYPES = ['product.created', 'product.updated', 'product.deleted'];

export const WebhookForm = ({ webhook, onClose, onSuccess }: WebhookFormProps) => {
  const [formData, setFormData] = useState({
    url: '',
    event: 'product.created',
    enabled: true,
    secret: '',
  });

  useEffect(() => {
    if (webhook) {
      setFormData({
        url: webhook.url || '',
        event: webhook.event || 'product.created',
        enabled: webhook.enabled ?? true,
        secret: webhook.secret || '',
      });
    }
  }, [webhook]);

  const createMutation = useMutation({
    mutationFn: createWebhook,
    onSuccess: onSuccess,
  });

  const updateMutation = useMutation({
    mutationFn: (data: Webhook) => updateWebhook(webhook!.id!, data),
    onSuccess: onSuccess,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      ...formData,
      secret: formData.secret || undefined,
    };
    if (webhook) {
      updateMutation.mutate(payload);
    } else {
      createMutation.mutate(payload);
    }
  };

  const isLoading = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{webhook ? 'Edit Webhook' : 'Create Webhook'}</h3>
          <button onClick={onClose} className="modal-close">×</button>
        </div>
        <form onSubmit={handleSubmit} className="webhook-form">
          <div className="form-group">
            <label htmlFor="url">URL *</label>
            <input
              id="url"
              type="url"
              value={formData.url}
              onChange={(e) => setFormData({ ...formData, url: e.target.value })}
              required
              disabled={isLoading}
              placeholder="https://example.com/webhook"
            />
          </div>
          <div className="form-group">
            <label htmlFor="event">Event *</label>
            <select
              id="event"
              value={formData.event}
              onChange={(e) => setFormData({ ...formData, event: e.target.value })}
              required
              disabled={isLoading}
            >
              {EVENT_TYPES.map((event) => (
                <option key={event} value={event}>
                  {event}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="secret">Secret (Optional)</label>
            <input
              id="secret"
              type="text"
              value={formData.secret}
              onChange={(e) => setFormData({ ...formData, secret: e.target.value })}
              disabled={isLoading}
              placeholder="HMAC secret for webhook verification"
            />
          </div>
          <div className="form-group">
            <label>
              <input
                type="checkbox"
                checked={formData.enabled}
                onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                disabled={isLoading}
              />
              Enabled
            </label>
          </div>
          <div className="form-actions">
            <button type="button" onClick={onClose} disabled={isLoading}>
              Cancel
            </button>
            <button type="submit" disabled={isLoading} className="btn-primary">
              {isLoading ? 'Saving...' : webhook ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
