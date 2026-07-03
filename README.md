# ServerKit Extension Registry

The curated index of installable [ServerKit](https://github.com/jhd3197/ServerKit)
extensions. Panels fetch [`index.json`](index.json) and merge its entries into
**Marketplace → Browse** (labeled "Registry"), with checksum-verified installs.
This repo is the whole registry — one JSON file, curated via pull request. No
build step, no backend, no accounts.

ServerKit is free/OSS: there are **no paid extensions, quotas, or billing — ever**.

## How panels consume this

- Panels fetch the raw index from `SERVERKIT_REGISTRY_URL`
  (default: `https://raw.githubusercontent.com/jhd3197/serverkit-extensions/main/index.json`),
  cache it for `SERVERKIT_REGISTRY_TTL` seconds (default 3600), and fall back to
  the last good cache, then to a copy bundled with the panel — the Marketplace
  never blanks when this repo or the network is unreachable.
- Discovery is **read-only**. Nothing here is ever auto-installed.
- Installing an entry downloads its `source`, verifies `sha256` when present
  (a mismatch is a hard failure with no partial install), and gates on
  `min_panel_version` / `max_panel_version`.

## Publishing an extension

1. **Structure your repo** per the panel's
   [extension docs](https://github.com/jhd3197/ServerKit/blob/main/docs/EXTENSIONS.md):
   a `plugin.json` at the archive root, plus `backend/` and/or `frontend/`.
2. **Cut a release.** Tag a version and attach the plugin `.zip` as a release
   asset (the installer prefers a `.zip` asset over the source zipball). Record
   the asset's digest: `sha256sum my-extension-0.1.0.zip`.
3. **Open a PR** adding (or bumping) your entry in `index.json`. Bumping
   `version` is what surfaces the "Update available" badge on installed panels.
   The full field reference lives in
   [`docs/EXTENSIONS_REGISTRY.md`](https://github.com/jhd3197/ServerKit/blob/main/docs/EXTENSIONS_REGISTRY.md)
   and is enforced by [`schema/index.schema.json`](schema/index.schema.json).

Validate before pushing:

```bash
python3 scripts/validate.py          # schema + rules (dependency-free)
python3 scripts/verify_sources.py    # downloads each source, checks sha256
```

Both run in CI on every PR; a broken or checksum-mismatched listing does not
merge.

> The index starts empty on purpose: every entry must have a downloadable,
> checksum-verifiable release *before* it lands (CI enforces this).
> `serverkit-gui` is queued as the first entry, pending its first release
> artifact.

## Review checklist (what a maintainer verifies)

- **Permissions honesty** — declared `permissions` match what the code actually
  uses (`docker|filesystem|shell|network|db`, or `agent.command:*`).
- **Checksum** — `sha256` present and matching the release asset.
- **License** — a real OSS license in the extension repo.
- **Compat** — `min_panel_version` reflects the oldest panel actually tested.
- **Brand-neutral** — no competitor names in names/descriptions.

## Repo layout

| Path | Purpose |
|---|---|
| `index.json` | The registry. The only file panels read. |
| `schema/index.schema.json` | JSON Schema for `index.json` (schema_version 1). |
| `scripts/validate.py` | Dependency-free rule validator (run locally + CI). |
| `scripts/verify_sources.py` | Downloads every source and checks `sha256`. |
