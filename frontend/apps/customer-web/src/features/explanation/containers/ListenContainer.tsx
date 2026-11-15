import { ListenControl } from '../components/ListenControl';
import { useAudioPlayback } from '../hooks/useAudioPlayback';

export interface ListenContainerProps {
  explanationId: string;
}

// Connects C7's Listen control to the spoken explanation; renders nothing once audio failed.
export function ListenContainer({ explanationId }: ListenContainerProps) {
  const playback = useAudioPlayback(explanationId);
  if (playback.status === 'unavailable') return null;
  return <ListenControl status={playback.status} onTogglePlayback={playback.togglePlayback} />;
}
