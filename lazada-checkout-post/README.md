# Lazada checkout POST automation

This directory contains the Lazada checkout POST runner used by the GitHub Actions workflow at:

- `.github/workflows/lazada-shipping-post-2m.yml`

## Required GitHub configuration

Configure these under:

`Repository Settings -> Secrets and variables -> Actions`

### Secret: `LAZADA_COOKIE`

**Type:** GitHub Actions repository secret

Contains the authenticated Lazada cookie header value used for the request.

Example shape only:

```text
lzd_cid=...; _tb_token_=...; lzd_uid=...; ...
```

Do not commit this value to the repository, print it in logs, or store it as a normal GitHub variable. Treat it like a password/session credential.

If the session expires, sign in to Lazada again and replace the secret with a fresh authenticated cookie value.

### Variable: `LAZADA_ITEM_SKU_PAIRS`

**Type:** GitHub Actions repository variable

JSON array of `[itemId, skuId]` pairs.

Example:

```json
[["13822368851","124830542173"],["123456789","987654321"]]
```

Expanded form:

```json
[
  ["13822368851", "124830542173"],
  ["123456789", "987654321"]
]
```

Both IDs are kept as strings to avoid accidental numeric conversion.

The runner processes each pair in array order.

### Variable: `LAZADA_QUANTITY`

**Type:** GitHub Actions repository variable

Optional. Defaults to `1`.

Example:

```text
1
```

The same quantity is currently applied to every item/SKU pair in a batch.

## Manual workflow inputs

The workflow can also be started manually with `workflow_dispatch`.

Available inputs:

- `pairs_json` — temporarily overrides `LAZADA_ITEM_SKU_PAIRS` for that run.
- `quantity` — temporarily overrides `LAZADA_QUANTITY` for that run.

The `LAZADA_COOKIE` secret is still required.

## Runtime behavior

The runner sends one checkout shipping POST for each configured `[itemId, skuId]` pair.

It logs only response metadata such as status code, final URL, response size, and the item/SKU being processed. It does not log the cookie value.

The runner is intentionally not designed to impersonate a human browser or bypass Lazada anti-automation controls. Its User-Agent identifies it as repository automation.

The batch stops if Lazada returns evidence of:

- a CAPTCHA or security-verification page
- a login redirect
- HTTP `403`
- HTTP `429`

This is deliberate. Do not add CAPTCHA solving, browser-fingerprint spoofing, proxy rotation, or other measures intended to evade Lazada's access controls.

## Current workflow scheduling

GitHub Actions does not support a native 2-minute cron interval. The current workflow schedules a job every 6 minutes and performs three executions within that job, separated by 120 seconds.

GitHub scheduled workflows can also be delayed by platform load, so the timing should be treated as approximate rather than real-time.

## Updating products

To change monitored/requested products, edit only the `LAZADA_ITEM_SKU_PAIRS` repository variable. No code change is required.

For example, changing from:

```json
[["13822368851","124830542173"]]
```

to:

```json
[["13822368851","124830542173"],["987654321","123456789"]]
```

adds the second item/SKU pair to subsequent runs.

## Troubleshooting

### Missing or expired session

Typical symptoms:

- redirect to a login page
- authorization/session-related HTML
- workflow exits non-zero

Refresh `LAZADA_COOKIE` with a valid authenticated session.

### Challenge or rate limit

If the workflow reports a CAPTCHA, security verification, `403`, or `429`, the runner stops the batch. Do not try to automate around the challenge. Reduce or disable automated traffic and use Lazada's supported interfaces where available.

### Invalid pair configuration

`LAZADA_ITEM_SKU_PAIRS` must be valid JSON and must contain at least one two-element array:

```json
[["itemId","skuId"]]
```

Incorrect examples:

```json
["itemId","skuId"]
```

```json
{"itemId":"123","skuId":"456"}
```

## Files

- `post-shipping.mjs` — request runner and response safety checks.
- `README.md` — configuration and operational documentation.
- `../.github/workflows/lazada-shipping-post-2m.yml` — GitHub Actions workflow.
