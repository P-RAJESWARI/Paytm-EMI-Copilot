import { getProblemMessageKey } from '../../../shared/api/problemMessageKey';
import { WeeklySummaryCard } from '../components/WeeklySummaryCard';
import { useMessageLanguage } from '../hooks/useMessageLanguage';
import { useWeeklyMessage } from '../hooks/useWeeklyMessage';

// Container for M5's weekly summary card: the message, its own language switch and sending.
export function WeeklySummaryContainer() {
  const { weeklyMessageQuery, sendMutation } = useWeeklyMessage();
  const {
    messageLanguage,
    setMessageLanguage,
    translateInMessageLanguage: t,
  } = useMessageLanguage();
  let placeholder;
  if (weeklyMessageQuery.isPending) {
    placeholder = (
      <p role="status" className="text-body text-border-strong">
        {t('weeklyMessage.loading')}
      </p>
    );
  } else if (weeklyMessageQuery.isError) {
    placeholder = (
      <p role="alert" className="text-body text-white">
        {t(getProblemMessageKey(weeklyMessageQuery.error))}
      </p>
    );
  }
  const weeklyMessage = weeklyMessageQuery.data;
  return (
    <WeeklySummaryCard
      weeklyMessage={weeklyMessage}
      placeholder={placeholder}
      messageLanguage={messageLanguage}
      onSelectMessageLanguage={setMessageLanguage}
      translateInMessageLanguage={t}
      onSendToPhone={() => {
        if (weeklyMessage !== undefined) sendMutation.mutate(weeklyMessage.periodStartDate);
      }}
      isSending={sendMutation.isPending}
      sendProblemMessage={
        sendMutation.error === null ? undefined : t(getProblemMessageKey(sendMutation.error))
      }
    />
  );
}
