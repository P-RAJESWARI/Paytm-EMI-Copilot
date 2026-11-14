// Runs axe in the real browser, where colour contrast can be measured (jsdom cannot), and fails
// the test with a readable list of every violation on the page.
import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

// Runs every rule axe enables by default (WCAG 2 A and AA, colour contrast and best practices).
// A soft check: the test goes on, so one run lists the violations of every screen it visits.
export async function expectNoAccessibilityViolations(page: Page, screenName: string) {
  await test.step(`${screenName} has no accessibility violations`, async () => {
    const results = await new AxeBuilder({ page }).analyze();
    const violationSummaries = results.violations.map(
      (violation) =>
        `${violation.id}: ${violation.help} (${violation.nodes
          .map((node) => `${node.target.join(' ')}${describeFailure(node.failureSummary)}`)
          .join('; ')})`,
    );
    expect.soft(violationSummaries, `Accessibility violations on ${screenName}`).toEqual([]);
  });
}

// Keeps the first line of axe's failure summary, which carries the measured contrast ratio.
function describeFailure(failureSummary: string | undefined): string {
  const detail = failureSummary?.split('\n')[1]?.trim();
  return detail === undefined ? '' : ` -> ${detail}`;
}
