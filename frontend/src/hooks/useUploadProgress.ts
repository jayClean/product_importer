import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchJob } from '../api/jobs';

export const useUploadProgress = (jobId: string | null) => {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<'idle' | 'pending' | 'running' | 'processing' | 'completed' | 'failed'>('idle');
  const [message, setMessage] = useState<string>('');

  // Use React Query for better state management and caching
  const { data, error, isFetching } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => fetchJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Stop polling if completed or failed
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false;
      }
      // Poll every 2 seconds for active jobs
      return 2000;
    },
    retry: 3,
    retryDelay: 1000,
  });

  useEffect(() => {
    if (!jobId) {
      setProgress(0);
      setStatus('idle');
      setMessage('');
      return;
    }

    // Update state from query data
    if (data) {
      // Progress is 0-1 from API, convert to 0-100 for display
      const progressValue = typeof data.progress === 'number' 
        ? Math.round(data.progress * 100) 
        : 0;
      setProgress(progressValue);
      
      // Map backend status to frontend status
      const mappedStatus = data.status === 'running' ? 'processing' : data.status;
      setStatus(mappedStatus as any);
      
      setMessage(data.message || '');
    } else if (error) {
      setStatus('failed');
      setMessage('Failed to fetch progress');
    } else {
      // Initial state while loading
      setStatus('pending');
      setMessage('Starting upload...');
    }
  }, [data, error, jobId]);

  return { progress, status, message, isFetching };
};
