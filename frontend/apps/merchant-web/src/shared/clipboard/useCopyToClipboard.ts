import { useCallback, useState } from 'react';

/** `copied` after a successful copy; `unavailable` when this browser cannot copy for us. */
export type CopyState = 'idle' | 'copied' | 'unavailable';

// Gives the Clipboard API, or undefined where the browser leaves it out (it is secure-context
// only, so a tablet opening the app over plain http on the shop network has none).
function findClipboard(): Clipboard | undefined {
  return 'clipboard' in navigator ? navigator.clipboard : undefined;
}

// True for the refusals a browser gives when copying is blocked or unsupported.
function isClipboardRefusal(error: unknown): boolean {
  return error instanceof DOMException || error instanceof TypeError;
}

// Copies text with the Clipboard API and says whether it worked, so the screen can show a calm
// "Copied" or the text to select by hand (plain http on a shop network has no clipboard).
export function useCopyToClipboard() {
  const [copyState, setCopyState] = useState<CopyState>('idle');
  const copyText = useCallback(async (text: string) => {
    const clipboard = findClipboard();
    if (clipboard === undefined) {
      setCopyState('unavailable');
      return;
    }
    try {
      await clipboard.writeText(text);
      setCopyState('copied');
    } catch (error) {
      if (!isClipboardRefusal(error)) throw error;
      setCopyState('unavailable');
    }
  }, []);
  return { copyState, copyText };
}
