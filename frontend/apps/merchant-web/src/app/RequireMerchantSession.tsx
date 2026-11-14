import { Navigate, Outlet } from 'react-router';

import { useMerchantSession } from '../shared/session/useMerchantSession';
import { MERCHANT_PATHS } from './merchantPaths';

// Lets a route render only on a paired tablet; otherwise (or after the token is lost) it goes to M1.
export function RequireMerchantSession() {
  const { session } = useMerchantSession();
  if (session === undefined) return <Navigate to={MERCHANT_PATHS.pairing} replace />;
  return <Outlet />;
}
