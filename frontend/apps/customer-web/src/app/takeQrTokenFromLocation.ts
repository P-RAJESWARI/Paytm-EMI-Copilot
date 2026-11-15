/** The URL fragment key the merchant's QR uses: https://<customer app>/#t=<qr token>. */
const QR_TOKEN_FRAGMENT_KEY = 't';

/** The parts of window.location and window.history this needs, so tests can pass their own. */
export interface BrowserLocationAccess {
  location: Pick<Location, 'hash' | 'pathname' | 'search'>;
  history: Pick<History, 'replaceState' | 'state'>;
}

// Reads the QR token from the URL fragment once and removes the fragment from the address bar and
// history (frontend.md section 9), so the token lives only in memory and never in a shared link.
export function takeQrTokenFromLocation({
  location,
  history,
}: BrowserLocationAccess): string | undefined {
  if (location.hash === '') return undefined;
  const fragmentParameters = new URLSearchParams(location.hash.slice(1));
  history.replaceState(history.state, '', `${location.pathname}${location.search}`);
  const qrToken = fragmentParameters.get(QR_TOKEN_FRAGMENT_KEY)?.trim();
  return qrToken === undefined || qrToken === '' ? undefined : qrToken;
}
