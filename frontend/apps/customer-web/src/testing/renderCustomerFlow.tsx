import { CustomerFlowScreens } from '../app/CustomerFlowScreens';
import {
  FixtureCustomerFlowApi,
  type CustomerFlowApi,
  type CustomerFlowState,
} from '../features/customer-flow';
import { renderCustomerApp } from './renderCustomerApp';

export interface RenderCustomerFlowOptions {
  customerFlowApi?: CustomerFlowApi | undefined;
  initialFlowState?: CustomerFlowState | undefined;
}

// Renders the whole customer flow (session gate plus screens) against the fixture by default.
export function renderCustomerFlow({
  customerFlowApi,
  initialFlowState,
}: RenderCustomerFlowOptions = {}) {
  return renderCustomerApp({
    children: <CustomerFlowScreens />,
    customerFlowApi,
    initialFlowState,
  });
}

export interface PreparedFixtureOptions {
  monthlyBudgetInPaise?: number | undefined;
  hasCustomerConsentedToComfortCheck?: boolean | undefined;
}

// Builds a fixture whose server side is already past C2 and C3, as if the customer had answered
// them; the app's own QR exchange then opens a new session on the same server state.
export async function prepareFixtureWithAnswers({
  monthlyBudgetInPaise = 300000,
  hasCustomerConsentedToComfortCheck = true,
}: PreparedFixtureOptions = {}): Promise<FixtureCustomerFlowApi> {
  const fixture = new FixtureCustomerFlowApi();
  await fixture.startSession('preparation-qr-token');
  await fixture.confirmBudget(monthlyBudgetInPaise);
  await fixture.answerComfortCheck(hasCustomerConsentedToComfortCheck);
  return fixture;
}
