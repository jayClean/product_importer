import { useState, useEffect } from 'react';
import { fetchUploadStatus } from '../api/uploads';

export const useUploadProgress = (jobId: string | null) => {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<'idle' | 'pending' | 'processing' | 'completed' | 'failed'>('idle');
  const [message, setMessage] = useState<string>('');

  useEffect(() => {
    if (!jobId) {
      setProgress(0);
      setStatus('idle');
      setMessage('');
      return;
    }

    setStatus('pending');
    setMessage('Starting upload...');

    // Polling interval
    const interval = setInterval(async () => {
      try {
        const data = await fetchUploadStatus(jobId);
        setProgress(data.progress || 0);
        setStatus(data.status || 'pending');
        setMessage(data.message || '');

        // Stop polling if completed or failed
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Error fetching progress:', error);
        setStatus('failed');
        setMessage('Failed to fetch progress');
        clearInterval(interval);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [jobId]);

  return { progress, status, message };
};
