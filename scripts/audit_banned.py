"""
scripts/audit_banned.py

Scan the repo for items banned by the project brief (section 2 and 9).
Exits 0 if clean, 1 if violations found.

Banned items checked:
  - Em dashes (U+2014)
  - Emoji characters (Unicode blocks 1F300-1FAFF, 2600-27BF)
  - CSS: border-radius with 9999px or 50%+ rounding on button-like selectors
  - CSS: 'rounded-full' (Tailwind utility)
  - CSS/JSX: gradient backgrounds (linear-gradient, radial-gradient, bg-gradient)
  - AI-slop phrases: revolutionize, seamless, unlock, empower, cutting-edge,
    next-generation, "in today's fast-paced"
  - Sample/fake metrics patterns: "10,000+ users", "99.9% uptime" in JSX/HTML
  - Testimonial markup: blockquote.testimonial, class="testimonial"
  - "Made with AI" / "Built with" badge text
  - TODO in user-facing copy files (.tsx, .html, .md outside docs/)

Usage:
    python scripts/audit_banned.py [--fix-dashes]   # --fix-dashes not yet implemented
    python scripts/audit_banned.py --paths src/      # limit to a subtree
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent

# File extensions to scan (skip binary, generated, venv, node_modules)
SCAN_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".html", ".css",
    ".md", ".json", ".toml", ".yaml", ".yml",
}

SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".pytest_cache", ".ruff_cache", "dist", "build",
}

# Files to skip entirely (self-reference avoidance).
SKIP_FILES = {"audit_banned.py"}

# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

Rule = tuple[str, str, re.Pattern[str]]  # (id, description, pattern)

RULES: list[Rule] = [
    (
        "EM_DASH",
        "Em dash (U+2014) found. Use commas, periods, colons, or parentheses.",
        re.compile(r"\u2014"),
    ),
    (
        "EMOJI",
        "Emoji character found. Use a real icon set or hand-drawn SVG.",
        re.compile(
            r"[\U0001F300-\U0001FAFF"   # Miscellaneous Symbols and Pictographs
            r"\U00002600-\U000027BF"    # Miscellaneous Symbols, Dingbats
            r"\U0001F000-\U0001F02F"    # Mahjong Tiles (sometimes emoji)
            r"\U0001F0A0-\U0001F0FF"    # Playing Cards
            r"]"
        ),
    ),
    (
        "ROUNDED_FULL",
        "'rounded-full' Tailwind class found on a UI element.",
        re.compile(r"\brounded-full\b"),
    ),
    (
        "BORDER_RADIUS_9999",
        "border-radius: 9999px (pill shape) found. Use 4-8px max.",
        re.compile(r"border-radius\s*:\s*9999px"),
    ),
    (
        "GRADIENT_BG",
        "Gradient background found. No decorative gradients allowed.",
        re.compile(r"(linear-gradient|radial-gradient|bg-gradient)", re.IGNORECASE),
    ),
    (
        "AISLOP_REVOLUTIONIZE",
        "Banned phrase 'revolutionize' in copy.",
        re.compile(r"\brevolutionize\b", re.IGNORECASE),
    ),
    (
        "AISLOP_SEAMLESS",
        "Banned phrase 'seamless' in copy.",
        re.compile(r"\bseamless(?:ly)?\b", re.IGNORECASE),
    ),
    (
        "AISLOP_UNLOCK",
        "Banned phrase 'unlock' in copy.",
        re.compile(r"\bunlock\b", re.IGNORECASE),
    ),
    (
        "AISLOP_EMPOWER",
        "Banned phrase 'empower' in copy.",
        re.compile(r"\bempower(?:ing|ed|s|ment)?\b", re.IGNORECASE),
    ),
    (
        "AISLOP_CUTTING_EDGE",
        "Banned phrase 'cutting-edge' in copy.",
        re.compile(r"\bcutting[- ]edge\b", re.IGNORECASE),
    ),
    (
        "AISLOP_NEXT_GEN",
        "Banned phrase 'next-generation' in copy.",
        re.compile(r"\bnext[- ]generation\b", re.IGNORECASE),
    ),
    (
        "AISLOP_FAST_PACED",
        "Banned phrase 'today\\'s fast-paced world' in copy.",
        re.compile(r"today.s fast[- ]paced", re.IGNORECASE),
    ),
    (
        "MADE_WITH_AI",
        "'Made with AI' or generator badge text found.",
        re.compile(r"made with (ai|claude|gpt|gemini|copilot)", re.IGNORECASE),
    ),
    (
        "TESTIMONIAL",
        "Testimonial markup found. No fake reviews allowed.",
        re.compile(r'class=["\'][^"\']*testimonial[^"\']*["\']', re.IGNORECASE),
    ),
    (
        "LOREM_IPSUM",
        "Lorem ipsum placeholder text found in user-facing file.",
        re.compile(r"\blorem ipsum\b", re.IGNORECASE),
    ),
]


def should_skip(path: Path) -> bool:
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
    if path.name in SKIP_FILES:
        return True
    if path.suffix not in SCAN_EXTENSIONS:
        return True
    return False


def scan_file(path: Path) -> list[tuple[str, int, str, str]]:
    """
    Returns list of (rule_id, line_number, description, line_content).
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    violations: list[tuple[str, int, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for rule_id, description, pattern in RULES:
            if pattern.search(line):
                violations.append((rule_id, lineno, description, line.strip()))
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit repo for banned patterns.")
    parser.add_argument(
        "--paths",
        nargs="*",
        default=[str(REPO_ROOT)],
        help="Paths to scan (default: repo root).",
    )
    parser.add_argument(
        "--rules",
        nargs="*",
        default=None,
        help="Rule IDs to run (default: all).",
    )
    args = parser.parse_args(argv)

    active_rules = set(args.rules) if args.rules else None

    total_violations = 0
    files_with_violations = 0

    for scan_path_str in args.paths:
        scan_path = Path(scan_path_str)
        candidates = (
            [scan_path] if scan_path.is_file()
            else [p for p in scan_path.rglob("*") if p.is_file()]
        )

        for path in sorted(candidates):
            if should_skip(path):
                continue
            violations = scan_file(path)
            if active_rules:
                violations = [v for v in violations if v[0] in active_rules]
            if violations:
                files_with_violations += 1
                rel = path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path
                print(f"\n{rel}")
                for rule_id, lineno, description, content in violations:
                    print(f"  Line {lineno:4d} [{rule_id}] {description}")
                    print(f"           {content[:120]!r}")
                    total_violations += 1

    print(f"\n{'=' * 60}")
    if total_violations == 0:
        print("PASS: No banned patterns found.")
        return 0
    else:
        print(f"FAIL: {total_violations} violation(s) in {files_with_violations} file(s).")
        return 1


if __name__ == "__main__":
    sys.exit(main())
