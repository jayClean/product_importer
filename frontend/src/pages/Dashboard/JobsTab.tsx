import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchJobs } from '../../api/jobs';
import { ProgressIndicator } from '../../components/ProgressIndicator';

export const JobsTab = () => {
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [autoRefresh, setAutoRefresh] = useState(true);

  const { data: jobs, isLoading, error, refetch } = useQuery({
    queryKey: ['jobs', statusFilter],
    queryFn: () => fetchJobs({ limit: 100, status: statusFilter || undefined }),
    refetchInterval: autoRefresh ? 5000 : false, // Refresh every 5 seconds if enabled
  });

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString();
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'completed':
        return 'status-completed';
      case 'failed':
        return 'status-failed';
      case 'running':
        return 'status-running';
      case 'pending':
        return 'status-pending';
      default:
        return '';
    }
  };

  return (
    <div className="jobs-tab">
      <div className="jobs-header">
        <h2>Import Jobs</h2>
        <div className="jobs-controls">
          <label>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh
          </label>
          <button onClick={() => refetch()} className="btn-primary">
            Refresh
          </button>
        </div>
      </div>

      <div className="jobs-filters">
        <select
          className="status-filter"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All Status</option>
          <option value="pending">Pending</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {isLoading && <p>Loading jobs...</p>}
      {error && <p className="error">Error loading jobs: {(error as Error).message}</p>}

      {jobs && jobs.length === 0 && (
        <p className="empty-state">No import jobs found</p>
      )}

      {jobs && jobs.length > 0 && (
        <div className="jobs-list">
          {jobs.map((job: any) => (
            <div key={job.id} className="job-card">
              <div className="job-header">
                <div>
                  <span className="job-id">
                    <strong>Job ID:</strong> {job.id}
                  </span>
                  <span className={`status-badge ${getStatusClass(job.status)}`}>
                    {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                  </span>
                </div>
              </div>

              {job.status === 'running' || job.status === 'pending' ? (
                <div className="job-progress">
                  <ProgressIndicator
                    progress={(job.progress || 0) * 100}
                    status={job.status}
                    message={job.message}
                  />
                </div>
              ) : null}

              <div className="job-details">
                <div className="job-detail-row">
                  <span className="detail-label">Type:</span>
                  <span className="detail-value">{job.type}</span>
                </div>
                {job.total_rows && (
                  <div className="job-detail-row">
                    <span className="detail-label">Total Rows:</span>
                    <span className="detail-value">{job.total_rows.toLocaleString()}</span>
                  </div>
                )}
                {job.processed_rows !== undefined && (
                  <div className="job-detail-row">
                    <span className="detail-label">Processed:</span>
                    <span className="detail-value">{job.processed_rows.toLocaleString()}</span>
                  </div>
                )}
                <div className="job-detail-row">
                  <span className="detail-label">Started:</span>
                  <span className="detail-value">{formatDate(job.started_at)}</span>
                </div>
                {job.finished_at && (
                  <div className="job-detail-row">
                    <span className="detail-label">Finished:</span>
                    <span className="detail-value">{formatDate(job.finished_at)}</span>
                  </div>
                )}
              </div>

              {job.error_message && (
                <div className="job-error">
                  <strong>Error:</strong> {job.error_message}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
