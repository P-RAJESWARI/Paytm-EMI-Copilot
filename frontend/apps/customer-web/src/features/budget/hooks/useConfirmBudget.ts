import { useMutation } from '@tanstack/react-query';

import { useCustomerFlowApi } from '../../customer-flow';

// Sends the budget the customer confirmed on C2 (a human gate: only after "Yes, correct").
export function useConfirmBudget() {
  const customerFlowApi = useCustomerFlowApi();
  return useMutation({
    mutationFn: (monthlyBudgetInPaise: number) =>
      customerFlowApi.confirmBudget(monthlyBudgetInPaise),
  });
}
