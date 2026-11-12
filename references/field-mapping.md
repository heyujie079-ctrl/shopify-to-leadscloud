# Field mapping

Use a canonical lead object between Shopify and LeadsCloud. Keep the canonical names stable; map them to the tenant's real LeadsCloud field IDs only after reading the tenant documentation.

## Canonical mapping

| Canonical field | Shopify source | Normalization | LeadsCloud destination |
|---|---|---|---|
| `external_id` | store domain + customer ID | `shopify:{store}:customer:{id}` | External/source ID custom field or documented external key |
| `email` | `customer.email` or `email` | trim and lowercase | Lead/contact email |
| `first_name` | `customer.first_name` | trim; preserve Unicode | First name |
| `last_name` | `customer.last_name` | trim; preserve Unicode | Last name |
| `full_name` | first + last name | join non-empty parts | Contact name when the target has one name field |
| `phone` | `customer.phone` | trim; use E.164 only when the source is confidently parseable | Phone/mobile |
| `source_system` | constant | `shopify` | Source system/channel |
| `source_type` | constant | `email_subscription` | Lead source detail |
| `store_domain` | webhook header or trusted configuration | lowercase host; never trust a body value over verified context | Website/store custom field |
| `shopify_customer_id` | `customer.id` or `id` | retain digits/GID losslessly as a string | Shopify customer ID custom field |
| `consent_state` | `email_marketing_consent.state` | accept only `SUBSCRIBED` for new-lead creation | Email consent status |
| `consent_updated_at` | consent object timestamp | ISO 8601 UTC where possible | Consent timestamp |
| `opt_in_level` | consent object | preserve enumerated value | Consent evidence/custom field |
| `country_code` | `default_address.country_code` | uppercase ISO code | Country/region |
| `locale` | customer locale when present | preserve BCP 47 form | Language/preferred locale |
| `tags` | customer tags | array; do not overwrite CRM tags by default | Source tags/custom field |
| `source_event_id` | webhook/event header or Flow-provided ID | preserve exactly | Event/audit ID |
| `source_page` | trusted form/UTM context | validate URL and remove secrets | First conversion page/custom field |
| `utm_*` | trusted form context | trim and length-limit | Attribution custom fields |

## Canonical payload

```json
{
  "external_id": "shopify:example.myshopify.com:customer:123",
  "email": "buyer@example.com",
  "first_name": "Ada",
  "last_name": "Lovelace",
  "full_name": "Ada Lovelace",
  "phone": null,
  "source_system": "shopify",
  "source_type": "email_subscription",
  "store_domain": "example.myshopify.com",
  "shopify_customer_id": "123",
  "consent_state": "SUBSCRIBED",
  "consent_updated_at": "2026-11-12T08:00:00Z",
  "opt_in_level": "SINGLE_OPT_IN",
  "country_code": "US",
  "locale": "en",
  "tags": [],
  "source_event_id": "event-id-from-source",
  "dedupe_key": "sha256:...",
  "idempotency_key": "sha256:...",
  "metadata": {}
}
```

## Mapping rules

- Do not overload a CRM sales-stage field with subscription state.
- Do not overwrite an assigned owner, lead stage, manual tags, notes, or activity history during a subscriber upsert.
- Store consent evidence separately from marketing attribution.
- Treat UTM and source-page values as untrusted input; length-limit and escape them for the destination API.
- When the target requires a name but Shopify provides none, use the documented tenant fallback only; do not invent a person name.
- Keep raw payload retention off by default. If compliance requires retention, encrypt it and define a deletion period.
