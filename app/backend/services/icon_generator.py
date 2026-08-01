"""
icon_generator.py — generates palette-colored Shira icons.

Given a palette ID (matrix, amber, blood, etc.), generates:
1. A colored PNG icon using the palette's accent color
2. A multi-resolution ICO file

The icon is created from Ico_Shine.png template:
- Extract the logo shape (alpha channel)
- Fill with palette's accent color
- Add dark outline for contrast on light backgrounds
- Add subtle glow using palette's foreground color
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

logger = logging.getLogger(__name__)

# Project root (2 levels up from this file: app/backend/services/ → root)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_PNG = PROJECT_ROOT / "Ico_Shine.png"
OUTPUT_ICO = PROJECT_ROOT / "shira.ico"
OUTPUT_PNG = PROJECT_ROOT / "shira_current.png"

# Import palettes from runtime_state
try:
    from app.backend.models.runtime_state import TERMINAL_PALETTES
except (ImportError, AttributeError):
    logger.debug("TERMINAL_PALETTES not available from runtime_state, using fallback")
    TERMINAL_PALETTES = {
        "matrix": {
            "name": "Terminal Green",
            "bg": "#0d1b0d",
            "fg": "#8fbf8f",
            "acc": "#6aa86a",
            "muted": "#3d5a3d",
            "success": "#8fbf8f",
            "danger": "#cf6a6a",
            "warning": "#d4b87a",
            "icon_color": "#8fbf8f",
        },
        "amber": {
            "name": "Amber CRT",
            "bg": "#1a1202",
            "fg": "#d4a843",
            "acc": "#c8963a",
            "muted": "#6b5426",
            "success": "#8fc97a",
            "danger": "#c97a7a",
            "warning": "#d4b843",
            "icon_color": "#d4a843",
        },
        "inverse": {
            "name": "Инверсия",
            "bg": "#e8e8e8",
            "fg": "#2a2a2a",
            "acc": "#555555",
            "muted": "#a0a0a0",
            "success": "#4a7a4a",
            "danger": "#a04040",
            "warning": "#907030",
            "icon_color": "#e8e8e8",
        },
        "grey": {
            "name": "Paper White",
            "bg": "#181818",
            "fg": "#c8c8c8",
            "acc": "#a0a0a0",
            "muted": "#555555",
            "success": "#88aa88",
            "danger": "#aa7777",
            "warning": "#aaa888",
            "icon_color": "#a0a0a0",
        },
        "synthwave": {
            "name": "Dusk",
            "bg": "#141020",
            "fg": "#b8a8d0",
            "acc": "#9888b8",
            "muted": "#5a4a7a",
            "success": "#7ab88a",
            "danger": "#b87a7a",
            "warning": "#d0b87a",
            "icon_color": "#b8a8d0",
        },
        "blood": {
            "name": "Crimson",
            "bg": "#1a0808",
            "fg": "#d08888",
            "acc": "#c07070",
            "muted": "#6a3a3a",
            "success": "#7ab88a",
            "danger": "#c07070",
            "warning": "#d0b87a",
            "icon_color": "#d08888",
        },
    }


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert '#rrggbb' to (r, g, b) tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return (100, 200, 100)  # fallback green
    try:
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )
    except ValueError:
        return (100, 200, 100)


def generate_palette_icon(
    palette_id: str, output_path: Path | None = None
) -> Path | None:
    """Generate a palette-colored icon PNG.

    Args:
        palette_id: one of TERMINAL_PALETTES keys
        output_path: where to save PNG (default: shira_current.png in project root)

    Returns:
        Path to generated PNG, or None on failure.
    """
    palette = TERMINAL_PALETTES.get(palette_id)
    if not palette:
        logger.warning(f"Unknown palette: {palette_id}")
        return None

    if not TEMPLATE_PNG.exists():
        logger.warning(f"Template icon not found: {TEMPLATE_PNG}")
        return None

    try:
        # Load template
        orig = Image.open(TEMPLATE_PNG).convert("RGBA")
        alpha = orig.split()[3]

        # Get palette colors — use icon_color if defined, else fall back to acc
        icon_color_hex = palette.get("icon_color", palette.get("acc", "#6aa86a"))
        accent_rgb = hex_to_rgb(icon_color_hex)
        fg_rgb = hex_to_rgb(palette.get("fg", "#8fbf8f"))
        accent_color = (*accent_rgb, 255)
        glow_color = (*fg_rgb, 180)
        outline_color = (0, 0, 0, 255)

        # Fill logo shape with accent color
        green_fill = Image.new("RGBA", orig.size, (0, 0, 0, 0))
        fill_pixels = Image.new("RGBA", orig.size, accent_color)
        green_fill.paste(fill_pixels, mask=alpha)

        # Create dark outline (dilate alpha, subtract original)
        alpha_dilated = alpha.filter(ImageFilter.MaxFilter(5))
        arr_dilated = np.array(alpha_dilated)
        arr_orig = np.array(alpha)
        arr_outline = np.clip(
            arr_dilated.astype(int) - arr_orig.astype(int), 0, 255
        ).astype(np.uint8)
        outline_mask = Image.fromarray(arr_outline, mode="L")

        outline = Image.new("RGBA", orig.size, outline_color)
        outline_layer = Image.new("RGBA", orig.size, (0, 0, 0, 0))
        outline_layer.paste(outline, mask=outline_mask)

        # Create glow (blurred alpha, tinted with foreground color)
        glow_blur = alpha.filter(ImageFilter.GaussianBlur(4))
        glow_layer = Image.new("RGBA", orig.size, (0, 0, 0, 0))
        glow_pixels = Image.new("RGBA", orig.size, glow_color)
        glow_layer.paste(glow_pixels, mask=glow_blur)

        # Composite: glow → outline → fill
        result = Image.new("RGBA", orig.size, (0, 0, 0, 0))
        result = Image.alpha_composite(result, glow_layer)
        result = Image.alpha_composite(result, outline_layer)
        result = Image.alpha_composite(result, green_fill)

        # Save PNG — ATOMIC RENAME to avoid "empty file" window
        # Write to temp file, then os.replace() swaps it in atomically.
        # Windows guarantees os.replace() is atomic — readers see either old or new file,
        # never an empty/partial one.
        # Use .tmp.png suffix so Pillow recognizes the format, then rename to final name.
        if output_path is None:
            output_path = OUTPUT_PNG
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = output_path.with_suffix(".tmp" + output_path.suffix)
        result.save(tmp_path, format="PNG")
        os.replace(str(tmp_path), str(output_path))
        return output_path

    except (OSError, ValueError, RuntimeError, AttributeError) as e:
        logger.error(f"Failed to generate palette icon: {e}")
        return None


def generate_palette_ico(
    palette_id: str, output_path: Path | None = None
) -> Path | None:
    """Generate a palette-colored ICO file (multi-resolution).

    Args:
        palette_id: one of TERMINAL_PALETTES keys
        output_path: where to save ICO (default: shira.ico in project root)

    Returns:
        Path to generated ICO, or None on failure.
    """
    # First generate PNG
    png_path = generate_palette_icon(palette_id)
    if png_path is None or not png_path.exists():
        return None

    try:
        if output_path is None:
            output_path = OUTPUT_ICO

        img = Image.open(png_path).convert("RGBA")
        sizes = [
            (16, 16),
            (24, 24),
            (32, 32),
            (48, 48),
            (64, 64),
            (128, 128),
            (256, 256),
        ]
        # Save ICO — ATOMIC RENAME to avoid "empty file" window
        tmp_path = output_path.with_suffix(".tmp" + output_path.suffix)
        img.save(tmp_path, format="ICO", sizes=sizes)
        os.replace(str(tmp_path), str(output_path))
        return output_path

    except (OSError, ValueError, RuntimeError, AttributeError) as e:
        logger.error(f"Failed to generate palette ICO: {e}")
        try:
            if "tmp_path" in locals() and tmp_path.exists():
                tmp_path.unlink()
        except (OSError, ValueError):
            logger.debug("Failed to clean up temporary ICO file")
        return None


def generate_palette_ico_unique(palette_id: str) -> Path | None:
    """Generate a palette-colored ICO with UNIQUE filename per palette.

    Returns path to shira_<palette>.ico (e.g. shira_matrix.ico, shira_blood.ico).

    CRITICAL: Windows caches icons by file PATH, not by file content.
    When shira.ico is overwritten, Windows keeps showing the OLD cached icon
    because the path hasn't changed. The ONLY reliable way to force Windows
    to reload the icon is to use a DIFFERENT file path.

    By generating shira_<palette>.ico (unique per palette), each palette
    change creates a new file path → Windows MUST read the new icon.
    """
    png_path = generate_palette_icon(palette_id)
    if png_path is None or not png_path.exists():
        return None

    try:
        # Unique filename per palette: shira_matrix.ico, shira_blood.ico, etc.
        unique_ico = PROJECT_ROOT / f"shira_{palette_id}.ico"
        img = Image.open(png_path).convert("RGBA")
        sizes = [
            (16, 16),
            (24, 24),
            (32, 32),
            (48, 48),
            (64, 64),
            (128, 128),
            (256, 256),
        ]
        # Atomic rename
        tmp_path = unique_ico.with_suffix(".tmp.ico")
        img.save(tmp_path, format="ICO", sizes=sizes)
        os.replace(str(tmp_path), str(unique_ico))
        return unique_ico
    except (OSError, ValueError, RuntimeError, AttributeError) as e:
        logger.error(f"Failed to generate unique palette ICO: {e}")
        return None


def get_current_icon_path() -> Path:
    """Return path to the current icon PNG (generates matrix if missing)."""
    if not OUTPUT_PNG.exists():
        generate_palette_icon("matrix")
    return OUTPUT_PNG


if __name__ == "__main__":
    # Test: generate all palette icons
    logger.info("Generating test icons for all palettes:")
    for palette_id in TERMINAL_PALETTES:
        png = generate_palette_icon(palette_id)
        ico = generate_palette_ico(palette_id)
        if png and ico:
            logger.info(
                "%s: PNG=%s (%dB), ICO=%s (%dB)",
                palette_id,
                png.name,
                png.stat().st_size,
                ico.name,
                ico.stat().st_size,
            )
