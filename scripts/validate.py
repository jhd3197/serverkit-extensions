#!/usr/bin/env python3
"""Validate index.json against the registry rules (schema_version 1 or 2).

Dependency-free on purpose so contributors can run it with any Python 3:

    python3 scripts/validate.py

Exit 0 = valid (warnings allowed), exit 1 = errors. The rules mirror
schema/index.schema.json plus the cross-entry checks a JSON Schema can't
express (unique slugs, sha256 recommendation, in-repo logo existence).

Schema v2 (additive) adds three optional fields:
  - logo    — https URL or repo-relative 'assets/<slug>/<file>' path
  - repo    — https URL of the extension's source repository
  - bundled — true for builtin extensions shipped inside the panel; these
              are catalog listings, so `source`/`sha256` are optional.
v1 entries stay valid unchanged.
"""
import json
import re
import sys
from pathlib import Path

# Windows consoles often default to cp1252, which can't print the ✔/✘/⚠
# markers; never let the report itself crash the validator.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    pass

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / 'index.json'

CATEGORIES = {'ai', 'monitoring', 'networking', 'security', 'deployment', 'integration', 'ui', 'utility'}
KNOWN_FIELDS = {
    'slug', 'display_name', 'description', 'version', 'category', 'author',
    'first_party', 'bundled', 'permissions', 'min_panel_version',
    'max_panel_version', 'source', 'sha256', 'repo', 'logo', 'homepage',
    'icon', 'screenshots', 'featured', 'feature_score',
}
SLUG_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
SEMVER_RE = re.compile(r'^\d+\.\d+(\.\d+)?([.-][0-9A-Za-z.-]+)?$')
SHA256_RE = re.compile(r'^[0-9a-f]{64}$')
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
LOGO_ASSET_RE = re.compile(r'^assets/[a-z0-9]+(-[a-z0-9]+)*/[A-Za-z0-9._-]+$')
# Same hygiene the panel now enforces: no em/en dashes in registry-surfaced text.
DASH_RE = re.compile(r'[–—]')

errors = []
warnings = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def check_entry(i, e):
    where = f"extensions[{i}]"
    if not isinstance(e, dict):
        err(f"{where}: entry must be an object")
        return None
    slug = e.get('slug')
    where = f"extensions[{i}] ({slug or 'no slug'})"

    bundled = e.get('bundled') is True

    for field in ('slug', 'display_name', 'version'):
        if not e.get(field):
            err(f"{where}: required field '{field}' is missing or empty")
    # `source` is required unless this is a bundled catalog listing.
    if not bundled and not e.get('source'):
        err(f"{where}: required field 'source' is missing or empty "
            f"(only bundled entries may omit it)")

    if slug and not SLUG_RE.match(slug):
        err(f"{where}: slug must be kebab-case ([a-z0-9-])")
    if e.get('version') and not SEMVER_RE.match(str(e['version'])):
        err(f"{where}: version '{e['version']}' is not semver-ish (X.Y[.Z])")
    if 'category' in e and e['category'] not in CATEGORIES:
        err(f"{where}: category '{e.get('category')}' not one of {sorted(CATEGORIES)}")
    for field in ('min_panel_version', 'max_panel_version'):
        v = e.get(field)
        if v is not None and field in e and not SEMVER_RE.match(str(v)):
            err(f"{where}: {field} '{v}' is not semver-ish")

    src = e.get('source') or ''
    if src and not src.startswith('https://'):
        err(f"{where}: source must be an https:// URL")

    sha = e.get('sha256')
    if sha is not None and not SHA256_RE.match(str(sha)):
        err(f"{where}: sha256 must be 64 lowercase hex chars (or null)")
    if sha is None and not bundled:
        warn(f"{where}: no sha256 — installs skip checksum verification "
             f"(strongly recommended; see README)")

    if 'bundled' in e and not isinstance(e['bundled'], bool):
        err(f"{where}: bundled must be a boolean")

    repo = e.get('repo')
    if repo is not None:
        if not isinstance(repo, str) or not repo.startswith('https://'):
            err(f"{where}: repo must be an https:// URL")

    logo = e.get('logo')
    if logo is not None:
        if not isinstance(logo, str):
            err(f"{where}: logo must be a string (https URL or 'assets/<slug>/<file>')")
        elif logo.startswith('https://'):
            pass  # external logo; verify_sources.py HEAD-checks it
        elif LOGO_ASSET_RE.match(logo):
            asset = ROOT / logo
            if not asset.is_file():
                err(f"{where}: logo '{logo}' points into this repo but the file "
                    f"does not exist")
        else:
            err(f"{where}: logo must be an https:// URL or a repo-relative "
                f"'assets/<slug>/<file>' path")

    if 'permissions' in e:
        perms = e['permissions']
        if not isinstance(perms, list) or any(not isinstance(p, str) or not p for p in perms):
            err(f"{where}: permissions must be a list of non-empty strings")

    if 'first_party' in e and not isinstance(e['first_party'], bool):
        err(f"{where}: first_party must be a boolean")

    desc = e.get('description')
    if isinstance(desc, str) and DASH_RE.search(desc):
        err(f"{where}: description contains an em/en dash — use a regular "
            f"hyphen or rephrase (brand-neutral, plain-ASCII punctuation)")

    if 'screenshots' in e:
        shots = e['screenshots']
        if not isinstance(shots, list) or any(
                not isinstance(s, str) or not s.startswith('https://') for s in shots):
            err(f"{where}: screenshots must be a list of https:// URLs")

    for k in e:
        if k not in KNOWN_FIELDS:
            warn(f"{where}: unknown field '{k}' (ignored by the panel)")

    return slug


def main():
    try:
        data = json.loads(INDEX.read_text(encoding='utf-8'))
    except FileNotFoundError:
        print(f"✘ {INDEX} not found"); return 1
    except json.JSONDecodeError as exc:
        print(f"✘ index.json is not valid JSON: {exc}"); return 1

    if data.get('schema_version') not in (1, 2):
        err(f"schema_version must be 1 or 2 (got {data.get('schema_version')!r})")
    if not DATE_RE.match(str(data.get('updated', ''))):
        err(f"updated must be YYYY-MM-DD (got {data.get('updated')!r})")
    exts = data.get('extensions')
    if not isinstance(exts, list):
        err("extensions must be a list")
        exts = []

    seen = {}
    for i, e in enumerate(exts):
        slug = check_entry(i, e)
        if slug:
            if slug in seen:
                err(f"duplicate slug '{slug}' (entries {seen[slug]} and {i})")
            seen[slug] = i

    for w in warnings:
        print(f"  ⚠ {w}")
    for e in errors:
        print(f"  ✘ {e}")
    if errors:
        print(f"\n✘ index.json: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"\n✔ index.json: {len(exts)} entr{'y' if len(exts) == 1 else 'ies'} valid, "
          f"{len(warnings)} warning(s)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
