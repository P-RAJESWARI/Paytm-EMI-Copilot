import { BandChip } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

import type { PlanComfortResponse } from '../../features/customer-flow';
import { formatPercentFromBasisPoints } from '../formatting/formatPercentFromBasisPoints';
import { getBandChipTone } from './planWording';

export interface PlanBandChipProps {
  comfort: PlanComfortResponse;
  /** Adds the comfort ratio after the band word, for example "Stretching 38.9%". */
  isShowingRatio?: boolean | undefined;
}

// The band of one plan as icon and translated word, with the ratio when asked; all from the API.
export function PlanBandChip({ comfort, isShowingRatio = false }: PlanBandChipProps) {
  const { t } = useTranslation();
  return (
    <BandChip
      tone={getBandChipTone(comfort.band)}
      label={t(`comfortBand.${comfort.band}`)}
      detail={
        isShowingRatio ? formatPercentFromBasisPoints(comfort.comfortRatioInBasisPoints) : undefined
      }
    />
  );
}
