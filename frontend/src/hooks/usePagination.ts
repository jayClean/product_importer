// Shared pagination logic for tables/cards.
export const usePagination = () => {
  // TODO: sync query params with router and expose helpers (next/prev/jump).
  return { page: 1, pageSize: 50 };
};
