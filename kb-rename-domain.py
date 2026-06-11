#!/usr/bin/env python3
"""Rename a domain value across card files and kb.yml configs.

Usage:
  kb-rename-domain.py [-r] [-n] <path> <old-domain> <new-domain>

Arguments:
  path         A .kb.md file, a .kb directory, or a parent directory
  old-domain   The domain value to replace
  new-domain   The replacement domain value

Options:
  -r, --recursive  Recurse into subdirectories looking for .kb directories
  -n, --dry-run    Show what would change without modifying files
"""

import argparse
import re
import sys
from pathlib import Path


def _update_card_file(path: Path, old: str, new: str, dry_run: bool) -> bool:
    """Replace domain in YAML frontmatter of a .kb.md file. Returns True if changed."""
    text = path.read_text(encoding='utf-8')

    # Only scan the YAML frontmatter block (between the first pair of --- delimiters)
    fm_match = re.match(r'^(---\n)(.*?)(\n---)', text, re.DOTALL)
    if not fm_match:
        return False

    before = fm_match.start(2)
    after = fm_match.end(2)
    frontmatter = text[before:after]

    pattern = re.compile(r'^(domain:\s*)' + re.escape(old) + r'(\s*)$', re.MULTILINE)
    new_frontmatter = pattern.sub(r'\g<1>' + new + r'\2', frontmatter)
    if new_frontmatter == frontmatter:
        return False

    if not dry_run:
        path.write_text(text[:before] + new_frontmatter + text[after:], encoding='utf-8')
    return True


def _update_kb_yml(path: Path, old: str, new: str, dry_run: bool) -> bool:
    """Replace domain in a kb.yml file. Returns True if changed."""
    text = path.read_text(encoding='utf-8')
    pattern = re.compile(r'^(domain:\s*)' + re.escape(old) + r'(\s*)$', re.MULTILINE)
    new_text = pattern.sub(r'\g<1>' + new + r'\2', text)
    if new_text == text:
        return False
    if not dry_run:
        path.write_text(new_text, encoding='utf-8')
    return True


def _files_in_kb_dir(kb_dir: Path):
    """Yield eligible files inside a .kb directory."""
    for f in sorted(kb_dir.iterdir()):
        if f.is_file() and (f.name.endswith('.kb.md') or f.name == 'kb.yml'):
            yield f


def collect_files(root: Path, recursive: bool):
    """Yield files to process based on the given root path and recursion flag."""
    # Single card file
    if root.is_file():
        if root.name.endswith('.kb.md'):
            yield root
        else:
            print(f'Warning: {root} is not a .kb.md file — skipping', file=sys.stderr)
        return

    # .kb directory: process it directly, then recurse into siblings if -r
    if root.name == '.kb' and root.is_dir():
        yield from _files_in_kb_dir(root)
        if recursive:
            for kb_dir in sorted(root.parent.rglob('.kb')):
                if kb_dir != root and kb_dir.is_dir():
                    yield from _files_in_kb_dir(kb_dir)
        return

    # Regular directory
    if recursive:
        for kb_dir in sorted(root.rglob('.kb')):
            if kb_dir.is_dir():
                yield from _files_in_kb_dir(kb_dir)
    else:
        kb_dir = root / '.kb'
        if kb_dir.is_dir():
            yield from _files_in_kb_dir(kb_dir)
        else:
            print(f'Warning: no .kb directory found directly under {root}', file=sys.stderr)
            print('Use -r to search recursively.', file=sys.stderr)


def update_file(path: Path, old: str, new: str, dry_run: bool) -> bool:
    if path.name == 'kb.yml':
        return _update_kb_yml(path, old, new, dry_run)
    return _update_card_file(path, old, new, dry_run)


def main():
    parser = argparse.ArgumentParser(
        description='Rename a domain value in card files and kb.yml configs.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Rename in one .kb directory
  kb-rename-domain.py path/to/.kb automotive-sdv automotive

  # Rename across all .kb directories under Execution/26/
  kb-rename-domain.py -r Execution/26/ automotive-sdv automotive

  # Preview without changing anything
  kb-rename-domain.py -rn Execution/ automotive-sdv automotive

  # Rename in a single card file
  kb-rename-domain.py path/to/card.kb.md automotive-sdv automotive
        """
    )
    parser.add_argument('path', help='A .kb.md file, .kb directory, or parent directory')
    parser.add_argument('old', metavar='old-domain', help='Domain value to replace')
    parser.add_argument('new', metavar='new-domain', help='Replacement domain value')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='Recurse into subdirectories looking for .kb directories')
    parser.add_argument('-n', '--dry-run', action='store_true',
                        help='Show what would change without modifying files')
    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.exists():
        print(f'Error: {args.path} does not exist', file=sys.stderr)
        return 1

    if args.dry_run:
        print(f'Dry run: domain {args.old!r} → {args.new!r}\n')

    changed = 0
    unchanged = 0

    for file_path in collect_files(root, args.recursive):
        if update_file(file_path, args.old, args.new, args.dry_run):
            verb = 'would update' if args.dry_run else 'updated'
            print(f'  {verb}: {file_path}')
            changed += 1
        else:
            unchanged += 1

    if changed == 0 and unchanged == 0:
        print(f'No eligible files found under {args.path}')
        return 1

    verb = 'would update' if args.dry_run else 'updated'
    print(f'\n{changed} file(s) {verb}, {unchanged} skipped (domain not matched).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
