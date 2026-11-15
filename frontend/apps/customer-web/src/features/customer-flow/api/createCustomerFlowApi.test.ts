import { describe, expect, it } from 'vitest';

import { createCustomerFlowApi, readCustomerFlowApiMode } from './createCustomerFlowApi';
import { FixtureCustomerFlowApi } from './FixtureCustomerFlowApi';
import { HttpCustomerFlowApi } from './HttpCustomerFlowApi';

const FACTORY_OPTIONS = {
  baseUrl: 'http://customer.test',
  fetchFunction: () => Promise.resolve(new Response('{}')),
};

describe('createCustomerFlowApi', () => {
  it('uses the fixture only for the exact value "fixture"; everything else talks HTTP', () => {
    expect(readCustomerFlowApiMode('fixture')).toBe('fixture');
    expect(readCustomerFlowApiMode(undefined)).toBe('http');
    expect(readCustomerFlowApiMode('Fixture')).toBe('http');
    expect(readCustomerFlowApiMode('http')).toBe('http');
  });

  it('builds the implementation for the mode', () => {
    expect(createCustomerFlowApi({ mode: 'fixture', ...FACTORY_OPTIONS })).toBeInstanceOf(
      FixtureCustomerFlowApi,
    );
    expect(createCustomerFlowApi({ mode: 'http', ...FACTORY_OPTIONS })).toBeInstanceOf(
      HttpCustomerFlowApi,
    );
  });
});
