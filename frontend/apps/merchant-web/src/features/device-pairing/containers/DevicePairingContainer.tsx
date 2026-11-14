import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { PairingForm } from '../components/PairingForm';
import { usePairDevice } from '../hooks/usePairDevice';
import type { PairingFormValues } from '../model/pairingForm';
import { describePairingProblem } from '../model/pairingProblemMessage';

// Container for M1: sends the pairing, turns a refusal into a calm translated message and
// empties the PIN after each failed try. The route guard moves on once the session exists.
export function DevicePairingContainer() {
  const { t } = useTranslation();
  const pairDeviceMutation = usePairDevice();
  const [failedAttemptCount, setFailedAttemptCount] = useState(0);

  // Sends one pairing attempt and counts it when the server refuses.
  function handlePair(values: PairingFormValues) {
    pairDeviceMutation.mutate(values, {
      onError: () => {
        setFailedAttemptCount((count) => count + 1);
      },
    });
  }

  const problem =
    pairDeviceMutation.error === null
      ? undefined
      : describePairingProblem(pairDeviceMutation.error);
  const problemMessage =
    problem === undefined
      ? undefined
      : t(
          problem.translationKey,
          problem.minuteCount === undefined ? {} : { count: problem.minuteCount },
        );
  return (
    <PairingForm
      onPair={handlePair}
      isPairing={pairDeviceMutation.isPending}
      problemMessage={problemMessage}
      failedAttemptCount={failedAttemptCount}
    />
  );
}
