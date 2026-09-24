import { createContext, useContext } from 'react';

export const SearchContext = createContext<string>('');

/** Search query from the shell header. Filterable screens consume this. */
export function useShellSearch(): string {
  return useContext(SearchContext);
}