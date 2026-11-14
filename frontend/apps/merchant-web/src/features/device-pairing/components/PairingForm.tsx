import { Button, PinInput } from '@emi-copilot/ui-kit';
import { useEffect, useId } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';

import {
  PAIRING_PIN_DIGIT_COUNT,
  validatePairingPin,
  validateShopId,
  type PairingFormValues,
} from '../model/pairingForm';

export interface PairingFormProps {
  onPair: (values: PairingFormValues) => void;
  isPairing: boolean;
  /** The translated, calm message of the last failed attempt. */
  problemMessage?: string | undefined;
  /** Changes after each failed attempt, so the PIN boxes empty for a fresh try. */
  failedAttemptCount: number;
}

// The M1 form: shop ID, six PIN boxes and "Pair device", with field checks before sending.
export function PairingForm({
  onPair,
  isPairing,
  problemMessage,
  failedAttemptCount,
}: PairingFormProps) {
  const { t } = useTranslation();
  const shopIdInputId = useId();
  const shopIdErrorId = useId();
  const { control, register, handleSubmit, formState, setValue } = useForm<PairingFormValues>({
    defaultValues: { shopId: '', pin: '' },
  });
  useEffect(() => {
    if (failedAttemptCount > 0) setValue('pin', '');
  }, [failedAttemptCount, setValue]);
  const shopIdError = formState.errors.shopId?.message;
  return (
    <form
      noValidate
      className="flex w-full max-w-100 flex-col gap-6"
      onSubmit={(event) => {
        void handleSubmit((values) => {
          onPair({ shopId: values.shopId.trim(), pin: values.pin });
        })(event);
      }}
    >
      <div className="flex flex-col gap-2">
        <h1 className="text-heading text-navy">{t('pairing.title')}</h1>
        <p className="text-body text-slate">{t('pairing.description')}</p>
      </div>
      <div className="flex flex-col gap-2">
        <label htmlFor={shopIdInputId} className="text-body font-semibold">
          {t('pairing.shopIdLabel')}
        </label>
        <input
          id={shopIdInputId}
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          aria-invalid={shopIdError !== undefined}
          aria-describedby={shopIdError === undefined ? undefined : shopIdErrorId}
          className="min-h-touch-target-primary rounded-input border-2 border-border bg-white px-4 text-lead font-semibold text-deep-navy"
          {...register('shopId', { validate: validateShopId })}
        />
        {shopIdError === undefined ? null : (
          <p id={shopIdErrorId} className="text-label font-normal text-risky-text">
            {t(shopIdError)}
          </p>
        )}
      </div>
      <Controller
        control={control}
        name="pin"
        rules={{ validate: validatePairingPin }}
        render={({ field, fieldState }) => (
          <PinInput
            label={t('pairing.pinLabel')}
            digitLabel={(position, digitCount) =>
              t('pairing.pinDigitLabel', { position, digitCount })
            }
            digitCount={PAIRING_PIN_DIGIT_COUNT}
            value={field.value}
            onChange={field.onChange}
            errorMessage={
              fieldState.error?.message === undefined ? undefined : t(fieldState.error.message)
            }
            isDisabled={isPairing}
          />
        )}
      />
      {problemMessage === undefined ? null : (
        <p role="alert" className="rounded-input bg-grey-tint p-3 text-body text-deep-navy">
          {problemMessage}
        </p>
      )}
      <Button type="submit" size="large" isFullWidth disabled={isPairing}>
        {isPairing ? t('pairing.submitting') : t('pairing.submit')}
      </Button>
      <p className="text-label font-normal text-slate">{t('pairing.noPinNote')}</p>
    </form>
  );
}
