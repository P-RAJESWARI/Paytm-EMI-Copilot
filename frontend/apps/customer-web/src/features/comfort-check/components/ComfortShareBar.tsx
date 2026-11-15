import { useTranslation } from 'react-i18next';

import type { ComfortBand } from '../../customer-flow';
import { formatPercentFromBasisPoints } from '../../../shared/formatting/formatPercentFromBasisPoints';

export interface ComfortShareBarProps {
  band: ComfortBand;
  existingEmisShareInBasisPoints: number;
  planShareInBasisPoints: number;
  comfortRatioInBasisPoints: number;
}

const BASIS_POINTS_PER_PERCENT = 100;
/** The marks the C5 mockup draws under the bar; labels only, the band comes from the API. */
const BAR_MARKS_IN_PERCENT = [0, 35, 50, 100] as const;

const PLAN_SEGMENT_CLASS_NAME_BY_BAND: Record<ComfortBand, string> = {
  COMFORTABLE: 'bg-green',
  STRETCHING: 'bg-orange',
  RISKY: 'bg-red',
};

// Gives a CSS width for a share of the month, never wider than the bar.
function toBarWidth(shareInBasisPoints: number): string {
  return `${Math.min(shareInBasisPoints / BASIS_POINTS_PER_PERCENT, 100)}%`;
}

// The C5 bar: current EMIs, then this plan, on a 0 to 100% scale with marks at 35% and 50%. It is
// one image with a text label; the numbers are also written out beside it.
export function ComfortShareBar({
  band,
  existingEmisShareInBasisPoints,
  planShareInBasisPoints,
  comfortRatioInBasisPoints,
}: ComfortShareBarProps) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-1">
      <div
        role="img"
        aria-label={t('comfortDetail.barLabel', {
          current: formatPercentFromBasisPoints(existingEmisShareInBasisPoints),
          total: formatPercentFromBasisPoints(comfortRatioInBasisPoints),
        })}
        className="flex h-4 w-full overflow-hidden rounded-pill bg-grey-tint"
      >
        <span
          className="h-full bg-steel-blue"
          style={{ width: toBarWidth(existingEmisShareInBasisPoints) }}
        />
        <span
          className={`h-full ${PLAN_SEGMENT_CLASS_NAME_BY_BAND[band]}`}
          style={{ width: toBarWidth(planShareInBasisPoints) }}
        />
      </div>
      <div aria-hidden="true" className="relative h-5 text-caption text-slate">
        {BAR_MARKS_IN_PERCENT.map((markInPercent) => (
          <span
            key={markInPercent}
            className="absolute -translate-x-1/2 first:translate-x-0 last:-translate-x-full"
            style={{ left: `${markInPercent}%` }}
          >
            {`${markInPercent}%`}
          </span>
        ))}
      </div>
    </div>
  );
}
