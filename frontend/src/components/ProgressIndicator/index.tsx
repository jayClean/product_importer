interface ProgressIndicatorProps {
  progress: number;
  status: string;
  message?: string;
}

export const ProgressIndicator = ({ progress, status, message }: ProgressIndicatorProps) => {
  const getStatusColor = () => {
    switch (status) {
      case 'completed':
        return '#10b981';
      case 'failed':
        return '#ef4444';
      case 'processing':
        return '#3b82f6';
      default:
        return '#6b7280';
    }
  };

  return (
    <div className="progress-indicator">
      <div className="progress-header">
        <span className="progress-status" style={{ color: getStatusColor() }}>
          {status.charAt(0).toUpperCase() + status.slice(1)}
        </span>
        <span className="progress-percentage">{Math.round(progress)}%</span>
      </div>
      <div className="progress-bar-container">
        <div
          className="progress-bar"
          style={{
            width: `${progress}%`,
            backgroundColor: getStatusColor(),
          }}
        />
      </div>
      {message && <p className="progress-message">{message}</p>}
    </div>
  );
};
