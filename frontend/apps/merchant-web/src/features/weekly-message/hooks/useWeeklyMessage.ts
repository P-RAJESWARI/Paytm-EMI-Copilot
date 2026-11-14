import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useMerchantApi } from '../../../shared/api/useMerchantApi';
import {
  WEEKLY_MESSAGE_QUERY_KEY,
  fetchWeeklyMessage,
  sendWeeklyMessage,
} from '../api/weeklyMessageApi';

// Reads this week's message and offers "Send to my phone", whose answer replaces the cached
// message so the card switches to "Sent to your phone" at once.
export function useWeeklyMessage() {
  const { apiClient } = useMerchantApi();
  const queryClient = useQueryClient();
  const weeklyMessageQuery = useQuery({
    queryKey: WEEKLY_MESSAGE_QUERY_KEY,
    queryFn: () => fetchWeeklyMessage(apiClient),
  });
  const sendMutation = useMutation({
    mutationFn: (periodStartDate: string) => sendWeeklyMessage(apiClient, periodStartDate),
    onSuccess: (weeklyMessage) => {
      queryClient.setQueryData(WEEKLY_MESSAGE_QUERY_KEY, weeklyMessage);
    },
  });
  return { weeklyMessageQuery, sendMutation };
}
