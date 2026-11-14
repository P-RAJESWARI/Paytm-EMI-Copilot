import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { getButtonClassName } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { MERCHANT_PATHS } from '../../../app/merchantPaths';
import { getProblemMessageKey } from '../../../shared/api/problemMessageKey';
import { CalmErrorMessage } from '../../../shared/components/CalmErrorMessage';
import { LoadingSkeleton } from '../../../shared/components/LoadingSkeleton';
import { PageHeading } from '../../../shared/components/PageHeading';
import { CustomerQrArea } from '../components/CustomerQrArea';
import { SaleStatusCard } from '../components/SaleStatusCard';
import { useCustomerQr } from '../hooks/useCustomerQr';
import { useHasMomentPassed } from '../hooks/useHasMomentPassed';
import { useSaleDetail } from '../hooks/useSaleDetail';

export interface ShowQrContainerProps {
  saleId: string;
}

// Container for M3 (tablet and phone): the sale, its QR code held in memory, the live status
// card, and a new QR when the old one expires while the customer is still choosing.
export function ShowQrContainer({ saleId }: ShowQrContainerProps) {
  const { t } = useTranslation();
  const saleDetailQuery = useSaleDetail(saleId);
  const isSaleChoosing = saleDetailQuery.data?.status === 'CHOOSING';
  const { customerQrQuery, issueNewQrMutation } = useCustomerQr(saleId, isSaleChoosing);
  const isQrExpired = useHasMomentPassed(customerQrQuery.data?.expiresAt);
  const backLink = (
    <Link to={MERCHANT_PATHS.newEmiSale} className={getButtonClassName({ variant: 'secondary' })}>
      {t('showQr.backToCounterList')}
    </Link>
  );

  if (saleDetailQuery.isPending) {
    return <LoadingSkeleton accessibleLabel={t('showQr.loadingSale')} />;
  }
  if (saleDetailQuery.isError) {
    return (
      <div className="flex flex-col items-start gap-4">
        <CalmErrorMessage
          message={t(getProblemMessageKey(saleDetailQuery.error))}
          retryLabel={t('common.tryAgain')}
          onRetry={() => void saleDetailQuery.refetch()}
        />
        {backLink}
      </div>
    );
  }
  const sale = saleDetailQuery.data;
  const qrError = issueNewQrMutation.error ?? customerQrQuery.error;
  return (
    <>
      <PageHeading
        title={t('showQr.title')}
        description={t('showQr.saleLine', {
          productName: sale.productName,
          price: formatRupeesFromPaise(sale.priceInPaise),
          code: sale.sessionCode,
        })}
        action={backLink}
      />
      <div className="grid gap-6 md:grid-cols-2">
        <CustomerQrArea
          sessionCode={sale.sessionCode}
          isSaleChoosing={isSaleChoosing}
          customerQr={customerQrQuery.data}
          isQrLoading={customerQrQuery.isPending}
          qrProblemMessage={qrError === null ? undefined : t(getProblemMessageKey(qrError))}
          isQrExpired={isQrExpired}
          onShowNewQr={() => {
            issueNewQrMutation.mutate();
          }}
          isIssuingNewQr={issueNewQrMutation.isPending}
        />
        <div className="flex flex-col gap-4">
          <SaleStatusCard sale={sale} />
          {isSaleChoosing ? (
            <p className="text-label font-normal text-slate">{t('showQr.serveOthersNote')}</p>
          ) : null}
        </div>
      </div>
    </>
  );
}
