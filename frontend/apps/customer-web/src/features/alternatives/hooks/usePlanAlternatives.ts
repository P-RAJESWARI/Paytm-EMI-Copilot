import { useQuery } from '@tanstack/react-query';

import { customerQueryKeys, useCustomerFlowApi } from '../../customer-flow';

// Asks the engine for smarter alternatives to the selected plan (C6); the figures are the server's.
export function usePlanAlternatives(offerId: string, monthlyBudgetInPaise: number) {
  const customerFlowApi = useCustomerFlowApi();
  return useQuery({
    queryKey: customerQueryKeys.alternatives(offerId, monthlyBudgetInPaise),
    queryFn: () => customerFlowApi.findAlternatives(offerId),
  });
}
