# Releasing Extensions — the automated pipeline

This is the recommended release flow for first-party ServerKit extensions (and
any community extension that wants zero manual release work). It is the exact
setup running in [`serverkit-gpu`](https://github.com/jhd3197/serverkit-gpu),
[`serverkit-crowdsec`](https://github.com/jhd3197/serverkit-crowdsec),
[`serverkit-dns-server`](https://github.com/jhd3197/serverkit-dns-server),
[`serverkit-k8s`](https://github.com/jhd3197/serverkit-k8s),
[`serverkit-mail`](https://github.com/jhd3197/serverkit-mail) and
[`serverkit-tramo`](https://github.com/jhd3197/serverkit-tramo) — copy it from
any of them.

**The whole release is: bump `version` in `plugin.json`, push.** No local zip
builds, no dragging files onto a release page, no hand-editing `index.json`.

```
git commit -m "Bump to 1.1.0" plugin.json && git push
        │
        ▼  GitHub Actions (release.yml)
  build frontend bundle (vite, runtime-ESM)
        │   └─ react / react-router / serverkit-sdk stay external
        ▼
  scripts/build-zip.sh  →  dist/<slug>-<version>.zip
        ▼
  GitHub Release v<version> with the zip attached
        ▼
  download the PUBLISHED zip back, sha256 it
        ▼
  upsert this extension's entry in serverkit-extensions/index.json
  (version, source URL, sha256, updated date) → commit → push → validate.py
```

The registry's `sha256` is always computed from the **published asset**,
never from a local build, so the checksum panels verify against can never
drift from what they download.

## One-time setup (per extension repo)

1. **Copy five files** from the reference repo
   ([`serverkit-gpu`](https://github.com/jhd3197/serverkit-gpu)) — they are
   fully generic (everything is derived from `plugin.json`):

   | File | Purpose |
   |---|---|
   | `.github/workflows/release.yml` | The pipeline above (push to `main` or `v*` tag). |
   | `.github/workflows/ci.yml` | Build + zip check on every push/PR. |
   | `scripts/build-zip.sh` / `build-zip.ps1` | Stages a clean `dist/<slug>-<version>.zip` (excludes `.git`, `node_modules` — including nested ones — `__pycache__`, `dist/`, `scripts/`). |
   | `scripts/update-registry.mjs` | Upserts the `index.json` entry from `plugin.json` + the published zip. |

2. **Add the `REGISTRY_TOKEN` secret** (repo → Settings → Secrets and
   variables → Actions): a fine-grained personal access token scoped to the
   `serverkit-extensions` repository with **Contents: Read and write**. The
   registry job uses it to check out this repo and push the entry update.
   Without the secret the release still ships — only the registry sync skips
   (with a warning), and you update `index.json` by PR instead.

3. Make sure `frontend/package-lock.json` is committed — CI builds with
   `npm ci`.

That's it. The next push to `main` whose `plugin.json` version has no
matching tag cuts the release automatically.

## Cutting a release

Two equivalent triggers:

- **Version bump (recommended).** Set `"version": "X.Y.Z"` in `plugin.json`,
  push to `main`. If tag `vX.Y.Z` doesn't exist yet, the release runs.
  Pushes that don't bump the version are a no-op (the workflow detects the
  existing tag and exits), so `main` stays always-releasable.
- **Tag push.** `git tag vX.Y.Z && git push origin vX.Y.Z` — the tag
  overrides `plugin.json`'s version.

Escape hatches: include `[skip release]` or `[skip ci]` in the commit
message to push without releasing. Frontend tests run automatically when
`frontend/package.json` declares a `test` script.

## What the registry job writes

`update-registry.mjs` upserts the entry for `plugin.json`'s `name`:

- `version` ← the tag (minus `v`), `updated` ← today
- `source` ← `https://github.com/<owner>/<repo>/releases/download/<tag>/<zip>`
- `sha256` ← digest of the **downloaded release asset**
- `review` ← carried over from the existing entry **only** when the stamp's
  sha256 matches the new artifact byte-for-byte; a fresh build produces a new
  hash, so a stale review stamp is dropped instead of silently vouching for
  code nobody reviewed. Re-review (read the diff, then re-stamp with the new
  hash) on every version bump.
- `bundled: false`, `repo`, `homepage`, `permissions`,
  `min_panel_version` ← from `plugin.json`

It commits as `github-actions[bot]` directly to this repo's `main` and then
runs `scripts/validate.py`. `verify_sources.py` in registry CI re-downloads
the asset and re-checks the digest, so a bad entry cannot land.

> If this registry moves to a GitHub org, update the `repository:` line in
> the `registry` job of `release.yml` (and the token scope) — nothing else
> changes.

## Requirements the pipeline assumes

- `plugin.json` at the repo root with `name`, `display_name`, `version`
  (semver), and — for runtime-ESM frontends — `frontend_entry: "dist/index.mjs"`.
- `frontend/` builds with `npm ci && npm run build` to
  `frontend/dist/index.mjs` (vite lib build; `react`, `react-router-dom` and
  `serverkit-sdk` externalized — the panel resolves them to its own
  singletons via its import map; everything else bundles).
- `backend/` (when present) is plain Python loaded as `app.plugins.<slug>`
  by the panel — host runtime imports (`app.plugins_sdk`,
  `app.middleware.rbac`, `app.utils.*`) are fine.

## Manual path (community extensions, or no token)

Nothing about the registry requires this pipeline — it just removes the
chore. You can always do it by hand:

1. `cd frontend && npm ci && npm run build`
2. `./scripts/build-zip.sh`
3. Attach the zip to a GitHub release, `sha256sum` it
4. Open a PR here bumping your entry's `version`/`source`/`sha256`

See [README → Publishing an extension](README.md#publishing-an-extension).
