import { getProblemMessageKey } from '../../../shared/api/problemMessageKey';
import { CalmErrorMessage } from '../../../shared/components/CalmErrorMessage';
import { LoadingSkeleton } from '../../../shared/components/LoadingSkeleton';
import { WeeklyMessagePhoneView } from '../components/WeeklyMessagePhoneView';
import { useMessageLanguage } from '../hooks/useMessageLanguage';
import { useWeeklyMessage } from '../hooks/useWeeklyMessage';

// Container for M8: this week's message with its own language switch, starting in the shop language.
export function WeeklyMessagePhoneContainer() {
  const { weeklyMessageQuery } = useWeeklyMessage();
  const {
    messageLanguage,
    setMessageLanguage,
    translateInMessageLanguage: t,
  } = useMessageLanguage();
  let placeholder;
  if (weeklyMessageQuery.isPending) {
    placeholder = <LoadingSkeleton accessibleLabel={t('weeklyMessage.loading')} lineCount={4} />;
  } else if (weeklyMessageQuery.isError) {
    placeholder = (
      <CalmErrorMessage
        message={t(getProblemMessageKey(weeklyMessageQuery.error))}
        retryLabel={t('common.tryAgain')}
        onRetry={() => void weeklyMessageQuery.refetch()}
      />
    );
  }
  return (
    <WeeklyMessagePhoneView
      weeklyMessage={weeklyMessageQuery.data}
      placeholder={placeholder}
      messageLanguage={messageLanguage}
      onSelectMessageLanguage={setMessageLanguage}
      translateInMessageLanguage={t}
    />
  );
}
