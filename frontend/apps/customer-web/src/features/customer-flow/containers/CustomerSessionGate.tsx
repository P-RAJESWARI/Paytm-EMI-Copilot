import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { CalmErrorMessage } from '../../../shared/components/CalmErrorMessage';
import { LoadingSkeleton } from '../../../shared/components/LoadingSkeleton';
import { ScreenLayout } from '../../../shared/components/ScreenLayout';
import { getProblemMessageKey } from '../model/problemMessageKey';
import { CustomerApiError } from '../api/customerApiError';
import { useStartCustomerSession } from '../hooks/useStartCustomerSession';
import type { CustomerFlowState } from '../model/customerFlowState';
import { SessionUnavailableScreen } from '../components/SessionUnavailableScreen';
import { CustomerFlowProvider } from './CustomerFlowProvider';

export interface CustomerSessionGateProps {
  /** The QR token read from the URL fragment, or undefined when the page was opened without one. */
  qrToken: string | undefined;
  /** The flow's screens, shown once a session is open. */
  children: ReactNode;
  /** Starts the flow at another step; only tests pass it. */
  initialFlowState?: CustomerFlowState | undefined;
}

// True when the server refused the QR (any 4xx): only a new QR from the shop helps.
function isQrRefused(error: unknown): boolean {
  return error instanceof CustomerApiError && error.status >= 400 && error.status < 500;
}

// Opens the session from the QR token: a skeleton while it opens, the session screen when the QR
// is refused or missing, a calm retry when the network failed, then the flow with its session.
function OpenSessionGate({
  qrToken,
  children,
  initialFlowState,
}: CustomerSessionGateProps & { qrToken: string }) {
  const { t } = useTranslation();
  const sessionQuery = useStartCustomerSession(qrToken);
  if (sessionQuery.isPending) {
    return (
      <ScreenLayout>
        <LoadingSkeleton accessibleLabel={t('flow.openingSession')} lineCount={4} />
      </ScreenLayout>
    );
  }
  if (sessionQuery.isError) {
    if (isQrRefused(sessionQuery.error)) return <SessionUnavailableScreen />;
    return (
      <ScreenLayout>
        <CalmErrorMessage
          message={t(getProblemMessageKey(sessionQuery.error))}
          retryLabel={t('common.tryAgain')}
          onRetry={() => void sessionQuery.refetch()}
        />
      </ScreenLayout>
    );
  }
  return (
    <CustomerFlowProvider session={sessionQuery.data} initialState={initialFlowState}>
      {children}
    </CustomerFlowProvider>
  );
}

// Shows the flow only for a page opened from a shop's QR; without a token it asks for a new QR.
export function CustomerSessionGate({ qrToken, ...gateProps }: CustomerSessionGateProps) {
  if (qrToken === undefined) return <SessionUnavailableScreen />;
  return <OpenSessionGate qrToken={qrToken} {...gateProps} />;
}
