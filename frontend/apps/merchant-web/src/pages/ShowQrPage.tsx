import { useParams } from 'react-router';

import { ShowQrContainer } from '../features/counter-sale';

// M3 route (/sale/:saleId/qr): one sale's QR code and live status, tablet and phone.
export function ShowQrPage() {
  const { saleId = '' } = useParams();
  return <ShowQrContainer key={saleId} saleId={saleId} />;
}
