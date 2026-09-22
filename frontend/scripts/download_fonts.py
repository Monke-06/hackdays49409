"""
Download self-hosted WOFF2 fonts and OFL licenses for:
- Source Serif 4
- IBM Plex Sans
- IBM Plex Mono
"""
import re
import urllib.request
from pathlib import Path

FONTS_DIR = Path(__file__).parent.parent / "public" / "fonts"
FONTS_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def download_file(url: str, dest: Path) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
    dest.write_bytes(data)
    print(f"Downloaded: {dest.name} ({len(data)} bytes)")
    return data

def verify_ofl(text: str, name: str) -> bool:
    required = [
        "SIL OPEN FONT LICENSE",
        "Version 1.1",
        "PREAMBLE",
        "PERMISSION & CONDITIONS",
    ]
    for req in required:
        if req not in text:
            raise ValueError(f"License for {name} missing required clause: {req!r}")
    print(f"Verified OFL License for {name}: OK")
    return True

# 1. Download & verify licenses
LICENSES = {
    "SOURCE_SERIF_4_LICENSE.txt": "https://raw.githubusercontent.com/adobe-fonts/source-serif/master/LICENSE.md",
    "IBM_PLEX_SANS_LICENSE.txt": "https://raw.githubusercontent.com/IBM/plex/master/LICENSE.txt",
    "IBM_PLEX_MONO_LICENSE.txt": "https://raw.githubusercontent.com/IBM/plex/master/LICENSE.txt",
}

for filename, url in LICENSES.items():
    dest = FONTS_DIR / filename
    data = download_file(url, dest)
    text = data.decode("utf-8", errors="replace")
    verify_ofl(text, filename)

# 2. Download WOFF2 font files
# We fetch from Google Fonts CSS with a modern User-Agent to extract direct woff2 links (latin subset)
FONT_CSS_URLS = {
    "Source Serif 4": (
        "https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,400&display=swap",
        [
            ("SourceSerif4-Regular.woff2", 400, "normal"),
            ("SourceSerif4-SemiBold.woff2", 600, "normal"),
            ("SourceSerif4-Bold.woff2", 700, "normal"),
            ("SourceSerif4-Italic.woff2", 400, "italic"),
        ]
    ),
    "IBM Plex Sans": (
        "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap",
        [
            ("IBMPlexSans-Regular.woff2", 400, "normal"),
            ("IBMPlexSans-Medium.woff2", 500, "normal"),
            ("IBMPlexSans-SemiBold.woff2", 600, "normal"),
            ("IBMPlexSans-Bold.woff2", 700, "normal"),
            ("IBMPlexSans-Italic.woff2", 400, "italic"),
        ]
    ),
    "IBM Plex Mono": (
        "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:ital,wght@0,400;0,500;0,600;1,400&display=swap",
        [
            ("IBMPlexMono-Regular.woff2", 400, "normal"),
            ("IBMPlexMono-Medium.woff2", 500, "normal"),
            ("IBMPlexMono-SemiBold.woff2", 600, "normal"),
            ("IBMPlexMono-Italic.woff2", 400, "italic"),
        ]
    ),
}

for family_name, (css_url, variants) in FONT_CSS_URLS.items():
    print(f"\nFetching CSS for {family_name}...")
    req = urllib.request.Request(css_url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        css_text = resp.read().decode("utf-8")

    # Parse @font-face blocks
    blocks = re.findall(r"@font-face\s*\{([^}]+)\}", css_text)
    for filename, target_weight, target_style in variants:
        found_url = None
        for block in blocks:
            # check latin subset
            if "unicode-range" in block and not any(r in block for r in ["U+0000-00FF", "U+0100-02AF", "U+0020-007E"]):
                continue
            weight_match = re.search(r"font-weight:\s*([0-9]+)", block)
            style_match = re.search(r"font-style:\s*([a-z]+)", block)
            weight = int(weight_match.group(1)) if weight_match else 400
            style = style_match.group(1) if style_match else "normal"

            if weight == target_weight and style == target_style:
                url_match = re.search(r"url\((https://[^)]+\.woff2)\)", block)
                if url_match:
                    found_url = url_match.group(1)
                    break

        if not found_url:
            # fallback: find any match with same weight and style
            for block in blocks:
                weight_match = re.search(r"font-weight:\s*([0-9]+)", block)
                style_match = re.search(r"font-style:\s*([a-z]+)", block)
                weight = int(weight_match.group(1)) if weight_match else 400
                style = style_match.group(1) if style_match else "normal"
                if weight == target_weight and style == target_style:
                    url_match = re.search(r"url\((https://[^)]+\.woff2)\)", block)
                    if url_match:
                        found_url = url_match.group(1)
                        break

        if found_url:
            dest = FONTS_DIR / filename
            download_file(found_url, dest)
        else:
            print(f"Warning: Could not find URL for {family_name} {target_weight} {target_style}")

print("\nAll fonts and licenses successfully downloaded and verified!")
