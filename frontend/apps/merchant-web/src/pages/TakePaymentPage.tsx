import { useParams } from 'react-router';

import { TakePaymentContainer } from '../features/payment-handoff';

// M4 route (/sale/:saleId/handoff): take the payment on Paytm with the agreed plan.
export function TakePaymentPage() {
  const { saleId = '' } = useParams();
  return <TakePaymentContainer key={saleId} saleId={saleId} />;
}
