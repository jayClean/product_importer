// Form validation helpers shared across Product/Webhook forms.
export const isValidSku = (value: string) => {
  // TODO: enforce alphanumeric + max length rules consistent with backend.
  return true;
};

export const isValidUrl = (value: string) => {
  // TODO: leverage URL constructor and additional custom rules.
  return true;
};
