"""
Contrast ratio verification script for design/DESIGN.md.
Uses WCAG 2.1 relative luminance formula for the warm paper palette:
Background: #F6F5F1, Text: #1B1B18, Accent: #1D4E6B, Verdicts: Green/Red/Amber/Grey
"""

def srgb_to_linear(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def luminance(r: int, g: int, b: int) -> float:
    return 0.2126 * srgb_to_linear(r) + 0.7152 * srgb_to_linear(g) + 0.0722 * srgb_to_linear(b)

def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip('#')
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def contrast(fg: str, bg: str) -> float:
    l1 = luminance(*hex_to_rgb(fg))
    l2 = luminance(*hex_to_rgb(bg))
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

def wcag_level(ratio: float) -> str:
    if ratio >= 7.0:
        return "AAA"
    elif ratio >= 4.5:
        return "AA"
    elif ratio >= 3.0:
        return "AA Large"
    return "FAIL"

# Warm Paper Tokens
TOKENS = {
    "bg-canvas":              "#F6F5F1",  # Warm paper background
    "bg-surface":             "#FFFFFF",  # Elevated white surface
    "bg-subtle":              "#EFECE6",  # Warm grey subtle
    "bg-muted":               "#E2DDD5",
    "text-primary":           "#1B1B18",  # Near-black charcoal
    "text-secondary":         "#4A4944",  # Dark warm grey
    "text-muted":             "#6B6963",  # Medium warm grey (helper text)
    "action-primary":         "#1D4E6B",  # Deep petroleum blue accent
    "action-primary-text":    "#FFFFFF",
    "action-danger":          "#8B1E1E",  # Deep crimson
    "verdict-green-text":     "#184F31",  # Supported
    "verdict-green-bg":       "#EBF5EE",
    "verdict-red-text":       "#8B1E1E",  # Contradicted
    "verdict-red-bg":         "#FAECEC",
    "verdict-amber-text":     "#784400",  # Suspicious boundary shift
    "verdict-amber-bg":       "#FDF5E6",
    "verdict-grey-text":      "#4A4944",  # Insufficient evidence
    "verdict-grey-bg":        "#EFECE6",
}

pairs = [
    ("Primary text #1B1B18 on warm paper canvas",   "text-primary",        "bg-canvas"),
    ("Primary text #1B1B18 on white surface",       "text-primary",        "bg-surface"),
    ("Secondary text #4A4944 on warm paper canvas", "text-secondary",      "bg-canvas"),
    ("Secondary text #4A4944 on white surface",     "text-secondary",      "bg-surface"),
    ("Muted text #6B6963 on warm paper canvas",     "text-muted",          "bg-canvas"),
    ("Muted text #6B6963 on white surface",         "text-muted",          "bg-surface"),
    ("Muted text #6B6963 on subtle bg #EFECE6",     "text-muted",          "bg-subtle"),
    ("Accent button text (#FFFFFF on #1D4E6B)",     "action-primary-text", "action-primary"),
    ("Accent link #1D4E6B on warm paper canvas",    "action-primary",      "bg-canvas"),
    ("Accent link #1D4E6B on white surface",        "action-primary",      "bg-surface"),
    ("Danger button text (#FFFFFF on #8B1E1E)",     "action-primary-text", "action-danger"),
    ("Verdict Supported: #184F31 on #EBF5EE",       "verdict-green-text",  "verdict-green-bg"),
    ("Verdict Contradicted: #8B1E1E on #FAECEC",    "verdict-red-text",    "verdict-red-bg"),
    ("Verdict Boundary Shift: #784400 on #FDF5E6",  "verdict-amber-text",  "verdict-amber-bg"),
    ("Verdict Insufficient: #4A4944 on #EFECE6",    "verdict-grey-text",   "verdict-grey-bg"),
]

print(f"{'Pair':<48} {'Fg Hex':<10} {'Bg Hex':<10} {'Ratio':>7} {'WCAG Level'}")
print("-" * 88)

for label, fg_key, bg_key in pairs:
    fg = TOKENS[fg_key]
    bg = TOKENS[bg_key]
    r = contrast(fg, bg)
    level = wcag_level(r)
    print(f"{label:<48} {fg:<10} {bg:<10} {r:>7.2f} {level}")

print()
print("Notes on Compliance:")
print("  - Primary text: >= 15:1 (AAA on all surfaces)")
print("  - Secondary text: >= 8:1 (AAA on all surfaces)")
print("  - Muted/helper text: 5.03:1 on paper, 5.49:1 on surface (AA, normal text)")
print("  - Accent and Danger actions: AAA/AA compliant")
print("  - Verdict banners: all >= 7:1 (AAA compliant)")
