import { Navigate, type RouteObject } from 'react-router';

import { NewEmiSalePage } from '../pages/NewEmiSalePage';
import { PairingPage } from '../pages/PairingPage';
import { SalesReportPage } from '../pages/SalesReportPage';
import { ShowQrPage } from '../pages/ShowQrPage';
import { TakePaymentPage } from '../pages/TakePaymentPage';
import { MERCHANT_PATHS } from './merchantPaths';
import { RequireMerchantSession } from './RequireMerchantSession';
import { MerchantAppShell } from './shell/MerchantAppShell';

// The merchant app's routes: M1 is open; everything else needs a paired tablet.
export const MERCHANT_ROUTES: RouteObject[] = [
  { path: MERCHANT_PATHS.pairing, element: <PairingPage /> },
  {
    element: <RequireMerchantSession />,
    children: [
      {
        element: <MerchantAppShell />,
        children: [
          { path: MERCHANT_PATHS.newEmiSale, element: <NewEmiSalePage /> },
          { path: MERCHANT_PATHS.showQrPattern, element: <ShowQrPage /> },
          { path: MERCHANT_PATHS.takePaymentPattern, element: <TakePaymentPage /> },
          { path: MERCHANT_PATHS.salesReport, element: <SalesReportPage /> },
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to={MERCHANT_PATHS.newEmiSale} replace /> },
];
