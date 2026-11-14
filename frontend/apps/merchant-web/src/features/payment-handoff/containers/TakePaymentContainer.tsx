import { getButtonClassName } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { MERCHANT_PATHS } from '../../../app/merchantPaths';
import { readMerchantApiErrorCode } from '../../../shared/api/merchantApiError';
import { getProblemMessageKey } from '../../../shared/api/problemMessageKey';
import { useCopyToClipboard } from '../../../shared/clipboard/useCopyToClipboard';
import { CalmErrorMessage } from '../../../shared/components/CalmErrorMessage';
import { LoadingSkeleton } from '../../../shared/components/LoadingSkeleton';
import { PageHeading } from '../../../shared/components/PageHeading';
import { EdcSteps } from '../components/EdcSteps';
import { HandoffPlanGrid } from '../components/HandoffPlanGrid';
import { PaymentLinkPanel } from '../components/PaymentLinkPanel';
import { PaymentStatusCard } from '../components/PaymentStatusCard';
import { useCreatePaymentLink } from '../hooks/useCreatePaymentLink';
import { useRefreshPaymentStatus } from '../hooks/useRefreshPaymentStatus';
import { useSaleHandoff } from '../hooks/useSaleHandoff';

export interface TakePaymentContainerProps {
  saleId: string;
}

// Container for M4: the agreed plan, EDC steps, an optional payment link (QR and copy) and the
// server-confirmed payment status, which the live feed and "Refresh status" keep current.
export function TakePaymentContainer({ saleId }: TakePaymentContainerProps) {
  const { t } = useTranslation();
  const handoffQuery = useSaleHandoff(saleId);
  const { createPaymentLink, isCreatingLink, createLinkError } = useCreatePaymentLink(saleId);
  const refreshStatusMutation = useRefreshPaymentStatus(saleId);
  const { copyState, copyText } = useCopyToClipboard();
  const backLink = (
    <Link to={MERCHANT_PATHS.newEmiSale} className={getButtonClassName({ variant: 'secondary' })}>
      {t('showQr.backToCounterList')}
    </Link>
  );

  if (handoffQuery.isPending) return <LoadingSkeleton accessibleLabel={t('handoff.loading')} />;
  if (handoffQuery.isError) {
    const isNotAgreedYet = readMerchantApiErrorCode(handoffQuery.error) === 'SALE_STATE_CONFLICT';
    return (
      <div className="flex flex-col items-start gap-4">
        <CalmErrorMessage
          message={
            isNotAgreedYet ? t('handoff.notReady') : t(getProblemMessageKey(handoffQuery.error))
          }
          retryLabel={t('common.tryAgain')}
          onRetry={() => void handoffQuery.refetch()}
        />
        {backLink}
      </div>
    );
  }
  const handoff = handoffQuery.data;
  const isWaiting = handoff.paymentStatus === 'WAITING';
  const openPaymentLink = isWaiting ? handoff.latestPaymentLink : null;
  const actionError = createLinkError ?? refreshStatusMutation.error;
  return (
    <>
      <PageHeading
        title={t('handoff.title')}
        description={t('handoff.description')}
        action={backLink}
      />
      <div className="grid gap-6 md:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-4">
          <HandoffPlanGrid sale={handoff.sale} />
          <EdcSteps
            edcInstructions={handoff.edcInstructions}
            onSendPaymentLink={() => {
              createPaymentLink(false);
            }}
            isSendingPaymentLink={isCreatingLink}
            canSendPaymentLink={isWaiting && openPaymentLink === null}
          />
          {openPaymentLink === null ? null : (
            <PaymentLinkPanel
              paymentUrl={openPaymentLink.paymentUrl}
              copyState={copyState}
              onCopyLink={() => void copyText(openPaymentLink.paymentUrl)}
            />
          )}
        </div>
        <div className="flex flex-col gap-4">
          {actionError === null ? null : (
            <CalmErrorMessage message={t(getProblemMessageKey(actionError))} />
          )}
          <PaymentStatusCard
            paymentStatus={handoff.paymentStatus}
            paymentConfirmedAt={handoff.paymentConfirmedAt}
            amountInPaise={handoff.edcInstructions.amountInPaise}
            planKind={handoff.sale.chosenPlan?.planKind}
            onRefreshStatus={() => {
              refreshStatusMutation.mutate();
            }}
            isRefreshingStatus={refreshStatusMutation.isPending}
            onTryAgain={() => {
              createPaymentLink(true);
            }}
            isTryingAgain={isCreatingLink}
          />
        </div>
      </div>
    </>
  );
}
