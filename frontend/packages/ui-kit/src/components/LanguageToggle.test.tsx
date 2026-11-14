import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { LanguageToggle } from './LanguageToggle';

const LANGUAGE_OPTIONS = [
  { language: 'en', label: 'EN' },
  { language: 'ta', label: 'தமிழ்' },
] as const;

describe('LanguageToggle', () => {
  it('renders a labelled group with the selected language pressed', () => {
    render(
      <LanguageToggle
        accessibleLabel="Language"
        options={LANGUAGE_OPTIONS}
        selectedLanguage="ta"
        onSelectLanguage={vi.fn()}
      />,
    );

    expect(screen.getByRole('group', { name: 'Language' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'தமிழ்' }).getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByRole('button', { name: 'EN' }).getAttribute('aria-pressed')).toBe('false');
    expect(screen.getByRole('button', { name: 'தமிழ்' }).getAttribute('lang')).toBe('ta');
  });

  it('reports the chosen language', async () => {
    const handleSelectLanguage = vi.fn();
    render(
      <LanguageToggle
        accessibleLabel="Language"
        options={LANGUAGE_OPTIONS}
        selectedLanguage="en"
        onSelectLanguage={handleSelectLanguage}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: 'தமிழ்' }));

    expect(handleSelectLanguage).toHaveBeenCalledWith('ta');
  });

  it('uses white selected buttons on the dark surface, at least 48 px tall', () => {
    render(
      <LanguageToggle
        accessibleLabel="Language"
        options={LANGUAGE_OPTIONS}
        selectedLanguage="en"
        onSelectLanguage={vi.fn()}
        surface="dark"
      />,
    );

    const selectedButton = screen.getByRole('button', { name: 'EN' });

    expect(selectedButton.className).toContain('bg-white');
    expect(selectedButton.className).toContain('min-h-touch-target');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <LanguageToggle
        accessibleLabel="Language"
        options={LANGUAGE_OPTIONS}
        selectedLanguage="en"
        onSelectLanguage={vi.fn()}
      />,
    );

    await expectNoAccessibilityViolations(container);
  });
});
