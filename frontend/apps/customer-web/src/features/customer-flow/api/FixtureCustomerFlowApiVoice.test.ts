import { describe, expect, it } from 'vitest';

import { FixtureCustomerFlowApi } from './FixtureCustomerFlowApi';

// Opens a fixture session with the design budget, as C1 and C2 do.
async function createFixtureWithBudget(): Promise<FixtureCustomerFlowApi> {
  const fixture = new FixtureCustomerFlowApi();
  await fixture.startSession('qr-token');
  await fixture.confirmBudget(300000);
  return fixture;
}

describe('FixtureCustomerFlowApi: Layer 4 voice and teach-back', () => {
  it('hears ₹3,000 for the budget without setting it, and needs a session', async () => {
    const fixture = new FixtureCustomerFlowApi();
    await expect(fixture.transcribeSpeech(new Blob(), 'BUDGET')).rejects.toMatchObject({
      status: 401,
    });
    await fixture.startSession('qr-token');

    const transcription = await fixture.transcribeSpeech(new Blob(), 'BUDGET');

    expect(transcription).toEqual({
      transcript: 'three thousand rupees',
      recognisedAmountInPaise: 300000,
      isLikelyMisheard: false,
    });
    await expect(fixture.listPlans()).rejects.toMatchObject({ code: 'BUDGET_NOT_CONFIRMED' });
  });

  it('speaks only its own explanation id', async () => {
    const fixture = await createFixtureWithBudget();

    const audio = await fixture.synthesiseExplanation('fixture-explanation-1');

    expect(audio.type).toBe('audio/wav');
    await expect(fixture.synthesiseExplanation('other')).rejects.toMatchObject({
      status: 404,
      code: 'EXPLANATION_NOT_FOUND',
    });
  });

  it('accepts the monthly figure with or without grouping and answers in the language', async () => {
    const fixture = await createFixtureWithBudget();

    const close = await fixture.checkTeachBack('mock-offer-no-cost-6m', 'மாதம் 3667', 'ta');
    const again = await fixture.checkTeachBack('mock-offer-no-cost-6m', 'about 3,000', 'en');

    expect(close).toMatchObject({ result: 'CLOSE_ENOUGH', heardText: null });
    expect(close.title).toBe('சரியாகச் சொன்னீர்கள்');
    expect(again).toMatchObject({ result: 'TRY_AGAIN', title: 'Nearly there' });
    expect(again.heardText).toBe('about 3,000');
  });
});
