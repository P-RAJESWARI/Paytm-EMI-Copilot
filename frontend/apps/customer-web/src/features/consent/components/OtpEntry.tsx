import { Button, PinInput } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

import type { OtpChallenge } from '../../customer-flow';
import type { OtpProblem } from '../hooks/useOtpChallenge';
import { formatCountdown } from '../model/formatCountdown';

export interface OtpEntryProps {
  otpChallenge: OtpChallenge | undefined;
  otpDigits: string;
  otpProblem: OtpProblem | undefined;
  secondsUntilResend: number;
  isRequestingOtp: boolean;
  /** A calm, translated message when the OTP could not be sent. */
  requestErrorMessage: string | undefined;
  onChangeOtpDigits: (digits: string) => void;
  onRequestOtp: () => void;
}

// C9's OTP block: "Send OTP" first, then six digit boxes, a calm message for a wrong or expired
// OTP (no lockout words), and either the resend wait or "Send a new OTP".
export function OtpEntry(props: OtpEntryProps) {
  const { t } = useTranslation();
  const canAskForOtp = props.secondsUntilResend === 0 && !props.isRequestingOtp;
  const problemMessage =
    props.otpProblem === undefined
      ? undefined
      : props.otpProblem.kind === 'expired'
        ? t('consent.expiredOtp')
        : props.otpProblem.attemptsRemaining === undefined
          ? t('consent.wrongOtp')
          : t('consent.wrongOtpWithTries', { count: props.otpProblem.attemptsRemaining });
  return (
    <section className="flex flex-col gap-3 rounded-card bg-white p-4">
      {props.otpChallenge === undefined ? (
        <p className="text-body">{t('consent.otpIntro')}</p>
      ) : (
        <PinInput
          label={t('consent.otpLabel', { lastTwoDigits: props.otpChallenge.phoneLastTwoDigits })}
          digitLabel={(position, count) => t('consent.otpDigit', { position, count })}
          value={props.otpDigits}
          onChange={props.onChangeOtpDigits}
          isMasked={false}
          errorMessage={problemMessage}
        />
      )}
      {props.secondsUntilResend > 0 ? (
        <p className="text-label font-normal text-slate">
          {t('consent.resendIn', { time: formatCountdown(props.secondsUntilResend) })}
        </p>
      ) : null}
      {props.otpChallenge === undefined || props.secondsUntilResend === 0 ? (
        <Button variant="secondary" onClick={props.onRequestOtp} disabled={!canAskForOtp}>
          {props.otpChallenge === undefined ? t('consent.sendOtp') : t('consent.resend')}
        </Button>
      ) : null}
      {props.requestErrorMessage === undefined ? null : (
        <p role="alert" className="text-body text-deep-navy">
          {props.requestErrorMessage}
        </p>
      )}
    </section>
  );
}
