#!/usr/bin/env python3
"""Report registry entries that lag their repository's latest release.

Why this exists: an extension's release pipeline builds the zip, cuts the
GitHub release, and only THEN upserts this index. That last step is the one
that silently skips when the repo has no REGISTRY_TOKEN secret -- the release
run still finishes green, so nothing anywhere goes red while the registry
keeps pointing at the previous version. serverkit-wordpress sat like that:
v1.0.1 released with the fix, index.json serving v1.0.0, both "passing".

This is the check that would have caught it. For every non-bundled entry with
a github.com `repo`, compare the indexed version against the newest
non-prerelease release tag. Pre-releases are ignored on purpose: serverkit-faro
publishes betas past its stable tag, and the registry should keep serving the
stable one.

    python3 scripts/check_latest_releases.py

Exit 0 = every entry matches its latest release (or has none yet).
Exit 1 = at least one entry is behind, or a repo could not be read.

Dependency-free, like the other scripts here. Set GITHUB_TOKEN to lift the
unauthenticated API rate limit (GitHub Actions provides one automatically).
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    pass

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / 'index.json'
GH_REPO_RE = re.compile(r'^https://github\.com/([^/]+)/([^/#?]+?)(?:\.git)?/?$')
API = 'https://api.github.com/repos/{owner}/{name}/releases?per_page=20'

behind = []
unknown = []


def _api(url):
    req = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'serverkit-extensions-release-check',
    })
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def latest_stable_tag(owner, name):
    """Newest non-draft, non-prerelease tag, or None when there are none."""
    for rel in _api(API.format(owner=owner, name=name)):
        if rel.get('draft') or rel.get('prerelease'):
            continue
        return (rel.get('tag_name') or '').lstrip('v')
    return None


def main():
    ok = 0
    data = json.loads(INDEX.read_text(encoding='utf-8'))
    for e in data.get('extensions', []):
        slug = e.get('slug', '?')
        if e.get('bundled'):
            continue  # ships inside the panel; no release of its own
        m = GH_REPO_RE.match(e.get('repo') or '')
        if not m:
            print(f"  - {slug}: no github.com repo url, skipped")
            continue
        owner, name = m.groups()
        try:
            latest = latest_stable_tag(owner, name)
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TimeoutError) as exc:
            unknown.append(f"{slug}: could not read releases ({exc})")
            continue
        indexed = str(e.get('version', ''))
        if latest is None:
            print(f"  - {slug}: no published release yet (index says {indexed})")
        elif latest == indexed:
            ok += 1
            print(f"  OK {slug}: {indexed}")
        else:
            behind.append(f"{slug}: index has {indexed}, latest release is {latest}")

    print()
    for line in behind:
        print(f"  BEHIND {line}")
    for line in unknown:
        print(f"  ERROR  {line}")

    if behind or unknown:
        print(f"\n{len(behind)} entry(ies) behind, {len(unknown)} unreadable.")
        if behind:
            print("Update index.json (version, source, sha256 of the PUBLISHED "
                  "asset), or add REGISTRY_TOKEN to the extension repo so its "
                  "release pipeline can do it on its own.")
        return 1
    print(f"{ok} entry(ies) match their latest release.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
