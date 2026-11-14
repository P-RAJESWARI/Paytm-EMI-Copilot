import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { useMerchantApi } from '../../../shared/api/useMerchantApi';
import { buildProductsQueryKey, fetchProducts } from '../api/counterSaleApi';
import { useDebouncedValue } from './useDebouncedValue';

const SEARCH_DEBOUNCE_IN_MILLISECONDS = 300;

// Reads the products matching what the merchant typed, keeping the last list on screen while
// the next one loads.
export function useProductSearch(searchText: string) {
  const { apiClient } = useMerchantApi();
  const debouncedSearchText = useDebouncedValue(searchText.trim(), SEARCH_DEBOUNCE_IN_MILLISECONDS);
  const productsQuery = useQuery({
    queryKey: buildProductsQueryKey(debouncedSearchText),
    queryFn: () => fetchProducts(apiClient, debouncedSearchText),
    placeholderData: keepPreviousData,
  });
  return { productsQuery, searchedText: debouncedSearchText };
}
