import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useRef, useState, type ReactNode } from 'react';

import {
  MerchantSessionContext,
  type MerchantSession,
  type MerchantSessionContextValue,
} from './merchantSessionContext';

export interface MerchantSessionProviderProps {
  children: ReactNode;
  /** Starts already paired; used by tests, the app always starts unpaired. */
  initialSession?: MerchantSession | undefined;
}

// Holds the merchant token in memory only (plan Q10): a reload means pairing again. Signing out
// also empties the server-data cache so nothing of the old session stays on screen.
export function MerchantSessionProvider({
  children,
  initialSession,
}: MerchantSessionProviderProps) {
  const queryClient = useQueryClient();
  const [session, setSession] = useState<MerchantSession | undefined>(initialSession);
  const sessionReference = useRef<MerchantSession | undefined>(initialSession);

  const signIn = useCallback((nextSession: MerchantSession) => {
    sessionReference.current = nextSession;
    setSession(nextSession);
  }, []);

  const signOut = useCallback(() => {
    if (sessionReference.current === undefined) return;
    sessionReference.current = undefined;
    setSession(undefined);
    queryClient.clear();
  }, [queryClient]);

  const getAccessToken = useCallback(() => sessionReference.current?.accessToken, []);

  const contextValue = useMemo<MerchantSessionContextValue>(
    () => ({ session, signIn, signOut, getAccessToken }),
    [session, signIn, signOut, getAccessToken],
  );
  return (
    <MerchantSessionContext.Provider value={contextValue}>
      {children}
    </MerchantSessionContext.Provider>
  );
}
