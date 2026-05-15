# Color legend for designer mode.
# These hex values are the single source of truth shared with the frontend
# (client/src/app/designer/paint-canvas/paint-canvas.component.ts).
LEGEND: list[dict] = [
    {
        "hex": "#FF4FA8",
        "label": "Flowering planted beds / wildflowers",
        "short": "flowers",
    },
    {"hex": "#000000", "label": "Drivable road surface (asphalt)", "short": "road"},
    {"hex": "#37B24D", "label": "Grass / lawn", "short": "grass"},
    {"hex": "#7B4B23", "label": "Trees with full canopy", "short": "trees"},
    {"hex": "#1E88E5", "label": "Water feature (fountain or pond)", "short": "water"},
    {"hex": "#FFD60A", "label": "Seating / benches with people", "short": "seating"},
    {
        "hex": "#FFFFFF",
        "label": "Natural stone paving (cobblestone path)",
        "short": "stone",
    },
    {
        "hex": "#9E9E9E",
        "label": "Leave this area unchanged (keep original pixels)",
        "short": "keep",
    },
]


def _color_directives() -> str:
    lines = []
    for entry in LEGEND:
        if entry["short"] == "keep":
            lines.append(
                f'- {entry["hex"]} (gray): Do NOT modify this area — '
                "reproduce the original photo pixels here exactly as they are."
            )
        else:
            lines.append(f'- {entry["hex"]}: {entry["label"]}')
    return "\n".join(lines)


def build_designer_prompt() -> str:
    return f"""You are given two images:
- IMAGE 1: the original, unmodified street photo. Use this as the pixel-perfect source \
for any area that must be kept unchanged, and as the reference for all buildings, facades, \
camera angle, and perspective.
- IMAGE 2: the same street photo with opaque color annotations painted on top \
by the user. These colors are a zone-by-zone design plan — they are NOT part of the output.

YOUR TASK: Produce a photorealistic version of this street that follows the design plan \
in IMAGE 2. For each colored zone, replace it with the realistic content described in the \
legend below. For gray zones (#9E9E9E), copy those pixels exactly from IMAGE 1 unchanged. \
For unpainted areas, also copy from IMAGE 1.

The final output must look like a real photograph. No paint strokes, color tints, or \
artistic overlays may appear.

COLOR LEGEND:
{_color_directives()}

REMOVE (mandatory — zero exceptions):
- Remove every single motor vehicle from the entire image.
- Remove parking lanes, kerb markings, and road surface markings.
- There must be absolutely no vehicles of any kind visible in the output.
- Remove traffic signs.

STRICT RULES:
- Gray (#9E9E9E) zones: reproduce pixel-for-pixel from IMAGE 1 — do not modify these areas \
(except to remove any vehicles present there).
- All other colored zones: replace with photorealistic content matching the legend.
- No paint or color annotation may be visible in the output.
- Every building, facade, roofline, window, door, and shop sign must remain identical \
to IMAGE 1 — do not add, remove, or alter any architecture.
- Maintain the exact same camera angle and perspective as IMAGE 1.
- The total street corridor width from building facade to building facade must remain unchanged.

SEASON & LIGHT:
- Depict spring or summer; all trees in full leaf.
- Warm, sunny afternoon; blue sky; natural daylight.

MOOD: Warm, lively, and human-scaled — like a thriving European street on a sunny afternoon.

STYLE: Photorealistic, natural daylight, high detail, no HDR over-processing.

CRITICAL REMINDER: IMAGE 2 is the design plan only. The output must be a clean photorealistic \
street photograph based on IMAGE 1, transformed according to the color zones in IMAGE 2.
"""
