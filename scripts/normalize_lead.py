#!/usr/bin/env python3
"""Normalize a Shopify subscriber event into the skill's canonical lead JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


def _text(value: Any) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def _customer(payload: dict[str, Any]) -> dict[str, Any]:
    nested = payload.get("customer")
    return nested if isinstance(nested, dict) else payload


def _consent(customer: dict[str, Any]) -> dict[str, Any]:
    for key in ("email_marketing_consent", "emailMarketingConsent"):
        value = customer.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _address(customer: dict[str, Any]) -> dict[str, Any]:
    for key in ("default_address", "defaultAddress"):
        value = customer.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _get(obj: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in obj and obj[key] is not None:
            return obj[key]
    return None


def _hash(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _customer_id(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    if text.startswith("gid://"):
        return text.rsplit("/", 1)[-1]
    return text


def normalize(
    payload: dict[str, Any], store_domain: str, source_event_id: str | None
) -> dict[str, Any]:
    customer = _customer(payload)
    consent = _consent(customer)
    address = _address(customer)

    email = _text(_get(customer, "email"))
    email = email.lower() if email else None
    customer_id = _customer_id(_get(customer, "id", "admin_graphql_api_id"))
    domain = store_domain.strip().lower().removeprefix("https://").removeprefix("http://").rstrip("/")
    if not domain or "/" in domain:
        raise ValueError("store domain must be a bare trusted hostname")
    if not email or "@" not in email:
        raise ValueError("a usable customer email is required")
    if not customer_id:
        raise ValueError("a stable Shopify customer ID is required")

    first_name = _text(_get(customer, "first_name", "firstName"))
    last_name = _text(_get(customer, "last_name", "lastName"))
    full_name = " ".join(part for part in (first_name, last_name) if part) or None
    state = _text(_get(consent, "state", "marketing_state", "marketingState"))
    state = state.upper() if state else None
    consent_at = _text(_get(consent, "consent_updated_at", "consentUpdatedAt", "updated_at", "updatedAt"))
    opt_in_level = _text(_get(consent, "opt_in_level", "optInLevel"))
    event_basis = _text(source_event_id) or consent_at
    if not event_basis:
        raise ValueError("source event ID or consent-updated timestamp is required for idempotency")

    external_id = f"shopify:{domain}:customer:{customer_id}"
    dedupe_key = _hash(f"shopify|{domain}|{customer_id}|email_subscription")
    idempotency_key = _hash(f"{dedupe_key}|{event_basis}")

    tags = _get(customer, "tags")
    if isinstance(tags, str):
        tags = [item.strip() for item in tags.split(",") if item.strip()]
    elif not isinstance(tags, list):
        tags = []

    return {
        "external_id": external_id,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "full_name": full_name,
        "phone": _text(_get(customer, "phone")),
        "source_system": "shopify",
        "source_type": "email_subscription",
        "store_domain": domain,
        "shopify_customer_id": customer_id,
        "consent_state": state,
        "consent_updated_at": consent_at,
        "opt_in_level": opt_in_level,
        "country_code": (_text(_get(address, "country_code", "countryCodeV2", "countryCode")) or "").upper() or None,
        "locale": _text(_get(customer, "locale")),
        "tags": tags,
        "source_event_id": _text(source_event_id),
        "dedupe_key": dedupe_key,
        "idempotency_key": idempotency_key,
        "eligible_for_create": state == "SUBSCRIBED",
        "metadata": {},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="Shopify JSON file; omit to read stdin")
    parser.add_argument("--store-domain", required=True, help="Trusted shop hostname")
    parser.add_argument("--event-id", help="Shopify webhook/event ID")
    parser.add_argument("--require-subscribed", action="store_true")
    args = parser.parse_args()

    raw = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("input JSON must be an object")
        result = normalize(payload, args.store_domain, args.event_id)
        if args.require_subscribed and not result["eligible_for_create"]:
            raise ValueError("email consent state is not SUBSCRIBED")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"normalize_lead: {exc}", file=sys.stderr)
        return 2

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
