import { useMemo } from 'react';

import { buildQrCodePath } from './buildQrCodePath';

/** `stacked` puts the large QR above its text (M3); `inline` puts a small QR beside it. */
export type QrPanelLayout = 'stacked' | 'inline';

/**
 * Size of the stacked code: `standard` is always 300 px; `fitsPhone` is 240 px below the md
 * breakpoint so the card fits a 360 px phone (M3 phone), and 300 px from md up.
 */
export type QrPanelStackedSize = 'standard' | 'fitsPhone';

export interface QrPanelProps {
  /** The text the QR encodes, normally the customer URL. */
  value: string;
  /** Translated description of the image, for example "Session QR code 4821". */
  accessibleLabel: string;
  title?: string | undefined;
  caption?: string | undefined;
  layout?: QrPanelLayout | undefined;
  stackedSize?: QrPanelStackedSize | undefined;
}

const STACKED_SIZE_CLASS_NAMES: Record<QrPanelStackedSize, string> = {
  standard: 'size-75',
  fitsPhone: 'size-60 md:size-75',
};

/** The QR standard asks for a quiet zone of four modules around the code. */
const QUIET_ZONE_MODULES = 4;

// A white card holding an SVG QR code drawn from `value`, with an optional title and caption.
export function QrPanel({
  value,
  accessibleLabel,
  title,
  caption,
  layout = 'stacked',
  stackedSize = 'standard',
}: QrPanelProps) {
  const qrCodePath = useMemo(() => buildQrCodePath(value), [value]);
  const viewBoxSize = qrCodePath.moduleCount + QUIET_ZONE_MODULES * 2;
  const isStacked = layout === 'stacked';
  return (
    <div
      className={`flex gap-4 rounded-card bg-white p-6 shadow-card ${
        isStacked ? 'flex-col items-center text-center' : 'flex-row items-center'
      }`}
    >
      <svg
        role="img"
        aria-label={accessibleLabel}
        viewBox={`${-QUIET_ZONE_MODULES} ${-QUIET_ZONE_MODULES} ${viewBoxSize} ${viewBoxSize}`}
        shapeRendering="crispEdges"
        className={`shrink-0 rounded-input border border-border bg-white text-deep-navy ${
          isStacked ? STACKED_SIZE_CLASS_NAMES[stackedSize] : 'size-36'
        }`}
      >
        <path d={qrCodePath.pathData} fill="currentColor" />
      </svg>
      {title === undefined && caption === undefined ? null : (
        <div className="flex flex-col gap-2">
          {title === undefined ? null : <p className="text-lead font-bold text-navy">{title}</p>}
          {caption === undefined ? null : (
            <p className="text-label font-normal text-slate">{caption}</p>
          )}
        </div>
      )}
    </div>
  );
}
