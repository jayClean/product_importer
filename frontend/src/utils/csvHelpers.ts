// Browser-side helpers for pre-validating CSV before upload.
export const sniffDelimiter = (file: File): Promise<string> => {
  // TODO: peek file head and determine delimiter to inform backend.
  return Promise.reject('Not implemented');
};

export const summarizeCsv = async (file: File) => {
  // TODO: produce friendly summary (rows, headers) for confirmation modal.
  return Promise.reject('Not implemented');
};
