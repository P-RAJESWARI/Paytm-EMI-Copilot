import { Outlet } from 'react-router';

import { useLiveSaleStatus } from '../../features/live-sale-status';
import { useMerchantProfile } from '../../shared/session/useMerchantProfile';
import { MerchantSidebar } from './MerchantSidebar';

// Container for every paired tablet screen: reads the shop card, keeps sale statuses live while
// any tab is open, and lays out sidebar and page.
export function MerchantAppShell() {
  const { data: merchantProfile } = useMerchantProfile();
  useLiveSaleStatus();
  return (
    <div className="flex min-h-screen flex-col bg-light-blue md:flex-row">
      <MerchantSidebar
        shopName={merchantProfile?.shopName}
        deviceLabel={merchantProfile?.deviceLabel}
      />
      <main className="flex min-w-0 flex-1 flex-col gap-4 p-4 md:px-8 md:py-7">
        <Outlet />
      </main>
    </div>
  );
}
