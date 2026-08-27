import { createContext, useContext } from 'react';

// Lets pages render their action buttons (e.g. "Add Customer") into the
// shared top bar instead of duplicating a page header per route.
export const LayoutContext = createContext({
  setHeaderActions: () => {},
});

export function useLayout() {
  return useContext(LayoutContext);
}
