import { Navigate, type RouteObject } from 'react-router';

import { NewEmiSalePage } from '../pages/NewEmiSalePage';
import { PairingPage } from '../pages/PairingPage';
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
          { path: MERCHANT_PATHS.salesReport, element: null },
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to={MERCHANT_PATHS.newEmiSale} replace /> },
];
