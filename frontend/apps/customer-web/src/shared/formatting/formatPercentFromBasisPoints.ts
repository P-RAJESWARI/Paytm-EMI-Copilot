const BASIS_POINTS_PER_TENTH_OF_A_PERCENT = 10;
const TENTHS_PER_PERCENT = 10;

// Gives "38.9%" for 3889 basis points: display only, one decimal, half-up, trailing ".0" kept off
// ("40%" for 4000). The ratio itself always comes from the API (api-conventions.md section 2).
export function formatPercentFromBasisPoints(basisPoints: number): string {
  if (!Number.isSafeInteger(basisPoints) || basisPoints < 0) {
    throw new RangeError('Basis points must be a non-negative safe integer.');
  }
  const leftoverBasisPoints = basisPoints % BASIS_POINTS_PER_TENTH_OF_A_PERCENT;
  const tenthsOfAPercent =
    (basisPoints - leftoverBasisPoints) / BASIS_POINTS_PER_TENTH_OF_A_PERCENT +
    (leftoverBasisPoints >= BASIS_POINTS_PER_TENTH_OF_A_PERCENT / 2 ? 1 : 0);
  const wholePercent = Math.floor(tenthsOfAPercent / TENTHS_PER_PERCENT);
  const leftoverTenths = tenthsOfAPercent % TENTHS_PER_PERCENT;
  return leftoverTenths === 0 ? `${wholePercent}%` : `${wholePercent}.${leftoverTenths}%`;
}
