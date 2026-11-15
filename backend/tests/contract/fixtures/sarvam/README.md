# Sarvam contract fixtures

Synthetic bodies in the **documented shape** of Sarvam AI's API (docs.sarvam.ai, checked 15 Nov 2026). They are not recordings: no real key, request id, audio or customer speech is in them.

| File | Endpoint | Shape |
|---|---|---|
| `stt_success.json` | `POST /speech-to-text` (200) | `transcript`, `language_code`, `request_id` |
| `tts_success.json` | `POST /text-to-speech` (200) | `audios[]` as base64 strings, `request_id` (an ID3 marker and zero bytes, not real mp3) |
| `error_429.json` | any (429) | `{"error": {"message", "code", "request_id"}}` |
| `error_403.json` | any (403) | the same error shape |
| `chat_success.json` | `POST /v1/chat/completions` (200, model `sarvam-105b-conversations`) | `choices[0].message.content`, `finish_reason`, `usage`, `model`; also a `reasoning_content` that the adapter must never read |
| `chat_length.json` | the same (200) | `finish_reason: "length"`, cut-off content |
| `chat_error_429.json` | the same (429) | the error shape above |

**Verified on 2026-11-15** by the owner's live smoke check (synthetic plan data, never in CI):
- the error body is `{"error": {"message", "code", "request_id"}}`;
- chat auth works with both headers sent (`api-subscription-key` and `Authorization: Bearer`);
- `reasoning_effort` accepts only `low`, `medium` or `high` (`none` answers 400 `invalid_request_error`);
- `finish_reason` is `stop` on success and `length` when the token budget runs out;
- the `usage` field names are `prompt_tokens` and `completion_tokens`;
- `sarvam-105b` spends its whole budget on hidden reasoning (max_tokens 600 and 2000 gave `length`, empty content, 599 reasoning tokens at 600; 4000 at `low` stopped after 6.3 s, over the 6 s timeout), so the default model is `sarvam-105b-conversations`, which stopped in 0.3 s with about 25 completion tokens, `completion_tokens_details` null and no reasoning content;
- text-to-speech (`bulbul:v3`, mp3) returned 71,889 bytes in 1.3 s;
- speech-to-text (`saaras:v4`) writes amounts as English words: "You pay three thousand six hundred and sixty seven rupees each month for six months." (`SpokenAmountParser` composes them).

**[Verify]** still open, then replace these fixtures with redacted recordings:
- the prices (`sarvam-105b-conversations` is not on the pricing page; the `sarvam-105b` prices are the estimate);
- the Tamil voice of the `bulbul:v3` speaker;
- whether one auth header alone suffices;
- the codes `rate_limit_exceeded_error`, `invalid_api_key_error`, `insufficient_quota_error` and its status code, and that a 403 means a refused key;
- whether speech-to-text reads the format from the file name, the part type or the bytes;
- which other fields the success bodies carry (the adapters ignore every field not listed above).
