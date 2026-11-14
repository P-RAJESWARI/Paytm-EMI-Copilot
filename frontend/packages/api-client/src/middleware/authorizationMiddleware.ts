import type { Middleware } from 'openapi-fetch';

// Adds "Authorization: Bearer <token>" when the app currently holds a merchant token. The token
// is read through the getter on every request and never kept, logged or stored by this package.
export function createAuthorizationMiddleware(
  getAccessToken: () => string | undefined,
): Middleware {
  return {
    onRequest({ request }) {
      const accessToken = getAccessToken();
      if (
        accessToken !== undefined &&
        accessToken !== '' &&
        !request.headers.has('Authorization')
      ) {
        request.headers.set('Authorization', `Bearer ${accessToken}`);
      }
      return request;
    },
  };
}
