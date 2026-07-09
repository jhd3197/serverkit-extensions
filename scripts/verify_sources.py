#!/usr/bin/env python3
"""Verify that each entry's `source` resolves to a downloadable zip and that
its `sha256` matches. Stdlib-only.

    python3 scripts/verify_sources.py [slug ...]

With no arguments every entry is checked; pass slugs to limit (CI passes the
slugs whose entries changed in a PR). Entries without a sha256 are reported
but never fail the run — the checksum is enforced panel-side only when
present. Network failures fail the entry loudly: a listed source that can't
be downloaded is a broken listing.

Bundled entries (`bundled: true`) ship inside the panel, not from the
registry — they carry no `source`, so the download/sha256 check is skipped.
Their `logo`/`screenshots` are still HEAD-checked when external.

Every external `logo` and `screenshots[]` URL is HEAD-checked: reachable
(status 200), an image (`Content-Type: image/*`), and under the size cap.
Repo-relative logos ('assets/<slug>/<file>') are checked for existence and
size on disk. Validity of the on-disk path is enforced by validate.py.

Source forms (same resolution the panel uses):
  - direct ....zip URL                    → download it
  - github.com/<owner>/<repo>             → latest release, prefer a .zip asset,
                                            fall back to the tag zipball
  - github.com/<owner>/<repo>/releases/tag/<tag> → that release's assets
"""
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

# Windows consoles often default to cp1252, which can't print the ✔/✘/⚠
# markers; never let the report itself crash the check.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    pass

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / 'index.json'
UA = {'User-Agent': 'serverkit-extensions-ci'}
LOGO_MAX_BYTES = 200 * 1024  # 200 KB cap for logos/screenshots


def fetch(url, binary=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    return data if binary else json.loads(data.decode('utf-8'))


def head(url):
    """HEAD an image URL; return (status, content_type, content_length)."""
    req = urllib.request.Request(url, headers=UA, method='HEAD')
    with urllib.request.urlopen(req, timeout=30) as resp:
        status = resp.status
        ctype = (resp.headers.get('Content-Type') or '').split(';')[0].strip().lower()
        clen = resp.headers.get('Content-Length')
        clen = int(clen) if clen and clen.isdigit() else None
    return status, ctype, clen


def resolve_zip_url(source):
    """Return the concrete zip URL a source resolves to."""
    if source.endswith('.zip'):
        return source
    m = re.match(r'^https://github\.com/([^/]+)/([^/]+?)(?:/releases/tag/([^/]+))?/?$', source)
    if not m:
        raise ValueError(f"unsupported source form: {source}")
    owner, repo, tag = m.groups()
    api = (f'https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}'
           if tag else
           f'https://api.github.com/repos/{owner}/{repo}/releases/latest')
    release = fetch(api)
    for asset in release.get('assets', []):
        if asset.get('name', '').endswith('.zip'):
            return asset['browser_download_url']
    # No .zip asset — same fallback the panel installer uses.
    return release['zipball_url']


def check_image(slug, label, ref):
    """Validate one logo/screenshot reference. Returns 1 on failure, else 0."""
    if ref.startswith('assets/'):
        path = ROOT / ref
        if not path.is_file():
            print(f"  ✘ {slug}: {label} '{ref}' not found on disk")
            return 1
        size = path.stat().st_size
        if size > LOGO_MAX_BYTES:
            print(f"  ✘ {slug}: {label} '{ref}' is {size} bytes "
                  f"(> {LOGO_MAX_BYTES} cap)")
            return 1
        print(f"  ✔ {slug}: {label} on disk ({size} bytes)")
        return 0
    try:
        status, ctype, clen = head(ref)
    except Exception as exc:
        print(f"  ✘ {slug}: {label} '{ref}' unreachable: {exc}")
        return 1
    if status != 200:
        print(f"  ✘ {slug}: {label} '{ref}' returned HTTP {status}")
        return 1
    if not ctype.startswith('image/'):
        print(f"  ✘ {slug}: {label} '{ref}' is not an image (Content-Type {ctype!r})")
        return 1
    if clen is not None and clen > LOGO_MAX_BYTES:
        print(f"  ✘ {slug}: {label} '{ref}' is {clen} bytes (> {LOGO_MAX_BYTES} cap)")
        return 1
    print(f"  ✔ {slug}: {label} reachable ({ctype}"
          f"{f', {clen} bytes' if clen is not None else ''})")
    return 0


def main():
    data = json.loads(INDEX.read_text(encoding='utf-8'))
    only = set(sys.argv[1:])
    failed = 0
    checked = 0
    for e in data.get('extensions', []):
        slug = e.get('slug', '?')
        if only and slug not in only:
            continue
        checked += 1

        if e.get('bundled') is True:
            print(f"  ⋯ {slug}: bundled entry — source/sha256 check skipped")
        else:
            try:
                zip_url = resolve_zip_url(e['source'])
                blob = fetch(zip_url, binary=True)
                digest = hashlib.sha256(blob).hexdigest()
            except Exception as exc:
                print(f"  ✘ {slug}: source unresolvable/undownloadable: {exc}")
                failed += 1
                continue
            if e.get('sha256') is None:
                print(f"  ⚠ {slug}: downloadable ({len(blob)} bytes, sha256 {digest}) "
                      f"but no sha256 pinned — consider adding the printed digest")
            elif digest == e['sha256']:
                print(f"  ✔ {slug}: sha256 verified ({len(blob)} bytes)")
            else:
                print(f"  ✘ {slug}: sha256 MISMATCH — index has {e['sha256']}, "
                      f"download is {digest}")
                failed += 1

        # Art checks apply to bundled and non-bundled entries alike.
        logo = e.get('logo')
        if logo:
            failed += check_image(slug, 'logo', logo)
        for j, shot in enumerate(e.get('screenshots', []) or []):
            failed += check_image(slug, f'screenshots[{j}]', shot)

    if only and checked == 0:
        print(f"  (no entries matched {sorted(only)})")
    print(f"\n{'✘' if failed else '✔'} verified {checked} source(s), {failed} failure(s)")
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
