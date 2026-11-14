import type { components } from './generated/backendApiSchema';

/** An RFC 7807 error body; `code` is the stable value the app maps to translated text. */
export type ProblemDetails = components['schemas']['ProblemDetailsResponse'];

// Gives the stable problem code of an error body, or undefined when the body is not a problem.
export function readProblemCode(errorBody: unknown): string | undefined {
  if (typeof errorBody !== 'object' || errorBody === null || !('code' in errorBody)) {
    return undefined;
  }
  return typeof errorBody.code === 'string' ? errorBody.code : undefined;
}
