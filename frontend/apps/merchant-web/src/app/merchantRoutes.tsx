import type { RouteObject } from 'react-router';

import { AppShellPlaceholderPage } from '../pages/AppShellPlaceholderPage';

// The merchant app's routes; step 2.6 replaces the placeholder with pairing, sale and report pages.
export const MERCHANT_ROUTES: RouteObject[] = [{ path: '*', element: <AppShellPlaceholderPage /> }];
