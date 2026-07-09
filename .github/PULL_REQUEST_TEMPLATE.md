## Extension entry

<!-- One extension per PR: a new entry or a version bump in index.json. -->

- **Slug**:
- **Version**:
- **Release URL**:

## Checklist

- [ ] `python3 scripts/validate.py` passes locally
- [ ] The release has a plugin `.zip` asset (`plugin.json` at the archive root,
      plus `backend/` and/or `frontend/`)
- [ ] `sha256` is the digest of that exact asset
      (`sha256sum my-extension-x.y.z.zip`)
- [ ] Declared `permissions` match what the code actually uses — over-broad or
      undeclared permissions are rejected
- [ ] `min_panel_version` reflects the oldest panel actually tested
- [ ] Real OSS license (`license` in the manifest + a LICENSE file in the repo)
- [ ] Name/description are brand-neutral, plain-ASCII punctuation (no em/en dashes)
- [ ] `repo` set to the extension's source repository (https URL)
- [ ] Logo committed at `assets/<slug>/logo.svg` (or `.png`, ≤ 200 KB) and the
      `logo` field points at it — or an https logo URL that CI can HEAD-check

<!--
Not applicable to community entries: `bundled: true` entries are the panel's
builtin extensions, GENERATED from the ServerKit repo via
`node scripts/export-registry-entries.mjs` — never hand-edited here.
-->

> ServerKit is free/OSS: there are no paid extensions, quotas, or billing — ever.
