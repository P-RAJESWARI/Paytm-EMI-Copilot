import { useLanguagePreference } from '@emi-copilot/shared-i18n';

import { useCustomerFlow } from '../../customer-flow';
import { WelcomeScreen } from '../components/WelcomeScreen';

// Connects C1 to the open session, the device's language preference and the flow's first step.
export function WelcomeContainer() {
  const { session, dispatch } = useCustomerFlow();
  const { selectedLanguage, selectLanguage } = useLanguagePreference();
  return (
    <WelcomeScreen
      shopName={session.shopName}
      productName={session.productName}
      priceInPaise={session.priceInPaise}
      selectedLanguage={selectedLanguage}
      onSelectLanguage={selectLanguage}
      onStart={() => {
        dispatch({ type: 'flowStarted' });
      }}
    />
  );
}
