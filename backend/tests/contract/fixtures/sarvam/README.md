# Sarvam contract fixtures

Synthetic bodies in the **documented shape** of Sarvam AI's API (docs.sarvam.ai, checked 15 Nov 2026). They are not recordings: no real key, request id, audio or customer speech is in them.

| File | Endpoint | Shape |
|---|---|---|
| `stt_success.json` | `POST /speech-to-text` (200) | `transcript`, `language_code`, `request_id` |
| `tts_success.json` | `POST /text-to-speech` (200) | `audios[]` as base64 strings, `request_id` (an ID3 marker and zero bytes, not real mp3) |
| `error_429.json` | any (429) | `{"error": {"message", "code", "request_id"}}` |
| `error_403.json` | any (403) | the same error shape |
| `chat_success.json` | `POST /v1/chat/completions` (200) | `choices[0].message.content`, `finish_reason`, `usage`, `model`; also a `reasoning_content` that the adapter must never read |
| `chat_length.json` | the same (200) | `finish_reason: "length"`, cut-off content |
| `chat_error_429.json` | the same (429) | the error shape above |

**[Verify]** with the real key (step 4.8 smoke script), then replace these with redacted recordings:
- the exact error body shape and codes (`rate_limit_exceeded_error`, `invalid_api_key_error`, `insufficient_quota_error` and its status code);
- that a 403 means a refused key;
- whether speech-to-text reads the format from the file name, the part type or the bytes;
- which other fields the success bodies carry (the adapters ignore every field not listed above);
- chat: whether auth is `Authorization: Bearer` or `api-subscription-key` (the adapter sends both), that `reasoning_effort` is accepted, the `finish_reason` values (only `stop` is accepted), the `usage` field names, and whether `reasoning_content` appears.
