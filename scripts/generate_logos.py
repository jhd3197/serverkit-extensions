#!/usr/bin/env python3
"""Generate registry logos for extensions that don't ship art yet.

House style follows assets/serverkit-gui/logo.svg: a 48x48 flat mark on a
dark rounded container (#0f172a), 2px round-capped strokes in a per-extension
accent color, all essential detail inside the inner 80% safe zone (see
assets/_brand/README.md). SVGs are a few hundred bytes, far under the
200 KB registry limit.

Idempotent: existing logo files are never overwritten, and index.json only
gains "logo" fields where none is set. Run from anywhere:

    python3 scripts/generate_logos.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / 'index.json'

# slug -> (aria label, accent color, inner glyph markup)
# Glyph canvas is 48x48; keep strokes inside ~7..41 (the safe zone).
LOGOS = {
    'serverkit-cloud-provision': (
        'Cloud Provisioning', '#38bdf8',
        '<path d="M15 31h18a6 6 0 0 0 1.2-11.9 9 9 0 0 0-17.4-2.1A6.5 6.5 0 0 0 15 31z" fill="none" stroke="{a}" stroke-width="2" stroke-linejoin="round"/>'
        '<path d="M24 39v-9m0 0-4 4m4-4 4 4" fill="none" stroke="{a}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    'serverkit-cloudflare-ops': (
        'Cloudflare Zone Ops', '#fb923c',
        '<path d="M14 27h20a5.5 5.5 0 0 0 1.1-10.9 8.5 8.5 0 0 0-16.5-2A6 6 0 0 0 14 27z" fill="none" stroke="{a}" stroke-width="2" stroke-linejoin="round"/>'
        '<path d="M15 33h10m4 0h4" stroke="{a}" stroke-width="2" stroke-linecap="round"/>'
        '<path d="M15 38h6m4 0h8" stroke="{a}" stroke-width="2" stroke-linecap="round" opacity="0.55"/>'
        '<circle cx="27" cy="33" r="2" fill="{a}"/>'
        '<circle cx="23" cy="38" r="2" fill="{a}" opacity="0.55"/>'
    ),
    'serverkit-crowdsec': (
        'CrowdSec', '#f87171',
        '<path d="M24 8l12 4.5V22c0 8-5.4 13.8-12 16-6.6-2.2-12-8-12-16v-9.5z" fill="none" stroke="{a}" stroke-width="2" stroke-linejoin="round"/>'
        '<circle cx="18.5" cy="21" r="1.8" fill="{a}"/>'
        '<circle cx="24" cy="21" r="1.8" fill="{a}"/>'
        '<circle cx="29.5" cy="21" r="1.8" fill="{a}"/>'
        '<path d="M17 27c2 3.5 4.5 5.5 7 6.5 2.5-1 5-3 7-6.5" fill="none" stroke="{a}" stroke-width="2" stroke-linecap="round"/>'
    ),
    'serverkit-dns-server': (
        'DNS Server', '#22d3ee',
        '<circle cx="24" cy="24" r="14" fill="none" stroke="{a}" stroke-width="2"/>'
        '<ellipse cx="24" cy="24" rx="6.5" ry="14" fill="none" stroke="{a}" stroke-width="2"/>'
        '<path d="M10.6 19h26.8M10.6 29h26.8" stroke="{a}" stroke-width="2" stroke-linecap="round"/>'
    ),
    'serverkit-email': (
        'Email Server', '#fbbf24',
        '<rect x="10" y="15" width="28" height="19" rx="3" fill="none" stroke="{a}" stroke-width="2"/>'
        '<path d="M11.5 17.5 24 27l12.5-9.5" fill="none" stroke="{a}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    'serverkit-ftp': (
        'FTP Server', '#a3e635',
        '<path d="M10 15a2 2 0 0 1 2-2h8l3 4h13a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H12a2 2 0 0 1-2-2z" fill="none" stroke="{a}" stroke-width="2" stroke-linejoin="round"/>'
        '<path d="M19 31v-6m0 0-2.5 2.5M19 25l2.5 2.5" fill="none" stroke="{a}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M29 25v6m0 0-2.5-2.5M29 31l2.5-2.5" fill="none" stroke="{a}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    'serverkit-git': (
        'Git Server', '#f97316',
        '<circle cx="14" cy="13" r="3.5" fill="none" stroke="{a}" stroke-width="2"/>'
        '<circle cx="14" cy="35" r="3.5" fill="none" stroke="{a}" stroke-width="2"/>'
        '<circle cx="34" cy="15" r="3.5" fill="none" stroke="{a}" stroke-width="2"/>'
        '<path d="M14 16.5v15" stroke="{a}" stroke-width="2" stroke-linecap="round"/>'
        '<path d="M34 18.5c0 7.5-6 8.5-14 11" fill="none" stroke="{a}" stroke-width="2" stroke-linecap="round"/>'
    ),
    'serverkit-gpu': (
        'GPU Monitor', '#4ade80',
        '<rect x="14" y="14" width="20" height="20" rx="3" fill="none" stroke="{a}" stroke-width="2"/>'
        '<rect x="20.5" y="20.5" width="7" height="7" rx="1.5" fill="none" stroke="{a}" stroke-width="2"/>'
        '<path d="M19 14V9m5 5V9m5 5V9M19 39v-5m5 5v-5m5 5v-5M14 19H9m5 5H9m5 5H9m30-10h-5m5 5h-5m5 5h-5" stroke="{a}" stroke-width="2" stroke-linecap="round"/>'
    ),
    'serverkit-mail': (
        'Mail Server', '#a78bfa',
        '<path d="M11 33V20a7 7 0 0 1 14 0v13" fill="none" stroke="{a}" stroke-width="2" stroke-linejoin="round"/>'
        '<path d="M11 33h26v-9a4 4 0 0 0-8 0" fill="none" stroke="{a}" stroke-width="2" stroke-linejoin="round"/>'
        '<path d="M31 20v-6h5" fill="none" stroke="{a}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M24 33v6" stroke="{a}" stroke-width="2" stroke-linecap="round"/>'
    ),
    'serverkit-remote-access': (
        'Remote Access', '#2dd4bf',
        '<path d="M11 36v-5a13 13 0 0 1 26 0v5" fill="none" stroke="{a}" stroke-width="2" stroke-linecap="round"/>'
        '<circle cx="24" cy="27" r="3.5" fill="none" stroke="{a}" stroke-width="2"/>'
        '<path d="M24 30.5V36" stroke="{a}" stroke-width="2" stroke-linecap="round"/>'
    ),
    'serverkit-status': (
        'Status Pages', '#34d399',
        '<path d="M9 24h7l4-11 7 22 4-11h8" fill="none" stroke="{a}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    'serverkit-wordpress': (
        'WordPress', '#60a5fa',
        '<circle cx="24" cy="24" r="15" fill="none" stroke="{a}" stroke-width="2"/>'
        '<path d="M15 19l3.5 12L24 20l5.5 11L33 19" fill="none" stroke="{a}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    'serverkit-k8s': (
        'Kubernetes', '#818cf8',
        '<path d="M24 8l13.9 8v16L24 40l-13.9-8V16z" fill="none" stroke="{a}" stroke-width="2" stroke-linejoin="round"/>'
        '<circle cx="24" cy="24" r="4" fill="none" stroke="{a}" stroke-width="2"/>'
        '<path d="M24 20v-8m3.5 6.2 9.4-3.4m-6.9 7 9.4 3.4M27.5 28l-1.5 7.6M20.5 28l-1.5 7.6m1.5-13.8-9.4 3.4m6.9-7-9.4-3.4" stroke="{a}" stroke-width="2" stroke-linecap="round"/>'
    ),
    'serverkit-tramo': (
        'Automations', '#f472b6',
        '<rect x="18" y="9" width="12" height="8" rx="2" fill="none" stroke="{a}" stroke-width="2"/>'
        '<rect x="9" y="31" width="12" height="8" rx="2" fill="none" stroke="{a}" stroke-width="2"/>'
        '<rect x="27" y="31" width="12" height="8" rx="2" fill="none" stroke="{a}" stroke-width="2"/>'
        '<path d="M24 17v5m0 0-9 4v5m9-9 9 4v5" fill="none" stroke="{a}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    ),
}

TEMPLATE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48"'
    ' role="img" aria-label="{label}">\n'
    '  <rect width="48" height="48" rx="10" fill="#0f172a"/>\n'
    '  {glyph}\n'
    '</svg>\n'
)


def main():
    index = json.loads(INDEX.read_text(encoding='utf-8'))
    slugs = {e['slug'] for e in index['extensions']}

    missing = sorted(slugs - set(LOGOS) - {'serverkit-gui',
                                           'serverkit-analytics',
                                           'serverkit-faro'})
    if missing:
        print(f'note: no generator art for: {", ".join(missing)}')

    written = []
    for slug, (label, accent, glyph) in sorted(LOGOS.items()):
        if slug not in slugs:
            print(f'skip {slug}: not in index.json')
            continue
        out = ROOT / 'assets' / slug / 'logo.svg'
        if out.exists():
            print(f'keep {out.relative_to(ROOT)} (already exists)')
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            body = '\n  '.join(
                line.format(a=accent) for line in glyph.split('\n'))
            out.write_text(TEMPLATE.format(label=label, glyph=body),
                           encoding='utf-8', newline='\n')
            written.append(slug)
            print(f'wrote {out.relative_to(ROOT)}')

    # Wire the logo field wherever an asset exists but the entry has none.
    wired = []
    for entry in index['extensions']:
        slug = entry['slug']
        if entry.get('logo'):
            continue
        for name in ('logo.svg', 'logo.png', 'logo.jpg', 'logo.webp'):
            rel = f'assets/{slug}/{name}'
            if (ROOT / rel).is_file():
                entry['logo'] = rel
                wired.append(rel)
                print(f'index: {slug} -> {rel}')
                break

    INDEX.write_text(json.dumps(index, indent=2, ensure_ascii=False) + '\n',
                     encoding='utf-8', newline='\n')
    print(f'\n{len(written)} logo(s) generated, {len(wired)} index entrie(s) wired')


if __name__ == '__main__':
    main()
