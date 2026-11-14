import { readProblemCode, type BackendApiClient } from '@emi-copilot/api-client';

import { MERCHANT_AUTHENTICATION_REQUIRED_CODE } from './merchantApiError';

type BackendApiMiddleware = Parameters<BackendApiClient['use']>[0];

// Reads a JSON body without consuming the original response; a non-JSON body gives undefined.
export async function readJsonBodyOfCopy(response: Response): Promise<unknown> {
  try {
    return await response.clone().json();
  } catch (error) {
    if (error instanceof SyntaxError) return undefined;
    throw error;
  }
}

// Calls onAuthenticationLost when any answer is 401 MERCHANT_AUTHENTICATION_REQUIRED, so an
// expired or revoked token sends the tablet back to pairing (a wrong PIN has another code).
export function createSignOutOnAuthenticationLostMiddleware(
  onAuthenticationLost: () => void,
): BackendApiMiddleware {
  return {
    async onResponse({ response }) {
      if (response.status !== 401) return undefined;
      const problemCode = readProblemCode(await readJsonBodyOfCopy(response));
      if (problemCode === MERCHANT_AUTHENTICATION_REQUIRED_CODE) onAuthenticationLost();
      return undefined;
    },
  };
}
