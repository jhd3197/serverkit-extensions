#!/usr/bin/env python3
"""Validate index.json against the registry rules (schema_version 1, 2 or 3).

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
Schema v3 (additive) adds three optional fields:
  - review  — hash-bound review stamp: {reviewer, date, sha256, ...} asserting
              that `reviewer` inspected the exact artifact `review.sha256`
              names. review.sha256 must equal the entry's own sha256, so any
              change to the released zip invalidates the stamp.
  - signature / publisher_key_id — base64 ed25519 detached signature over the
              release zip, plus the id of the pinned publisher key that must
              verify it. The panel reads both (signing_service.verify_for_install);
              a first_party entry without them costs an install-consent prompt.
v1/v2 entries stay valid unchanged.

The accepted field list is READ FROM schema/index.schema.json rather than
duplicated here, so the published contract and this validator cannot drift —
that drift is what previously left `signature` undocumented in the schema and
absent from the validator's field list at the same time.
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
SCHEMA = ROOT / 'schema' / 'index.schema.json'

CATEGORIES = {'ai', 'games', 'monitoring', 'networking', 'security', 'deployment', 'integration', 'ui', 'utility'}
# Used only when the schema file cannot be read; the schema is the source of
# truth (see _known_fields). Keep in sync as a last resort, not as the contract.
_FALLBACK_FIELDS = {
    'slug', 'display_name', 'description', 'version', 'category', 'author',
    'first_party', 'bundled', 'permissions', 'min_panel_version',
    'max_panel_version', 'source', 'sha256', 'signature', 'publisher_key_id',
    'review', 'repo', 'logo', 'homepage', 'icon', 'screenshots', 'featured',
    'feature_score',
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


def _known_fields():
    """Entry fields the published schema documents.

    Read from schema/index.schema.json so the contract contributors are told
    to follow and the check that enforces it are the same list. Still
    dependency-free — this reads the property names, it does not run a JSON
    Schema engine. An unreadable schema degrades to the frozen fallback with a
    warning rather than declaring every field unknown.
    """
    try:
        with open(SCHEMA, 'r', encoding='utf-8') as f:
            props = json.load(f)['$defs']['extension']['properties']
        if props:
            return set(props)
        warn(f"{SCHEMA.name}: extension.properties is empty; using the fallback field list")
    except Exception as e:  # unreadable, malformed, or restructured
        warn(f"{SCHEMA.name} could not be read ({e}); using the fallback field list")
    return set(_FALLBACK_FIELDS)


KNOWN_FIELDS = _known_fields()


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

    review = e.get('review')
    if review is not None:
        if not isinstance(review, dict):
            err(f"{where}: review must be an object "
                f"({{reviewer, date, sha256, ...}})")
        else:
            if not review.get('reviewer') or not isinstance(review.get('reviewer'), str):
                err(f"{where}: review.reviewer is required (GitHub handle)")
            rdate = review.get('date')
            if not rdate or not DATE_RE.match(str(rdate)):
                err(f"{where}: review.date is required (YYYY-MM-DD)")
            rsha = review.get('sha256')
            if not rsha or not SHA256_RE.match(str(rsha)):
                err(f"{where}: review.sha256 is required (64 lowercase hex — "
                    f"the reviewed artifact)")
            elif sha is None:
                err(f"{where}: review.sha256 present but the entry has no "
                    f"sha256 — pin the artifact hash first")
            elif rsha != sha:
                err(f"{where}: review.sha256 does not match the entry sha256 — "
                    f"the stamp is for a different artifact (stale review?)")
    elif not e.get('first_party') and not bundled:
        warn(f"{where}: community entry without a review stamp — the panel "
             f"marks it 'unreviewed' and asks installers to acknowledge the risk")

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

    # A signature the panel cannot attribute to a key verifies nothing, and a
    # key id with no signature verifies nothing either. Both or neither.
    has_sig = bool(e.get('signature'))
    has_key = bool(e.get('publisher_key_id'))
    if has_sig and not has_key:
        err(f"{where}: signature is set but publisher_key_id is not — the "
            f"panel needs the key id to know which pinned key must verify it")
    if has_key and not has_sig:
        err(f"{where}: publisher_key_id is set but signature is not — nothing "
            f"for that key to verify")
    if has_sig and not e.get('sha256'):
        err(f"{where}: signature is set but sha256 is not — the signature "
            f"covers the artifact, so the artifact must also be pinned")
    if e.get('first_party') is True and not bundled and not (has_sig and has_key):
        err(f"{where}: downloadable first-party releases must carry a "
            f"signature and publisher_key_id")

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
            warn(f"{where}: field '{k}' is not in schema/index.schema.json. "
                 f"The panel drops fields it does not register, so either add "
                 f"it to the schema or remove it")

    return slug


def main():
    try:
        data = json.loads(INDEX.read_text(encoding='utf-8'))
    except FileNotFoundError:
        print(f"✘ {INDEX} not found"); return 1
    except json.JSONDecodeError as exc:
        print(f"✘ index.json is not valid JSON: {exc}"); return 1

    if data.get('schema_version') not in (1, 2, 3):
        err(f"schema_version must be 1, 2 or 3 (got {data.get('schema_version')!r})")
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
