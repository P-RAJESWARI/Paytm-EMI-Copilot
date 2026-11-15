import { act, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { CustomerApiError } from '../../customer-flow';
import {
  buildFixtureExplanation,
  FIXTURE_NO_COST_PLAN,
} from '../../customer-flow/api/fixtureCustomerFlowData';
import { DESIGN_PLAN_ANSWERS } from '../../../testing/customerFlowTestData';
import { prepareFixtureWithAnswers, renderCustomerFlow } from '../../../testing/renderCustomerFlow';

const EXPLANATION_STEP = { step: 'explanation', answers: DESIGN_PLAN_ANSWERS } as const;
const AUDIO_OBJECT_URL = 'blob:explanation-audio';

let playAudio: Mock<() => Promise<void>>;
let pauseAudio: Mock<() => void>;
let revokeObjectUrl: Mock<(objectUrl: string) => void>;

beforeEach(() => {
  playAudio = vi.fn(() => Promise.resolve());
  pauseAudio = vi.fn<() => void>();
  revokeObjectUrl = vi.fn<(objectUrl: string) => void>();
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockImplementation(playAudio);
  vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(pauseAudio);
  Object.assign(URL, { createObjectURL: () => AUDIO_OBJECT_URL, revokeObjectURL: revokeObjectUrl });
});

afterEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
});

describe('C7 explanation: audio and notes', () => {
  it('plays the spoken explanation, then pauses it, and releases the audio on leaving', async () => {
    const customerFlowApi = await prepareFixtureWithAnswers();
    const synthesise = vi.spyOn(customerFlowApi, 'synthesiseExplanation');
    const { container, unmount } = renderCustomerFlow({
      customerFlowApi,
      initialFlowState: EXPLANATION_STEP,
    });

    await userEvent.click(await screen.findByRole('button', { name: 'Listen to this' }));

    expect(await screen.findByRole('button', { name: 'Playing. Tap to pause.' })).toBeTruthy();
    expect(synthesise).toHaveBeenCalledWith('fixture-explanation-1');
    expect(screen.getByText('₹3,667 a month')).toBeTruthy();
    await expectNoAccessibilityViolations(container);
    await userEvent.click(screen.getByRole('button', { name: 'Playing. Tap to pause.' }));
    expect(await screen.findByRole('button', { name: 'Listen to this' })).toBeTruthy();
    expect(pauseAudio).toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: 'Listen to this' }));
    expect(await screen.findByRole('button', { name: 'Playing. Tap to pause.' })).toBeTruthy();
    expect(synthesise).toHaveBeenCalledTimes(1);

    unmount();
    expect(revokeObjectUrl).toHaveBeenCalledWith(AUDIO_OBJECT_URL);
  });

  it('releases the audio and offers Listen again when playback ends', async () => {
    const playSpy = vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined);
    const customerFlowApi = await prepareFixtureWithAnswers();
    renderCustomerFlow({ customerFlowApi, initialFlowState: EXPLANATION_STEP });
    await userEvent.click(await screen.findByRole('button', { name: 'Listen to this' }));
    await screen.findByRole('button', { name: 'Playing. Tap to pause.' });

    act(() => {
      const playedElement: unknown = playSpy.mock.contexts[0];
      if (playedElement instanceof HTMLMediaElement)
        playedElement.dispatchEvent(new Event('ended'));
    });

    expect(await screen.findByRole('button', { name: 'Listen to this' })).toBeTruthy();
    expect(revokeObjectUrl).toHaveBeenCalledWith(AUDIO_OBJECT_URL);
  });

  it('hides Listen quietly when the audio cannot be made: no banner, no alert', async () => {
    const customerFlowApi = await prepareFixtureWithAnswers();
    vi.spyOn(customerFlowApi, 'synthesiseExplanation').mockRejectedValue(
      new CustomerApiError(502, 'SPEECH_UNAVAILABLE', { hasProblemBody: true }),
    );
    renderCustomerFlow({ customerFlowApi, initialFlowState: EXPLANATION_STEP });

    await userEvent.click(await screen.findByRole('button', { name: 'Listen to this' }));

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /Listen to this|Getting the audio/ })).toBeNull();
    });
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.getByText('₹3,667 a month')).toBeTruthy();
  });

  it('hides Listen when the phone refuses to play the audio', async () => {
    playAudio.mockRejectedValue(new DOMException('Not allowed', 'NotAllowedError'));
    const customerFlowApi = await prepareFixtureWithAnswers();
    renderCustomerFlow({ customerFlowApi, initialFlowState: EXPLANATION_STEP });

    await userEvent.click(await screen.findByRole('button', { name: 'Listen to this' }));

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /Listen to this/ })).toBeNull();
    });
    expect(revokeObjectUrl).toHaveBeenCalledWith(AUDIO_OBJECT_URL);
  });

  it('shows the standard note and no Listen for template text without an id', async () => {
    const customerFlowApi = await prepareFixtureWithAnswers();
    vi.spyOn(customerFlowApi, 'explainPlan').mockResolvedValue({
      ...buildFixtureExplanation(FIXTURE_NO_COST_PLAN, 'en'),
      source: 'TEMPLATE',
      explanationId: '',
    });
    const { container } = renderCustomerFlow({
      customerFlowApi,
      initialFlowState: EXPLANATION_STEP,
    });

    expect(await screen.findByText('Showing the standard plan details.')).toBeTruthy();
    expect(screen.queryByText(/Written by AI/)).toBeNull();
    expect(screen.queryByRole('button', { name: 'Listen to this' })).toBeNull();
    await expectNoAccessibilityViolations(container);
  });

  it('opens the optional teach-back check from "Check my understanding"', async () => {
    const customerFlowApi = await prepareFixtureWithAnswers();
    renderCustomerFlow({ customerFlowApi, initialFlowState: EXPLANATION_STEP });

    await userEvent.click(await screen.findByRole('button', { name: 'Check my understanding' }));

    expect(
      await screen.findByRole('heading', {
        name: 'Tell us in your own words what you will pay each month.',
      }),
    ).toBeTruthy();
  });
});
