import { encode } from 'uqr';

export interface QrCodePath {
  /** Modules per side, without the quiet zone. */
  moduleCount: number;
  /** One SVG path drawing every dark module as a 1 x 1 square. */
  pathData: string;
}

// Encodes the text as a QR code (medium error correction) and turns its dark modules into one SVG path.
export function buildQrCodePath(value: string): QrCodePath {
  const qrCode = encode(value, { ecc: 'M', border: 0 });
  const squares: string[] = [];
  qrCode.data.forEach((row, rowIndex) => {
    row.forEach((isDark, columnIndex) => {
      if (isDark) squares.push(`M${columnIndex} ${rowIndex}h1v1h-1z`);
    });
  });
  return { moduleCount: qrCode.size, pathData: squares.join('') };
}
