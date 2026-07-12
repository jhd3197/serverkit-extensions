# ServerKit Extension Registry

The curated index of installable [ServerKit](https://github.com/jhd3197/ServerKit)
extensions. Panels fetch [`index.json`](index.json) and merge its entries into
**Marketplace → Browse** (labeled "Registry"), with checksum-verified installs.
This repo is the whole registry — one JSON file, curated via pull request. No
build step, no backend, no accounts.

ServerKit is free/OSS: there are **no paid extensions, quotas, or billing — ever**.

## Extensions in the registry

> This table is a human-friendly mirror of [`index.json`](index.json). The JSON
> is the source of truth panels read; if the two ever disagree, trust the JSON.

Legend: **Type** — `Bundled` ships inside the panel (installed/uninstalled in
place, no download); `Installable` is fetched and checksum-verified from a
release.

| Extension | Category | Type | Summary |
|---|---|---|---|
| [Automations](https://github.com/jhd3197/ServerKit) | deployment | Bundled | Node-based automation builder powered by tramo: visual workflows with 21 integration packs, deployed to a managed container. |
| [Cloud Provisioning](https://github.com/jhd3197/ServerKit) | deployment | Bundled | Provision new servers from connected cloud providers (Cloud Servers tab). |
| [Cloudflare Zone Ops](https://github.com/jhd3197/ServerKit) | integration | Bundled | Zone settings, cache purge, WAF, Workers, Tunnels, and R2/KV/D1 on your Cloudflare DNS connection. |
| [CrowdSec](https://github.com/jhd3197/ServerKit) | security | Bundled | CrowdSec engine integration: decisions, alerts, ban/unban, and allowlists via `cscli`. |
| [DNS Server](https://github.com/jhd3197/ServerKit) | integration | Bundled | Authoritative DNS via PowerDNS in Docker: zones, records, DNSSEC, delegation checks. |
| [Email Server](https://github.com/jhd3197/ServerKit) | integration | Bundled | Postfix/Dovecot mail stack with DKIM/SPF/DMARC, SpamAssassin, and Roundcube webmail. |
| [Faro](https://github.com/jhd3197/serverkit-faro) | utility | Installable | One-click Open in Faro: `faro://` SFTP deep links from Services, Domains, and WordPress. |
| [FTP Server](https://github.com/jhd3197/ServerKit) | utility | Bundled | FTP server management (vsftpd/proftpd): users, config, and logs (Files tab). |
| [Git Server](https://github.com/jhd3197/ServerKit) | deployment | Bundled | Self-hosted Git server (Gitea) exposed through the extension system. |
| [GPU Monitor](https://github.com/jhd3197/ServerKit) | monitoring | Bundled | Live NVIDIA GPU metrics: utilization, memory, temperature, power, and fan. |
| [Kubernetes](https://github.com/jhd3197/ServerKit) | deployment | Bundled | Manage remote clusters via kubectl: nodes, workloads, pods with live logs, plus scale/restart/delete/apply. |
| [Mail Server](https://github.com/jhd3197/ServerKit) | integration | Bundled | Self-hosted mail via Stalwart with a deliverability preflight (PTR, port-25, RBL) and brute-force jails. |
| [Remote Access](https://github.com/jhd3197/ServerKit) | integration | Bundled | WireGuard tunnels between paired agents to expose NAT'd home services through an edge server. |
| [ServerKit Agent GUI (Beta)](https://github.com/jhd3197/serverkit-gui) | monitoring | Installable | Agent-powered desktop view: streams live Windows/Linux screenshots for managed servers. |
| [Status Pages](https://github.com/jhd3197/ServerKit) | monitoring | Bundled | Public status pages backed by uptime monitors (management UI in the Observability group). |
| [WordPress](https://github.com/jhd3197/ServerKit) | integration | Bundled | Full WordPress suite: provisioning, plugins, environments, updates, security, and vulnerability scanning (flagship). |

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
3. **Add artwork (optional but recommended).** Commit a logo at
   `assets/<slug>/logo.svg` (or `.png`, ≤ 200 KB) in the same PR, and set the
   entry's `logo` field to that repo-relative path
   (`assets/<slug>/logo.svg`) — the panel and the serverkit.ai `/ext` endpoint
   resolve it to an absolute URL, so one relative path works everywhere. An
   external `https://` logo URL is also accepted (CI HEAD-checks it: reachable,
   `image/*`, under the size cap). **Use the downloadable logo template + spec
   (512 px canvas, safe zones, transparency check) in
   [`assets/_brand/`](assets/_brand/README.md).**
4. **Open a PR** adding (or bumping) your entry in `index.json`. Bumping
   `version` is what surfaces the "Update available" badge on installed panels.
   The full field reference lives in
   [`docs/EXTENSIONS_REGISTRY.md`](https://github.com/jhd3197/ServerKit/blob/main/docs/EXTENSIONS_REGISTRY.md)
   and is enforced by [`schema/index.schema.json`](schema/index.schema.json).

> **Schema v2.** The index is now `schema_version: 2` — additive over v1, so
> existing entries stay valid. It adds three optional fields: `logo` (above),
> `repo` (https URL of your source repo, shown as a "Source repo" link), and
> `bundled`. **Bundled entries** are the panel's own builtin extensions listed
> for the public catalog; they ship inside the panel, so they carry no
> `source`/`sha256` and are **generated from the panel repo** — do not hand-type
> them. Regenerate the block with
> `node scripts/export-registry-entries.mjs` in the
> [ServerKit](https://github.com/jhd3197/ServerKit) checkout and paste it in.

Validate before pushing:

```bash
python3 scripts/validate.py          # schema + rules (dependency-free)
python3 scripts/verify_sources.py    # downloads each source, checks sha256
```

Both run in CI on every PR; a broken or checksum-mismatched listing does not
merge.

> Every `Installable` entry must point at a downloadable, checksum-verifiable
> release *before* it lands (CI enforces this). `Bundled` entries are the
> exception: they ship inside the panel and are generated from the panel repo,
> so they carry no `source`/`sha256`.

## Review checklist (what a maintainer verifies)

- **Permissions honesty** — declared `permissions` match what the code actually
  uses (`docker|filesystem|shell|network|db`, or `agent.command:*`).
- **Checksum** — `sha256` present and matching the release asset.
- **License** — a real OSS license in the extension repo.
- **Compat** — `min_panel_version` reflects the oldest panel actually tested.
- **Brand-neutral** — no competitor names in names/descriptions, and no
  em/en dashes (plain-ASCII punctuation; `validate.py` enforces this).
- **Artwork** — `logo` is https or a committed `assets/<slug>/<file>` that
  actually exists, ≤ 200 KB, an image.

## Repo layout

| Path | Purpose |
|---|---|
| `index.json` | The registry. The only file panels read. |
| `schema/index.schema.json` | JSON Schema for `index.json` (schema_version 1 or 2). |
| `assets/<slug>/` | Extension artwork (logo.svg / logo.png), served via serverkit.ai. |
| `scripts/validate.py` | Dependency-free rule validator (run locally + CI). |
| `scripts/verify_sources.py` | Downloads every source, checks `sha256`, HEAD-checks art. |
