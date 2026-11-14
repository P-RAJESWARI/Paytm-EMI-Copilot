import { formatRupeesFromPaise, useLanguagePreference } from '@emi-copilot/shared-i18n';
import { Button, getButtonClassName } from '@emi-copilot/ui-kit';
import { useId } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { MERCHANT_PATHS } from '../../../app/merchantPaths';
import { formatShopTime } from '../../../shared/formatting/formatShopTime';
import type { PlanKind } from '../../../shared/plan/planName';
import type { HandoffPaymentStatus } from '../api/paymentHandoffApi';

export interface PaymentStatusCardProps {
  paymentStatus: HandoffPaymentStatus;
  paymentConfirmedAt: string | null;
  amountInPaise: number;
  planKind: PlanKind | undefined;
  onRefreshStatus: () => void;
  isRefreshingStatus: boolean;
  onTryAgain: () => void;
  isTryingAgain: boolean;
}

const BORDER_CLASS_BY_STATUS: Record<HandoffPaymentStatus, string> = {
  WAITING: 'border-border',
  PAID: 'border-green',
  NOT_COMPLETED: 'border-border',
};

// M4's payment status: waiting (server-confirmed only, "don't hand over yet"), paid with the
// confirmation time, or not completed, which never says "declined" and offers a new try.
export function PaymentStatusCard(props: PaymentStatusCardProps) {
  const { t } = useTranslation();
  const { selectedLanguage } = useLanguagePreference();
  const headingId = useId();
  const { paymentStatus, paymentConfirmedAt } = props;
  const paidDetails = {
    amount: formatRupeesFromPaise(props.amountInPaise),
    planName: t(`handoff.planNameInSentence.${props.planKind ?? 'STANDARD'}`),
  };
  const body =
    paymentStatus === 'PAID'
      ? paymentConfirmedAt === null
        ? t('handoff.status.PAID.bodyWithoutTime', paidDetails)
        : t('handoff.status.PAID.body', {
            ...paidDetails,
            time: formatShopTime(paymentConfirmedAt, selectedLanguage),
          })
      : t(`handoff.status.${paymentStatus}.body`);
  return (
    <section
      aria-labelledby={headingId}
      aria-live="polite"
      className={`flex flex-col gap-3 rounded-card border-2 bg-white p-6 shadow-card ${BORDER_CLASS_BY_STATUS[paymentStatus]}`}
    >
      <p className="text-label text-slate">{t('handoff.status.heading')}</p>
      <h2 id={headingId} className="text-title text-navy">
        {t(`handoff.status.${paymentStatus}.title`)}
      </h2>
      <p className="text-body text-deep-navy">{body}</p>
      {paymentStatus === 'WAITING' ? (
        <Button
          variant="secondary"
          onClick={props.onRefreshStatus}
          disabled={props.isRefreshingStatus}
        >
          {props.isRefreshingStatus
            ? t('handoff.status.refreshing')
            : t('handoff.status.WAITING.action')}
        </Button>
      ) : null}
      {paymentStatus === 'PAID' ? (
        <Link to={MERCHANT_PATHS.newEmiSale} className={getButtonClassName({ size: 'large' })}>
          {t('handoff.status.PAID.action')}
        </Link>
      ) : null}
      {paymentStatus === 'NOT_COMPLETED' ? (
        <Button size="large" onClick={props.onTryAgain} disabled={props.isTryingAgain}>
          {t('handoff.status.NOT_COMPLETED.action')}
        </Button>
      ) : null}
    </section>
  );
}
