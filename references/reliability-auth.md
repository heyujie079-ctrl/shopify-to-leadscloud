# Reliability and authentication

## Deduplication and idempotency

Use two stable keys:

- `dedupe_key = SHA256("shopify|{store_domain}|{customer_id}|email_subscription")`
- `idempotency_key = SHA256("{dedupe_key}|{source_event_id_or_consent_timestamp}")`

Keep the same idempotency key for every retry of one event. Prefer a documented LeadsCloud idempotency header or native upsert. If neither exists:

1. Search the same tenant by `external_id`.
2. If absent, search by normalized email plus source system.
3. Create only when both searches return no record.
4. Protect the lookup/create sequence with a durable unique constraint or integration-side lock; a lookup alone is race-prone.

If the target cannot search or enforce uniqueness, stop before production and report that exactly-once behavior cannot be guaranteed.

## Authentication decision table

Use only the method confirmed by LeadsCloud tenant documentation.

| Confirmed scheme | Implementation |
|---|---|
| Bearer token | `Authorization: Bearer <secret>` from a secret store |
| API key header | Use the exact documented header name; never guess `X-API-Key` |
| API key query parameter | Use only if required; prevent URL/query logging |
| OAuth 2.0 | Store refresh credentials securely, cache access tokens until shortly before expiry, and refresh once after an explicit token-expired response |
| HMAC signature | Follow the documented canonical string, encoding, digest, timestamp, and nonce rules exactly; reject clock-skewed requests |

Do not implement a generic HMAC guess. Different APIs sign different combinations of path, query, headers, timestamp, and body.

Required configuration should be secret-injected, not committed:

```text
LEADSCLOUD_BASE_URL
LEADSCLOUD_CREATE_LEAD_PATH
LEADSCLOUD_LOOKUP_PATH
LEADSCLOUD_AUTH_MODE
LEADSCLOUD_TENANT_ID
LEADSCLOUD_TOKEN or LEADSCLOUD_API_KEY or OAuth/HMAC secrets
```

Validate that the base URL is HTTPS and belongs to the confirmed LeadsCloud domain. Block redirects to a different host when authorization headers are present.

## Retry policy

Classify before retrying:

- Retry: network timeout, connection reset, HTTP 408, 425, 429, and 5xx.
- Do not retry unchanged: HTTP 400, 401, 403, 404, 409 caused by duplicate data, and 422.
- On 401 caused by an expired OAuth access token, refresh once and retry once.
- Honor a valid `Retry-After`; otherwise use exponential backoff with full jitter and base delays of 1, 2, 4, 8, and 16 seconds.
- Cap immediate attempts at 5. After that, place the event in a durable dead-letter queue or failed-run store and notify an operator once.

Shopify Flow may retry failed HTTP actions for up to its platform limit. The receiver must therefore be idempotent even when application-level retries are disabled.

## Status handling

| Result | Integration action |
|---|---|
| 2xx with target record ID | Mark delivered and audit the redacted result |
| 2xx without expected confirmation | Treat as ambiguous; verify by lookup before another create |
| 409 duplicate | Lookup the existing record; link the event without creating another record |
| 400/422 | Quarantine with validation summary and field name |
| 401/403 | Stop; rotate/fix credentials or scopes |
| 429/5xx/network | Retry with the same idempotency key |

## Operational safeguards

- Use connect and total timeouts; keep total request time below the caller's limit.
- Log only redacted identifiers, response status, target request ID, and error class.
- Emit metrics for received, normalized, deduplicated, created, updated, retried, quarantined, and failed events.
- Test replay, concurrent duplicate delivery, rate limiting, expired credentials, and malformed payloads before production.
