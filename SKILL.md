---
name: shopify-to-leadscloud
description: Sync Shopify email subscribers and website form leads into LeadsCloud CRM with explicit field mapping, idempotent deduplication, bounded retries, and documented authentication. Use when designing, implementing, testing, or troubleshooting a Shopify-to-询盘云 subscriber/lead integration; do not use for Shopify product subscriptions unless the user explicitly means recurring purchases.
---

# Shopify to LeadsCloud

Build a reliable, auditable path from a Shopify subscription event to one LeadsCloud lead. Treat “website subscription” as email-marketing consent unless the user explicitly means a recurring product subscription.

## Choose the source path

- Prefer Shopify Flow trigger `Customer subscribed to email marketing` followed by `Send HTTP request` for theme signup forms or Shopify Forms. Verify that the store plan supports the HTTP action.
- Use Shopify webhook `customers_email_marketing_consent/update` when Flow cannot send HTTP, a custom app already exists, or lower-level delivery control is needed. Verify the Shopify HMAC against the raw request body before parsing JSON.
- For third-party forms, use the form provider's webhook. Shopify's subscription trigger does not cover arbitrary third-party forms.
- Use the installed `shopify` skill for current Shopify workflow guidance and `shopify-admin` for Admin GraphQL or webhook operations.

## Required LeadsCloud facts

Before any live write, obtain and verify all of the following from the user's tenant documentation or account administrator:

1. Base URL and create-lead endpoint.
2. Search/upsert endpoint or documented idempotency mechanism.
3. Authentication scheme, exact header/query names, tenant or organization identifier, and credential scopes.
4. Required fields, custom-field identifiers, validation limits, rate limits, and sandbox/test tenant details.

Never infer these values from another CRM or expose a credential in code, Flow logs, chat, screenshots, or generated examples. If any item is missing, continue only with a dry-run payload/configuration and provide a concise missing-information list.

## Implementation workflow

1. Read [references/field-mapping.md](references/field-mapping.md) when mapping or validating payloads. Use `scripts/normalize_lead.py` to convert a captured Shopify event into the canonical lead schema.
2. Read [references/reliability-auth.md](references/reliability-auth.md) before implementing lookup, authentication, retries, or production writes.
3. Normalize email, identifiers, consent state, timestamps, and source metadata. Reject events without a usable email, a stable Shopify customer ID, or confirmed subscribed consent unless the user explicitly defines another acceptance rule.
4. Deduplicate in this order: stable external ID, documented idempotency key, then normalized email within the same tenant. Update the existing lead instead of creating a duplicate only when the target API explicitly supports that action and the user has authorized updates.
5. Authenticate server-to-server. Keep secrets in Shopify Flow Secrets, the deployment secret manager, or environment variables; never in theme JavaScript or repository files.
6. Write first to a sandbox or dry-run capture endpoint. Compare the target record against the source event and field map before enabling production delivery.
7. Retry only transient failures using the bounded policy in the reliability reference. Do not retry validation/authentication failures unchanged. Preserve the same idempotency key across retries.
8. Record an audit result containing source event ID, external ID, idempotency key, target record ID, attempt count, final status, and a redacted error summary. Do not log tokens or full customer payloads.

## Completion checks

- Replaying the same event does not create a second lead.
- A resubscription updates consent without overwriting unrelated CRM ownership, stage, notes, or sales activity.
- A 429 or 5xx is retried with the same idempotency key and stops after the configured limit.
- A 400/401/403 is quarantined for correction rather than retried indefinitely.
- Logs redact email, phone, authorization values, and raw webhook bodies.
- Unsubscribe events are not converted into new leads; handle consent revocation only when explicitly in scope.
