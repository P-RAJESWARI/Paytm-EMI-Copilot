// Lists the string lines of a Tamil translation object that lack the "draft: needs native review"
// marker (frontend.md section 7). `tamilObjectName` is the exported constant holding the Tamil strings.
export function findTamilLinesWithoutDraftMarker(
  source: string,
  tamilObjectName: string,
): string[] {
  const tamilObjectStart = source.indexOf(`export const ${tamilObjectName}`);
  if (tamilObjectStart === -1) throw new Error(`${tamilObjectName} was not found in the source`);
  const tamilObjectEnd = source.indexOf('\n};', tamilObjectStart);
  return source
    .slice(tamilObjectStart, tamilObjectEnd === -1 ? undefined : tamilObjectEnd)
    .split('\n')
    .filter((line) => /:\s*['"`]/.test(line))
    .filter((line) => !line.includes('// draft: needs native review'));
}
