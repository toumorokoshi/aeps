#!/usr/bin/env python3
"""
Fix script for AEP markdown links.

This script validates and fixes:
1. No markdown links point to .md files (except external GitHub links)
2. All AEP references point to existing AEPs
3. Links follow the correct format
4. HTTP URLs are valid
5. Self-reference links like [aep-123][aep-123] are converted to naked text aep-123
6. Reference-style links with AEP identifiers like [aep-123]: ./0123 are removed

Usage:
    python fix.py [--check] [--path PATH]

Options:
    --check    Only check for violations without fixing them
    --path     Path to AEP directory (default: aep/general)
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple, Set
from urllib.parse import urlparse


def find_aep_directories(aep_path: Path) -> Set[str]:
    """Find all AEP directories and return their numbers."""
    aep_dirs = set()

    if not aep_path.exists():
        print(f"Error: {aep_path} directory not found")
        sys.exit(1)

    for item in aep_path.iterdir():
        if item.is_dir() and item.name.isdigit():
            aep_dirs.add(item.name)

    return aep_dirs


def find_markdown_links(content: str) -> List[Tuple[int, str, str]]:
    """Find all markdown links in content and return (line_number, link_text, url)."""
    links = []
    lines = content.split('\n')

    # Pattern to match markdown links: [text](url)
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

    for line_num, line in enumerate(lines, 1):
        matches = link_pattern.findall(line)
        for link_text, url in matches:
            links.append((line_num, link_text, url))

    return links


def find_self_reference_links(content: str) -> List[Tuple[int, str]]:
    """Find all self-reference links like [aep-123][aep-123] and return (line_number, link_text)."""
    links = []
    lines = content.split('\n')

    # Pattern to match self-reference links: [aep-123][aep-123]
    self_ref_pattern = re.compile(r'\[(aep-\d+)\]\[\1\]', re.IGNORECASE)

    for line_num, line in enumerate(lines, 1):
        matches = self_ref_pattern.findall(line)
        for link_text in matches:
            links.append((line_num, link_text))

    return links


def find_reference_links(content: str) -> List[Tuple[int, str, str]]:
    """Find all reference-style markdown links in content and return (line_number, link_text, url)."""
    links = []
    lines = content.split('\n')

    # Pattern to match reference-style links: [link]: url
    # This matches patterns like [aep.dev]: https://aep.dev/ or [aep-2]: ./0002.md
    ref_pattern = re.compile(r'^\[([^\]]+)\]:\s*(.+)$')

    for line_num, line in enumerate(lines, 1):
        match = ref_pattern.match(line.strip())
        if match:
            link_text = match.group(1)
            url = match.group(2).strip()
            links.append((line_num, link_text, url))

    return links


def is_aep_reference(url: str) -> bool:
    """Check if a URL is an AEP reference."""
    # Match patterns like /0001, ./0001, /0121, etc.
    aep_pattern = re.compile(r'^\.?/(\d+)$')
    return bool(aep_pattern.match(url))


def is_aep_identifier(link_text: str) -> bool:
    """Check if a link text is an AEP identifier (like aep-122, aep-4, etc.)."""
    # Match patterns like aep-122, aep-4, aep-0001, etc.
    aep_id_pattern = re.compile(r'^aep-\d+$', re.IGNORECASE)
    return bool(aep_id_pattern.match(link_text))


def is_http_url(url: str) -> bool:
    """Check if a URL is an HTTP/HTTPS URL."""
    parsed = urlparse(url)
    return parsed.scheme in ('http', 'https')


def is_valid_http_url(url: str) -> bool:
    """Check if a URL is a well-formatted HTTP or HTTPS URL."""
    parsed = urlparse(url)
    return parsed.scheme in ('http', 'https') and bool(parsed.netloc)

def validate_file(file_path: Path, existing_aeps: Set[str], check_only: bool = False) -> Tuple[List[str], List[Tuple[int, str, str]]]:
    """Validate a single markdown file and return list of errors and fixes."""
    errors = []
    fixes = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        errors.append(f"Error reading {file_path}: {e}")
        return errors, fixes

    lines = content.split('\n')
    lines_with_newlines = content.splitlines(keepends=True)

    # Find all types of links
    regular_links = find_markdown_links(content)
    reference_links = find_reference_links(content)
    self_reference_links = find_self_reference_links(content)
    all_links = regular_links + reference_links

    for line_num, link_text, url in all_links:
        line_idx = line_num - 1
        original_line = lines_with_newlines[line_idx]

        # Check for .md suffix (but exclude external GitHub links)
        if url.endswith('.md') and not url.startswith('https://github.com/'):
            error_msg = f"{file_path}:{line_num}: Link '{link_text}' points to .md file: {url}"
            errors.append(error_msg)

            if not check_only:
                # Fix: remove .md extension
                fixed_url = url[:-3]  # Remove .md
                fixed_line = original_line.replace(url, fixed_url)
                fixes.append((line_idx, original_line, fixed_line))
                print(f"  Fixing: {url} -> {fixed_url}")

        # Check AEP references
        if is_aep_reference(url):
            # Extract AEP number
            match = re.match(r'^\.?/(\d+)$', url)
            if match:
                aep_num = match.group(1)
                if aep_num not in existing_aeps:
                    error_msg = f"{file_path}:{line_num}: Link '{link_text}' references non-existent AEP: {url}"
                    errors.append(error_msg)
                    # No automatic fix for non-existent AEPs

        # Check HTTP URLs
        if is_http_url(url):
            if not is_valid_http_url(url):
                error_msg = f"{file_path}:{line_num}: Link '{link_text}' points to invalid HTTP URL: {url}"
                errors.append(error_msg)
                # No automatic fix for invalid HTTP URLs

        # Check for reference-style links with AEP identifiers
        # This checks if the link is a reference-style link (from find_reference_links)
        # and if the link text is an AEP identifier
        if is_aep_identifier(link_text) and any(ref_line == line_num for ref_line, _, _ in reference_links):
            error_msg = f"{file_path}:{line_num}: Reference-style link '{link_text}' should be removed - AEP identifiers should not be used as link text"
            errors.append(error_msg)

            if not check_only:
                # Fix: remove the reference-style link entirely
                fixed_line = original_line.replace(f"[{link_text}]: {url}\n", "")
                if fixed_line == original_line:
                    # Try without newline
                    fixed_line = original_line.replace(f"[{link_text}]: {url}", "")
                fixes.append((line_idx, original_line, fixed_line))
                print(f"  Fixing: Removing reference-style link [{link_text}]: {url}")

    # Check for self-reference links like [aep-123][aep-123]
    for line_num, link_text in self_reference_links:
        line_idx = line_num - 1
        original_line = lines_with_newlines[line_idx]

        error_msg = f"{file_path}:{line_num}: Self-reference link '{link_text}' should be converted to naked text"
        errors.append(error_msg)

        if not check_only:
            # Fix: convert [aep-123][aep-123] to aep-123
            fixed_line = original_line.replace(f"[{link_text}][{link_text}]", link_text)
            fixes.append((line_idx, original_line, fixed_line))
            print(f"  Fixing: [{link_text}][{link_text}] -> {link_text}")

    return errors, fixes


def apply_fixes(file_path: Path, fixes: List[Tuple[int, str, str]]) -> bool:
    """Apply fixes to a file."""
    if not fixes:
        return True

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Apply fixes in reverse order to maintain line indices
        for line_idx, original_line, fixed_line in reversed(fixes):
            # Preserve the original newline character
            if original_line.endswith('\n'):
                if not fixed_line.endswith('\n'):
                    fixed_line += '\n'
            lines[line_idx] = fixed_line

        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return True
    except Exception as e:
        print(f"Error applying fixes to {file_path}: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Fix AEP markdown links')
    parser.add_argument('--check', action='store_true',
                       help='Only check for violations without fixing them')
    parser.add_argument('--path', default='aep/general',
                       help='Path to AEP directory (default: aep/general)')

    args = parser.parse_args()

    aep_path = Path(args.path)
    check_only = args.check

    if check_only:
        print("Checking AEP markdown links for violations...")
    else:
        print("Fixing AEP markdown links...")

    # Find all existing AEPs
    existing_aeps = find_aep_directories(aep_path)
    print(f"Found {len(existing_aeps)} existing AEPs: {sorted(existing_aeps)}")

    # Find all markdown files
    markdown_files = list(aep_path.rglob("*.md.j2"))
    print(f"Found {len(markdown_files)} markdown files to process")

    all_errors = []
    all_fixes = []

    for file_path in markdown_files:
        errors, fixes = validate_file(file_path, existing_aeps, check_only)
        all_errors.extend(errors)
        if fixes:
            all_fixes.append((file_path, fixes))

    # Report results
    if all_errors:
        print(f"\n❌ Found {len(all_errors)} validation errors:")
        for error in all_errors:
            print(f"  {error}")

        if not check_only and all_fixes:
            print(f"\n🔧 Applying {sum(len(fixes) for _, fixes in all_fixes)} fixes...")
            for file_path, fixes in all_fixes:
                if apply_fixes(file_path, fixes):
                    print(f"  Fixed {len(fixes)} issues in {file_path}")
                else:
                    print(f"  Failed to fix issues in {file_path}")
                    sys.exit(1)
            print("✅ All fixes applied successfully!")
        else:
            sys.exit(1)
    else:
        print("\n✅ All links are valid!")
        sys.exit(0)


if __name__ == "__main__":
    main()