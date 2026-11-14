import { render, screen } from '@testing-library/react';
import { encode } from 'uqr';
import { describe, expect, it } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { buildQrCodePath } from './buildQrCodePath';
import { QrPanel } from './QrPanel';

const CUSTOMER_URL = 'http://localhost:5174/s#token=example-token';

describe('buildQrCodePath', () => {
  it('draws one square for every dark module of the encoded QR code', () => {
    const qrCode = encode(CUSTOMER_URL, { ecc: 'M', border: 0 });
    const darkModuleCount = qrCode.data.flat().filter((isDark) => isDark).length;

    const qrCodePath = buildQrCodePath(CUSTOMER_URL);

    expect(qrCodePath.moduleCount).toBe(qrCode.size);
    expect(qrCodePath.pathData.match(/h1v1h-1z/g)?.length).toBe(darkModuleCount);
  });

  it('starts with the dark top-left finder module and differs for different text', () => {
    expect(buildQrCodePath('first').pathData.startsWith('M0 0h1v1h-1z')).toBe(true);
    expect(buildQrCodePath('first').pathData).not.toBe(buildQrCodePath('second').pathData);
  });
});

describe('QrPanel', () => {
  it('renders the QR code as a labelled image with a quiet zone and the caption', () => {
    render(
      <QrPanel
        value={CUSTOMER_URL}
        accessibleLabel="Session QR code 4821"
        caption="Opens on their phone. No app needed."
      />,
    );

    const image = screen.getByRole('img', { name: 'Session QR code 4821' });
    const moduleCount = buildQrCodePath(CUSTOMER_URL).moduleCount;

    expect(image.getAttribute('viewBox')).toBe(`-4 -4 ${moduleCount + 8} ${moduleCount + 8}`);
    expect(image.querySelector('path')?.getAttribute('fill')).toBe('currentColor');
    expect(screen.getByText('Opens on their phone. No app needed.')).toBeTruthy();
  });

  it('shows the title beside a smaller code in the inline layout', () => {
    render(
      <QrPanel
        value={CUSTOMER_URL}
        accessibleLabel="Session QR code"
        title="Ask the customer to scan"
        layout="inline"
      />,
    );

    expect(screen.getByText('Ask the customer to scan')).toBeTruthy();
    expect(screen.getByRole('img').getAttribute('class')).toContain('size-36');
  });

  it('renders no text block when neither title nor caption is given', () => {
    const { container } = render(<QrPanel value={CUSTOMER_URL} accessibleLabel="QR" />);

    expect(container.querySelectorAll('p')).toHaveLength(0);
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <QrPanel
        value={CUSTOMER_URL}
        accessibleLabel="Session QR code"
        title="Scan"
        caption="Code 4821"
      />,
    );

    await expectNoAccessibilityViolations(container);
  });
});
