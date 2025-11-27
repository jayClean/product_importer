import { useState, useRef } from 'react';
import { useMutation } from '@tanstack/react-query';
import { uploadCsv } from '../../api/uploads';
import { useUploadProgress } from '../../hooks/useUploadProgress';
import { ProgressIndicator } from '../ProgressIndicator';
import { Toasts } from '../Toasts';

export const UploadWizard = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { progress, status, message } = useUploadProgress(jobId);

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadCsv(file),
    onSuccess: (data) => {
      setJobId(data.id);
      setToasts([{ id: Date.now(), message: 'Upload started!', type: 'success' }]);
    },
    onError: (error: Error) => {
      setToasts([{ id: Date.now(), message: `Upload failed: ${error.message}`, type: 'error' }]);
    },
  });

  const [toasts, setToasts] = useState<Array<{ id: number; message: string; type: 'success' | 'error' | 'info' }>>([]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type !== 'text/csv' && !file.name.endsWith('.csv')) {
        setToasts([{ id: Date.now(), message: 'Please select a CSV file', type: 'error' }]);
        // Reset file input
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
        return;
      }
      setSelectedFile(file);
      setJobId(null);
      // Auto-upload after file selection
      setTimeout(() => {
        uploadMutation.mutate(file);
      }, 100);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) {
      if (file.type !== 'text/csv' && !file.name.endsWith('.csv')) {
        setToasts([{ id: Date.now(), message: 'Please drop a CSV file', type: 'error' }]);
        return;
      }
      setSelectedFile(file);
      setJobId(null);
      // Auto-upload after file drop
      setTimeout(() => {
        uploadMutation.mutate(file);
      }, 100);
    }
  };

  const handleUpload = () => {
    if (selectedFile) {
      uploadMutation.mutate(selectedFile);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setJobId(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="upload-wizard">
      <h2>Upload Product CSV</h2>
      <p className="upload-description">
        Upload a CSV file with columns: <code>sku</code>, <code>name</code>, <code>description</code>
      </p>

      {!jobId && (
        <div
          className="upload-area"
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          onClick={() => {
            // Only open file picker if no file is selected
            if (!selectedFile) {
              fileInputRef.current?.click();
            }
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          {selectedFile ? (
            <div className="file-selected">
              <p>Selected: <strong>{selectedFile.name}</strong></p>
              <p className="file-size">{(selectedFile.size / 1024).toFixed(2)} KB</p>
              {uploadMutation.isPending ? (
                <p className="upload-status">Uploading...</p>
              ) : (
                <div className="upload-actions">
                  <button onClick={handleUpload} disabled={uploadMutation.isPending}>
                    Upload
                  </button>
                  <button onClick={handleReset} className="secondary">
                    Choose Different File
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="upload-prompt">
              <p>📁 Click to select or drag and drop CSV file</p>
            </div>
          )}
        </div>
      )}

      {jobId && (
        <div className="upload-progress">
          <ProgressIndicator progress={progress} status={status} message={message} />
          {status === 'completed' && (
            <button onClick={handleReset} className="upload-another">
              Upload Another File
            </button>
          )}
          {status === 'failed' && (
            <button onClick={handleReset} className="upload-another">
              Try Again
            </button>
          )}
        </div>
      )}

      <Toasts toasts={toasts} onRemove={(id) => setToasts(toasts.filter(t => t.id !== id))} />
    </div>
  );
};
