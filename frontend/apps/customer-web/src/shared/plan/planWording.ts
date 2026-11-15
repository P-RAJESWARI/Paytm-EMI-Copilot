import type { BandChipTone } from '@emi-copilot/ui-kit';

import type { ComfortBand, EmiType } from '../../features/customer-flow';

const PLAN_NAME_KEY_BY_EMI_TYPE: Record<EmiType, string> = {
  NO_COST: 'plan.name.NO_COST',
  STANDARD: 'plan.name.STANDARD',
};

const BAND_CHIP_TONE_BY_BAND: Record<ComfortBand, BandChipTone> = {
  COMFORTABLE: 'comfortable',
  STRETCHING: 'stretching',
  RISKY: 'risky',
};

// Gives the translation key of a plan's plain name ("No-cost EMI" or "EMI") from its EMI type,
// as Layer 2's merchant screens do (ADR 0022 decision 5); the lender line says who funds it.
export function getPlanNameKey(emiType: EmiType): string {
  return PLAN_NAME_KEY_BY_EMI_TYPE[emiType];
}

// Gives the ui-kit chip tone of a comfort band the API classified (the UI never classifies).
export function getBandChipTone(band: ComfortBand): BandChipTone {
  return BAND_CHIP_TONE_BY_BAND[band];
}
