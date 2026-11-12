# Shopify to LeadsCloud

[简体中文](README.zh-CN.md) | English

An Agent Skill for designing, implementing, testing, and troubleshooting a reliable sync from Shopify email subscribers or website form leads into LeadsCloud (询盘云) CRM.

## What it covers

- Shopify Flow and webhook source paths
- Canonical Shopify-to-LeadsCloud field mapping
- External-ID and email-based deduplication
- Stable idempotency keys for replay-safe delivery
- Bounded retries for rate limits and transient failures
- Bearer, API key, OAuth, and documented HMAC authentication patterns
- Redacted audit logging and production readiness checks
- A dependency-free Python normalizer for captured Shopify subscriber events

The skill deliberately does not invent undocumented LeadsCloud endpoints, tenant identifiers, field IDs, or signature algorithms. A live integration requires the real API documentation and credentials for the target LeadsCloud tenant.

## Repository structure

```text
shopify-to-leadscloud/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── field-mapping.md
│   └── reliability-auth.md
└── scripts/
    └── normalize_lead.py
```

## Install

Clone the repository into your Codex skills directory:

```bash
git clone https://github.com/heyujie079-ctrl/shopify-to-leadscloud.git ~/.codex/skills/shopify-to-leadscloud
```

On the next turn, invoke it explicitly or let Codex discover it automatically:

```text
Use $shopify-to-leadscloud to design a Shopify subscriber sync into LeadsCloud CRM.
```

## Normalize a Shopify event

```bash
python scripts/normalize_lead.py subscriber.json \
  --store-domain example.myshopify.com \
  --event-id event-001 \
  --require-subscribed
```

The script outputs a canonical lead payload with `external_id`, `dedupe_key`, and `idempotency_key`. It does not send data to a remote service.

## Production prerequisites

Before enabling live writes, obtain and verify:

1. LeadsCloud base URL and create-lead endpoint.
2. Search/upsert endpoint or native idempotency mechanism.
3. Exact authentication scheme and tenant/organization identifier.
4. Required and custom field identifiers.
5. Rate limits and a sandbox or test tenant.

Never commit production credentials. Use Shopify Flow Secrets, a deployment secret manager, or environment variables.
