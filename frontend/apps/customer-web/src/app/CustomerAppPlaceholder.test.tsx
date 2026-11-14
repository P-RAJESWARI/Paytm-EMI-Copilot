import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { I18nextProvider } from 'react-i18next';
import { afterEach, describe, expect, it } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { initializeCustomerI18n } from '../i18n/initializeCustomerI18n';
import { CustomerAppPlaceholder } from './CustomerAppPlaceholder';

// Renders the placeholder with fresh translations.
function renderPlaceholder() {
  return render(
    <I18nextProvider i18n={initializeCustomerI18n()}>
      <CustomerAppPlaceholder />
    </I18nextProvider>,
  );
}

afterEach(() => {
  window.localStorage.clear();
});

describe('customer app placeholder', () => {
  it('renders through i18n and switches to Tamil', async () => {
    renderPlaceholder();
    expect(screen.getByText('Buy on EMI knowing every cost')).toBeTruthy();

    await userEvent.click(screen.getByRole('button', { name: 'தமிழ்' }));

    expect(screen.getByText('எல்லா செலவும் தெரிந்து EMI-யில் வாங்குங்கள்')).toBeTruthy();
  });

  it('has no accessibility violations', async () => {
    const { container } = renderPlaceholder();

    await expectNoAccessibilityViolations(container);
  });
});
