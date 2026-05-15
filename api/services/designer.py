# Color legend for designer mode.
# These hex values are the single source of truth shared with the frontend
# (client/src/app/designer/paint-canvas/paint-canvas.component.ts).
LEGEND: list[dict] = [
    {
        "hex": "#FF4FA8",
        "color_name": "hot pink",
        "label": "Flowering planted beds / wildflowers",
        "short": "flowers",
    },
    {
        "hex": "#000000",
        "color_name": "black",
        "label": "Drivable road surface (asphalt)",
        "short": "road",
    },
    {
        "hex": "#37B24D",
        "color_name": "green",
        "label": "Grass / lawn",
        "short": "grass",
    },
    {
        "hex": "#7B4B23",
        "color_name": "brown",
        "label": "Trees with full canopy",
        "short": "trees",
    },
    {
        "hex": "#1E88E5",
        "color_name": "blue",
        "label": "Water feature (fountain or pond)",
        "short": "water",
    },
    {
        "hex": "#FFD60A",
        "color_name": "yellow",
        "label": "Seating / benches with people",
        "short": "seating",
    },
    {
        "hex": "#FFFFFF",
        "color_name": "white",
        "label": "Natural stone paving (cobblestone path)",
        "short": "stone",
    },
    {
        "hex": "#9E9E9E",
        "color_name": "gray",
        "label": "Leave this area unchanged (keep original pixels)",
        "short": "keep",
    },
]


def _color_directives() -> str:
    lines = []
    for entry in LEGEND:
        name = entry["color_name"]
        hex_ = entry["hex"]
        if entry["short"] == "keep":
            lines.append(
                f"- {name} ({hex_}): Do NOT modify this area — "
                "reproduce the original photo pixels here exactly as they are."
            )
        else:
            lines.append(f"- {name} ({hex_}): {entry['label']}")
    return "\n".join(lines)


def _forbidden_colors() -> str:
    lines = []
    for entry in LEGEND:
        if entry["short"] in ("keep",):
            continue
        lines.append(
            f"- {entry['color_name'].capitalize()} ({entry['hex']}): must NEVER appear as a "
            f"flat colored patch — replace it with photorealistic {entry['label'].lower()}"
        )
    return "\n".join(lines)


def build_designer_prompt() -> str:
    return f"""You are given two images:
- IMAGE 1: the original, unmodified street photo. Use this as the pixel-perfect source \
for any area that must be kept unchanged, and as the reference for all buildings, facades, \
camera angle, and perspective.
- IMAGE 2: the same street photo with opaque color annotations painted on top \
by the user. These colors are a zone-by-zone design plan — they are zone codes, NOT colors \
to reproduce. They must never appear in your output.

YOUR TASK: Produce a photorealistic version of this street that follows the design plan \
in IMAGE 2. For each colored zone, replace it with the realistic content described in the \
legend below. For gray zones (#9E9E9E / gray), copy those pixels exactly from IMAGE 1 unchanged. \
For unpainted areas, also copy from IMAGE 1.

The final output must look like a real photograph taken with a camera. \
No paint strokes, color tints, flat-colored surfaces, or artistic overlays may appear.

COLOR LEGEND (zone codes → what to render):
{_color_directives()}

FORBIDDEN IN OUTPUT — the annotation colors from IMAGE 2 are zone codes only. \
They must never appear as flat surfaces in your output. \
Your output must be a photorealistic render derived from IMAGE 1, not a recoloring of IMAGE 2.

REMOVE (mandatory — zero exceptions):
- Remove every single motor vehicle from the entire image.
- Remove parking lanes, kerb markings, and road surface markings.
- There must be absolutely no vehicles of any kind visible in the output.
- Remove traffic signs.

STRICT RULES:
- Gray (#9E9E9E) zones: reproduce pixel-for-pixel from IMAGE 1 — do not modify these areas \
(except to remove any vehicles present there).
- All other colored zones: replace with photorealistic content matching the legend. \
The zone color itself must disappear entirely and be replaced by realistic texture and detail.
- No annotation color may be visible anywhere in the output — not as a tint, wash, \
overlay, or flat surface.
- Every building, facade, roofline, window, door, and shop sign must remain identical \
to IMAGE 1 — do not add, remove, or alter any architecture.
- Maintain the exact same camera angle and perspective as IMAGE 1.
- The total street corridor width from building facade to building facade must remain unchanged.

SEASON & LIGHT:
- Depict spring or summer; all trees in full leaf.
- Warm, sunny afternoon; blue sky; natural daylight.

MOOD: Warm, lively, and human-scaled — like a thriving European street on a sunny afternoon.

STYLE: Photorealistic, natural daylight, high detail, no HDR over-processing.

CRITICAL REMINDER: IMAGE 2 is a color-coded zone map — a plan, not a photo to edit. \
Each colored zone tells you WHAT to render there (see legend above), not WHAT COLOR to use. \
The output must be an entirely photorealistic street photograph. \
Any flat colored patch in the output is a failure.
"""
