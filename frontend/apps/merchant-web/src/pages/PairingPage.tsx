import { Navigate } from 'react-router';

import { MERCHANT_PATHS } from '../app/merchantPaths';
import { BrandPanel, DevicePairingContainer } from '../features/device-pairing';
import { useMerchantSession } from '../shared/session/useMerchantSession';

// M1 route: the brand panel beside the pairing form; a paired tablet goes straight to New EMI sale.
export function PairingPage() {
  const { session } = useMerchantSession();
  if (session !== undefined) return <Navigate to={MERCHANT_PATHS.newEmiSale} replace />;
  return (
    <div className="flex min-h-screen flex-col bg-light-blue md:flex-row">
      <BrandPanel />
      <main className="flex flex-1 items-center justify-center p-6 md:p-12">
        <DevicePairingContainer />
      </main>
    </div>
  );
}
