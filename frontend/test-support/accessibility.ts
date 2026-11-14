import axe from 'axe-core';

// Runs axe on a rendered element and fails the test with a readable list of any violations.
export async function expectNoAccessibilityViolations(element: Element): Promise<void> {
  const results = await axe.run(element);
  if (results.violations.length === 0) {
    return;
  }
  const violationSummaries = results.violations.map(
    (violation) =>
      `${violation.id}: ${violation.help} (${violation.nodes.map((node) => node.target.join(' ')).join(', ')})`,
  );
  throw new Error(`Accessibility violations:\n${violationSummaries.join('\n')}`);
}
