import { useQuery } from '@tanstack/react-query';

import { customerQueryKeys } from '../api/customerQueryKeys';
import type { BudgetAndComfortAnswers } from '../model/customerFlowState';
import { useCustomerFlowApi } from './useCustomerFlowApi';

// Fetches every plan for the confirmed budget, ranked by the server (C4). The key names the budget
// and the comfort choice, so changing either fetches afresh.
export function usePlanComparison(answers: BudgetAndComfortAnswers) {
  const customerFlowApi = useCustomerFlowApi();
  return useQuery({
    queryKey: customerQueryKeys.plans(answers.confirmedBudgetInPaise, answers.comfortCheck.status),
    queryFn: () => customerFlowApi.listPlans(),
  });
}
